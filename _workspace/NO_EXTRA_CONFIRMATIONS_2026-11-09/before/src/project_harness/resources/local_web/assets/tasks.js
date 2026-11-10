'use strict';
// No commands or paths are accepted from the form. Text previews use textContent.
let taskView = null;
let taskOperation = null;
const taskRoutes = {RESERVE_READY_TASK:'Получите текущую задачу',VERIFY_CURRENT_TASK:'Получите результат агента и выполните независимую проверку',COMPLETE_VERIFIED_TASK:'Проверьте актуальность результата и завершите Task',RESUME_BLOCKED_TASK:'Устраните blocker и укажите resolution',EXTERNAL_SAFETY_RECOVERY:'Восстановите доверенный handoff; in-place resume запрещён',EXECUTE_LOCAL_AUTOMATIC:'Automatic executor недоступен',AUTOMATIC_RUN_IN_PROGRESS:'Automatic Run: требуется отдельная диагностика',PREPARE_ACTIVE_STAGE_PLAN:'Откройте «Стадии и доказательства» и подготовьте active Stage plan',PREPARE_STAGE_APPROVAL:'Откройте «Стадии и доказательства» и выполните отдельный Stage review',TARGET_ALREADY_REACHED:'Текущий target принят'};
const taskButtons = ['task-next','task-copy','task-upload','task-canonical','task-verify','task-complete','task-block','task-resume','task-manual-submit'];
function taskBase(pid=state.activeProject) { return '/api/projects/'+encodeURIComponent(pid); }
async function loadTasks() {
  taskView=null; $('task-consent').checked=false; $('task-manual-confirm').checked=false;
  for (const id of taskButtons) $(id).disabled=true;
  if (!state.activeProject || state.view?.kind!=='project') {
    text('tasks-summary','Выберите Project Instance во вкладке «Проекты».');
    $('task-prompt').value=''; return;
  }
  const pid=state.activeProject;
  try {
    const v=await api(taskBase(pid)+'/tasks');
    if (pid!==state.activeProject) return;
    taskView=v;
    text('tasks-summary',`Режим: ${v.execution_mode}; стадия: ${v.active_stage}; Task: ${v.current?.status || 'нет'}; завершено: ${v.status.completed_task_refs.length}. Следующий шаг: ${taskRoutes[v.status.next_operator_route.route] || v.status.next_operator_route.route}`);
    text('tasks-disabled',v.disabled_reason || 'Передайте закреплённый JIT внешнему агенту вручную. GET не создаёт Run.');
    text('tasks-list',format({work_packages:v.work_packages,tasks:v.tasks})); text('tasks-outlines',format(v.future_outlines));
    text('task-contract',format({task:v.current,run:v.active_run,binding_digest:v.binding_digest}));
    $('task-prompt').value=v.prompt_text || ''; text('task-context',format(v.context));
    text('task-plan',format(v.verification_plan)); text('task-result-state',format(v.result));
    const me=v.manual_evidence; $('task-manual-checks').replaceChildren();
    $('task-manual-panel').hidden=!me?.binding.checks.length;
    text('task-manual-state',format(me?.evidence || 'Нет manual checks'));
    if(me) for(const [index,check] of me.binding.checks.entries()) {
      const box=document.createElement('fieldset');box.dataset.checkIndex=index;
      const title=document.createElement('legend');title.textContent=check;box.append(title);
      const observation=document.createElement('textarea');observation.dataset.field='observation';observation.maxLength=4000;observation.placeholder='Что проверено, как и что наблюдалось';box.append(observation);
      const status=document.createElement('select');status.dataset.field='status';
      for(const value of ['', 'PASS','FAIL']){const option=document.createElement('option');option.value=value;option.textContent=value || 'Укажите результат';status.append(option);}box.append(status);
      const sources=document.createElement('select');sources.multiple=true;sources.dataset.field='sources';sources.setAttribute('aria-label','Просмотренные файлы');
      for(const path of Object.keys(me.product_files)){const option=document.createElement('option');option.value=path;option.textContent=path;sources.append(option);}box.append(sources);
      $('task-manual-checks').append(box);
    }
    text('task-verification',format(v.verification_report || 'Независимая проверка ещё не выполнена.'));
    text('task-blockers',format(v.blockers)); $('task-blocker-ref').replaceChildren();
    for (const b of v.blockers) {const option=document.createElement('option');option.value=`${b.id}@${b.revision}`;option.textContent=option.value; $('task-blocker-ref').append(option);}
    const manual=!v.disabled_reason, active=manual && !!v.active_run, received=v.result.status==='RESULT_RECEIVED';
    $('task-next').disabled=state.requestBusy || !manual || !['RESERVE_READY_TASK','VERIFY_CURRENT_TASK','COMPLETE_VERIFIED_TASK'].includes(v.status.next_operator_route.route);
    $('task-copy').disabled=state.requestBusy || !v.prompt_text;
    for (const id of ['task-upload','task-canonical','task-block']) $(id).disabled=state.requestBusy || !active;
    $('task-verify').disabled=state.requestBusy || !active || !received;
    $('task-complete').disabled=state.requestBusy || !active || !received || v.verification_report?.status!=='PASS';
    $('task-resume').disabled=state.requestBusy || !manual || v.status.next_operator_route.route!=='RESUME_BLOCKED_TASK';
    $('task-manual-submit').disabled=state.requestBusy || !active || !me?.binding.checks.length || !['BLOCKED'].includes(me.evidence.status);
    try {taskOperation=sessionStorage.getItem('harness-task-operation-'+pid);} catch (_) {taskOperation=null;}
    $('task-reconcile').disabled=!taskOperation || state.requestBusy;
    if (taskOperation) await readTaskOperation(pid,taskOperation);
  } catch (e) {text('tasks-summary',e.message); showNotice(e.message,'error');}
}
async function readTaskOperation(pid,id) {
  const {operation}=await api(taskBase(pid)+'/operations/'+encodeURIComponent(id));
  if (pid===state.activeProject) text('task-operation',format(operation));
  return operation;
}
async function taskAction(action,payload,uploadFile=null) {
  if (!taskView || state.requestBusy) return;
  const v=taskView, pid=state.activeProject;
  state.requestBusy=true; for(const id of taskButtons) $(id).disabled=true;
  $('task-consent').checked=false; $('task-manual-confirm').checked=false;
  try {
    if (uploadFile) {
      if (uploadFile.size>1048576) throw new Error('Result ограничен 1 MiB.');
      const data=new FormData();data.set('expected_fingerprint',v.fingerprint);data.set('binding_digest',v.binding_digest);data.set('result',uploadFile);
      const staged=await api(taskBase(pid)+'/tasks/result-upload',{method:'POST',formData:data});
      payload.upload_id=staged.upload_id;
    }
    const op=await api(taskBase(pid)+'/operations',{method:'POST',body:{action,payload,expected_fingerprint:v.fingerprint,idempotency_key:newIdempotencyKey()}});
    taskOperation=op.operation_id;
    try {sessionStorage.setItem('harness-task-operation-'+pid,taskOperation);} catch (_) {}
    for (let n=0;n<240;n++) {
      const current=await readTaskOperation(pid,taskOperation);
      if (terminalStates.has(current.state)) {
        showNotice(current.state==='SUCCEEDED' ? 'Действие завершено. Результат, PASS и Task DONE показаны раздельно.' : (current.error?.message_ru || current.state),'success');break;
      }
      await new Promise(resolve=>setTimeout(resolve,500));
    }
  } catch (e) {showNotice(e.message+' Обновлено текущее состояние; действие автоматически не повторяется.','error');}
  finally {state.requestBusy=false;if(pid===state.activeProject) await selectProject(pid,true);}
}
$('task-next').addEventListener('click',()=>taskAction('next',{}));
$('task-manual-submit').addEventListener('click',()=>{
  if(!taskView?.manual_evidence) return;
  const me=taskView.manual_evidence, binding=me.binding;
  const document={...binding,reviewer:$('task-manual-reviewer').value,checks:[]};
  for(const box of $('task-manual-checks').children){
    const index=Number(box.dataset.checkIndex);
    document.checks.push({index,check:binding.checks[index],status:box.querySelector('[data-field=status]').value,
      observation:box.querySelector('[data-field=observation]').value,
      sources:Array.from(box.querySelector('[data-field=sources]').selectedOptions).map(x=>({path:x.value,sha256:'sha256:'+me.product_files[x.value].sha256}))});
  }
  taskAction('manual-evidence',{document,confirmed:$('task-manual-confirm').checked});
});
$('task-copy').addEventListener('click',async()=>{
  try {await navigator.clipboard.writeText($('task-prompt').value);showNotice('Закреплённый JIT скопирован.','success');}
  catch (_) {$('task-prompt').focus();$('task-prompt').select();showNotice('Промпт выделен: нажмите Ctrl+C.');}
});
$('task-upload').addEventListener('click',()=>{
  const file=$('task-result-file').files[0];if(!file) {showNotice('Выберите result JSON.','error');return;}
  taskAction('receive-result',{upload_id:null,binding_digest:taskView.binding_digest},file);
});
$('task-canonical').addEventListener('click',()=>taskAction('receive-result',{upload_id:null,binding_digest:taskView.binding_digest}));
$('task-verify').addEventListener('click',()=>taskAction('verify',{binding_digest:taskView.binding_digest,plan_digest:taskView.verification_plan.digest,consent:$('task-consent').checked}));
$('task-complete').addEventListener('click',()=>taskAction('complete',{binding_digest:taskView.binding_digest}));
$('task-block').addEventListener('click',()=>taskAction('block',{run_ref:taskView.active_run.run_ref,reason:$('task-reason').value}));
$('task-resume').addEventListener('click',()=>taskAction('resume',{blocker_ref:$('task-blocker-ref').value,resolution:$('task-resolution').value}));
$('task-reconcile').addEventListener('click',async()=>{
  if(!taskOperation || state.requestBusy) return;
  try {await api(taskBase()+'/operations/'+encodeURIComponent(taskOperation)+'/reconcile',{method:'POST',body:{confirm:true}});await loadTasks();}
  catch(e) {showNotice(e.message,'error');}
});
