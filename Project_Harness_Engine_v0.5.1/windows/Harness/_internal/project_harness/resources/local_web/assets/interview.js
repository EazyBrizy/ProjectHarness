'use strict';
// Local typed inputs and explicit manual exchange. All untrusted content is text.
let interviewView = null;
let cliConnectionView = null, cliJobView = null, cliPollTimer = null;
let replyPreview = null;
const answerInputs = new Map();
const fieldLabels = {
  'project.problem_statement':'Проблема', 'project.primary_outcome':'Основной проверяемый результат',
  'implementation.target_level':'Целевой уровень', 'project.users':'Пользователи и их задачи',
  'project.scale.initial':'Первоначальный масштаб', 'project.scale.growth':'Ожидаемый рост',
  'project.connectivity':'Работа без интернета', 'project.platforms':'Платформы',
  'project.deployment.target':'Среда размещения', 'project.deployment.environment':'Условия размещения',
  'project.data.sensitivity':'Чувствительность данных', 'project.data.categories':'Категории данных',
  'project.data.storage':'Хранение данных', 'project.integrations':'Интеграции',
  'project.scope.in':'Входит в проект', 'project.scope.out':'Не входит в проект',
  'project.constraints.mandatory':'Обязательные ограничения', 'project.constraints.forbidden':'Запрещённые действия',
  'project.constraints.non_functional':'Нефункциональные требования',
  'project.success_criteria':'Критерии успеха', 'project.assumptions':'Предположения',
  'project.unknowns':'Вопросы, которые ещё нужно решить', 'architecture.summary':'Архитектурное предложение',
  'architecture.style':'Архитектурный стиль', 'architecture.components':'Основные компоненты',
  'profile.ref':'Профиль проекта', 'profile.rationale':'Почему выбран этот профиль',
  'technology.selections':'Технологии и версии',
};
const displayLabels = {...fieldLabels,
  'project.scope':'Границы проекта',
  'project.documentation.availability':'Наличие документации',
  'architecture':'Архитектура проекта','architecture.interfaces':'Связи между компонентами',
  'architecture.data_flow':'Движение данных','architecture.quality_attributes':'Требования к качеству',
  'architecture.decisions':'Архитектурные решения','architecture.risks':'Архитектурные риски',
  'technology':'Технологии проекта','technology.selections':'Выбор технологий',
  'technology.build_commands':'Сборка проекта','technology.test_commands':'Проверки проекта',
  'technology.lint_commands':'Проверка качества кода','planning.work_packages':'План работ',
  'skills.resolutions':'Служебные инструменты','implementation.claimed_current_level':'Текущая готовность проекта',
  'project.ambiguity_mode':'Способ работы с неопределённостью',
  'brownfield.baseline_summary':'Исходное состояние проекта','brownfield.known_defects':'Известные ошибки',
  'brownfield.known_gaps':'Недостающие возможности','brownfield.technical_debt':'Технический долг',
  'brownfield.documentation_conflicts':'Противоречия в документации'};
const valueLabels = {PROTOTYPE:'Прототип',ALPHA:'Альфа-версия',BETA:'Бета-версия',
  MVP:'Первая рабочая версия',RELEASE:'Готовый выпуск',UNSURE:'Нужно выбрать',UNKNOWN:'Не указано',
  PUBLIC:'Общедоступные',INTERNAL:'Внутренние',CONFIDENTIAL:'Конфиденциальные',
  RESTRICTED:'С ограниченным доступом',SECRET:'Секретные',REGULATED:'Регулируемые',
  ONLINE_ONLY:'Только с интернетом',LIMITED_OFFLINE:'Часть функций без интернета',OFFLINE_FIRST:'Основная работа без интернета'};
const templateFields = new Set(['implementation.claimed_current_level','project.ambiguity_mode','skills.resolutions','profile.ref']);
const propertyLabels = {name:'Название',need:'Задача пользователя',statement:'Критерий',verification:'Как проверить',
  area:'Назначение',technology:'Технология',version_constraint:'Версия или диапазон версий',
  responsibility:'За что отвечает',question:'Вопрос',decision_plan:'Когда и как решить',owner:'Кто решает',
  blocking:'Обязателен для текущего этапа',description:'Описание',rationale:'Обоснование',
  in:'Входит в проект',out:'Не входит в проект',initial:'Первоначальный масштаб',growth:'Рост',
  summary:'Описание',components:'Компоненты',interfaces:'Связи',data_flow:'Движение данных',
  mandatory:'Обязательно',forbidden:'Запрещено',non_functional:'Требования к качеству',
  target:'Среда',environment:'Условия',categories:'Категории',storage:'Хранение',sensitivity:'Чувствительность'};
function displayLabel(field) { return displayLabels[field] || Object.entries(displayLabels).find(([key]) => field.startsWith(key+'.'))?.[1] || 'Дополнительные сведения о проекте'; }
function meaningful(value) {
  if(value===null || value===undefined || value==='' || ['UNKNOWN','UNSURE','NONE'].includes(value)) return false;
  if(Array.isArray(value)) return value.some(meaningful);
  if(typeof value==='object') return Object.values(value).some(meaningful);
  return true;
}
function readable(value) {
  if(value===null || value===undefined || value==='') return 'Не заполнено';
  if(typeof value==='string') return valueLabels[value] || value;
  if(typeof value==='boolean') return value?'Да':'Нет';
  if(Array.isArray(value)) return value.length?value.map(readable).join('\n'):'Не заполнено';
  if(typeof value==='object') {
    const fields=Object.entries(value).filter(([key,v])=>!['id','revision','ref','schema_ref','skill_ref'].includes(key) && meaningful(v));
    return fields.map(([k,v])=>(propertyLabels[k] || displayLabels[k] || k)+': '+readable(v)).join('\n') || 'Не заполнено';
  }
  return String(value);
}
function provenanceText(fact,view) {
  const kind=fact.provenance.kind;
  const source=(fact.provenance.source_refs||[]).map(ref=>ref==='INPUT'?'сохранённые сведения':view.documents.find(d=>d.document_ref===ref||d.source_ref===ref)?.source_relative_path).filter(Boolean);
  if(kind==='SOURCE_CHANGED_REVIEW_REQUIRED') return 'Предложено моделью. Документы изменились — этот ответ нужно пересмотреть.';
  if(kind==='GPT_DRAFT_UNVERIFIED') return 'Предложено моделью; требуется ваша оценка.'+(source.length?' Основание: '+source.join(', ')+'.':'');
  if(kind==='USER_ANSWER')return 'Выбрано или введено пользователем. Это решение в черновике проекта.';
  return 'Сохранено в черновике проекта. Это ещё не результат анализа документов.';
}
function interviewPath(suffix = '') { return `/api/projects/${encodeURIComponent(state.activeProject)}${suffix}`; }
function element(tag, content, cls) {
  const item = document.createElement(tag);
  if (content !== undefined) item.textContent = String(content);
  if (cls) item.className = cls;
  return item;
}
function getDraftField(field) { return field.split('.').reduce((obj, key) => obj[key], interviewView.draft); }
function appendValue(parent,value) {
  if(Array.isArray(value)) {
    if(!value.length) {parent.append(element('p','Не заполнено','muted'));return;}
    const list=element('ul');for(const item of value) {const li=element('li');appendValue(li,item);list.append(li);}parent.append(list);
  } else if(value && typeof value==='object') {
    const dl=element('dl',undefined,'analysis-structured');
    for(const [key,item] of Object.entries(value)) {
      if(['id','revision','ref','schema_ref','skill_ref','source_refs'].includes(key))continue;
      const dd=element('dd');appendValue(dd,item);dl.append(element('dt',propertyLabels[key]||key),dd);
    }parent.append(dl);
  } else parent.append(element('p',readable(value),'analysis-text'));
}
function sourceLine(refs) {
  const names=(refs||[]).map(ref=>ref==='INPUT'?'сохранённые сведения':interviewView?.documents.find(d=>d.document_ref===ref||d.source_ref===ref)?.source_relative_path).filter(Boolean);
  return element('p',names.length?'Основание: '+[...new Set(names)].join(', '):'Предложение модели без ссылки на документ.','analysis-source');
}
function analysisQuestion(q,parent,actionable=false) {
  const row=element('section',undefined,'question');
  row.append(element('h4',questionText(q.question,q.field)),element('p',q.why,'analysis-text'),
    element('p',q.stage==='FUTURE'?'Решение будущего этапа; сейчас не блокирует работу.':q.blocking?'Нужно решить для текущего этапа.':'Можно уточнить в ходе текущего этапа.','muted small'),sourceLine(q.source_refs));
  renderDecisionOptions(q,row,actionable);
  parent.append(row);
}
function renderDecisionOptions(q,parent,actionable) {
  if(!q.choices?.length) {
    parent.append(element('p','Этот анализ создан без готовых вариантов. Повторите анализ документов, чтобы получить рекомендации.','muted small'));return;
  }
  const grid=element('div',undefined,'decision-options');
  for(const choice of q.choices) {
    const card=element('section',undefined,'decision-option');
    if(choice.id===q.recommended_choice_id){card.classList.add('decision-recommended');card.append(element('strong','Рекомендуется','decision-badge'));}
    card.append(element('h4',choice.title),element('p',choice.description,'analysis-text'));
    if(choice.tradeoffs.length){const list=element('ul');for(const note of choice.tradeoffs)list.append(element('li',note));card.append(list);}
    card.append(element('p',choice.resolves_question?'Выбор отвечает на этот вопрос.':'Сохраняется подход. Вопрос останется открытым до получения данных.','muted small'));
    if(choice.changes.length){const effects=element('details');effects.append(element('summary','Какие сведения изменятся'));
      for(const change of choice.changes){effects.append(element('strong',(change.operation==='APPEND'?'Добавить: ':'Задать: ')+displayLabel(change.field)));appendValue(effects,change.value);}card.append(effects);}
    if(actionable){const button=element('button','Выбрать этот вариант',choice.id===q.recommended_choice_id?'document-primary':'outline');button.type='button';
      button.addEventListener('click',()=>interviewAction(()=>saveQuestionAnswer(q,{choice_id:choice.id,answer_text:'',custom_value:null,has_custom_value:false})));card.append(button);}
    grid.append(card);
  }
  parent.append(grid,element('p','Почему рекомендуется: '+q.recommendation_reason,'decision-reason'));
  if(!actionable)parent.append(element('p','Выбор будет доступен на шаге 3 после сохранения предложений анализа.','muted small'));
  const selected=interviewView?.user_answers?.findLast(a=>a.question===q.question && a.field===q.field);
  if(actionable && selected)parent.append(element('p',(selected.superseded_fields?.length?'Связанные сведения изменены. Ранее выбран подход: ':'Сохранён подход: ')+selected.title+'. '+selected.answer,'decision-selected'));
  if(actionable)renderCustomAnswer(q,parent);
}
function renderCustomAnswer(q,parent) {
  const details=element('details',undefined,'custom-decision');details.append(element('summary','Свой вариант'));
  const textInput=element('textarea');textInput.rows=3;textInput.maxLength=4000;textInput.id='custom-answer-'+q.id;
  const label=element('label','Ваш ответ');label.htmlFor=textInput.id;details.append(label,textInput);
  const advanced=element('details');advanced.append(element('summary','Изменить сведения проекта в форме'));
  const holder=element('div',undefined,'answer-field');let read=null,initial;
  const schema=fieldEditorSchema(q.field);
  if(schema && !['project.unknowns','planning.work_packages','skills.resolutions'].includes(q.field)) {
    const value=getDraftField(q.field);initial=JSON.stringify(value);read=typedEditor(value,holder,schema);advanced.append(holder);details.append(advanced);
  }
  const button=element('button','Сохранить свой ответ','outline');button.type='button';
  button.addEventListener('click',()=>interviewAction(async()=>{
    const value=read?read():null,changed=Boolean(read && JSON.stringify(value)!==initial);
    const answer=textInput.value.trim()||(changed?readable(value):'');
    if(!answer)throw new Error('Введите свой ответ или заполните сведения в форме.');
    await saveQuestionAnswer(q,{choice_id:null,answer_text:answer,custom_value:changed?value:null,has_custom_value:changed});
  }));details.append(button);parent.append(details);
}
async function saveQuestionAnswer(q,answer) {
  const result=await api(interviewPath('/interview/answers'),{method:'POST',body:{
    analysis_import_id:interviewView.analysis_import_id,question_id:q.id,...answer,
    expected_fingerprint:interviewView.fingerprint,idempotency_key:newIdempotencyKey()}});
  await selectProject(state.activeProject,true);
  showNotice(result.user_answer?.resolves_question?'Ответ сохранён. Вопрос решён.':'Подход сохранён. Вопрос остаётся открытым до получения данных.','success');
}
function questionText(value,field) {
  return field==='implementation.target_level'?value.replace(/\b(PROTOTYPE|ALPHA|BETA|MVP|RELEASE|UNSURE)\b/g,key=>valueLabels[key]):value;
}
function renderAnalysis(analysis,parent,includeQuestions=true) {
  if(!analysis)return;
  parent.append(element('h3','Что описано в документации'),element('p',analysis.summary,'analysis-text'));
  if(analysis.source_changed)parent.append(element('p','Документы изменились после этого анализа. Повторите анализ перед использованием выводов.','notice error'));
  const stage=element('section',undefined,'analysis-stage');
  stage.append(element('h3','Ближайший этап: '+analysis.current_stage.title),element('p',analysis.current_stage.goal,'analysis-text'),
    element('p',analysis.current_stage.basis,'muted'),sourceLine(analysis.current_stage.source_refs));parent.append(stage);
  for(const answer of analysis.answers) {
    const row=element('section',undefined,'known-answer');
    row.append(element('h4',answer.title),element('p',{DOCUMENTED:'Описано в документации',PROPOSED:'Предложение, ещё не принято',CONFLICT:'В документах есть противоречие'}[answer.status],'muted small'),
      element('p',answer.answer,'analysis-text'),sourceLine(answer.source_refs));parent.append(row);
  }
  parent.append(element('h3','План из документации','analysis-heading'),element('p','Это последовательность работ из источников. Формальный план выполнения в Harness оформляется отдельно.','muted small'));
  if(!analysis.roadmap.length)parent.append(element('p','План работ в документации не описан. Этапы и задачи не добавлены автоматически.','muted'));
  for(const scope of ['CURRENT','FUTURE']) {
    const stages=analysis.roadmap.filter(s=>s.stage===scope);if(!stages.length)continue;
    const section=scope==='FUTURE'?element('details'):element('section');
    section.append(element(scope==='FUTURE'?'summary':'h4',scope==='CURRENT'?'Что делать сейчас':'Будущие этапы'));
    const grid=element('div',undefined,'analysis-roadmap');
    for(const item of stages) {
      const row=element('section',undefined,'question');row.append(element('h4',item.title),element('p',item.goal,'analysis-text'));
      const steps=element('ol');for(const step of item.steps)steps.append(element('li',step));row.append(steps);
      if(item.done_when.length){row.append(element('strong','Этап готов, когда:'));const done=element('ul');for(const criterion of item.done_when)done.append(element('li',criterion));row.append(done);}
      row.append(sourceLine(item.source_refs));grid.append(row);
    }section.append(grid);parent.append(section);
  }
  for(const scope of includeQuestions?['CURRENT','FUTURE']:[]) {
    const questions=analysis.questions.filter(q=>q.stage===scope);if(!questions.length)continue;
    const group=scope==='FUTURE'?element('details'):element('section');
    group.append(element(scope==='FUTURE'?'summary':'h3',scope==='CURRENT'?`Решения текущего этапа (${questions.length})`:`Вопросы будущих этапов (${questions.length})`));
    for(const q of questions)analysisQuestion(q,group);parent.append(group);
  }
  if(includeQuestions && !analysis.questions.some(q=>q.stage==='CURRENT'))parent.append(element('p','Модель не обнаружила дополнительных вопросов, блокирующих ближайший этап. Формальная готовность проверяется отдельно.','muted'));
  if(analysis.notes.length){const notes=element('details');notes.append(element('summary','Пояснения аналитика'));for(const note of analysis.notes)notes.append(element('p',note,'analysis-text'));parent.append(notes);}
}
function clearInterview() {
  interviewView = replyPreview = cliJobView = null; clearTimeout(cliPollTimer);
  answerInputs.clear();
  $('interview-body').classList.add('hidden');
  $('gpt-reply').value = '';
  $('import-preview').classList.add('hidden');
  $('reply-diff').replaceChildren(); text('preview-summary', '');
  $('saved-analysis').replaceChildren();
  $('repair-area').classList.add('hidden');
}
function resolveEditorSchema(node) {
  for(let depth=0;node?.$ref && depth<24;depth++) {
    if(!node.$ref.startsWith('#/'))return {};
    node=node.$ref.slice(2).split('/').reduce((item,key)=>item?.[key],interviewView.editor_schema);
  }return node||{};
}
function schemaType(node) {return Array.isArray(node.type)?node.type.find(t=>t!=='null'):node.type;}
function chooseEditorSchema(node,value) {
  node=resolveEditorSchema(node);
  const variants=(node.oneOf||node.anyOf||[]).map(resolveEditorSchema);
  if(!variants.length)return node;
  const type=Array.isArray(value)?'array':value===null||value===undefined?null:typeof value==='object'?'object':typeof value;
  return variants.find(v=>schemaType(v)===type)||variants.find(v=>schemaType(v)==='object')||variants[0];
}
function fieldEditorSchema(field) {
  if(!interviewView?.mutable_fields.includes(field))return null;
  let node=interviewView.editor_schema;
  for(const key of field.split('.'))node=resolveEditorSchema(node)?.properties?.[key];
  return node?resolveEditorSchema(node):null;
}
function emptyEditorValue(schema) {
  const node=chooseEditorSchema(schema,undefined),type=schemaType(node);
  if(type==='object') {
    const entries=Object.entries(node.properties||{}).filter(([key,child])=>(node.required||[]).includes(key)||resolveEditorSchema(child).type?.includes?.('null'));
    return Object.fromEntries(entries.map(([key,child])=>[key,resolveEditorSchema(child).type?.includes?.('null')?null:emptyEditorValue(child)]));
  }
  if(type==='array')return [];
  // Empty means unanswered, never the first enum item or a project default.
  if(node.enum?.includes(null)||Array.isArray(node.type)&&node.type.includes('null'))return null;
  if(type==='boolean'||type==='number'||type==='integer')return null;
  return '';
}
function typedEditor(value,container,schema) {
  const node=chooseEditorSchema(schema,value),type=schemaType(node);
  if(type==='array'||Array.isArray(value)) {
    const rows=[];let changed=false;
    const list=element('div');container.append(list);
    function add(item) {
      const row=element('div',undefined,'typed-row');const read=typedEditor(item,row,node.items||{});
      const record={read,removed:false};rows.push(record);
      const remove=element('button','Удалить запись','quiet');remove.type='button';
      remove.addEventListener('click',()=>{changed=true;record.removed=true;row.remove();});row.append(remove);list.append(row);
    }
    for(const item of value||[])add(item);
    const button=element('button','Добавить запись','outline');button.type='button';
    button.addEventListener('click',()=>{changed=true;add(emptyEditorValue(node.items||{}));});container.append(button);
    return ()=>value===null&&!changed?null:rows.filter(r=>!r.removed).map(r=>r.read());
  }
  if(type==='object'||value && typeof value==='object') {
    const getters={};
    const initialObject=value||emptyEditorValue(node);
    for(const [key,item] of Object.entries(initialObject)) {
      if(['id','ref','source_refs'].includes(key) && meaningful(item)) {getters[key]=()=>item;continue;}
      const row=element('div'),label=element('label',propertyLabels[key]||key);row.append(label);
      getters[key]=typedEditor(item,row,node.properties?.[key]||{});container.append(row);
      const input=row.querySelector(':scope > textarea,:scope > select');
      if(input){input.id='draft-control-'+(++editorControlIndex);label.htmlFor=input.id;}
    }
    return ()=>{
      const result=Object.fromEntries(Object.entries(getters).map(([key,get])=>[key,get()]));
      return value===null&&JSON.stringify(result)===JSON.stringify(initialObject)?null:result;
    };
  }
  const choices=node.enum||((type==='boolean'||typeof value==='boolean')?[true,false]:null);
  const input=element(choices?'select':'textarea');
  if(choices) {
    const empty=element('option','Ответ не выбран');empty.value='';input.append(empty);
    for(const item of choices.filter(v=>v!==null)) {const option=element('option',typeof item==='boolean'?item?'Да':'Нет':valueLabels[item]||item);option.value=String(item);input.append(option);}
    input.value=value===null||value===undefined?'':String(value);
  } else {input.rows=2;input.maxLength=node.maxLength||16000;input.value=value??'';}
  const initial=input.value;
  container.append(input);
  return ()=>{
    if(input.value===initial)return value;
    if(choices)return choices.find(v=>String(v)===input.value)??null;
    if(type==='number'||type==='integer') {
      if(input.value.trim()==='')return null;
      const number=Number(input.value);
      if(!Number.isFinite(number)||type==='integer'&&!Number.isInteger(number))throw new Error('Введите корректное число в числовом поле.');
      return number;
    }
    return input.value.trim()||((node.type||[]).includes('null')?null:'');
  };
}
let editorControlIndex=0;
function answerField(field, container) {
  if(answerInputs.has(field))return;
  const schema=fieldEditorSchema(field);if(!schema)return;
  const value = getDraftField(field);
  const box = element('div', undefined, 'answer-field');
  const id = 'answer-' + field.replaceAll('.', '-');
  const label=element('label',fieldLabels[field]||displayLabel(field));box.append(label);
  const read=typedEditor(value,box,schema),control=box.querySelector(':scope > textarea,:scope > select');
  if(control){control.id=id;label.htmlFor=id;}
  answerInputs.set(field,{read,initial:JSON.stringify(value),typed:true});container.append(box);
}
function renderQuestions(view) {
  answerInputs.clear(); $('question-fields').replaceChildren();
  const analysis=view.analysis;
  if(view.user_answers?.length) {
    const answers=element('details');answers.append(element('summary',`Выбранные ответы и подходы (${view.user_answers.length})`));
    for(const answer of view.user_answers){const row=element('section',undefined,'known-answer');row.append(element('strong',answer.question),
      element('p',answer.title+': '+answer.answer,'analysis-text'),element('p',answer.source_changed?'Документы изменились — ответ стоит пересмотреть.':answer.superseded_fields?.length?'После ответа сведения изменены. Приоритет имеет текущий черновик.':answer.resolves_question?'Ответ сохранён.':'Подход выбран; данные ещё нужно уточнить.','muted small'));answers.append(row);}
    $('question-fields').append(answers);
  }
  if(analysis && !analysis.source_changed) {
    for(const q of analysis.questions.filter(q=>q.stage==='CURRENT')) {
      const row=element('section',undefined,'question');
      row.append(element('h3',questionText(q.question,q.field)),element('p',q.why,'muted small'),sourceLine(q.source_refs));
      if(q.choices?.length){renderDecisionOptions(q,row,true);$('question-fields').append(row);continue;}
      row.append(element('p','Для готовых вариантов повторите анализ документов. Пока можно заполнить ответ самостоятельно.','muted small'));
      if(q.field!=='project.unknowns')answerField(q.field,row);
      const resolve=element('button','Сохранить ответ и отметить вопрос решённым','outline');resolve.type='button';
      resolve.addEventListener('click',()=>interviewAction(async()=>{
        const patch=collectAnswerPatch();
        patch['project.unknowns']=view.draft.project.unknowns.filter(u=>(typeof u==='string'?u:u.question)!==q.question);
        await runInterviewOperation('update-draft',{patch,expected_input_digest:view.input_revision});
      }));row.append(resolve);$('question-fields').append(row);
    }
    const future=analysis.questions.filter(q=>q.stage==='FUTURE');
    if(future.length){const details=element('details');details.append(element('summary',`Вопросы будущих этапов (${future.length})`));for(const q of future)analysisQuestion(q,details,true);$('question-fields').append(details);}
  }
  const seen=new Set();
  const formal=analysis?element('details'):null;
  if(formal)formal.append(element('summary','Что ещё нужно заполнить для запуска проекта в Harness'),
    element('p','Это требования формальной подготовки Harness. Они отделены от вопросов ближайшего этапа и плана из документов.','muted small'));
  for (const q of view.questions) {
    if (q.status !== 'OPEN') continue;
    if(seen.has(q.field))continue;seen.add(q.field);
    const box = element('section', undefined, 'question');
    box.append(element('h3', displayLabel(q.field)), element('p',q.text || 'Уточните сведения для этой части проекта.','analysis-text'));
    if(q.why_asked)box.append(element('p',q.why_asked,'muted small'));
    if (q.field === 'project.documentation.availability') {
      box.append(element('p', 'Загрузите документы или выберите «Документации нет» во вкладке «Документы».'));
    } else {
      const fields = Object.keys(fieldLabels).filter(f => f === q.field || f.startsWith(q.field + '.'));
      for (const field of fields) answerField(field, box);
      if (!fields.length) box.append(element('p', 'Эту часть можно заполнить с помощью модели. Её предложения появятся в списке изменений перед сохранением.'));
    }
    (formal||$('question-fields')).append(box);
  }
  if(formal && formal.querySelector('.question'))$('question-fields').append(formal);
  const known = $('known-answers'); known.replaceChildren();
  const facts=view.known_answers.filter(f=>!templateFields.has(f.field) && displayLabels[f.field] && meaningful(f.value));
  if(!facts.length) known.append(element('p','Пока нет заполненных сведений о проекте. Служебные настройки шаблона здесь не показываются.','muted'));
  for (const fact of facts) {
    const row = element('div', undefined, 'known-answer');
    row.append(element('strong', displayLabel(fact.field)), element('pre', readable(fact.value), 'source-preview'),
      element('p',provenanceText(fact,view),'muted small'));
    if (fieldEditorSchema(fact.field)) {
      const edit = element('button', 'Изменить ответ', 'quiet'); edit.type = 'button';
      edit.addEventListener('click', () => {
        answerField(fact.field, row); row.querySelector('textarea,select')?.focus(); edit.disabled = true;
      }); row.append(edit);
    }
    known.append(row);
  }
}
async function loadInterview() {
  if (!state.activeProject || state.view?.kind !== 'workspace') {
    clearInterview(); text('interview-status', 'Выберите подготовку проекта во вкладке «Проекты» или создайте её во вкладке «Документы».'); return;
  }
  const pid = state.activeProject;
  text('interview-status', 'Загружаем сведения и вопросы…');
  try {
    const view = await api(interviewPath('/interview'));
    if (pid !== state.activeProject) return;
    interviewView = view;
    $('interview-body').classList.remove('hidden');
    const freshPack=view.exports.some(x=>x.binding.fingerprint===view.fingerprint);
    const applied=view.imports.some(x=>x.state==='COMMITTED');
    text('interview-status',view.recovery_required?'Сохранение ответа было прервано':
      !applied && view.documents.length ? freshPack?'Пакет подготовлен. Ожидается ответ модели.':'Документы загружены и готовы к анализу.':
      view.readiness.status==='WAITING_DECISION'?'Нужно выбрать целевой уровень проекта.':
      view.readiness.missing_fields.length?'Есть вопросы для уточнения.':'Основные сведения о проекте заполнены.');
    text('interview-next',view.recovery_required?'Нажмите «Восстановить сохранение ответа».':
      freshPack?'Документы подготовлены. Выберите анализ через CLI или скачайте ZIP кнопкой «Сформировать пакет вручную».':
      !applied && view.documents.length?'Выберите способ: автоматический анализ через CLI или пакет для ручной передачи модели.':
      view.readiness.missing_fields.length?'Подготовьте пакет для модели или уточните сведения на шаге 3.':
      'Сведения заполнены. Для продолжения откройте раздел «Согласования».');
    if(view.approval_rework_requests?.length) text('interview-next','Нужна доработка: '+view.approval_rework_requests.map(r=>r.comment).join('; '));
    const documents=$('interview-documents');documents.replaceChildren();
    if(view.documents.length) {
      const list=element('details'),summary=element('summary',`Загружено документов: ${view.documents.length}`),files=element('ul');
      for(const doc of view.documents) files.append(element('li',doc.source_relative_path));
      list.append(summary,files);documents.append(list);
    } else documents.append(element('p',view.documentation_choice==='NONE'?'Вы указали, что документации нет.':'Документация пока не загружена.'));
    text('interview-readiness',format({readiness:view.readiness,source_revision:view.source_revision,input_revision:view.input_revision,
      fingerprint:view.fingerprint,documents:view.documents,known_answers:view.known_answers,exports:view.exports,imports:view.imports}));
    $('recover-reply').classList.toggle('hidden', !view.recovery_required);
    renderQuestions(view);
    $('saved-analysis').replaceChildren();
    if(view.analysis)renderAnalysis(view.analysis,$('saved-analysis'),false);
    renderImportHistory(view.imports);
    // Reload restores the last pending preview from the server, not from a
    // secret-bearing browser store. No mutation or automatic recovery occurs.
    const pending = view.imports.filter(r => r.state === 'PREVIEW' && r.binding.fingerprint===view.fingerprint).at(-1);
    if (pending) renderReplyPreview(pending);
    else { replyPreview = null; $('import-preview').classList.add('hidden'); }
    $('answers-form').classList.toggle('hidden',Boolean(pending));
    $('check-answers').classList.toggle('hidden',Boolean(pending));
    text('questions-help',pending?'Сначала сохраните предложения на шаге 2. Затем здесь появятся только оставшиеся вопросы по сохранённым сведениям.':'Ответьте на вопросы текущего этапа. Будущие решения можно отложить.');
    await loadCliState();
  } catch (error) { text('interview-status', error.message); }
}
async function interviewAction(work) {
  if (!interviewView || state.requestBusy) return;
  state.requestBusy = true;
  for (const control of $('interview-panel').querySelectorAll('button,input,textarea,select')) control.disabled = true;
  try { await work(); }
  catch (error) {
    if (error.result?.repair_prompt) {
      $('repair-area').classList.remove('hidden'); text('repair-prompt', error.result.repair_prompt);
      $('import-preview').classList.add('hidden'); replyPreview = null;
    }
    showNotice(error.message + ' Перечитайте состояние перед новой попыткой.', 'error');
  } finally {
    state.requestBusy = false;
    for (const control of $('interview-panel').querySelectorAll('button,input,textarea,select')) control.disabled = false;
    renderCliState();
  }
}
async function runInterviewOperation(action, payload) {
  const pid = state.activeProject;
  const result = await api(interviewPath('/operations'), {method:'POST', body:{action, payload,
    expected_fingerprint:interviewView.fingerprint, idempotency_key:newIdempotencyKey()}});
  for (let i = 0; i < 120; i++) {
    const response = await api(`/api/projects/${encodeURIComponent(pid)}/operations/${encodeURIComponent(result.operation_id)}`);
    if (terminalStates.has(response.operation.state)) {
      if (response.operation.state !== 'SUCCEEDED') throw new Error(response.operation.error?.message_ru || response.operation.state);
      await selectProject(pid,true);
      showNotice('Ответы проверены и сохранены. Можно продолжить работу с проектом.', 'success'); return;
    }
    await new Promise(resolve => setTimeout(resolve, 400));
  }
  showNotice(`Операция ${result.operation_id} ещё выполняется. Обновите состояние; повтор автоматически не выполняется.`);
}
function collectAnswerPatch() {
  const patch={};
  for(const [field,item] of answerInputs) {
    if(item.typed) {const value=item.read();if(JSON.stringify(value)!==item.initial)patch[field]=value;}
    else if(item.control.value!==item.initial) {
      const value=item.control.value.trim();patch[field]=item.array?value.split('\n').map(v=>v.trim()).filter(Boolean):value||null;
    }
  }return patch;
}
$('answers-form').addEventListener('submit', event => {
  event.preventDefault();
  interviewAction(async () => {
    const patch = collectAnswerPatch();
    if (!Object.keys(patch).length) { showNotice('Изменённых ответов нет.'); return; }
    await runInterviewOperation('update-draft', {patch, expected_input_digest:interviewView.input_revision});
  });
});
$('check-answers').addEventListener('click', () => interviewAction(() => runInterviewOperation('check-intake', {})));
$('interview-documents-link').addEventListener('click', () => selectScreen('documents'));
$('recover-reply').addEventListener('click', () => interviewAction(async () => {
  const result = await api(interviewPath('/gpt/replies/recover'), {method:'POST',body:{confirm:true}});
  showNotice(`Состояние сохранения обновлено.`, 'success'); await loadInterview();
}));
function renderCliState() {
  const active=['QUEUED','RUNNING','VALIDATING','CANCELLING'].includes(cliJobView?.state);
  const connected=Boolean(cliConnectionView?.connected);
  const selection=cliConnectionView?.selection;
  const jobSelection=cliJobView?.selection;
  const jobMessage=cliJobView?.job_id?cliJobView.message_ru+(jobSelection?` Модель запуска: ${jobSelection.model}; рассуждение: ${effortLabel(jobSelection.reasoning_effort)}.`:' Модель старого запуска не была сохранена.') :'';
  text('cli-connection-status',connected?'Codex CLI подключён.':'Подключите установленный Codex CLI или выберите ручной пакет.');
  text('cli-analysis-status',jobMessage);
  $('cli-analysis-status').classList.toggle('hidden',!jobMessage);
  text('cli-connect-label',connected?'Подключено':'Подключить CLI');
  $('cli-connect-check').classList.toggle('hidden',!connected);
  $('cli-connect').classList.toggle('cli-connected',connected);
  $('cli-connect').title=connected?'Проверить подключение CLI':'Подключить установленный Codex CLI';
  $('cli-connection-help').classList.toggle('hidden',connected);
  $('cli-model-settings').classList.toggle('hidden',!connected || !selection);
  if(selection) {
    const models=cliConnectionView.models;
    $('cli-model').replaceChildren();
    for(const m of models){const option=element('option',m.name+' ('+m.id+')');option.value=m.id;$('cli-model').append(option);}
    $('cli-model').value=selection.model;renderEfforts(selection.model,selection.reasoning_effort);
    text('cli-model-status',`Для следующего запуска: ${selection.model}; рассуждение: ${effortLabel(selection.reasoning_effort)}. Настройки сохраняются автоматически.`);
  } else text('cli-model-status',connected?'Нажмите «Подключено», чтобы получить список моделей и выбрать модель анализа.':'После подключения здесь появится выбор модели.');
  if(connected) $('cli-connection-help').open=false;
  $('cli-connect').disabled=state.requestBusy || active;
  $('cli-analyze').disabled=state.requestBusy || active;
  $('cli-analysis-cancel').classList.toggle('hidden',!active);
  $('cli-analysis-cancel').disabled=state.requestBusy || cliJobView?.state==='CANCELLING';
  $('cli-model').disabled=$('cli-effort').disabled=state.requestBusy||active;
  if(active) {text('interview-status','Документы анализируются.');text('interview-next',cliJobView.message_ru);}
  else if(replyPreview) {
    text('interview-status','Анализ получен. Предложения ещё не сохранены.');
    text('interview-next','Посмотрите ответы и план на шаге 2. Нажмите «Сохранить предложения», чтобы внести их в черновик.');
  } else if(interviewView?.analysis) {
    text('interview-status','Результат анализа сохранён в черновике.');
    text('interview-next',interviewView.analysis.source_changed?'Документы изменились. Запустите анализ заново.':'Ответы и план показаны на шаге 2. Решения текущего этапа — на шаге 3.');
  }
}
function effortLabel(value) {return {minimal:'Минимальная',low:'Низкая',medium:'Средняя',high:'Высокая',xhigh:'Очень высокая',max:'Максимальная'}[value]||value;}
function renderEfforts(model,selected) {
  const item=cliConnectionView.models.find(m=>m.id===model);$('cli-effort').replaceChildren();
  for(const value of item.efforts){const option=element('option',effortLabel(value));option.value=value;$('cli-effort').append(option);}
  $('cli-effort').value=item.efforts.includes(selected)?selected:item.default_effort;
}
async function saveCliModel(model,effort) {
  cliConnectionView=await api('/api/cli/model',{method:'POST',body:{model,reasoning_effort:effort}});renderCliState();
}
$('cli-model').addEventListener('change',()=>{
  const model=$('cli-model').value;renderEfforts(model,$('cli-effort').value);const effort=$('cli-effort').value;
  interviewAction(()=>saveCliModel(model,effort));
});
$('cli-effort').addEventListener('change',()=>{const model=$('cli-model').value,effort=$('cli-effort').value;interviewAction(()=>saveCliModel(model,effort));});
async function loadCliState() {
  clearTimeout(cliPollTimer);
  const pid=state.activeProject;
  try {
    const connection=await api('/api/cli');
    const job=await api(interviewPath('/cli/analysis'));
    if(pid!==state.activeProject)return;
    cliConnectionView=connection;cliJobView=job;renderCliState();scheduleCliPoll(pid);
  } catch(error) {text('cli-connection-status',error.message);}
}
function scheduleCliPoll(pid) {
  clearTimeout(cliPollTimer);
  if(['QUEUED','RUNNING','VALIDATING','CANCELLING'].includes(cliJobView?.state))
    cliPollTimer=setTimeout(()=>pollCliAnalysis(pid),1200);
}
async function pollCliAnalysis(pid) {
  if(pid!==state.activeProject || state.screen!=='interview')return;
  try {
    const job=await api(interviewPath('/cli/analysis'));
    if(pid!==state.activeProject)return;
    cliJobView=job;renderCliState();
    if(job.state==='SUCCEEDED') {await loadInterview();showNotice(job.message_ru,'success');}
    else if(['FAILED','INTERRUPTED'].includes(job.state)) {
      showNotice(job.message_ru,'error');
      if(job.repair_prompt){$('repair-area').classList.remove('hidden');text('repair-prompt',job.repair_prompt);}
    } else scheduleCliPoll(pid);
  } catch(error) {text('cli-analysis-status',error.message+' Обновите состояние, чтобы продолжить чтение результата.');}
}
$('cli-connect').addEventListener('click',()=>interviewAction(async()=>{
  cliConnectionView=null;
  cliConnectionView=await api('/api/cli/connect',{method:'POST',body:{}});
  renderCliState();showNotice('Codex CLI подключён. Можно запускать анализ документов.','success');
}));
$('cli-analyze').addEventListener('click',()=>interviewAction(async()=>{
  if(!cliConnectionView?.connected || !cliConnectionView?.selection) cliConnectionView=await api('/api/cli/connect',{method:'POST',body:{}});
  cliJobView=await api(interviewPath('/cli/analysis'),{method:'POST',body:{
    expected_fingerprint:interviewView.fingerprint,idempotency_key:newIdempotencyKey()}});
  renderCliState();scheduleCliPoll(state.activeProject);
  showNotice('Анализ запущен. Результат появится в этой вкладке.','success');
}));
$('cli-analysis-cancel').addEventListener('click',()=>interviewAction(async()=>{
  if(!cliJobView?.job_id)return;
  cliJobView=await api(interviewPath('/cli/analysis/'+encodeURIComponent(cliJobView.job_id)+'/cancel'),{method:'POST',body:{}});
  renderCliState();scheduleCliPoll(state.activeProject);
}));
$('review-export').addEventListener('click',()=>interviewAction(async()=>{
  const pid=state.activeProject;
  const result=await api(interviewPath('/analysis/package'),{method:'POST',body:{
    expected_fingerprint:interviewView.fingerprint,idempotency_key:newIdempotencyKey()}});
  const archive=await api(`/api/projects/${encodeURIComponent(pid)}/gpt/exports/${encodeURIComponent(result.exchange_id)}/archive.zip`,{responseType:'blob'});
  const url=URL.createObjectURL(archive),link=element('a');
  link.href=url;link.download='harness-analysis.zip';document.body.append(link);
  try {link.click();} finally {link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  await loadInterview();
  text('interview-next','Передайте скачанный ZIP-архив ChatGPT или Codex. Полученный JSON-ответ вставьте на шаге 2.');
  showNotice('ZIP-архив подготовлен, скачивание началось. Прикрепите его к ChatGPT или Codex.','success');
}));
async function explicitCopy(value) {
  try { await navigator.clipboard.writeText(value); showNotice('Инструкция для модели скопирована.', 'success'); }
  catch (_) { showNotice('Не удалось скопировать автоматически. Выделите инструкцию и скопируйте её вручную.', 'error'); }
}
$('preview-reply').addEventListener('click', () => interviewAction(async () => {
  $('repair-area').classList.add('hidden');
  $('import-preview').classList.add('hidden'); replyPreview = null;
  text('preview-summary', 'Проверяем новый ответ…');
  const result = await api(interviewPath('/gpt/replies/preview'), {method:'POST', body:{
    text:$('gpt-reply').value, expected_fingerprint:interviewView.fingerprint}});
  if (result.status === 'REPLAYED') {
    showNotice('Этот ответ уже сохранён. Повторное сохранение не требуется.', 'success'); await loadInterview(); return;
  }
  renderReplyPreview(result.preview); showNotice('Изменения показаны ниже. Сведения проекта ещё не изменены.', 'success');
}));
function renderReplyPreview(preview) {
  replyPreview = preview;
  $('import-preview').classList.remove('hidden'); $('reply-diff').replaceChildren();
  const current=preview.analysis?.questions.filter(q=>q.stage==='CURRENT').length;
  text('preview-summary',`Предложения ещё не сохранены. ${current===undefined?'Этот результат создан прежним форматом анализа. Повторите анализ, чтобы получить ответы, план и вопросы без дублей.':`Решений текущего этапа: ${current}.`}`);
  text('interview-preview-technical',format(preview));
  text('interview-next','Посмотрите предложения модели на шаге 2. Нажмите «Сохранить предложения», чтобы внести их в черновик проекта.');
  if(preview.analysis)renderAnalysis(preview.analysis,$('reply-diff'));
  const changes=element('details');changes.append(element('summary',`Изменения сведений проекта (${preview.diff.length})`));
  for (const row of preview.diff) {
    const box = element('section', undefined, 'diff-row');
    box.append(element('h4', displayLabel(row.field)),element('p','Предложение модели'));appendValue(box,row.after);
    box.append(sourceLine(preview.claims?.find(c=>c.field===row.field)?.source_refs));
    const before=element('details');before.append(element('summary','До анализа'));appendValue(before,row.before);box.append(before);changes.append(box);
  }
  $('reply-diff').append(changes);
  const formal=element('details');formal.append(element('summary','Что ещё требуется для формального плана Harness'),
    element('p',`Нужно уточнить: ${preview.readiness.missing_fields.map(displayLabel).join(', ') || 'нет'}. Отдельные согласования выполняются в разделе «Согласования».`));$('reply-diff').append(formal);
  $('answers-form').classList.add('hidden');$('check-answers').classList.add('hidden');
  text('questions-help','Сначала сохраните предложения на шаге 2. Затем здесь появятся оставшиеся вопросы.');
}
$('commit-reply').addEventListener('click', () => interviewAction(async () => {
  if (!replyPreview) return;
  await api(interviewPath(`/gpt/replies/${replyPreview.import_id}/commit`), {method:'POST',body:{
    preview_digest:replyPreview.preview_digest, expected_fingerprint:replyPreview.binding.fingerprint}});
  $('gpt-reply').value=''; await loadInterview(); showNotice('Предложения сохранены в черновике. Посмотрите оставшиеся вопросы.', 'success');
}));
$('cancel-reply').addEventListener('click', () => interviewAction(async () => {
  if (!replyPreview) return;
  await api(interviewPath(`/gpt/replies/${replyPreview.import_id}/cancel`), {method:'POST',body:{preview_digest:replyPreview.preview_digest}});
  await loadInterview(); showNotice('Предложения отклонены. Сведения проекта не изменились.', 'success');
}));
$('copy-repair').addEventListener('click', () => explicitCopy($('repair-prompt').textContent));
function renderImportHistory(imports) {
  $('import-history').replaceChildren();
  for (const item of imports) $('import-history').append(element('p', `${item.user_answer?'Ответ пользователя':'Ответ модели'} №${imports.indexOf(item)+1}: ${{PREVIEW:'ожидает сохранения',COMMITTED:'сохранён',CANCELLED:'отклонён'}[item.state] || 'проверяется'}`, 'small body-value'));
}
