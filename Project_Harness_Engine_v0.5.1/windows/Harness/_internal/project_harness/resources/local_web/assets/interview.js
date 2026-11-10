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
};
const fieldOptions = {
  'implementation.target_level':['PROTOTYPE','ALPHA','BETA','MVP','RELEASE','UNSURE'],
  'project.connectivity':['ONLINE_ONLY','LIMITED_OFFLINE','OFFLINE_FIRST','UNKNOWN'],
  'project.data.sensitivity':['PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED','SECRET','REGULATED','UNKNOWN'],
};
const displayLabels = {...fieldLabels,
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
    return fields.map(([,v])=>readable(v)).join(' · ') || 'Не заполнено';
  }
  return String(value);
}
function provenanceText(fact,view) {
  const kind=fact.provenance.kind;
  const source=(fact.provenance.source_refs||[]).map(ref=>ref==='INPUT'?'сохранённые сведения':view.documents.find(d=>d.document_ref===ref)?.source_relative_path).filter(Boolean);
  if(kind==='SOURCE_CHANGED_REVIEW_REQUIRED') return 'Предложено моделью. Документы изменились — этот ответ нужно пересмотреть.';
  if(kind==='GPT_DRAFT_UNVERIFIED') return 'Предложено моделью; требуется ваша оценка.'+(source.length?' Основание: '+source.join(', ')+'.':'');
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
function clearInterview() {
  interviewView = replyPreview = cliJobView = null; clearTimeout(cliPollTimer);
  answerInputs.clear();
  $('interview-body').classList.add('hidden');
  $('gpt-reply').value = '';
  $('import-preview').classList.add('hidden');
  $('reply-diff').replaceChildren(); text('preview-summary', '');
  $('repair-area').classList.add('hidden');
}
function answerField(field, container) {
  if (answerInputs.has(field) || !fieldLabels[field]) return;
  const value = getDraftField(field);
  const box = element('div', undefined, 'answer-field');
  const id = 'answer-' + field.replaceAll('.', '-');
  const label = element('label', fieldLabels[field]); label.htmlFor = id;
  let control;
  if (fieldOptions[field]) {
    control = element('select');
    for (const option of ['', ...fieldOptions[field]]) {
      const opt = element('option', valueLabels[option] || option || 'Ответ не выбран'); opt.value = option; control.append(opt);
    }
    control.value = value || '';
  } else {
    control = element('textarea'); control.rows = Array.isArray(value) ? 3 : 2;
    control.maxLength = 16000;
    control.value = Array.isArray(value) ? value.map(v => typeof v === 'string' ? v :
      v.question || v.statement || v.name || '').join('\n') : value || '';
  }
  control.id = id;
  box.append(label, control);
  if (Array.isArray(value)) box.append(element('small', 'Одна запись на строку. Изменение заменит этот список вашим ответом.', 'muted'));
  answerInputs.set(field, {control, initial: control.value, array: Array.isArray(value)});
  container.append(box);
}
function renderQuestions(view) {
  answerInputs.clear(); $('question-fields').replaceChildren();
  for (const q of view.questions) {
    if (q.status !== 'OPEN') continue;
    const box = element('section', undefined, 'question');
    box.append(element('h3', displayLabel(q.field)), element('p', 'Укажите, что вам известно. Неизвестное можно уточнить с помощью модели.', 'muted small'));
    if (q.field === 'project.documentation.availability') {
      box.append(element('p', 'Загрузите документы или выберите «Документации нет» во вкладке «Документы».'));
    } else {
      const fields = Object.keys(fieldLabels).filter(f => f === q.field || f.startsWith(q.field + '.'));
      for (const field of fields) answerField(field, box);
      if (!fields.length) box.append(element('p', 'Эту часть можно заполнить с помощью модели. Её предложения появятся в списке изменений перед сохранением.'));
    }
    $('question-fields').append(box);
  }
  const known = $('known-answers'); known.replaceChildren();
  const facts=view.known_answers.filter(f=>!templateFields.has(f.field) && displayLabels[f.field] && meaningful(f.value));
  if(!facts.length) known.append(element('p','Пока нет заполненных сведений о проекте. Служебные настройки шаблона здесь не показываются.','muted'));
  for (const fact of facts) {
    const row = element('div', undefined, 'known-answer');
    row.append(element('strong', displayLabel(fact.field)), element('pre', readable(fact.value), 'source-preview'),
      element('p',provenanceText(fact,view),'muted small'));
    if (fieldLabels[fact.field]) {
      const edit = element('button', 'Изменить ответ', 'quiet'); edit.type = 'button';
      edit.addEventListener('click', () => {
        answerField(fact.field, row); answerInputs.get(fact.field)?.control.focus(); edit.disabled = true;
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
    renderImportHistory(view.imports);
    // Reload restores the last pending preview from the server, not from a
    // secret-bearing browser store. No mutation or automatic recovery occurs.
    const pending = view.imports.filter(r => r.state === 'PREVIEW').at(-1);
    if (pending) renderReplyPreview(pending);
    else { replyPreview = null; $('import-preview').classList.add('hidden'); }
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
$('answers-form').addEventListener('submit', event => {
  event.preventDefault();
  interviewAction(async () => {
    const patch = {};
    for (const [field, item] of answerInputs) if (item.control.value !== item.initial) {
      const value = item.control.value.trim();
      patch[field] = item.array ? value.split('\n').map(v=>v.trim()).filter(Boolean) : value || null;
    }
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
  const jobMessage=cliJobView?.job_id?cliJobView.message_ru:'';
  text('cli-connection-status',connected?'Codex CLI подключён.':'Подключите установленный Codex CLI или выберите ручной пакет.');
  text('cli-analysis-status',jobMessage);
  $('cli-analysis-status').classList.toggle('hidden',!jobMessage);
  text('cli-connect-label',connected?'Подключено':'Подключить CLI');
  $('cli-connect-check').classList.toggle('hidden',!connected);
  $('cli-connect').classList.toggle('cli-connected',connected);
  $('cli-connect').title=connected?'Проверить подключение CLI':'Подключить установленный Codex CLI';
  $('cli-connection-help').classList.toggle('hidden',connected);
  if(connected) $('cli-connection-help').open=false;
  $('cli-connect').disabled=state.requestBusy || active;
  $('cli-analyze').disabled=state.requestBusy || active;
  $('cli-analysis-cancel').classList.toggle('hidden',!active);
  $('cli-analysis-cancel').disabled=state.requestBusy || cliJobView?.state==='CANCELLING';
  if(active) text('interview-next',cliJobView.message_ru);
  if(cliJobView?.state==='SUCCEEDED' && cliJobView.input_fingerprint===interviewView?.fingerprint)
    text('interview-next','Анализ CLI завершён. Посмотрите предложения на шаге 2 и оставшиеся вопросы на шаге 3.');
}
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
  if(!cliConnectionView?.connected) cliConnectionView=await api('/api/cli/connect',{method:'POST',body:{}});
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
  text('preview-summary',`Изменений: ${preview.diff.length}. Осталось вопросов: ${preview.questions.filter(q=>q.status==='OPEN').length}. Изменения ещё не сохранены.`);
  text('interview-preview-technical',format(preview));
  text('interview-next','Посмотрите предложения модели на шаге 2. Нажмите «Сохранить предложения», чтобы внести их в черновик проекта.');
  for (const row of preview.diff) {
    const box = element('section', undefined, 'diff-row');
    box.append(element('h4', displayLabel(row.field)), element('p', 'Текущий ответ'), element('pre', readable(row.before), 'source-preview'),
      element('p', 'Предложение модели'), element('pre', readable(row.after), 'source-preview'));
    $('reply-diff').append(box);
  }
  $('reply-diff').append(element('p', `Осталось вопросов: ${preview.questions.filter(q => q.status === 'OPEN').length}. ` +
    `Нужно уточнить: ${preview.readiness.missing_fields.map(displayLabel).join(', ') || 'нет'}.`));
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
  for (const item of imports) $('import-history').append(element('p', `Ответ модели №${imports.indexOf(item)+1}: ${{PREVIEW:'ожидает сохранения',COMMITTED:'сохранён',CANCELLED:'отклонён'}[item.state] || 'проверяется'}`, 'small body-value'));
}
