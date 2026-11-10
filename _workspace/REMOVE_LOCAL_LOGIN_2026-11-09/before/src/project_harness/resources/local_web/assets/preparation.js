'use strict';
let preparationView = null;
let preparationTarget = null;
let preparationRequest = null;
let preparationPoll = null;
let preparationPollCount = 0;
function clearPreparation() {
  preparationView = preparationTarget = preparationRequest = null;
  clearTimeout(preparationPoll); preparationPoll = null;
  preparationPollCount = 0;
  $('preparation-complete').classList.add('hidden');
  $('preparation-form').classList.add('hidden');
  $('recover-preparation').classList.add('hidden');
  $('first-prompt').value = ''; text('preparation-status', 'Выберите intake.');
}
async function loadPreparation() {
  if (!state.csrf || !state.activeProject || (state.view && state.view.kind !== 'workspace')) { clearPreparation(); return; }
  const pid = state.activeProject;
  try {
    const view = await api(interviewPath('/preparation'));
    if (pid !== state.activeProject) return;
    preparationView = view;
    const complete = view.result && view.operation_state === 'SUCCEEDED';
    $('preparation-form').classList.toggle('hidden', view.phase !== 'NOT_STARTED' || !view.ready);
    $('preparation-complete').classList.toggle('hidden', !complete);
    $('recover-preparation').classList.toggle('hidden', view.phase === 'NOT_STARTED' || complete);
    text('preparation-parent', view.parent_directory || view.destination || '');
    text('preparation-status', complete ? 'Проект опубликован. Initial directory / ZIP / project: PASS. Текущий проект: PASS при публикации.' :
      view.phase === 'NOT_STARTED' ? view.ready ? 'Все согласования получены. Подтвердите новую папку; мастер соберёт и проверит проект.' :
        'Сначала завершите отдельные согласования.' : `${view.phase} · ${view.operation_state}. ${view.error?.message_ru || 'Сборка сохранена; закрытие вкладки её не отменяет.'}`);
    if (complete) {
      const result = view.result;
      text('published-folder', result.destination);
      text('published-refs', `Active: ${result.active_stage} · Target: ${result.target_level}\nTask: ${result.first_task_ref}\nRun: ${result.first_run_ref}`);
      $('download-handoff').href = interviewPath('/artifacts/' + encodeURIComponent(view.operation_id));
      const prompt = await api(interviewPath('/preparation/' + encodeURIComponent(view.operation_id) + '/prompt'));
      if (pid === state.activeProject) $('first-prompt').value = prompt.prompt;
    }
    clearTimeout(preparationPoll);
    if (['QUEUED','RUNNING'].includes(view.operation_state) && preparationPollCount++ < 180) preparationPoll = setTimeout(loadPreparation, 1000);
  } catch (error) {
    text('preparation-status', error.message);
    // POST can return QUEUED just before the worker persists its preparation
    // intent. A reconnect in that small window must keep reading, not stall.
    if (pid === state.activeProject && error.result?.error?.code === 'OPERATION_CONFLICT' && preparationPollCount++ < 180) {
      clearTimeout(preparationPoll); preparationPoll = setTimeout(loadPreparation,1000);
    }
  }
}
async function startPreparation() {
  if (state.requestBusy || !preparationView?.ready) return;
  if (!$('confirm-new-folder').checked) { showNotice('Подтвердите размещение в новой папке.', 'error'); return; }
  state.requestBusy = true; $('prepare-project').disabled = true;
  const pid = state.activeProject;
  try {
    const target = await api(interviewPath('/preparation/target'), {method:'POST', body:{
      folder_name:$('project-folder-name').value, binding_digest:preparationView.binding_digest,
      expected_fingerprint:preparationView.expected_fingerprint, confirm:true}});
    preparationTarget = target;
    preparationRequest = {target_id:target.target_id, binding_digest:target.binding_digest,
      expected_fingerprint:target.expected_fingerprint, idempotency_key:newIdempotencyKey()};
    const op = await api(interviewPath('/preparation/start'), {method:'POST', body:preparationRequest});
    text('preparation-status', `Подготовка ${op.operation_id}: ${op.state}`);
    // Only GET polling. Reconnect reads the durable preparation receipt.
    for (let i=0; i<180 && pid===state.activeProject; i++) {
      const data = await api(interviewPath('/operations/' + encodeURIComponent(op.operation_id)));
      text('preparation-status', `Подготовка: ${data.operation.state}. ${data.operation.error?.message_ru || ''}`);
      if (terminalStates.has(data.operation.state)) break;
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
    if (pid===state.activeProject) await loadPreparation();
  } catch (error) { showNotice(error.message + ' Перечитайте состояние перед повтором.', 'error'); await loadPreparation(); }
  finally { state.requestBusy=false; $('prepare-project').disabled=false; }
}
$('preparation-form').addEventListener('submit', event=>{event.preventDefault();startPreparation();});
$('refresh-preparation').addEventListener('click', loadPreparation);
$('recover-preparation').addEventListener('click', async()=>{
  if (state.requestBusy) return;
  state.requestBusy=true;
  try { await api(interviewPath('/preparation/recover'),{method:'POST',body:{confirm:true}}); await loadPreparation(); }
  catch(error) { showNotice(error.message,'error'); }
  finally { state.requestBusy=false; }
});
$('copy-first-prompt').addEventListener('click', async()=>{
  const field=$('first-prompt');
  try { await navigator.clipboard.writeText(field.value); showNotice('Первый JIT скопирован. Передайте его Codex вручную.','success'); }
  catch (_) { field.focus(); field.select(); showNotice('Промпт выделен. Нажмите Ctrl+C для копирования.'); }
});
$('open-project-folder').addEventListener('click',async()=>{
  try { await api(interviewPath('/preparation/open-folder'),{method:'POST',body:{confirm:true}}); showNotice('Папка передана Проводнику.','success'); }
  catch(error) { showNotice(error.message,'error'); }
});
