'use strict';
// PH-LW-04. No telemetry, external URLs, dynamic HTML or provider integration.
const state = { connected: false, projects: [], activeProject: null, view: null, screen: 'projects', requestBusy: false };
const $ = (id) => document.getElementById(id);
const terminalStates = new Set(['SUCCEEDED', 'FAILED', 'BLOCKED', 'CANCELLED', 'INTERRUPTED']);
const screenLabels = {
  projects: ['Проекты', 'Загрузите MD/ZIP документов или выберите «Документации нет». Можно продолжить существующий проект.'],
  documents: ['Документы', 'Приём MD/ZIP в приватный snapshot; анализ и согласования отдельно.'],
  interview: ['Опрос и GPT', 'Уточните существенные пробелы, подготовьте пакет и вручную импортируйте черновик внешнего GPT.'],
  approvals: ['Согласования', 'Проверьте содержание каждого решения, подтвердите отдельно или верните на доработку.'],
  overview: ['Обзор проекта', 'Актуальная стадия, целевой уровень, ограничения и следующий шаг из canonical core.'],
  tasks: ['Задачи и Run', 'Exact JIT → результат внешнего агента → независимая проверка → завершение Task.'],
  gates: ['Стадии и доказательства', 'Stage Gate, exact semantic evidence, reviewed plan и последовательный level-up.'],
  maintenance: ['Обслуживание', 'Same-level maintenance, read-only Brownfield assessment и explicit migration.'],
  diagnostics: ['Диагностика', 'Здесь показаны core-status и причины отключения действий; automatic execution остаётся NO-GO.']
};
const actionLabels = {
  'check-intake': 'Проверить опрос', 'prepare': 'Подготовить handoff',
  'next': 'Открыть текущую задачу', 'validate-project': 'Проверить проект',
  'verify': 'Проверить текущий Run', 'update-draft': 'Редактировать черновик'
};
const uiAllowed = new Set(['check-intake', 'next', 'validate-project', 'verify']);

function showNotice(message, category = '') {
  const el = $('notice');
  el.textContent = String(message);
  el.className = 'notice' + (category ? ' ' + category : '');
}
function text(id, value) {
  $(id).textContent = value === null || value === undefined || value === '' ? '—' : String(value);
}
function format(value) {
  if (value === null || value === undefined || (Array.isArray(value) && !value.length)) return 'Нет';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}
let apiRequests = Promise.resolve();
async function api(path, options = {}) {
  const method = options.method || 'GET';
  if (method !== 'GET' && path !== '/api/ui/resume') await resumeWrites;
  // One tab must not contend with its own reads (including the project list).
  // Keep the original binding/consent and never replay a mutation.
  const previous = apiRequests;
  let release;
  apiRequests = new Promise(resolve => { release = resolve; });
  await previous;
  try { return await requestApi(path, options); }
  finally { release(); }
}
async function requestApi(path, options = {}) {
  const method = options.method || 'GET';
  // Navigation saves share the app-data fence with operation admission.
  // Finish our own earlier save before a user mutation; never replay a POST.
  const headers = { Accept: 'application/json' };
  if (method !== 'GET') {
    if (!options.formData) headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(path, { method, headers, credentials: 'omit',
                                        cache: 'no-store', body: options.formData || (options.body ? JSON.stringify(options.body) : undefined) });
  let result;
  try { result = await response.json(); }
  catch (_error) { throw new Error('Сервер вернул неизвестный формат.'); }
  if (!response.ok) {
    const info = result.error || {};
    // A reload can overlap the previous page's still-running GET. Retry only
    // a bounded read on the explicit fence conflict; POST is never replayed.
    const readAttempt = options.readAttempt || 0;
    if (method === 'GET' && info.code === 'OPERATION_CONFLICT' && readAttempt < 12) {
      await new Promise(resolve => setTimeout(resolve, 250));
      return requestApi(path, {...options, readAttempt: readAttempt + 1});
    }
    const error = new Error(info.message_ru || 'Действие не выполнено.');
    error.result = result;
    throw error;
  }
  return result;
}
function selectScreen(screen) {
  if (!screenLabels[screen]) return;
  state.screen = screen;
  try { sessionStorage.setItem('harness-screen', screen); } catch (_) { /* optional UI preference */ }
  text('screen-title', screenLabels[screen][0]);
  text('screen-description', screenLabels[screen][1]);
  $('documents-panel').classList.toggle('hidden', screen !== 'documents');
  $('interview-panel').classList.toggle('hidden', screen !== 'interview');
  $('approvals-panel').classList.toggle('hidden', screen !== 'approvals');
  $('tasks-panel').classList.toggle('hidden', screen !== 'tasks');
  $('lifecycle-panel').classList.toggle('hidden', !['gates','maintenance'].includes(screen));
  $('project-layout').classList.toggle('hidden', ['documents', 'interview', 'approvals','tasks'].includes(screen));
  if (screen === 'documents') loadSources();
  if (screen === 'interview') loadInterview();
  if (screen === 'approvals') loadApprovals();
  if (screen === 'tasks') loadTasks();
  if (['gates','maintenance'].includes(screen)) loadLifecycle();
  for (const button of document.querySelectorAll('[data-screen]')) {
    const active = button.dataset.screen === screen;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
}
function renderProjects() {
  const list = $('project-list');
  list.replaceChildren();
  text('project-count', `${state.projects.length} шт.`);
  if (!state.projects.length) {
    const msg = document.createElement('p');
    msg.className = 'muted';
    msg.textContent = 'Проектов пока нет. Создайте подготовку ниже и загрузите MD/ZIP, либо выберите «Документации нет».';
    list.append(msg);
    return;
  }
  for (const entry of state.projects) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'project-button';
    button.setAttribute('aria-pressed', String(entry.project_id === state.activeProject));
    const name = document.createElement('strong');
    name.textContent = entry.project_id;
    const info = document.createElement('span');
    info.textContent = `${entry.kind === 'workspace' ? 'Подготовка' : 'Проект'} · ${entry.core_status}`;
    button.append(name, info);
    button.addEventListener('click', async () => { await selectProject(entry.project_id); rememberSelection(); });
    list.append(button);
  }
}
function renderActions(actions) {
  const root = $('action-list');
  root.replaceChildren();
  for (const item of actions) {
    if (item.action === 'get-status') continue;
    const row = document.createElement('div');
    row.className = 'action-row';
    const button = document.createElement('button');
    button.className = 'action-button';
    button.type = 'button';
    button.textContent = actionLabels[item.action] || item.action;
    const usable = item.enabled === true && uiAllowed.has(item.action);
    button.disabled = !usable || state.requestBusy;
    const explanation = document.createElement('small');
    explanation.textContent = usable ? 'Требуется явное подтверждение; статус перепроверяется сервером.' :
      (item.disabled_reason || 'В текущем интерфейсе эта операция недоступна.');
    if (!usable && item.enabled) explanation.textContent = 'Используйте соответствующую отдельную форму проекта.';
    if (item.action === 'prepare') {
      explanation.textContent = state.view?.kind === 'workspace' ?
        'Подтвердите новую папку в форме подготовки после отдельных согласований.' : 'Project Instance уже опубликован.';
      button.disabled = state.requestBusy || state.view?.kind !== 'workspace';
      button.addEventListener('click', () => selectScreen('approvals'));
    }
    if (item.action === 'stage-status' && state.view?.kind === 'project') {
      button.disabled = state.requestBusy || !item.enabled;
      explanation.textContent = 'Открыть текущее состояние стадий и evidence.';
      button.addEventListener('click', () => selectScreen('gates'));
    } else if (['verify','complete','block','resume','receive-result','manual-evidence','next'].includes(item.action) && state.view?.kind === 'project') {
      button.disabled = state.requestBusy;
      explanation.textContent = item.disabled_reason || 'Откройте отдельную форму Task/Run.';
      button.addEventListener('click', () => selectScreen('tasks'));
    } else if (typeof lifecycleLabels !== 'undefined' && lifecycleLabels[item.action]) {
      button.disabled=state.requestBusy||!item.enabled;button.textContent=lifecycleLabels[item.action];
      explanation.textContent=item.disabled_reason||'Открыть форму с exact refs и отдельным подтверждением.';
      button.addEventListener('click',()=>selectScreen('gates'));
    } else if (usable) button.addEventListener('click', () => submitAction(item.action));
    row.append(button, explanation);
    root.append(row);
  }
}
function renderView(view) {
  state.projects = state.projects.map(entry => entry.project_id === view.project_id ?
    {...entry, kind:view.kind, core_status:view.core_status} : entry);
  $('project-empty').classList.add('hidden');
  $('project-details').classList.remove('hidden');
  const refs = view.refs || {};
  text('project-kind', view.kind === 'workspace' ? 'Черновик' : 'Project Instance');
  text('core-status', view.core_status);
  text('active-stage', refs.active_stage || 'Пока нет');
  text('target-level', refs.target_level || 'Не выбран');
  text('accepted-level', refs.highest_accepted_level || 'Не принят');
  text('current-task', format(view.current));
  text('done', format(view.done));
  text('blockers', format(view.blockers));
  text('next-action', format(view.required_user_action));
  renderActions(view.available_actions || []);
  renderProjects();
  renderSourceFlow();
}
let projectRead = null;
function selectProject(projectId, afterCommit = false) {
  if (projectRead?.id === projectId) {
    if (afterCommit) return projectRead.promise.then(() => selectProject(projectId, true));
    return projectRead.promise;
  }
  const current = {id:projectId,promise:null}; projectRead=current;
  current.promise=readSelectedProject(projectId, afterCommit).finally(()=>{if(projectRead===current)projectRead=null;});
  return current.promise;
}
async function readSelectedProject(projectId, afterCommit = false) {
  if (projectId !== state.activeProject && typeof clearInterview === 'function') clearInterview();
  if (projectId !== state.activeProject && typeof clearApprovals === 'function') clearApprovals();
  if (projectId !== state.activeProject && typeof clearPreparation === 'function') clearPreparation();
  state.activeProject = projectId;
  try { sessionStorage.setItem('harness-project', projectId); } catch (_) { /* no credentials */ }
  state.view = null;
  if (state.screen === 'tasks' && typeof taskButtons !== 'undefined') {
    taskView = null;
    for (const id of taskButtons) $(id).disabled = true;
    $('task-consent').checked = false;
  }
  showNotice('Чтение canonical статуса…');
  try {
    const result = await api('/api/projects/' + encodeURIComponent(projectId));
    if (projectId !== state.activeProject) return;
    state.view = result.project;
    renderView(state.view);
    if (state.screen === 'documents') await loadSources();
    if (state.screen === 'interview') await loadInterview();
    if (state.screen === 'approvals') await loadApprovals();
    if (state.screen === 'tasks') await loadTasks();
    if (['gates','maintenance'].includes(state.screen)) await loadLifecycle(afterCommit);
    showNotice('Статус получен. GET не запускает проектные операции.', 'success');
  } catch (err) { showNotice(err.message, 'error'); }
}
async function refresh() {
  sourceFeedback = null;
  if (state.screen === 'tasks' && typeof taskButtons !== 'undefined') {
    taskView = null;
    for (const id of taskButtons) $(id).disabled = true;
    $('task-consent').checked = false;
  }
  showNotice('Чтение списка проектов…');
  try {
    const result = await api('/api/projects');
    state.projects = result.projects || [];
    renderProjects();
    if (state.activeProject) await selectProject(state.activeProject, true);
    else showNotice('Список обновлён. Изменяющих операций не выполнено.', 'success');
  } catch (err) { showNotice(err.message, 'error'); }
}
function newIdempotencyKey() {
  const raw = new Uint8Array(16);
  crypto.getRandomValues(raw);
  return 'browser-' + Array.from(raw, b => b.toString(16).padStart(2, '0')).join('');
}
async function submitAction(action) {
  if (!state.activeProject || !state.view || state.requestBusy) return;
  if (!uiAllowed.has(action)) return;
  if (!window.confirm(`Выполнить действие «${actionLabels[action] || action}» для выбранного проекта? Это отдельная операция.`)) return;
  state.requestBusy = true;
  renderActions(state.view.available_actions || []);
  showNotice('Отправка защищённого действия…');
  const currentProject = state.activeProject;
  try {
    const posted = await api('/api/projects/' + encodeURIComponent(currentProject) + '/operations',
      { method: 'POST', body: { action, payload: {}, idempotency_key: newIdempotencyKey(),
                                expected_fingerprint: state.view.fingerprint } });
    const opid = posted.operation_id;
    $('operation-view').classList.remove('hidden');
    text('operation-view', `Операция ${opid}: ${posted.state}`);
    // Polling *only* reads an opaque operation ID; refresh never POSTs.
    for (let attempt = 0; attempt < 120; attempt++) {
      const next = await api('/api/projects/' + encodeURIComponent(currentProject) + '/operations/' + encodeURIComponent(opid));
      const op = next.operation;
      text('operation-view', `Операция ${op.operation_id}: ${op.state}\n${op.error ? format(op.error.message_ru) : ''}`);
      if (terminalStates.has(op.state)) {
        showNotice(op.state === 'SUCCEEDED' ? 'Операция завершена. Статус перечитан из core.' :
          `Операция ${op.state}. Исправьте причину или явно проверьте состояние.`,
          op.state === 'SUCCEEDED' ? 'success' : 'error');
        await refresh();
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 900));
    }
    showNotice('Операция ещё исполняется. Повторное нажатие не требуется; сохранён operation ID.', 'error');
  } catch (err) { showNotice(err.message + ' Обновите состояние перед новой попыткой.', 'error'); }
  finally { state.requestBusy = false; if (state.view) renderActions(state.view.available_actions || []); }
}
for (const button of document.querySelectorAll('[data-screen]')) {
  button.addEventListener('click', () => { selectScreen(button.dataset.screen); rememberSelection(); });
}
// PH-LW-05 document flow: FormData only, no absolute paths or untrusted HTML.
const chosenDocuments = { files: [] };
let sourceRequest = null;
let sourceFeedback = null;
function clearDocumentValidation() {
  $('document-validation').classList.add('hidden');
  $('document-validation').textContent = '';
  for (const field of $('documents-panel').querySelectorAll('[aria-invalid]')) field.removeAttribute('aria-invalid');
}
function documentError(message, fieldId) {
  text('document-validation', message);
  $('document-validation').classList.remove('hidden');
  showNotice(message, 'error');
  const field = $(fieldId);
  if (['INPUT','SELECT','TEXTAREA'].includes(field.tagName)) field.setAttribute('aria-invalid', 'true');
  field.focus();
  $('document-validation').scrollIntoView({block:'nearest'});
  return null;
}
function requireDocumentWorkspace() {
  if (!state.activeProject || !state.view) {
    if (!$('new-project-name').value.trim()) return documentError('Введите название проекта и нажмите «Создать проект для документов». Затем можно импортировать ZIP или MD.', 'new-project-name');
    return documentError('Проект ещё не создан. Нажмите «Создать проект для документов», затем повторите действие.', 'create-intake');
  }
  if (state.view.kind !== 'workspace') return documentError('Источники опубликованного проекта здесь не заменяются. Создайте новый проект для документов или выберите существующий черновик во вкладке «Проекты».', 'new-project-name');
  if (state.sourceSnapshot?.project_id !== state.activeProject) return documentError('Состояние документов ещё не прочитано. Нажмите «Обновить состояние» и повторите действие.', 'refresh');
  return state.sourceSnapshot;
}
$('new-project-name').addEventListener('input', clearDocumentValidation);
function renderSourceFlow() {
  const workspace = state.view?.kind === 'workspace';
  const snapshot = workspace && state.sourceSnapshot?.project_id === state.activeProject ? state.sourceSnapshot : null;
  const selected = chosenDocuments.files.length;
  for (const id of ['create-intake','create-no-docs','upload-sources','confirm-no-docs','documents-next']) $(id).disabled = state.requestBusy;
  $('source-files').disabled = state.requestBusy;
  $('source-import-mode').disabled = state.requestBusy;
  $('clear-source-files').disabled = state.requestBusy;
  $('clear-source-files').classList.toggle('hidden', !selected);
  const project = state.projects.find(entry => entry.project_id === state.activeProject);
  text('upload-project', workspace ? `Документы для проекта: ${project?.display_name || project?.project_name || state.activeProject}` : 'Проект для загрузки ещё не выбран.');
  let title, detail, category = '';
  if (sourceRequest?.projectId === state.activeProject) {
    title = sourceRequest.phase === 'validating' ? 'Файлы переданы. Проверяем архив и документы…' : 'Загружаем файлы…';
    detail = 'Дождитесь результата проверки. Повторно нажимать кнопку не нужно.';
  } else if (!workspace) {
    title = selected ? 'Файлы выбраны. Сначала создайте или выберите проект' : 'Сначала создайте или выберите проект';
    detail = state.view?.kind === 'project' ? 'У опубликованного Project Instance источники здесь не заменяются. Для нового проекта заполните название слева.' :
      'Введите название слева и нажмите «Создать проект для документов». Выбранные файлы сохранятся; после создания нажмите «Импортировать файлы».';
  } else if (sourceFeedback?.projectId === state.activeProject) {
    ({title, detail, category} = sourceFeedback);
  } else if (!snapshot) {
    title = 'Читаем состояние документов…';
    detail = 'Дождитесь списка источников. Если чтение не удалось, нажмите «Обновить».';
  } else if (selected) {
    title = 'Файлы выбраны — загрузка ещё не началась';
    detail = 'Нажмите «Импортировать файлы» и подтвердите загрузку. Затем здесь появится результат проверки.';
  } else if (snapshot.documents.length) {
    title = `Документы загружены: ${snapshot.documents.length} MD`;
    detail = 'Загрузка и проверка завершены. Следующий шаг — «Перейти к опросу и GPT». Анализ и согласования выполняются отдельно.';
    category = 'success';
  } else if (snapshot.documentation_choice === 'NONE') {
    title = 'Подтверждено: документации нет';
    detail = 'Можно продолжить: нажмите «Перейти к опросу и GPT».';
    category = 'success';
  } else {
    title = 'Проект готов к загрузке документов';
    detail = 'Выберите ZIP с Markdown или файлы MD, затем нажмите «Импортировать файлы». Выбор файла сам по себе не запускает загрузку.';
  }
  text('upload-step-title', title); text('upload-step-detail', detail);
  $('upload-step').className = 'upload-step' + (category ? ' ' + category : '');
}
function finishSourceRequest() {
  state.requestBusy = false;
  sourceRequest = null;
  if (state.view) renderActions(state.view.available_actions || []);
  renderSourceFlow();
}
function setSelected(files) {
  clearDocumentValidation();
  chosenDocuments.files = Array.from(files).slice(0, 100);
  sourceFeedback = null;
  text('upload-result', '');
  text('upload-selected', chosenDocuments.files.length ?
    `${chosenDocuments.files.length} файл(ов): ${chosenDocuments.files.map(f => f.name).join(', ')}` : 'Файлы не выбраны');
  renderSourceFlow();
}
$('source-files').addEventListener('change', event => setSelected(event.target.files));
$('clear-source-files').addEventListener('click', () => { setSelected([]); $('source-files').value=''; });
const zone = $('upload-zone');
for (const name of ['dragenter', 'dragover']) zone.addEventListener(name, event => {
  event.preventDefault(); zone.classList.add('dragover');
});
for (const name of ['dragleave', 'drop']) zone.addEventListener(name, event => {
  event.preventDefault(); zone.classList.remove('dragover');
});
zone.addEventListener('drop', event => { if (event.dataTransfer) setSelected(event.dataTransfer.files); });
async function loadSources() {
  const projectId = state.activeProject;
  $('source-list').replaceChildren();
  text('source-preview', 'Выберите документ для просмотра.');
  renderSourceFlow();
  if (!state.activeProject || !state.view || state.view.kind !== 'workspace') {
    text('source-summary', 'Выберите подготовительную рабочую область. Для Project Instance источники не заменяются.');
    return;
  }
  try {
    const response = await api(`/api/projects/${encodeURIComponent(projectId)}/sources`);
    if (projectId !== state.activeProject || state.view?.kind !== 'workspace') return;
    state.sourceSnapshot = response;
    if (sourceFeedback?.projectId === projectId && sourceFeedback.title === 'Не удалось прочитать состояние документов') sourceFeedback = null;
    text('source-summary', `Revision ${response.source_revision}; выбор: ${response.documentation_choice}; ` +
      `${response.documents.length} MD документов, ${response.skipped.length} пропущено. ` +
      'Импорт не выполняет смысловой анализ; черновик и вопросы доступны во вкладке «Опрос и GPT».');
    renderSourceFlow();
    for (const doc of response.documents) {
      const item = document.createElement('div'); item.className = 'source-item';
      const button = document.createElement('button'); button.type='button'; button.className='outline';
      button.textContent = 'Предпросмотр';
      button.addEventListener('click', () => showPreview(doc.document_ref));
      const name = document.createElement('span');
      name.textContent = `${doc.original_name} / ${doc.source_relative_path} · ${doc.byte_size} байт · ${doc.sha256}`;
      item.append(button,name); $('source-list').append(item);
    }
    for (const skipped of response.skipped) {
      const item = document.createElement('p'); item.className='muted small';
      item.textContent = `Не импортировано: ${skipped.original_name} / ${skipped.relative_path || ''} — ${skipped.reason}`;
      $('source-list').append(item);
    }
  } catch (error) {
    if (projectId !== state.activeProject) return;
    state.sourceSnapshot = null;
    sourceFeedback = {projectId, title:'Не удалось прочитать состояние документов', detail:error.message + ' Нажмите «Обновить».', category:'error'};
    text('source-summary', error.message); renderSourceFlow();
  }
}
$('documents-next').addEventListener('click', () => {
  if (state.requestBusy) return;
  clearDocumentValidation();
  const snapshot = requireDocumentWorkspace();
  if (!snapshot) return;
  if (chosenDocuments.files.length) return documentError('Выбранные файлы ещё не импортированы. Нажмите «Импортировать файлы» и дождитесь результата.', 'upload-sources');
  if (!snapshot.documents.length && snapshot.documentation_choice !== 'NONE') return documentError('Сначала загрузите документацию: выберите ZIP или MD и нажмите «Импортировать файлы». Если документов нет, нажмите «Документации нет».', 'source-files');
  selectScreen('interview'); rememberSelection();
});
async function showPreview(docRef) {
  try {
    const data = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/documents/${encodeURIComponent(docRef)}/preview`);
    text('source-preview', `${data.relative_path} (обычный текст; никакого HTML)

${data.preview_text}`);
  } catch (error) { text('source-preview', error.message); }
}
async function createWorkspace(noDocumentation) {
  if (state.requestBusy) return;
  clearDocumentValidation();
  const name = $('new-project-name').value.trim();
  if (!name) return documentError('Введите название проекта.', 'new-project-name');
  if (!window.confirm(noDocumentation ? 'Подтвердить, что документации нет, и перейти к опросу?' :
        'Создать новую рабочую область intake для документов?')) return;
  state.requestBusy = true;
  renderSourceFlow();
  try {
    const result = await api('/api/intakes', {method:'POST', body:{project_name:name,
      no_documentation:noDocumentation, idempotency_key:newIdempotencyKey()}});
    await refresh();
    await selectProject(result.project_id);
    rememberSelection();
    showNotice(noDocumentation ? 'Отсутствие документации сохранено. Дальше — вопросы опроса.' :
      'Проект создан. Выберите MD/ZIP и нажмите «Импортировать файлы».', 'success');
  } catch (error) { showNotice(error.message, 'error'); }
  finally { finishSourceRequest(); }
}
$('create-intake').addEventListener('click', () => createWorkspace(false));
$('create-no-docs').addEventListener('click', () => createWorkspace(true));
$('confirm-no-docs').addEventListener('click', async () => {
  if (state.requestBusy) return;
  clearDocumentValidation();
  if (!requireDocumentWorkspace()) return;
  if (!window.confirm('Заменить источники осознанным ответом «Документации нет»? Согласования станут недействительными.')) return;
  state.requestBusy = true;
  renderSourceFlow();
  try {
    const response = await api(`/api/projects/${encodeURIComponent(state.activeProject)}/sources/no-documentation`,
      {method:'POST', body:{expected_fingerprint:state.view.fingerprint, expected_source_revision:state.sourceSnapshot.source_revision}});
    setSelected([]); $('source-files').value='';
    text('upload-result', `${response.status} · revision ${response.source_revision}. Опрос ещё не выполнен.`);
    await selectProject(state.activeProject);
  } catch (error) { showNotice(error.message, 'error'); }
  finally { finishSourceRequest(); }
});
$('upload-sources').addEventListener('click', () => {
  if (state.requestBusy) return;
  clearDocumentValidation();
  if (!requireDocumentWorkspace()) return;
  if (!chosenDocuments.files.length) return documentError('Выберите ZIP с документацией или один/несколько файлов MD, затем нажмите «Импортировать файлы».', 'source-files');
  if (!window.confirm('Загрузить файлы как недоверенные источники? Новая ревизия отменит прежние approvals.')) return;
  const form = new FormData();
  form.set('mode', $('source-import-mode').value);
  form.set('expected_fingerprint', state.view.fingerprint);
  form.set('expected_source_revision', String(state.sourceSnapshot.source_revision));
  chosenDocuments.files.forEach(file => form.append('files', file, file.name));
  const xhr = new XMLHttpRequest();
  const projectId = state.activeProject;
  const target = `/api/projects/${encodeURIComponent(projectId)}/sources/upload`;
  state.requestBusy = true;
  sourceRequest = {projectId, phase:'uploading'};
  renderSourceFlow();
  $('upload-progress').classList.remove('hidden');
  $('upload-progress').value = 0;
  text('upload-result', 'Загрузка в приватный карантин — ещё не принято.');
  xhr.open('POST', target, true);
  xhr.setRequestHeader('Accept', 'application/json');
  xhr.upload.onprogress = event => {
    if (event.lengthComputable) $('upload-progress').value = Math.round(event.loaded / event.total * 100);
  };
  xhr.upload.onload = () => {
    if (sourceRequest?.projectId === projectId) {
      sourceRequest.phase = 'validating'; renderSourceFlow();
      $('upload-progress').removeAttribute('value');
    }
  };
  xhr.onload = async () => {
    let completedMessage = '';
    try {
      const result = JSON.parse(xhr.responseText);
      if (xhr.status < 200 || xhr.status >= 300) throw new Error(result.error?.message_ru || 'Импорт отклонён');
      completedMessage = `${result.status === 'UNCHANGED' ? 'Эти файлы уже загружены; повторный импорт не создал копий. ' : ''}Принято: ${result.accepted_count}; пропущено: ${result.skipped_count}; ` +
        `отклонено: ${result.rejected_count}; ревизия: ${result.source_revision}. ` +
        'Документы импортированы — анализ ещё не выполнен. ' +
        (result.skipped || []).map(x => x.reason).join(', ');
      setSelected([]); $('source-files').value='';
      await selectProject(projectId);
    } catch (error) {
      completedMessage = error.message + ' Импорт не подтверждён. Обновите состояние перед повторной попыткой.';
      sourceFeedback = {projectId, title:'Импорт не подтверждён', detail:completedMessage, category:'error'};
    }
    finally {
      finishSourceRequest(); $('upload-progress').classList.add('hidden');
      text('upload-result', completedMessage);
    }
  };
  xhr.onerror = () => {
    sourceFeedback = {projectId, title:'Не удалось получить результат загрузки',
      detail:'Сбой соединения. Нажмите «Обновить», чтобы проверить, сохранены ли документы. После этого решите, нужен ли повторный импорт.', category:'error'};
    finishSourceRequest(); $('upload-progress').classList.add('hidden');
    text('upload-result', sourceFeedback.detail);
  };
  xhr.send(form);
});

$('refresh').addEventListener('click', refresh);
let resumeRevision = 0;
let resumeWrites = Promise.resolve();
function rememberSelection() {
  if (!state.connected) return;
  const project_id = state.activeProject, screen = state.screen;
  resumeWrites = resumeWrites.then(async () => {
    try {
      const saved = await api('/api/ui/resume', {method:'POST', body:{project_id, screen, expected_revision:resumeRevision}});
      resumeRevision = saved.revision;
    } catch (error) {
      const current = await api('/api/ui/resume'); resumeRevision = current.revision;
      showNotice('Выбор для следующего запуска не сохранён: ' + error.message, 'error');
    }
  }).catch(error => showNotice(error.message, 'error'));
}
$('stop-harness').addEventListener('click', async () => {
  if (!window.confirm('Завершить Harness? Активные изменения должны закончиться; уже выполненные действия не отменяются.')) return;
  try {
    await resumeWrites;
    await api('/api/desktop/stop', {method:'POST', body:{}});
    state.connected = false;
    $('refresh').disabled = true; $('stop-harness').disabled = true;
    text('connection-state', 'Сервер остановлен');
    showNotice('Harness завершает работу. Эту вкладку можно закрыть. Проекты сохранены.', 'success');
  } catch (error) { showNotice(error.message, 'error'); }
});
async function restoreDesktop() {
  const saved = await api('/api/ui/resume'); resumeRevision = saved.revision;
  try { state.activeProject = sessionStorage.getItem('harness-project') || saved.project_id; }
  catch (_) { state.activeProject = saved.project_id; }
  await refresh();
  const fallbackScreen = saved.screen || 'projects';
  try { selectScreen(sessionStorage.getItem('harness-screen') || fallbackScreen); }
  catch (_) { selectScreen(fallbackScreen); }
}
(async function initialize() {
  try {
    await restoreDesktop();
    state.connected = true;
    $('refresh').disabled = false; $('stop-harness').disabled = false;
    text('connection-state', 'Сервер готов');
  } catch (err) {
    text('connection-state', 'Нет соединения');
    showNotice('Не удалось подключиться к Harness. Запустите его через ярлык и обновите страницу.', 'error');
  }
})();
