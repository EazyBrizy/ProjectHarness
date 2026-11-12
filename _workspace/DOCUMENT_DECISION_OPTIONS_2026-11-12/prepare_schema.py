import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness/resources/local_web'
def obj(properties):return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
def text(n):return {'type':'string','minLength':1,'maxLength':n}
ident={'type':'string','pattern':'^[A-Z][A-Z0-9_]{1,79}$'}
schema=json.loads((BASE/'gpt_exchange_reply_v3.schema.json').read_text('utf-8'))
schema.update({'$id':'urn:project-harness:local-web:gpt-exchange-reply:4','title':'Document analysis with decision options v4'})
schema['properties']['envelope_version']={'const':4}
question=schema['properties']['questions']['items'];schema['properties']['questions']['maxItems']=50
extra={'existing_unknown_index':{'type':['integer','null'],'minimum':0},
 'choices':{'type':'array','minItems':2,'maxItems':3,'items':obj({'id':ident,'title':text(160),
    'description':text(1000),'tradeoffs':{'type':'array','maxItems':3,'items':text(400)},
    'answer':text(2000),'resolves_question':{'type':'boolean'},'changes':{'type':'array','maxItems':4,
       'items':obj({'field':text(120),'operation':{'enum':['SET','APPEND']},'value':{}})}})},
 'recommended_choice_id':ident,'recommendation_reason':text(1200)}
question['properties'].update(extra);question['required']+=list(extra)
(BASE/'gpt_exchange_reply_v4.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Created local-web v4; v2/v3/core schemas untouched')
