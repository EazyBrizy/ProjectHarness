from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness'
ASSETS=SRC/'resources/local_web/assets'
p=ASSETS/'interview.js';s=p.read_text('utf-8')
s=s.replace('let exportReview = null;','let cliConnectionView = null, cliJobView = null, cliPollTimer = null;')
s=s.replace('interviewView = exportReview = replyPreview = null;','interviewView = replyPreview = cliJobView = null; clearTimeout(cliPollTimer);')
s=s.replace("  $('export-review').classList.add('hidden');\n",'')
s=s.replace('Следующий шаг: нажмите «Подготовить пакет для анализа». Загрузка файлов сама по себе не запускает анализ.','Выберите способ: автоматический анализ через CLI или пакет для ручной передачи модели.')
s=s.replace("    else { replyPreview = null; $('import-preview').classList.add('hidden'); }","    else { replyPreview = null; $('import-preview').classList.add('hidden'); }\n    await loadCliState();")
s=s.replace("    for (const control of $('interview-panel').querySelectorAll('button,input,textarea,select')) control.disabled = false;","    for (const control of $('interview-panel').querySelectorAll('button,input,textarea,select')) control.disabled = false;\n    renderCliState();")
a=s.index('function classificationSelect(');b=s.index('async function explicitCopy',a)
s=s[:a]+"""function renderCliState() {
  const active=['QUEUED','RUNNING','VALIDATING','CANCELLING'].includes(cliJobView?.state);
  text('cli-connection-status',cliConnectionView?.connected?'Codex CLI подключён.':'Подключите установленный Codex CLI или выберите ручной пакет.');
  text('cli-analysis-status',cliJobView?.job_id?cliJobView.message_ru:'После запуска результат анализа появится здесь, без скачивания пакета и копирования JSON.');
  $('cli-connect').textContent=cliConnectionView?.connected?'Проверить подключение':'Подключить CLI';
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
  await api(interviewPath('/analysis/package'),{method:'POST',body:{
    expected_fingerprint:interviewView.fingerprint,idempotency_key:newIdempotencyKey()}});
  await loadInterview();showNotice('Пакет готов. Скачайте его и передайте ChatGPT или Codex CLI.','success');
}));
"""+s[b:]
p.write_text(s,'utf-8')

p=ASSETS/'index.html';s=p.read_text('utf-8')
a=s.index('          <h3>1. Подготовьте документы для анализа</h3>');b=s.index('          <div id="export-history">',a)
s=s[:a]+'''          <h3>1. Выберите способ анализа документов</h3>
          <section class="question" aria-labelledby="cli-analysis-title">
            <h4 id="cli-analysis-title">Автоматически через Codex CLI</h4>
            <p>Подключите Codex CLI, установленный на этом компьютере. Harness сам передаст документы на анализ и покажет предложения в браузере. Скачивать пакет и переносить JSON не потребуется.</p>
            <p id="cli-connection-status" role="status">CLI пока не подключён.</p>
            <button id="cli-connect" type="button" class="outline">Подключить CLI</button>
            <button id="cli-analyze" type="button" class="document-primary">Анализировать документы через CLI</button>
            <button id="cli-analysis-cancel" type="button" class="quiet hidden">Остановить анализ</button>
            <p id="cli-analysis-status" role="status" aria-live="polite"></p>
          </section>
          <section class="question" aria-labelledby="manual-analysis-title">
            <h4 id="manual-analysis-title">Вручную через ChatGPT или Codex</h4>
            <p>Harness сформирует пакет документов. Скачайте его, передайте выбранной модели, а её ответ вставьте на шаге 2. Подключать CLI к приложению для этого не требуется.</p>
            <button id="review-export" type="button" class="outline">Сформировать пакет вручную</button>
          </section>
'''+s[b:]
s=s.replace('Полученный ответ в формате JSON','Полученный ответ в формате JSON')
s=s.replace('Попросите модель выполнить инструкцию из пакета. Вставьте сюда полный ответ в формате JSON — Harness покажет предложенные изменения перед сохранением.','При анализе через CLI предложения появятся здесь автоматически. При ручном обмене вставьте полный JSON из ответа модели — Harness покажет изменения перед сохранением.')
p.write_text(s,'utf-8')

p=SRC/'resources/local_web/metadata_v1.json';m=json.loads(p.read_text('utf-8'))
m['local_web_build_id']='CLI-DOC-ANALYSIS-20261110'
m['note']='Explicitly authorized reusable Codex CLI connection and read-only document analysis, with manual package alternative. No product Task automation; no per-document classification UI; strict existing preview validation.'
p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf-8')

p=ASSETS/'app.js';s=p.read_text('utf-8').replace('Подготовьте документы для анализа, получите ответ модели и уточните сведения о проекте.','Выберите автоматический анализ через CLI или ручной пакет для модели, затем уточните сведения о проекте.');p.write_text(s,'utf-8')
print('Dual-mode analysis UI added; classification selectors removed. No extra confirmations.')
