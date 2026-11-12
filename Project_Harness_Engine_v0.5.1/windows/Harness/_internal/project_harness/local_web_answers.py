"""Validated decision suggestions and explicit user answers, never execution."""
from copy import deepcopy

from .errors import ValidationFailure
from .local_web_drafts import DRAFT_FIELDS, preview_draft_update
from .local_web_exchange_contract import (ExchangeError, KEY, digest, draft_patch, get_field,
    set_field, unapproved, schema_errors, semantic_errors)
from .project_input import load_project_input_schema, _validate_schema_node, validate_project_input, questions_for
from .serialization import load_data, pretty_json
from .platform_fs import _native_io_path
from .operation_guard import project_operation_guard
from .util import utc_now

CHOICE_FIELDS = DRAFT_FIELDS - {'project.unknowns', 'planning.work_packages', 'skills.resolutions'}


def field_schema(field):
    schema = load_project_input_schema()
    node = schema
    for key in field.split('.'):
        while '$ref' in node:
            node = schema['$defs'][node['$ref'].split('/')[-1]]
        node = node.get('properties', {}).get(key, {})
    while '$ref' in node:
        node = schema['$defs'][node['$ref'].split('/')[-1]]
    return node, schema


def apply_changes(base, changes):
    candidate = unapproved(base)
    seen = set()
    for change in changes:
        field, operation, value = change['field'], change['operation'], change['value']
        if field not in CHOICE_FIELDS or field in seen or operation not in {'SET','APPEND'}:
            raise ExchangeError('CHOICE_FIELD_INVALID', 'Вариант содержит повторное или запрещённое поле.')
        seen.add(field)
        node, schema = field_schema(field)
        if operation == 'APPEND':
            current = get_field(candidate, field)
            if not isinstance(current, list) or not isinstance(value, list) or not value or node.get('type') != 'array':
                raise ExchangeError('CHOICE_VALUE_INVALID', 'APPEND добавляет непустой список записей в существующий список.')
            issues = [i for item in value for i in _validate_schema_node(item, node['items'], schema)]
            combined = deepcopy(current)
            for item in value:
                if item not in combined:
                    combined.append(deepcopy(item))
            set_field(candidate, field, combined)
        else:
            issues = _validate_schema_node(value, node, schema)
            set_field(candidate, field, value)
        if issues:
            raise ExchangeError('CHOICE_VALUE_INVALID', 'Значение варианта не соответствует схеме поля.', schema_errors(issues))
    draft_patch(unapproved(base), candidate, allow_target_choice=True)
    validation = validate_project_input(candidate, require_approvals=False)
    if validation['errors']:
        raise ExchangeError('CHOICE_VALUE_INVALID', 'Вариант нарушает правила черновика.', semantic_errors(candidate, validation['errors']))
    return candidate


def validate_choices(analysis, candidate):
    bases = {}
    for question in analysis['questions']:
        choices = question['choices']
        ids = [c['id'] for c in choices]
        if len(set(ids)) != len(ids) or question['recommended_choice_id'] not in ids:
            raise ExchangeError('CHOICE_RECOMMENDATION_INVALID', 'Нужны разные ID вариантов и рекомендация из этого списка.')
        if len({c['title'].strip() for c in choices}) != len(choices):
            raise ExchangeError('CHOICES_DISTINCT_REQUIRED', 'Варианты должны иметь разные понятные названия.')
        bases[question['id']] = {}
        for choice in choices:
            proposed = apply_changes(candidate, choice['changes'])
            node, _ = field_schema(question['field'])
            if choice['resolves_question'] and node.get('enum') and get_field(proposed, question['field']) in (None,'UNKNOWN','UNSURE'):
                raise ExchangeError('CHOICE_VALUE_INVALID', 'Вариант не закрывает вопрос выбора: каноническое значение осталось неизвестным.')
            for change in choice['changes']:
                bases[question['id']][change['field']] = digest(get_field(candidate, change['field']))
    return bases


def answer_views(records, state, current_draft):
    latest = {}
    for record in sorted((r for r in records if r['state']=='COMMITTED' and r.get('user_answer')), key=lambda r:r['commit_sequence']):
        answer = deepcopy(record['user_answer'])
        superseded=[]
        for change in record.get('answer_changes',[]):
            current=get_field(current_draft,change['field'])
            if (change['operation']=='SET' and digest(current)!=record['field_digests'].get(change['field'])
                or change['operation']=='APPEND' and (not isinstance(current,list) or any(v not in current for v in change['value']))):
                superseded.append(change['field'])
        answer.update(import_id=record['import_id'], committed_at=record['committed_at'],
            source_changed=record['binding']['source_revision'] != state['revision'],superseded_fields=superseded)
        latest[(answer['field'],answer['question_id'])] = answer
    return list(latest.values())


def answer_question(service, pid, *, analysis_import_id, question_id, choice_id,
                    answer_text, custom_value, has_custom_value, expected_fingerprint, idempotency_key):
    from .local_web_exchange import (_root, _records, _import, _save, _room, _private_directory,
        _binding, _check_current, _check_prepared, assert_no_pending_exchange, commit_reply, _import_view)
    if (not isinstance(idempotency_key,str) or not KEY.fullmatch(idempotency_key)
        or not isinstance(question_id,str) or not isinstance(answer_text,str) or len(answer_text)>4000
        or type(has_custom_value) is not bool or choice_id is not None and not isinstance(choice_id,str)):
        raise ExchangeError('ANSWER_INVALID', 'Выберите вариант или введите свой ответ.')
    root, imports, store = _root(service,pid)
    request = {'analysis_import_id':analysis_import_id,'question_id':question_id,'choice_id':choice_id,
        'answer_text':answer_text,'custom_value':custom_value,'has_custom_value':has_custom_value,
        'expected_fingerprint':expected_fingerprint}
    request_digest = digest(request)
    import_id = 'LWI-'+digest([pid,'USER_ANSWER',idempotency_key]).split(':')[1][:32].upper()
    path = store/'imports'/(import_id+'.json')
    with project_operation_guard(root):
        if _native_io_path(path).exists():
            prior = _import(store,import_id,pid)
            if prior.get('answer_request_digest') != request_digest:
                raise ExchangeError('ANSWER_REPLAY_CONFLICT','Этот ключ уже связан с другим ответом.')
            if prior['state']=='COMMITTED':
                return _import_view(prior)
            # Retry the same durable user intent through existing recovery boundary.
            return commit_reply(service,pid,import_id,preview_digest=prior['preview_digest'],expected_fingerprint=expected_fingerprint)
        assert_no_pending_exchange(root)
        _check_prepared(service,pid)
        records = _records(store,'LWI-')
        analyses = sorted((r for r in records if r['state']=='COMMITTED' and r.get('analysis')),key=lambda r:r['commit_sequence'])
        if not analyses or analyses[-1]['import_id'] != analysis_import_id:
            raise ExchangeError('ANSWER_STALE','Анализ или ответы изменились. Обновите состояние.')
        record = analyses[-1]
        current_binding = _binding(service,root,imports)
        if current_binding['fingerprint'] != expected_fingerprint:
            raise ExchangeError('STALE_EXCHANGE','Форма ответа устарела. Обновите состояние.')
        if any(current_binding[k] != record['binding'][k] for k in ('source_revision','source_snapshot_ref','source_inventory_sha256')):
            raise ExchangeError('STALE_EXCHANGE','Документы изменились. Повторите анализ перед выбором варианта.')
        original = load_data(root/'PROJECT_INPUT.yaml')
        question = next((q for q in record['analysis']['questions'] if q['id']==question_id),None)
        if not question or not any((u if isinstance(u,str) else u['question'])==question['question'] for u in original['project']['unknowns']):
            raise ExchangeError('ANSWER_NOT_OPEN','Этот вопрос уже решён или отсутствует в текущем анализе.')
        origin = record.get('analysis_origin_import_id',record['import_id'])
        if choice_id is not None:
            if answer_text or has_custom_value or custom_value is not None:
                raise ExchangeError('ANSWER_INVALID','Выбор готового варианта не принимает подменённые значения.')
            choice = next((c for c in question.get('choices',[]) if c['id']==choice_id),None)
            if not choice:
                raise ExchangeError('CHOICE_UNKNOWN','Такого варианта нет в этом вопросе.')
            changes = choice['changes']
            for change in changes:
                if change['operation']!='SET':continue
                field = change['field']
                allowed = {record.get('option_bases',{}).get(question_id,{}).get(field)}
                for prior in records:
                    answer = prior.get('user_answer',{})
                    if prior['state']=='COMMITTED' and answer.get('question_id')==question_id and answer.get('analysis_origin_import_id')==origin:
                        allowed.add(prior.get('field_digests',{}).get(field))
                if digest(get_field(original,field)) not in allowed:
                    raise ExchangeError('CHOICE_STALE','Связанные сведения уже изменены. Обновите анализ или используйте свой вариант.')
            answer_text, resolves, title = choice['answer'],choice['resolves_question'],choice['title']
        else:
            answer_text = answer_text.strip()
            if not answer_text:
                raise ExchangeError('ANSWER_REQUIRED','Введите свой ответ или заполните сведения в форме.')
            changes = [{'field':question['field'],'operation':'SET','value':custom_value}] if has_custom_value else []
            node,_ = field_schema(question['field'])
            node_types=node.get('type',[])
            if not changes and (node_types=='string' or isinstance(node_types,list) and 'string' in node_types):
                changes=[{'field':question['field'],'operation':'SET','value':answer_text}]
            elif not changes and node.get('type')=='array' and node.get('items',{}).get('type')=='string':
                changes=[{'field':question['field'],'operation':'APPEND','value':[answer_text]}]
            resolves,title = True,'Свой вариант'
        candidate = apply_changes(original,changes)
        node,_ = field_schema(question['field'])
        if resolves and node.get('enum') and get_field(candidate,question['field']) in (None,'UNKNOWN','UNSURE'):
            raise ExchangeError('ANSWER_VALUE_REQUIRED','Для этого ответа выберите значение поля в форме.')
        unknowns=[]
        for item in original['project']['unknowns']:
            if (item if isinstance(item,str) else item['question'])!=question['question']:
                unknowns.append(deepcopy(item))
            elif not resolves:
                value={'question':item,'blocking':True} if isinstance(item,str) else deepcopy(item)
                value['decision_plan']=answer_text;unknowns.append(value)
        patch={change['field']:get_field(candidate,change['field']) for change in changes}
        patch['project.unknowns']=unknowns
        proposal=preview_draft_update(root,patch,expected_input_digest=current_binding['input_revision'])
        user_answer={'question_id':question_id,'question':question['question'],'field':question['field'],
            'choice_id':choice_id,'title':title,'answer':answer_text,'resolves_question':resolves,
            'analysis_origin_import_id':origin,'kind':'SELECTED_OPTION' if choice_id else 'CUSTOM_ANSWER'}
        value={'project_ref':pid,'exchange_id':record['exchange_id'],'import_id':import_id,'record_kind':'USER_ANSWER',
            'preview_revision':len(records)+1,'response_digest':request_digest,'answer_request_digest':request_digest,
            'state':'PREVIEW','binding':current_binding,'patch':patch,'after_digest':proposal['after_digest'],
            'field_digests':{f:digest(get_field(proposal['candidate'],f)) for f in patch},
            'claims':[{'field':f,'source_refs':['INPUT']} for f in patch],
            'diff':[{'field':f,'before':get_field(original,f),'after':get_field(proposal['candidate'],f)} for f in sorted(patch)],
            'analysis':deepcopy(record['analysis']),'analysis_origin_import_id':origin,
            'option_bases':deepcopy(record.get('option_bases',{})),'user_answer':user_answer,'answer_changes':deepcopy(changes),
            'readiness':validate_project_input(proposal['candidate'],require_approvals=True),'questions':questions_for(proposal['candidate']),
            'approvals_invalidated':proposal['approvals_invalidated'],
            'approval_invalidation_receipt':{'reason':'USER_ANSWER','before_input_revision':proposal['before_digest'],
                'after_input_revision':proposal['after_digest'],'subjects':[k for k,v in original['approvals'].items() if v['approved'] and proposal['changed']]},
            'created_at':utc_now(),'committed_at':None}
        value['preview_digest']=digest({k:value[k] for k in ('response_digest','binding','diff','after_digest','approval_invalidation_receipt')})
        if len(records)>=128:raise ExchangeError('EXCHANGE_COUNT_LIMIT','Достигнут лимит записей ответов.')
        _room(store,len(pretty_json(value).encode('utf-8')));_private_directory(store);_private_directory(store/'imports')
        _save(path,value)
        return commit_reply(service,pid,import_id,preview_digest=value['preview_digest'],expected_fingerprint=expected_fingerprint)
