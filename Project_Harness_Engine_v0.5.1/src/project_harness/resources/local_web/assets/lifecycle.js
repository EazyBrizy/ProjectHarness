'use strict';
let lifecycleView=null, lifecycleDraft=null, lifecycleRead=null, lifecycleOperation=null;
const lifecycleLabels={
  'stage-status':'Показать Stage State',
  'prepare-stage-approval':'Подготовить Stage review','prepare-active-stage-plan':'Подготовить active Stage plan',
  'prepare-level-up':'Выбрать новый target','prepare-maintenance':'Подготовить same-level maintenance',
  'prepare-maintenance-cancel':'Подготовить отмену maintenance','prepare-migration':'Просмотреть план migration',
  'resume-stage-gate':'Возобновить Stage Gate','assess-maturity':'Оценить Brownfield / Hybrid','recover-migration':'Восстановить прерванную migration',
  'accept-stage':'Принять Stage','plan-active-stage':'Применить reviewed plan','level-up':'Подтвердить level-up',
  'start-maintenance':'Начать maintenance','cancel-maintenance':'Отменить maintenance','migrate-project':'Подтвердить migration'};
const lifecycleEditable={
 'accept-stage':['outcome_results','criteria_results','hard_constraint_results','profile_control_results','evidence_refs','known_limitations','next_stage_gaps','notes','permitted_use'],
 'plan-active-stage':['work_packages'], 'level-up':['target_level'],
 'start-maintenance':['objective','rationale','work_package'], 'cancel-maintenance':['rationale'], 'migrate-project':['input_document']};
const lifecycleFieldLabels={outcome_results:'Результаты outcomes',criteria_results:'Результаты criteria',hard_constraint_results:'Hard constraints',profile_control_results:'Profile controls',evidence_refs:'Evidence refs',rationale:'Обоснование',validator:'Проверяющий (ACT-...)',status:'Результат',known_limitations:'Известные ограничения',next_stage_gaps:'Пробелы следующей Stage',permitted_use:'Допустимое использование',work_packages:'Work Packages',work_package:'Work Package',tasks:'Задачи',title:'Название',objective:'Цель',purpose:'Назначение',expected_result:'Ожидаемый результат',scope:'Разрешённые пути',read:'Чтение',write:'Запись',forbidden:'Запрещено',verification:'Независимая проверка',commands:'Команды (запуск только при Task consent)',manual_checks:'Проверки оператора',expected_paths:'Ожидаемые файлы',acceptance_criteria:'Критерии приёмки',documentation:'Документация',target_level:'Новый target',notes:'Примечания'};
function lifecycleBase(pid=state.activeProject){return '/api/projects/'+encodeURIComponent(pid);}
function resolveFormSchema(s,root){if(s?.$ref){return s.$ref.slice(2).split('/').reduce((v,k)=>v?.[k],root)||{};}return s||{};}
function formDefault(schema,root){const s=resolveFormSchema(schema,root);if('const' in s)return s.const;if(s.enum)return s.enum[0];if(s.type==='object')return Object.fromEntries((s.required||[]).map(k=>[k,formDefault(s.properties?.[k],root)]));if(s.type==='array')return [];if(s.type==='boolean')return false;if(s.type==='integer')return s.minimum||1;return '';}
// Render actual schema fields as labelled controls. There is no bulk PASS action.
function lifecycleField(parent,key,value,schema,root,path){
 const s=resolveFormSchema(schema,root), box=document.createElement('fieldset'),legend=document.createElement('legend');
 legend.textContent=lifecycleFieldLabels[key]||key;box.append(legend);parent.append(box);
 const immutable=['schema_version','schema_ref','record_kind','id','revision','implementation_stage','future_stage_work','criterion_ref','constraint_ref','outcome_ref','control_ref'].includes(key)||('const' in s);
 if(immutable){const el=document.createElement('pre');el.textContent=format(value);box.append(el);return ()=>value;}
 if(Array.isArray(value)){
   const item=resolveFormSchema(s.items,root);
   if(!value.some(v=>v&&typeof v==='object') && item.type!=='object'){
     if(key==='evidence_refs'){
       const sel=document.createElement('select');sel.multiple=true;sel.dataset.field=path;sel.setAttribute('aria-label',legend.textContent+' '+path);
       const refs=[...new Set([...(lifecycleView?.evidence_candidates||[]).map(x=>x.ref),...value])];
       for(const ref of refs){const opt=document.createElement('option');opt.value=ref;opt.textContent=ref;opt.selected=value.includes(ref);sel.append(opt);}box.append(sel);return ()=>Array.from(sel.selectedOptions).map(x=>x.value);
     }
     const el=document.createElement('textarea');el.rows=3;el.value=value.join('\n');el.dataset.field=path;el.setAttribute('aria-label',legend.textContent+' (по одной строке)');box.append(el);return ()=>el.value.split('\n').map(x=>x.trim()).filter(Boolean);
   }
   const rows=document.createElement('div');box.append(rows);let readers=[];
   function add(v){const row=document.createElement('div');rows.append(row);const index=readers.length;const get=lifecycleField(row,String(index+1),v,s.items,root,path+'.'+index);readers.push({row,get});const remove=document.createElement('button');remove.type='button';remove.textContent='Удалить элемент';remove.onclick=()=>{readers=readers.filter(x=>x.row!==row);row.remove();};row.append(remove);}
   for(const v of value)add(v);
   const plus=document.createElement('button');plus.type='button';plus.textContent='Добавить '+(lifecycleFieldLabels[key]||key);plus.onclick=()=>{
     let next=formDefault(s.items,root);
     if(key==='tasks'&&lifecycleDraft.action==='start-maintenance'&&value[0]){
       next=structuredClone(value[0]);next.id=value[0].id.replace(/-\d+$/,'')+'-'+crypto.randomUUID().replaceAll('-','').slice(0,8).toUpperCase();next.depends_on_tasks=[];
     }
     add(next);
   };box.append(plus);return ()=>readers.map(x=>x.get());
 }
 if(value&&typeof value==='object'){
   const readers=Object.fromEntries(Object.entries(value).map(([k,v])=>[k,lifecycleField(box,k,v,s.properties?.[k],root,path+'.'+k)]));
   return ()=>Object.fromEntries(Object.entries(readers).map(([k,get])=>[k,get()]));
 }
 const label=document.createElement('label');label.textContent=legend.textContent;box.append(label);
 let el;let choices=s.enum;
 if(key==='target_level')choices=['PROTOTYPE','ALPHA','BETA','MVP','RELEASE'];
 if(choices){el=document.createElement('select');for(const v of choices){const opt=document.createElement('option');opt.value=v===null?'':String(v);opt.textContent=v===null?'Не указано':String(v);el.append(opt);}el.value=value===null?'':String(value);}
 else if(typeof value==='boolean'){el=document.createElement('input');el.type='checkbox';el.checked=value;}
 else{el=document.createElement('textarea');el.rows=2;el.value=value===null?'':String(value);}
 el.dataset.field=path;el.setAttribute('aria-label',legend.textContent+' '+path);label.append(el);
 return ()=>typeof value==='boolean'?el.checked:typeof value==='number'?Number(el.value):(value===null&&!el.value?null:el.value);
}
function renderLifecycleDraft(record){
 const host=$('lifecycle-fields');host.replaceChildren();const key=Object.keys(record)[0],body=record[key];
 const schema=lifecycleDraft.schema||{}, resolved=resolveFormSchema(schema.properties?.[key],schema),readers={};
 const editable=lifecycleEditable[lifecycleDraft.action]||[];
 const context=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Закреплённый контекст (только чтение)';pre.textContent=format(Object.fromEntries(Object.entries(body).filter(([k])=>!editable.includes(k))));context.append(summary,pre);host.append(context);
 for(const k of editable)if(k in body)readers[k]=lifecycleField(host,k,body[k],resolved.properties?.[k],schema,key+'.'+k);
 lifecycleRead=()=>({[key]:{...body,...Object.fromEntries(Object.entries(readers).map(([k,get])=>[k,get()]))}});
 $('lifecycle-json').value=JSON.stringify(record,null,2);$('lifecycle-confirm').checked=false;
 $('lifecycle-form-title').textContent=lifecycleLabels[lifecycleDraft.action];$('lifecycle-apply').textContent=lifecycleLabels[lifecycleDraft.action];$('lifecycle-form-panel').hidden=false;
}
let lifecycleLoading=null;
function loadLifecycle(afterCommit=false){
 if(lifecycleLoading?.pid===state.activeProject){
  if(afterCommit)return lifecycleLoading.promise.then(()=>loadLifecycle());
  return lifecycleLoading.promise;
 }
 const current={pid:state.activeProject,promise:null};lifecycleLoading=current;
 current.promise=readLifecycle().finally(()=>{if(lifecycleLoading===current)lifecycleLoading=null;});return current.promise;
}
async function readLifecycle(){
 lifecycleView=null;lifecycleDraft=null;lifecycleRead=null;$('lifecycle-form-panel').hidden=true;$('lifecycle-actions').replaceChildren();
 if(!state.csrf||!state.activeProject||!state.view){text('lifecycle-summary','Выберите проект.');return;}
 const pid=state.activeProject;
 try{
  const v=await api(lifecycleBase(pid)+'/lifecycle');if(pid!==state.activeProject)return;lifecycleView=v;
  const st=v.status||{};text('lifecycle-summary',st.runtime_phase|| (v.kind==='workspace'?'Read-only Brownfield assessment; baseline approval выполняется отдельно.':'Migration: проверьте ограничения и подтвердите явно.'));
  $('lifecycle-levels').replaceChildren();for(const [key,label] of [['target_level','Target'],['active_stage','Active'],['claimed_current_level','Claimed'],['observed_candidate_level','Observed'],['highest_accepted_level','Highest accepted']]){const d=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=st[key]||'—';d.append(dt,dd);$('lifecycle-levels').append(d);}
  text('lifecycle-gaps',format(v.missing_subjects||v.assessments||v.migration?.validation||[]));text('lifecycle-context',format(v));text('lifecycle-history',format({acceptance:v.acceptance_history||[],records:v.record_history||{}}));
  const actions=state.view?.available_actions||[];
  for(const action of Object.keys(lifecycleLabels).filter(x=>x.startsWith('prepare-')||['resume-stage-gate','assess-maturity','recover-migration'].includes(x))){
   const entry=actions.find(x=>x.action===action);if(!entry?.enabled)continue;
   const button=document.createElement('button');button.type='button';button.dataset.lifecycle=action;button.textContent=lifecycleLabels[action];button.disabled=state.requestBusy;
   button.onclick=()=>{if(action.startsWith('prepare-'))lifecycleAction(action,{});else if(window.confirm(action==='resume-stage-gate'?'Перепроверить gaps текущего Gate без изменения Task blocker?':action==='recover-migration'?'Подтвердить recovery существующего migration journal через core?':'Сохранить read-only assessment без выполнения команд репозитория?'))lifecycleAction(action,{confirmed:true});};$('lifecycle-actions').append(button);
  }
  try{lifecycleOperation=sessionStorage.getItem('harness-lifecycle-operation-'+pid);}catch(_){lifecycleOperation=null;}
  $('lifecycle-reconcile').disabled=!lifecycleOperation;
 }catch(e){text('lifecycle-summary',e.message);showNotice(e.message,'error');}
}
async function lifecycleAction(action,payload){
 if(!lifecycleView||state.requestBusy)return;const pid=state.activeProject,fp=lifecycleView.fingerprint;state.requestBusy=true;$('lifecycle-apply').disabled=true;
 try{
  const submitted=await api(lifecycleBase(pid)+'/operations',{method:'POST',body:{action,payload,expected_fingerprint:fp,idempotency_key:newIdempotencyKey()}});lifecycleOperation=submitted.operation_id;
  try{sessionStorage.setItem('harness-lifecycle-operation-'+pid,lifecycleOperation);}catch(_){}
  let op;for(let n=0;n<240;n++){op=(await api(lifecycleBase(pid)+'/operations/'+lifecycleOperation)).operation;text('lifecycle-operation',format(op));if(terminalStates.has(op.state))break;await new Promise(r=>setTimeout(r,500));}
  if(action.startsWith('prepare-')&&op.state==='SUCCEEDED'){
    lifecycleDraft=await api(lifecycleBase(pid)+'/lifecycle/drafts/'+lifecycleOperation);renderLifecycleDraft(lifecycleDraft.document);
  }else if(op.state==='SUCCEEDED'||op.state==='BLOCKED'){state.requestBusy=false;await selectProject(pid,true);text('lifecycle-operation',format(op));}
  showNotice(op.state==='SUCCEEDED'?'Операция завершена; фактический core result показан ниже.':op.error?.message_ru||op.state,op.state==='SUCCEEDED'?'success':'error');
 }catch(e){showNotice(e.message+' Автоматического повтора нет.','error');}
 finally{state.requestBusy=false;$('lifecycle-confirm').checked=false;$('lifecycle-apply').disabled=false;$('lifecycle-reconcile').disabled=!lifecycleOperation;}
}
$('lifecycle-apply').onclick=()=>{if(lifecycleDraft&&lifecycleRead)lifecycleAction(lifecycleDraft.action,{draft_id:lifecycleDraft.draft_id,document:lifecycleRead(),actor:$('lifecycle-actor').value,confirmed:$('lifecycle-confirm').checked,rationale:$('lifecycle-rationale').value});};
$('lifecycle-export').onclick=()=>{if(lifecycleRead)$('lifecycle-json').value=JSON.stringify(lifecycleRead(),null,2);};
$('lifecycle-import').onclick=()=>{try{const value=JSON.parse($('lifecycle-json').value);if(!value||Array.isArray(value)||Object.keys(value).length!==1||Object.keys(value)[0]!==Object.keys(lifecycleDraft.document)[0])throw new Error('Неверный envelope');renderLifecycleDraft(value);}catch(e){showNotice(e.message,'error');}};
$('lifecycle-reconcile').onclick=async()=>{if(!lifecycleOperation||state.requestBusy)return;try{const value=await api(lifecycleBase()+'/operations/'+lifecycleOperation+'/reconcile',{method:'POST',body:{confirm:true}});text('lifecycle-operation',format(value));await selectProject(state.activeProject,true);}catch(e){showNotice(e.message,'error');}};
async function selectLocalFolder(purpose){
 if(state.requestBusy)return;state.requestBusy=true;
 try{showNotice('Выберите папку в системном окне.');const value=await api('/api/local-selection',{method:'POST',body:{purpose,project_name:$('new-project-name').value||'Existing Harness project',mode:$('repository-mode').value,idempotency_key:newIdempotencyKey()}});if(value.project_id){state.requestBusy=false;await refresh();await selectProject(value.project_id);selectScreen(purpose==='repository'?'interview':'maintenance');}else showNotice('Выбор отменён.');}catch(e){showNotice(e.message,'error');}finally{state.requestBusy=false;}
}
$('select-repository').onclick=()=>selectLocalFolder('repository');
$('select-existing-project').onclick=()=>selectLocalFolder('project');

