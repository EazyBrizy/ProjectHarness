'use strict';
// Local typed inputs and explicit manual exchange. All untrusted content is text.
let interviewView = null;
let exportReview = null;
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
  'project.scope.in':'Входит в scope', 'project.scope.out':'Не входит в scope',
  'project.constraints.mandatory':'Обязательные ограничения', 'project.constraints.forbidden':'Запрещённые действия',
  'project.constraints.non_functional':'Нефункциональные требования',
  'project.success_criteria':'Критерии успеха', 'project.assumptions':'Предположения',
  'project.unknowns':'Нерешённые material вопросы', 'architecture.summary':'Архитектурное предложение',
  'architecture.style':'Архитектурный стиль', 'architecture.components':'Основные компоненты',
  'profile.ref':'Profile ref', 'profile.rationale':'Обоснование profile',
};
const fieldOptions = {
  'implementation.target_level':['PROTOTYPE','ALPHA','BETA','MVP','RELEASE','UNSURE'],
  'project.connectivity':['ONLINE_ONLY','LIMITED_OFFLINE','OFFLINE_FIRST','UNKNOWN'],
  'project.data.sensitivity':['PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED','SECRET','REGULATED','UNKNOWN'],
};
function interviewPath(suffix = '') { return `/api/projects/${encodeURIComponent(state.activeProject)}${suffix}`; }
function element(tag, content, cls) {
  const item = document.createElement(tag);
  if (content !== undefined) item.textContent = String(content);
  if (cls) item.className = cls;
  return item;
}
function getDraftField(field) { return field.split('.').reduce((obj, key) => obj[key], interviewView.draft); }
function clearInterview() {
  interviewView = exportReview = replyPreview = null;
  answerInputs.clear();
  $('interview-body').classList.add('hidden');
  $('gpt-reply').value = '';
  $('export-review').classList.add('hidden');
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
      const opt = element('option', option || 'Ответ не выбран'); opt.value = option; control.append(opt);
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
    box.append(element('h3', q.text), element('p', q.why_asked, 'muted small'));
    if (q.field === 'project.documentation.availability') {
      box.append(element('p', 'Загрузите MD/ZIP или явно подтвердите отсутствие документации во вкладке «Документы».'));
    } else {
      const fields = Object.keys(fieldLabels).filter(f => f === q.field || f.startsWith(q.field + '.'));
      for (const field of fields) answerField(field, box);
      if (!fields.length) box.append(element('p', 'Это структурированное предложение заполняется через GPT draft exchange ниже. Оно проверяется схемой и показывается в diff до применения.'));
    }
    $('question-fields').append(box);
  }
  const known = $('known-answers'); known.replaceChildren();
  for (const fact of view.known_answers) {
    const row = element('div', undefined, 'known-answer');
    row.append(element('strong', fieldLabels[fact.field] || fact.field), element('pre', format(fact.value), 'source-preview'),
      element('p', `${fact.provenance.kind}; refs: ${fact.provenance.source_refs.join(', ') || 'нет'}; ` +
        `${fact.provenance.exchange_id || fact.provenance.input_revision || ''}`, 'muted small'));
    if (fieldLabels[fact.field]) {
      const edit = element('button', 'Изменить ответ', 'quiet'); edit.type = 'button';
      edit.addEventListener('click', () => {
        answerField(fact.field, row);
        answerInputs.get(fact.field)?.control.focus();
        edit.disabled = true;
      }); row.append(edit);
    }
    known.append(row);
  }
}
async function loadInterview() {
  if (!state.activeProject || state.view?.kind !== 'workspace') {
    clearInterview(); text('interview-status', 'Выберите Greenfield intake во вкладке «Проекты» или создайте его во вкладке «Документы».'); return;
  }
  const pid = state.activeProject;
  text('interview-status', 'Читаем текущие вопросы и readiness…');
  try {
    const view = await api(interviewPath('/interview'));
    if (pid !== state.activeProject) return;
    interviewView = view;
    $('interview-body').classList.remove('hidden');
    text('interview-status', `${view.readiness.status} · source revision ${view.source_revision} · draft ${view.input_revision}`);
    text('interview-next', view.recovery_required ? 'Сначала сверьте прерванный commit.' :
      view.readiness.status === 'WAITING_DECISION' && view.draft.implementation.target_level === 'UNSURE' ?
        'Выберите canonical target, когда решение принято. Остальные material gaps остаются открытыми.' :
        view.readiness.missing_fields.length ? 'Ответьте на открытые вопросы или подготовьте пакет для смыслового опроса GPT.' :
          'Draft заполнен. Откройте «Согласования» и подтвердите каждое решение отдельно.');
    if (view.approval_rework_requests?.length) text('interview-next',
      'На доработку: ' + view.approval_rework_requests.map(r => `${r.subject}: ${r.comment}`).join('; '));
    text('interview-documents', `Документация: ${view.documentation_choice}. ` +
      view.documents.map(d => `${d.original_name}/${d.source_relative_path} · ${d.document_ref} · ${d.sha256}`).join('\n'));
    text('interview-readiness', format(view.readiness));
    $('recover-reply').classList.toggle('hidden', !view.recovery_required);
    renderQuestions(view);
    renderExports(view.exports);
    renderImportHistory(view.imports);
    // Reload restores the last pending preview from the server, not from a
    // secret-bearing browser store. No mutation or automatic recovery occurs.
    const pending = view.imports.filter(r => r.state === 'PREVIEW').at(-1);
    if (pending) renderReplyPreview(pending);
    else { replyPreview = null; $('import-preview').classList.add('hidden'); }
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
      showNotice('Ответы проверены и сохранены ядром. Formal approvals не назначены.', 'success'); return;
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
  showNotice(`Сверка: ${result.status}.`, 'success'); await loadInterview();
}));
function classificationSelect(id) {
  const select = element('select'); select.id = id;
  for (const value of ['UNKNOWN','PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED','SECRET','REGULATED']) {
    const opt = element('option', value === 'UNKNOWN' ? 'Не проверено' : value); opt.value=value; select.append(opt);
  }
  return select;
}
$('review-export').addEventListener('click', () => interviewAction(async () => {
  exportReview = await api(interviewPath('/gpt/export-review'));
  $('export-documents').replaceChildren();
  $('export-review').classList.remove('hidden');
  $('draft-classification').value = 'UNKNOWN';
  text('export-warning', `${exportReview.warning_ru}\nSensitivity проекта: ${exportReview.project_data_sensitivity || 'не определена'}; draft: ${exportReview.draft_bytes} байт; документов: ${exportReview.documents.length}.`);
  for (const doc of exportReview.documents) {
    const row = element('div', undefined, 'export-document');
    const id = 'classification-' + doc.document_ref;
    const label = element('label', `${doc.original_name}/${doc.source_relative_path} · ${doc.byte_size} байт · ${doc.sha256}`); label.htmlFor=id;
    row.append(label, classificationSelect(id)); $('export-documents').append(row);
  }
}));
$('create-export').addEventListener('click', () => interviewAction(async () => {
  if (!exportReview) throw new Error('Сначала проверьте состав.');
  const classifications = {};
  for (const doc of exportReview.documents) classifications[doc.document_ref] = $('classification-' + doc.document_ref).value;
  await api(interviewPath('/gpt/exports'), {method:'POST', body:{
    expected_fingerprint:exportReview.binding.fingerprint, review_digest:exportReview.review_digest,
    classifications, draft_classification:$('draft-classification').value,
    consent:true, idempotency_key:newIdempotencyKey()}});
  $('export-review').classList.add('hidden'); exportReview = null;
  await loadInterview(); showNotice('Pack создан. Скачивание и копирование — отдельные ваши действия.', 'success');
}));
async function explicitCopy(value) {
  try { await navigator.clipboard.writeText(value); showNotice('Prompt скопирован по вашему действию.', 'success'); }
  catch (_) { showNotice('Clipboard недоступен. Выделите текст prompt и скопируйте вручную.', 'error'); }
}
function renderExports(exports) {
  $('export-history').replaceChildren();
  for (const item of exports.toReversed()) {
    const box = element('details'); box.open = item === exports.at(-1);
    box.append(element('summary', `Export ${item.export_revision} · ${item.exchange_id} · ${item.files.length} файл(ов)`));
    box.append(element('pre', item.prompt, 'source-preview'));
    const copy = element('button', 'Копировать prompt', 'outline'); copy.type='button';
    copy.addEventListener('click', () => explicitCopy(item.prompt)); box.append(copy);
    const stale = item.binding.fingerprint !== interviewView.fingerprint;
    for (const file of item.files) {
      const row = element('p', `${file.name} · ${file.bytes} байт · ${file.sha256} `, 'small body-value');
      if (!stale) {
        const link = element('a', 'Скачать');
        link.href = interviewPath(`/gpt/exports/${encodeURIComponent(item.exchange_id)}/${encodeURIComponent(file.name)}`);
        link.download = file.name; row.append(link);
      } else row.append(element('span', 'Устарел после изменения draft/источников.'));
      box.append(row);
    }
    $('export-history').append(box);
  }
}
$('preview-reply').addEventListener('click', () => interviewAction(async () => {
  $('repair-area').classList.add('hidden');
  $('import-preview').classList.add('hidden'); replyPreview = null;
  text('preview-summary', 'Проверяем новый ответ…');
  const result = await api(interviewPath('/gpt/replies/preview'), {method:'POST', body:{
    text:$('gpt-reply').value, expected_fingerprint:interviewView.fingerprint}});
  if (result.status === 'REPLAYED') {
    showNotice('Этот exact ответ уже применён; повторного изменения нет.', 'success'); await loadInterview(); return;
  }
  renderReplyPreview(result.preview); showNotice('Preview готов. Canonical draft ещё не изменён.', 'success');
}));
function renderReplyPreview(preview) {
  replyPreview = preview;
  $('import-preview').classList.remove('hidden'); $('reply-diff').replaceChildren();
  text('preview-summary', `${preview.state} · ${preview.import_id} · ${preview.readiness.status}. ` +
    `Изменено полей: ${preview.diff.length}. Approvals: ${preview.approval_invalidation_receipt.reason}. ` +
    `Будут invalidated: ${preview.approval_invalidation_receipt.subjects.join(', ') || 'нет'}.`);
  for (const row of preview.diff) {
    const box = element('section', undefined, 'diff-row');
    box.append(element('h4', row.field), element('p', 'Текущий ответ'), element('pre', format(row.before), 'source-preview'),
      element('p', 'Imported draft (не verified)'), element('pre', format(row.after), 'source-preview'));
    $('reply-diff').append(box);
  }
  $('reply-diff').append(element('p', `Осталось вопросов: ${preview.questions.filter(q => q.status === 'OPEN').length}. ` +
    `Missing fields: ${preview.readiness.missing_fields.join(', ') || 'нет'}.`));
}
$('commit-reply').addEventListener('click', () => interviewAction(async () => {
  if (!replyPreview) return;
  await api(interviewPath(`/gpt/replies/${replyPreview.import_id}/commit`), {method:'POST',body:{
    preview_digest:replyPreview.preview_digest, expected_fingerprint:replyPreview.binding.fingerprint}});
  $('gpt-reply').value=''; await loadInterview(); showNotice('Draft применён. Проверьте оставшиеся вопросы; это не formal approval.', 'success');
}));
$('cancel-reply').addEventListener('click', () => interviewAction(async () => {
  if (!replyPreview) return;
  await api(interviewPath(`/gpt/replies/${replyPreview.import_id}/cancel`), {method:'POST',body:{preview_digest:replyPreview.preview_digest}});
  await loadInterview(); showNotice('Import отменён до commit. Canonical draft сохранён.', 'success');
}));
$('copy-repair').addEventListener('click', () => explicitCopy($('repair-prompt').textContent));
function renderImportHistory(imports) {
  $('import-history').replaceChildren();
  for (const item of imports) $('import-history').append(element('p', `${item.import_id} · ${item.state} · ${item.response_digest}`, 'small body-value'));
}
