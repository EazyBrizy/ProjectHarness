from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness'
ASSETS=SRC/'resources/local_web/assets'
p=ASSETS/'interview.js';s=p.read_text('utf-8')
s=s.replace("'Входит в scope'","'Входит в проект'").replace("'Не входит в scope'","'Не входит в проект'").replace("'Нерешённые material вопросы'","'Вопросы, которые ещё нужно решить'").replace("'Profile ref'","'Профиль проекта'").replace("'Обоснование profile'","'Почему выбран этот профиль'")
at="function interviewPath(suffix = '')"
helpers="""const displayLabels = {...fieldLabels,
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
  if(Array.isArray(value)) return value.length?value.map(readable).join('\\n'):'Не заполнено';
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
"""
assert at in s;s=s.replace(at,helpers+at)
s=s.replace("element('option', option || 'Ответ не выбран')","element('option', valueLabels[option] || option || 'Ответ не выбран')")
s=s.replace("box.append(element('h3', q.text), element('p', q.why_asked, 'muted small'));","box.append(element('h3', displayLabel(q.field)), element('p', 'Укажите, что вам известно. Неизвестное можно уточнить с помощью модели.', 'muted small'));")
s=s.replace('Загрузите MD/ZIP или явно подтвердите отсутствие документации во вкладке «Документы».','Загрузите документы или выберите «Документации нет» во вкладке «Документы».')
s=s.replace('Это структурированное предложение заполняется через GPT draft exchange ниже. Оно проверяется схемой и показывается в diff до применения.','Эту часть можно заполнить с помощью модели. Её предложения появятся в списке изменений перед сохранением.')
a=s.index("  for (const fact of view.known_answers) {");b=s.index('\n}\nasync function loadInterview()',a)
s=s[:a]+"""  const facts=view.known_answers.filter(f=>!templateFields.has(f.field) && displayLabels[f.field] && meaningful(f.value));
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
  }"""+s[b:]
s=s.replace('Выберите Greenfield intake во вкладке «Проекты» или создайте его во вкладке «Документы».','Выберите подготовку проекта во вкладке «Проекты» или создайте её во вкладке «Документы».').replace('Читаем текущие вопросы и readiness…','Загружаем сведения и вопросы…')
a=s.index("    text('interview-status', `${view.readiness.status}");b=s.index("    $('recover-reply')",a)
s=s[:a]+"""    const freshPack=view.exports.some(x=>x.binding.fingerprint===view.fingerprint);
    const applied=view.imports.some(x=>x.state==='COMMITTED');
    text('interview-status',view.recovery_required?'Сохранение ответа было прервано':
      !applied && view.documents.length ? freshPack?'Пакет подготовлен. Ожидается ответ модели.':'Документы загружены и готовы к анализу.':
      view.readiness.status==='WAITING_DECISION'?'Нужно выбрать целевой уровень проекта.':
      view.readiness.missing_fields.length?'Есть вопросы для уточнения.':'Основные сведения о проекте заполнены.');
    text('interview-next',view.recovery_required?'Нажмите «Восстановить сохранение ответа».':
      freshPack?'Скачайте пакет ниже и передайте его ChatGPT или Codex CLI. Полученный ответ вставьте на шаге 2.':
      !applied && view.documents.length?'Следующий шаг: нажмите «Подготовить пакет для анализа». Загрузка файлов сама по себе не запускает анализ.':
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
"""+s[b:]
s=s.replace('Ответы проверены и сохранены ядром. Formal approvals не назначены.','Ответы проверены и сохранены. Можно продолжить работу с проектом.')
s=s.replace('Сверка: ${result.status}.','Состояние сохранения обновлено.')
s=s.replace("value === 'UNKNOWN' ? 'Не проверено' : value","valueLabels[value] || value")
s=s.replace("`${exportReview.warning_ru}\\nSensitivity проекта: ${exportReview.project_data_sensitivity || 'не определена'}; draft: ${exportReview.draft_bytes} байт; документов: ${exportReview.documents.length}.`","`В пакет войдут документы (${exportReview.documents.length}), заполненные сведения и вопросы. Выберите категорию данных для документов и черновика.`")
s=s.replace("`${doc.original_name}/${doc.source_relative_path} · ${doc.byte_size} байт · ${doc.sha256}`","doc.source_relative_path")
s=s.replace('Pack создан. Скачивание и копирование — отдельные ваши действия.','Пакет готов. Скачайте его и передайте модели; затем вставьте её ответ на шаге 2.')
s=s.replace('Prompt скопирован по вашему действию.','Инструкция для модели скопирована.').replace('Clipboard недоступен. Выделите текст prompt и скопируйте вручную.','Не удалось скопировать автоматически. Выделите инструкцию и скопируйте её вручную.')
s=s.replace('`Export ${item.export_revision} · ${item.exchange_id} · ${item.files.length} файл(ов)`','`Пакет для анализа №${item.export_revision} · файлов: ${item.files.length}`')
s=s.replace("box.append(element('pre', item.prompt, 'source-preview'));","box.append(element('p','Скачайте все файлы этого пакета и приложите их в ChatGPT или Codex CLI. Вместе с файлами передайте инструкцию ниже.'));\n    const instructions=element('details');instructions.append(element('summary','Инструкция для модели'),element('pre',item.prompt,'source-preview'));box.append(instructions);")
s=s.replace("'Копировать prompt'","'Копировать инструкцию'")
s=s.replace('`${file.name} · ${file.bytes} байт · ${file.sha256} `','`${file.name} · ${Math.ceil(file.bytes/1024)} КБ `')
s=s.replace('Устарел после изменения draft/источников.','Пакет устарел после изменения сведений или документов. Подготовьте новый пакет.')
s=s.replace('Этот exact ответ уже применён; повторного изменения нет.','Этот ответ уже сохранён. Повторное сохранение не требуется.').replace('Preview готов. Canonical draft ещё не изменён.','Изменения показаны ниже. Сведения проекта ещё не изменены.')
a=s.index("  text('preview-summary', `${preview.state}");b=s.index('  for (const row of preview.diff)',a)
s=s[:a]+"""  text('preview-summary',`Изменений: ${preview.diff.length}. Осталось вопросов: ${preview.questions.filter(q=>q.status==='OPEN').length}. Изменения ещё не сохранены.`);
  text('interview-preview-technical',format(preview));
  text('interview-next','Посмотрите предложения модели на шаге 2. Нажмите «Сохранить предложения», чтобы внести их в черновик проекта.');
"""+s[b:]
s=s.replace("element('h4', row.field)","element('h4', displayLabel(row.field))").replace("format(row.before)","readable(row.before)").replace("'Imported draft (не verified)'","'Предложение модели'").replace("format(row.after)","readable(row.after)")
s=s.replace("`Missing fields: ${preview.readiness.missing_fields.join(', ') || 'нет'}.`","`Нужно уточнить: ${preview.readiness.missing_fields.map(displayLabel).join(', ') || 'нет'}.`")
# The existing template has one combined string, keep remaining questions readable too.
s=s.replace("Missing fields: ${preview.readiness.missing_fields.join(', ') || 'нет'}","Нужно уточнить: ${preview.readiness.missing_fields.map(displayLabel).join(', ') || 'нет'}")
s=s.replace('Draft применён. Проверьте оставшиеся вопросы; это не formal approval.','Предложения сохранены в черновике. Посмотрите оставшиеся вопросы.').replace('Import отменён до commit. Canonical draft сохранён.','Предложения отклонены. Сведения проекта не изменились.')
s=s.replace("`${item.import_id} · ${item.state} · ${item.response_digest}`","`Ответ модели №${imports.indexOf(item)+1}: ${{PREVIEW:'ожидает сохранения',COMMITTED:'сохранён',CANCELLED:'отклонён'}[item.state] || 'проверяется'}`")
p.write_text(s,'utf-8')

p=ASSETS/'index.html';s=p.read_text('utf-8');a=s.index('      <section id="interview-panel"');b=s.index('      <section id="approvals-panel"',a)
s=s[:a]+'''      <section id="interview-panel" class="panel hidden" aria-labelledby="interview-title">
        <h2 id="interview-title">Анализ документов и уточнение проекта</h2>
        <p id="interview-status" role="status">Выберите проект.</p>
        <div id="interview-body" class="hidden">
          <div class="next"><p id="interview-next"></p></div>
          <div id="interview-documents" class="body-value"></div>
          <button id="interview-documents-link" type="button" class="quiet">Открыть документы</button>
          <h3>1. Подготовьте документы для анализа</h3>
          <p>Harness соберёт документы и вопросы в пакет. Передайте его ChatGPT или Codex CLI, затем верните ответ на шаге 2. Автоматическая отправка модели не выполняется.</p>
          <button id="review-export" type="button" class="document-primary">Подготовить пакет для анализа</button>
          <div id="export-review" class="hidden">
            <p id="export-warning" class="body-value"></p>
            <div id="export-documents"></div>
            <label for="draft-classification">Категория данных черновика и ответов</label>
            <select id="draft-classification"><option value="UNKNOWN">Не указано</option><option value="PUBLIC">Общедоступные</option><option value="INTERNAL">Внутренние</option><option value="CONFIDENTIAL">Конфиденциальные</option><option value="RESTRICTED">С ограниченным доступом</option><option value="SECRET">Секретные</option><option value="REGULATED">Регулируемые</option></select>
            <button id="create-export" type="button" class="document-primary">Создать пакет для анализа</button>
          </div>
          <div id="export-history"></div>
          <hr>
          <h3>2. Верните ответ модели</h3>
          <p>Попросите модель выполнить инструкцию из пакета. Вставьте сюда полный ответ в формате JSON — Harness покажет предложенные изменения перед сохранением.</p>
          <label for="gpt-reply">Ответ модели в формате JSON (до 512 КБ)</label>
          <textarea id="gpt-reply" rows="8" spellcheck="false" placeholder="Вставьте сюда полный JSON из ответа модели"></textarea>
          <button id="preview-reply" type="button" class="outline">Показать предложенные изменения</button>
          <div id="repair-area" class="hidden"><p>Формат ответа не подошёл. Скопируйте инструкцию исправления и передайте её модели вместе с исходным пакетом.</p><pre id="repair-prompt" class="source-preview"></pre>
            <button id="copy-repair" type="button" class="outline">Копировать инструкцию исправления</button></div>
          <div id="import-preview" class="hidden">
            <h3>Предложенные изменения</h3>
            <p id="preview-summary" role="status"></p>
            <div id="reply-diff"></div>
            <button id="commit-reply" type="button" class="outline">Сохранить предложения</button>
            <button id="cancel-reply" type="button" class="quiet">Отклонить предложения</button>
            <details><summary>Технические сведения об ответе</summary><pre id="interview-preview-technical" class="source-preview"></pre></details>
          </div>
          <div id="import-history"></div>
          <hr>
          <h3>3. Уточните оставшиеся вопросы</h3>
          <p class="muted">Можно ответить самостоятельно или уточнить ответы после анализа моделью. Сведения сохраняются в черновике проекта.</p>
          <form id="answers-form"><div id="question-fields" class="interview-fields"></div>
            <button id="save-answers" type="submit" class="outline">Сохранить ответы</button>
          </form>
          <button id="check-answers" type="button" class="outline">Проверить заполнение</button>
          <button id="recover-reply" type="button" class="outline hidden">Восстановить сохранение ответа</button>
          <details><summary>Сохранённые сведения о проекте</summary>
            <p class="muted">Здесь показаны заполненные сведения черновика и применённые предложения модели. У каждого ответа указан источник. Служебные настройки шаблона не показаны.</p>
            <div id="known-answers"></div>
          </details>
          <details id="interview-technical"><summary>Технические сведения</summary><pre id="interview-readiness" class="source-preview"></pre></details>
        </div>
      </section>
'''+s[b:];p.write_text(s,'utf-8')

p=ASSETS/'app.js';s=p.read_text('utf-8').replace('Уточните существенные пробелы, подготовьте пакет и вручную импортируйте черновик внешнего GPT.','Подготовьте документы для анализа, получите ответ модели и уточните сведения о проекте.').replace('Статус получен. GET не запускает проектные операции.','Состояние обновлено.').replace('Список обновлён. Изменяющих операций не выполнено.','Список проектов обновлён.');p.write_text(s,'utf-8')
p=SRC/'resources/local_web/metadata_v1.json';m=json.loads(p.read_text('utf-8'));m['local_web_build_id']='CLEAR-INTERVIEW-20261110';m['note']='Presentation-only interview clarity: Russian labels, explicit analysis steps, meaningful draft information, technical hashes collapsed; no core/API/schema changes.';p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf-8')

for name in ('test_ph_lw_06_http.py','test_ph_lw_08_http.py','test_ph_lw_12_acceptance.py'):
 p=SRC.parents[1]/'tests'/name;s=p.read_text('utf-8').replace('Ответы проверены и сохранены ядром','Ответы проверены и сохранены').replace("to_contain_text('PREVIEW')","to_contain_text('Изменений:')").replace("to_contain_text('WAITING_DECISION')","to_contain_text('Нужно выбрать целевой уровень')");p.write_text(s,'utf-8')
print('Interview presentation updated. API payloads, canonical data, hashes and statuses unchanged.')
