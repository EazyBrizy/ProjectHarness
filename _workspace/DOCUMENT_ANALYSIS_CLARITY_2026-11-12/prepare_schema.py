"""Create the new local-web-only reply schema; v2/core contracts stay intact."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness/resources/local_web'
text=lambda maximum=2000:{'type':'string','minLength':1,'maxLength':maximum}
def obj(properties):
    return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
def array(items,maximum=40):
    return {'type':'array','maxItems':maximum,'items':items}
refs={'type':'array','maxItems':20,'uniqueItems':True,'items':text(100)}
s=json.loads((BASE/'gpt_exchange_reply_v2.schema.json').read_text('utf-8'))
s.update({'$id':'urn:project-harness:local-web:gpt-exchange-reply:3','title':'Document analysis draft reply v3'})
s['required'].remove('uncertainties');s['required'].append('analysis')
s['properties'].pop('uncertainties');s['properties']['envelope_version']={'const':3}
s['properties']['questions']=array(obj({'id':{'type':'string','pattern':'^[A-Z][A-Z0-9_]{1,79}$'},
    'field':text(120),'question':text(),'why':text(),'stage':{'enum':['CURRENT','FUTURE']},
    'blocking':{'type':'boolean'},'source_refs':refs}),30)
s['properties']['analysis']=obj({'summary':text(8000),
    'current_stage':obj({'title':text(200),'goal':text(3000),'basis':text(3000),'source_refs':refs}),
    'answers':array(obj({'title':text(200),'answer':text(6000),'status':{'enum':['DOCUMENTED','PROPOSED','CONFLICT']},'source_refs':refs})),
    'roadmap':array(obj({'title':text(200),'stage':{'enum':['CURRENT','FUTURE']},'goal':text(3000),
        'steps':array(text(2000),30),'done_when':array(text(2000),20),'source_refs':refs}),30),
    'notes':array(text(),20)})
(BASE/'gpt_exchange_reply_v3.schema.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Created v3 document analysis schema')
