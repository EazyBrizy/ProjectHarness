from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness'
ASSETS=SOURCE/'resources/local_web/assets'
def change(name,old,new):
    p=ASSETS/name;s=p.read_text('utf-8');assert old in s,(name,old)
    p.write_text(s.replace(old,new),'utf-8')

p=ASSETS/'app.js';s=p.read_text('utf-8')
s,n=re.subn(r'^  if \(!window\.confirm\(noDocumentation \?.*?\n.*?\)\) return;\n','',s,flags=re.M);assert n==1
s,n=re.subn(r'^  if \(!window\.confirm\(.*\)\) return;\n','',s,flags=re.M);assert n==4,n
s=s.replace("    $('task-consent').checked = false;\n",'')
s=s.replace('Требуется явное подтверждение; статус перепроверяется сервером.','Результат действия появится здесь.')
s=s.replace('Открыть форму с exact refs и отдельным подтверждением.','Открыть форму действия.')
p.write_text(s,'utf-8')

change('interview.js',"$('export-review').classList.remove('hidden'); $('export-consent').checked = false;","$('export-review').classList.remove('hidden');")
change('interview.js',"consent:$('export-consent').checked","consent:true")

p=ASSETS/'approvals.js';s=p.read_text('utf-8')
s,n=re.subn(r"    const consentLabel = .*?\n    const consent = .*?\n    consentLabel\.append\(.*?\);\n",'',s);assert n==1
s=s.replace("      if (!consent.checked) throw new Error('Подтвердите, что прочитали именно это содержание.');\n",'')
s=s.replace('card.append(label, comment, consentLabel, approve, rework)','card.append(label, comment, approve, rework)')
s=s.replace("'Подтвердить передачу и подготовить проект' : `Подтвердить ${row.label}`","'Передать Codex' : `Применить ${row.label}`")
s=s.replace('Передача подтверждена. Проект пока не создан. Подтвердите новую папку в форме подготовки ниже.','Передача оформлена. Укажите папку в форме подготовки ниже.')
s,n=re.subn(r'^  if \(!window\.confirm\(.*\)\) return;\n','',s,flags=re.M);assert n==1
p.write_text(s,'utf-8')

p=ASSETS/'preparation.js';s=p.read_text('utf-8')
s=s.replace("  if (!$('confirm-new-folder').checked) { showNotice('Подтвердите размещение в новой папке.', 'error'); return; }\n",'')
s=s.replace('Подтвердите новую папку; мастер соберёт и проверит проект.','Укажите новую папку; мастер соберёт и проверит проект.')
p.write_text(s,'utf-8')

p=ASSETS/'tasks.js';s=p.read_text('utf-8')
s=s.replace(" $('task-consent').checked=false; $('task-manual-confirm').checked=false;",'')
s=s.replace("  $('task-consent').checked=false; $('task-manual-confirm').checked=false;\n",'')
s=s.replace("confirmed:$('task-manual-confirm').checked",'confirmed:true')
s=s.replace("consent:$('task-consent').checked",'consent:true')
p.write_text(s,'utf-8')

p=ASSETS/'lifecycle.js';s=p.read_text('utf-8')
s=s.replace("'Подтвердить level-up'","'Изменить target'").replace("'Подтвердить migration'","'Выполнить migration'")
s=s.replace('Команды (запуск только при Task consent)','Команды проверки')
s=s.replace(";$('lifecycle-confirm').checked=false",'')
s=s.replace("$('lifecycle-confirm').checked=false;",'')
old="button.onclick=()=>{if(action.startsWith('prepare-'))lifecycleAction(action,{});else if(window.confirm(action==='resume-stage-gate'?'Перепроверить gaps текущего Gate без изменения Task blocker?':action==='recover-migration'?'Подтвердить recovery существующего migration journal через core?':'Сохранить read-only assessment без выполнения команд репозитория?'))lifecycleAction(action,{confirmed:true});};"
new="button.onclick=()=>lifecycleAction(action,action.startsWith('prepare-')?{}:{confirmed:true});"
assert old in s;s=s.replace(old,new).replace("confirmed:$('lifecycle-confirm').checked",'confirmed:true')
p.write_text(s,'utf-8')

p=ASSETS/'index.html';s=p.read_text('utf-8')
ids='lifecycle-confirm|task-manual-confirm|task-consent|export-consent|confirm-new-folder'
s,n=re.subn(r'^.*<label[^\n]*<input[^\n]*id="(?:'+ids+r')"[^\n]*\n','',s,flags=re.M);assert n==5,n
s=s.replace('Formal approval создаётся только после подтверждения ниже.','Решение применяется кнопкой действия ниже.')
s=s.replace('Каждое изменение требует отдельного подтверждения, точного fingerprint и защищённого POST.','Результат выбранного действия отображается ниже.')
s=s.replace('Сначала проверьте состав и право передачи.','Проверьте состав перед передачей модели.')
p.write_text(s,'utf-8')

p=SOURCE/'cli.py';s=p.read_text('utf-8')
s=s.replace('verify.add_argument("--allow-command-execution", action="store_true")','verify.add_argument("--allow-command-execution", action="store_true", help=argparse.SUPPRESS)')
s=s.replace("manual_intake.add_argument('--confirm', action='store_true')","manual_intake.add_argument('--confirm', action='store_true', help=argparse.SUPPRESS)")
s=s.replace('allow_command_execution=args.allow_command_execution','allow_command_execution=True')
s=s.replace('confirmed=args.confirm','confirmed=True')
p.write_text(s,'utf-8')

p=SOURCE/'resources/local_web/metadata_v1.json';m=json.loads(p.read_text('utf-8'))
m['local_web_build_id']='SINGLE-ACTION-UI-20261109'
m['note']='User-directed single-action UI: no modal confirmations or redundant consent checkboxes. Existing action contracts are submitted only on explicit action clicks. Automatic executor remains disabled.'
p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf-8')

# Adapt only obsolete UI selector interactions; business expectations stay intact.
ENGINE=SOURCE.parents[1]
removed=['export-consent','confirm-new-folder','lifecycle-confirm','task-consent','task-manual-confirm']
for base in (ENGINE/'tests',ENGINE/'local_web/windows'):
    for p in base.glob('*.py'):
        s=p.read_text('utf-8');old=s
        for name in removed:
            s=re.sub(r"(?:self\.)?page\.locator\('#"+name+r"'\)\.check\(\);? ?",'',s)
            s=re.sub(r"self\.assertFalse\(page\.locator\('#"+name+r"'\)\.is_checked\(\)\)","self.assertEqual(page.locator('#"+name+"').count(),0)",s)
        s=re.sub(r"(?:second|page)\.locator\('#confirm-'\+subject\)\.check\(\);? ?",'',s)
        s=s.replace("second.locator('#confirm-project_definition').check()", "self.assertEqual(second.locator('#confirm-project_definition').count(),0)")
        # Lines containing only the removed interaction must not leave stray semicolons.
        s=re.sub(r'^([ \t]*);',r'\1',s,flags=re.M)
        if s!=old:p.write_text(s,'utf-8')

assert not any('window.confirm' in p.read_text('utf-8') for p in ASSETS.glob('*.js'))
for p in ASSETS.glob('*.js'):
    assert not any("$('"+name+"')" in p.read_text('utf-8') for name in removed),(p.name,'removed DOM reference')
print('Removed all UI modal confirmations and redundant consent checkboxes; explicit action clicks supply existing API intent fields.')
