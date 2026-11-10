'use strict';
let approvalView = null;
let pendingApprovalRequest = null;
const invalidationLabels = {SOURCE_CHANGED:'Изменились источники', MATERIAL_DRAFT_CHANGE:'Изменилось содержание draft',
  REWORK_OR_EXTERNAL_APPROVAL_CHANGE:'Решение возвращено на доработку либо approval изменён вне этого flow'};
function clearApprovals() {
  approvalView = pendingApprovalRequest = null;
  $('approval-subjects').replaceChildren(); $('approval-receipts').replaceChildren();
  $('approval-actor').value = ''; $('retry-approval').classList.add('hidden');
}
let approvalRead = null;
function loadApprovals() {
  const pid = state.activeProject;
  if (approvalRead?.pid === pid) return approvalRead.promise;
  const pending = {pid, promise: null}; approvalRead = pending;
  pending.promise = readApprovals(pid).finally(() => {
    if (approvalRead === pending) approvalRead = null;
  });
  return pending.promise;
}
async function readApprovals(pid) {
  await loadPreparation();
  if (pid !== state.activeProject) return;
  if (!state.activeProject || state.view?.kind !== 'workspace') {
    clearApprovals(); text('approvals-status', 'Выберите provisional intake. Accepted Project Instance здесь не изменяется.'); return;
  }
  try {
    const view = await api(interviewPath('/approvals'));
    if (pid !== state.activeProject) return;
    approvalView = view; renderApprovals();
  } catch (error) { approvalView = null; $('approval-subjects').replaceChildren(); text('approvals-status', error.message); }
}
function renderApprovals() {
  const view = approvalView;
  text('approvals-status', `${view.subjects.filter(r=>r.approved).length} из ${view.subjects.length} решений · ${view.readiness.status}`);
  text('approvals-next', view.next_action === 'PREPARATION_PENDING_PH_LW_08' ?
    'Передача подтверждена. Проект пока не создан. Подтвердите новую папку в форме подготовки ниже.' :
    view.recovery_required ? 'Сверьте прерванное согласование перед продолжением.' :
    view.unbound_approvals.length ? 'Найдены approvals без актуальной привязки. Явно сбросьте их перед повторным согласованием.' :
    !view.subject_complete ? `Уточните draft во вкладке «Опрос и GPT». Missing fields: ${view.readiness.missing_fields.join(', ') || 'см. readiness'}.` :
    !view.actor ? 'Укажите оператора один раз для этой intake session.' :
    `Следующее решение: ${view.subjects.find(r=>r.subject===view.next_subject)?.label}. Проверьте содержание ниже.`);
  $('approval-actor-form').classList.toggle('hidden', Boolean(view.actor));
  text('approval-actor-display', view.actor ? `Оператор каждого решения: ${view.actor}` : 'Оператор пока не задан.');
  $('recover-approval').classList.toggle('hidden', !view.recovery_required);
  $('invalidate-approvals').classList.toggle('hidden', !view.unbound_approvals.length);
  $('approval-invalidations').replaceChildren();
  for (const item of view.invalidations) $('approval-invalidations').append(element('p',
    `${item.subject}: требуется повторение — ${invalidationLabels[item.reason]}. Прежний receipt ${item.previous_receipt} сохранён.`));
  const root = $('approval-subjects'); root.replaceChildren();
  for (const row of view.subjects) {
    const card = element('section', undefined, 'question'); card.id = 'approval-' + row.subject;
    card.append(element('h3', `${row.label} · ${row.approved ? 'Согласовано' : 'Ожидает решения'}`));
    const reworkRequest = view.rework_requests.find(r => r.subject === row.subject);
    if (reworkRequest) card.append(element('p', 'На доработку: ' + reworkRequest.comment));
    card.append(element('pre', format(row.content), 'source-preview'));
    card.append(element('p', `Оператор: ${view.actor || 'не задан'}. Subject digest: ${row.subject_digest}. Draft: ${view.binding.input_revision}. Source revision: ${view.binding.source_revision}.`, 'muted small body-value'));
    const comment = element('textarea'); comment.id = 'comment-' + row.subject; comment.maxLength = 2000; comment.rows = 2;
    const label = element('label', 'Комментарий (обязателен для доработки)'); label.htmlFor = comment.id;
    const consentLabel = element('label', undefined, 'consent');
    const consent = element('input'); consent.type = 'checkbox'; consent.id = 'confirm-' + row.subject;
    consentLabel.append(consent, document.createTextNode(`Я прочитал показанное содержание ${row.label} и подтверждаю отдельное решение.`));
    const approve = element('button', row.subject === 'codex_handoff' ? 'Подтвердить передачу и подготовить проект' : `Подтвердить ${row.label}`, 'outline');
    approve.id = 'approve-' + row.subject; approve.type = 'button';
    const blocked = !view.actor || !view.subject_complete || view.recovery_required || view.unbound_approvals.length || row.approved || view.next_subject !== row.subject;
    approve.disabled = Boolean(blocked);
    approve.addEventListener('click', () => approvalAction(async () => {
      if (!consent.checked) throw new Error('Подтвердите, что прочитали именно это содержание.');
      await sendApproval(row, 'APPROVE', comment.value);
    }));
    const rework = element('button', 'На доработку', 'quiet'); rework.id = 'rework-' + row.subject; rework.type = 'button';
    rework.disabled = !view.actor || view.recovery_required || Boolean(view.unbound_approvals.length);
    rework.addEventListener('click', () => approvalAction(async () => {
      if (!comment.value.trim()) throw new Error('Опишите, что требуется уточнить.');
      await sendApproval(row, 'REWORK', comment.value);
      selectScreen('interview');
    }));
    card.append(label, comment, consentLabel, approve, rework); root.append(card);
  }
  $('approval-receipts').replaceChildren();
  for (const row of view.receipts.toReversed()) {
    const details = element('details'); details.append(element('summary', `${row.sequence}. ${row.subject} · ${row.decision} · ${row.actor} · ${row.timestamp}`),
      element('pre', format(row), 'source-preview')); $('approval-receipts').append(details);
  }
}
async function approvalAction(work) {
  if (state.requestBusy || !approvalView) return;
  state.requestBusy = true;
  for (const el of $('approvals-panel').querySelectorAll('button,input,textarea')) el.disabled = true;
  try { await work(); }
  catch (error) { showNotice(error.message + ' Перечитайте состояние; автоматического повтора нет.', 'error'); }
  finally {
    state.requestBusy = false;
    for (const el of $('approvals-panel').querySelectorAll('button,input,textarea')) el.disabled = false;
    if (approvalView) renderApprovals();
  }
}
async function sendApproval(row, decision, comment) {
  const pid = state.activeProject;
  const body = {subject:row.subject, decision, comment, review_digest:approvalView.review_digest,
    subject_digest:row.subject_digest, expected_fingerprint:approvalView.binding.fingerprint,
    idempotency_key:newIdempotencyKey(), confirm:true};
  pendingApprovalRequest = {pid, body};
  $('retry-approval').classList.remove('hidden');
  await replayApproval();
}
async function replayApproval() {
  if (!pendingApprovalRequest || pendingApprovalRequest.pid !== state.activeProject) throw new Error('Нет запроса для этой intake session.');
  const receipt = await api(interviewPath('/approvals/decisions'), {method:'POST',body:pendingApprovalRequest.body});
  pendingApprovalRequest = null; $('retry-approval').classList.add('hidden');
  await loadApprovals();
  showNotice(`Решение ${receipt.decision} сохранено: ${receipt.receipt_id}. Оператор: ${receipt.actor}.`, 'success');
}
$('approval-actor-form').addEventListener('submit', event => {
  event.preventDefault(); approvalAction(async () => {
    await api(interviewPath('/approvals/actor'), {method:'POST',body:{actor:$('approval-actor').value,
      expected_fingerprint:approvalView.binding.fingerprint}}); await loadApprovals();
  });
});
$('refresh-approvals').addEventListener('click', loadApprovals);
$('retry-approval').addEventListener('click', () => approvalAction(replayApproval));
$('recover-approval').addEventListener('click', () => approvalAction(async () => {
  const result = await api(interviewPath('/approvals/recover'), {method:'POST',body:{confirm:true}});
  await loadApprovals(); showNotice(`Сверка: ${result.status}.`, 'success');
}));
$('invalidate-approvals').addEventListener('click', () => approvalAction(async () => {
  if (!window.confirm('Сбросить approvals только текущего draft? История receipts сохраняется.')) return;
  await sendApproval(approvalView.subjects[0], 'INVALIDATE', 'Явный сброс approvals без актуальной привязки');
}));
