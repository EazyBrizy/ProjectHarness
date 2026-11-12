"""Document-analysis v3 projection, separate from executable Stage planning.

Only one question channel. Source refs and existing unresolved user questions
are retained; future decisions do not become current-stage blockers.
"""
from copy import deepcopy
import re
import unicodedata

from .local_web_exchange_contract import ExchangeError


def text_key(text):
    # Preserve identifiers, units, mathematical symbols and significant case:
    # C/C++/C#, MB/Mb, file paths and versions are different project decisions.
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip().rstrip('?？').rstrip()


def normalize_analysis(reply, original, refs, fields):
    analysis = deepcopy(reply['analysis'])
    questions = []
    by_id, by_text = {}, {}
    existing = original['project']['unknowns']
    covered = set()
    for item in reply['questions']:
        item = deepcopy(item)
        index = item.get('existing_unknown_index')
        if reply['envelope_version'] >= 4:
            if index is None:
                index = next((i for i, u in enumerate(existing) if text_key(u if isinstance(u, str) else u['question']) == text_key(item['question'])), None)
            if index is not None:
                if type(index) is not int or not 0 <= index < len(existing):
                    raise ExchangeError('QUESTION_BINDING_INVALID', 'Вопрос ссылается на отсутствующую неопределённость.')
                old = existing[index]
                item['question'] = old if isinstance(old, str) else old['question']
                old_blocking = not isinstance(old, dict) or old.get('blocking') is not False
                if item['blocking'] != old_blocking:
                    raise ExchangeError('QUESTION_SCOPE_CONFLICT', 'Анализ не может менять обязательность существующего вопроса без решения пользователя.')
                covered.add(index)
            item['existing_unknown_index'] = index
        if item['field'] not in fields:
            raise ExchangeError('QUESTION_FIELD_INVALID', 'Вопрос ссылается на неизвестное поле черновика.')
        if item['stage'] == 'FUTURE' and item['blocking']:
            raise ExchangeError('QUESTION_SCOPE_INVALID', 'Вопрос будущего этапа не может блокировать текущий этап.')
        key = text_key(item['question'])
        if not key or index is None and not unicodedata.normalize('NFKC', item['question']).rstrip().endswith('?'):
            raise ExchangeError('QUESTION_REQUIRED', 'В questions нужны вопросы, а не комментарии или отчёты о проверках.')
        prior = by_id.get(item['id']) or by_text.get(key)
        if prior:
            if any(prior[k] != item[k] for k in ('field', 'stage', 'blocking')):
                raise ExchangeError('QUESTION_SCOPE_CONFLICT', 'Повторяющийся вопрос имеет противоречивый этап или обязательность.')
            if reply['envelope_version'] >= 4 and any(prior.get(k) != item.get(k) for k in ('choices','recommended_choice_id','recommendation_reason','existing_unknown_index')):
                raise ExchangeError('CHOICE_SET_CONFLICT', 'Дублирующийся вопрос содержит разные варианты решения.')
            prior['source_refs'] = list(dict.fromkeys(prior['source_refs'] + item['source_refs']))
            by_id[item['id']] = prior
            by_text[key] = prior
            continue
        value = deepcopy(item)
        questions.append(value)
        by_id[item['id']] = by_text[key] = value
    analysis['questions'] = questions
    if reply['envelope_version'] >= 4 and covered != set(range(len(existing))):
        raise ExchangeError('QUESTION_COVERAGE_REQUIRED', 'Для каждого существующего открытого вопроса нужны варианты решения с existing_unknown_index.')
    def check(item):
        if isinstance(item, dict):
            for key, value in item.items():
                if key == 'source_refs' and any(ref not in refs for ref in value):
                    raise ExchangeError('SOURCE_REF_UNKNOWN', 'Анализ ссылается на источник вне exact export inventory.')
                check(value)
        elif isinstance(item, list):
            for value in item:
                check(value)
    check(analysis)
    if reply['project_input_draft']['project']['unknowns'] != original['project']['unknowns']:
        raise ExchangeError('SINGLE_QUESTION_CHANNEL', 'Новые вопросы передаются только в questions; project.unknowns скопируйте из пакета.')
    # Existing user-authored uncertainty is never silently removed by an
    # external analysis. It remains until an explicit draft edit resolves it.
    unknowns = deepcopy(original['project']['unknowns'])
    known = {text_key(u if isinstance(u, str) else u['question']) for u in unknowns}
    for item in questions:
        if text_key(item['question']) not in known:
            unknowns.append({'question': item['question'], 'blocking': item['blocking'],
                'decision_plan': ('Текущий этап. ' if item['stage'] == 'CURRENT' else 'Будущий этап. ') + item['why']})
            known.add(text_key(item['question']))
    return analysis, unknowns


def question_projection(questions, analysis):
    """Suppress generic copies of the same field, keep actual core gaps."""
    if not analysis:
        return questions
    declared = analysis['questions']
    texts = {text_key(q['question']) for q in declared}
    covered = {q['field'] for q in declared if q['stage'] == 'CURRENT'}
    projected = []
    for q in questions:
        if text_key(q.get('text', '')) in texts:
            continue
        if q['field'] in covered:
            continue
        projected.append(q)
    return projected
