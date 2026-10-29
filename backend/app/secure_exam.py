import copy
import json
import hashlib
import secrets
import time
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Header,UploadFile,File,Form,Request
from fastapi.responses import FileResponse
from sqlalchemy import select,update,delete
from sqlalchemy.orm import Session
from pydantic import Field
from .schemas import Strict
from .database import get_db
from .models import ExamTicket,SecureAttempt
from .bank import bank,get_task,stimulus
from .guards import quota
from .config import settings
from .media import receive_audio
from .evaluation import evaluate,EvaluationUnavailable,RUBRICA_VERSION
from .oral_evaluation import evaluate_oral

router=APIRouter(prefix='/api/secure',tags=['Sesión con autoridad del servidor'])
MODES={'Global':['lectura','escucha','escritura','oral'],'S1':['lectura','escucha'],'S2':['lectura','escritura'],'S3':['escucha','oral'],'S4':['oral'],'S5':['escritura','oral']}
TIMES={'lectura':3600,'escucha':3300,'escritura':3000,'oral':1200}
def digest(value):return hashlib.sha256(value.encode()).hexdigest()

class Enter(Strict):
    code:str=Field(min_length=16,max_length=128)
class Save(Strict):
    revision:int=Field(ge=0)
    answers:dict[str,int]=Field(default_factory=dict,max_length=40)
    text:str=Field(default='',max_length=15000)
    choices:dict[str,int]=Field(default_factory=dict,max_length=5)
class Rev(Strict):
    revision:int=Field(ge=0)
class Event(Strict):
    kind:str=Field(pattern='^(visibility_hidden|fullscreen_exit|connection_lost|candidate_note)$')
    note:str=Field(default='',max_length=500)

def authorized(authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Sesión requerida / Sessie vereist')
    token=authorization[7:]
    if not 32<=len(token)<=128:raise HTTPException(401,'Sesión inválida / Ongeldige sessie')
    attempt=db.scalar(select(SecureAttempt).where(SecureAttempt.token_hash==digest(token)))
    if not attempt or attempt.expires_at<time.time():raise HTTPException(401,'Sesión caducada / Sessie verlopen')
    return attempt

def commit(db,attempt,data,revision):
    result=db.execute(update(SecureAttempt).where(SecureAttempt.id==attempt.id,SecureAttempt.revision==revision).values(data=data,revision=revision+1),execution_options={'synchronize_session':False})
    if result.rowcount!=1:
        db.rollback();raise HTTPException(409,'Sesión actualizada en otro lugar; recarga / Sessie gewijzigd; vernieuw de pagina')
    db.commit();db.refresh(attempt)

def task_for(data,task_id):return next((t for t in data.get('bank_snapshot',[]) if t['id']==task_id),None) or get_task(task_id)
def current(data):return task_for(data,data['task_ids'][data['index']]) if data['status']=='active' else None
def move(data,skip=False):
    previous=current(data)
    index=data['index']+1
    while skip and index<len(data['task_ids']) and task_for(data,data['task_ids'][index])['skill']==previous['skill']:index+=1
    data['index']=index
    if index==len(data['task_ids']):data['status']='finished';data['deadline']=None;data['finished_at']=time.time();return
    task=current(data)
    if task['skill']!=previous['skill']:data['deadline']=time.time()+TIMES[task['skill']]
    if previous['skill']=='escucha' and task['skill']=='escritura' and data['modality']=='Global' and not data.get('break_done'):
        data['break_until']=time.time()+900;data['deadline']=None;data['break_done']=True
    data['task_deadline']=min(data['deadline'] or float('inf'),time.time()+task.get('audioSeconds',TIMES[task['skill']])) if task['skill']=='escucha' else None

def sync(db,attempt):
    data=copy.deepcopy(attempt.data);changed=False;now=time.time()
    if data.get('break_until') and data['break_until']<=now:
        ended=data['break_until'];data['break_until']=None;data['deadline']=ended+TIMES[current(data)['skill']];changed=True
    if data['status']=='active' and not data.get('break_until'):
        if data.get('deadline') and data['deadline']<=now:move(data,True);changed=True
        elif data.get('task_deadline') and data['task_deadline']<=now:move(data);changed=True
    if changed:commit(db,attempt,data,attempt.revision)

def public(attempt):
    data=attempt.data;t=current(data)
    sanitized=copy.deepcopy(t)
    if sanitized:
        for q in sanitized['questions']:q.pop('answer',None);q.pop('explanation',None)
    score={}
    if data['status']=='finished':
        for skill in ['lectura','escucha']:
            selected=[task_for(data,i) for i in data['task_ids'] if task_for(data,i)['skill']==skill]
            correct=total=0
            for task in selected:
                a=data['responses'].get(task['id'],{}).get('answers',{})
                if task.get('maxSelections'):
                    total+=task['maxSelections'];correct+=sum(a.get(q['id'])==1 and q['answer']==1 for q in task['questions'])
                else:total+=len(task['questions']);correct+=sum(a.get(q['id'])==q['answer'] for q in task['questions'])
            if total:score[skill]={'correct':correct,'total':total}
    return {'id':attempt.id,'modality':data['modality'],'bank_sha256':data.get('bank_sha256'),'revision':attempt.revision,'server_now':time.time(),'deadline':data['deadline'],'task_deadline':data.get('task_deadline'),
            'break_until':data.get('break_until'),'status':data['status'],'index':data['index'],'total_tasks':len(data['task_ids']),'task':sanitized,
            'response':data['responses'].get(t['id'],{}) if t else {},'scores':score,'reviews':data.get('reviews',{}),
            'writing_tasks':[{'id':i,'index':index,'title':task_for(data,i)['title']} for index,i in enumerate(data['task_ids']) if t and t['skill']=='escritura' and task_for(data,i)['skill']=='escritura'],
            'reviewable_tasks':[i for i in data['task_ids'] if task_for(data,i)['skill'] in {'escritura','oral'}],
            'oral_topic':data['responses'].get('eio-4',{}).get('choices',{}).get('eio-4',0),'event_count':len(data.get('events',[])),'recording_parts':list(data.get('recordings',{})),'pending_human_review':True}

@router.post('/sessions',status_code=201,dependencies=[Depends(quota)])
def enter(body:Enter,db:Session=Depends(get_db)):
    if settings.environment=='production' and not settings.secure_bank_path:raise HTTPException(503,'Falta banco privado de examen / Privé-toetsbank ontbreekt')
    code=digest(body.code);ticket=db.get(ExamTicket,code)
    if not ticket or ticket.expires_at<time.time():raise HTTPException(401,'Código inválido o caducado / Ongeldige of verlopen code')
    consumed=db.execute(update(ExamTicket).where(ExamTicket.code_hash==code,ExamTicket.used==0).values(used=1))
    if consumed.rowcount!=1:db.rollback();raise HTTPException(409,'Código ya utilizado / Code al gebruikt')
    snapshot=copy.deepcopy(bank())
    ids=[t['id'] for t in snapshot if t['skill'] in MODES[ticket.modality]]
    token=secrets.token_urlsafe(32);task=next(t for t in snapshot if t['id']==ids[0]);now=time.time()
    attempt=SecureAttempt(id=str(uuid4()),token_hash=digest(token),expires_at=now+86400,revision=0,
        data={'bank_snapshot':snapshot,'bank_sha256':digest(json.dumps(snapshot,sort_keys=True,ensure_ascii=False)),'modality':ticket.modality,'task_ids':ids,'index':0,'status':'active','deadline':now+TIMES[task['skill']],
              'task_deadline':now+task['audioSeconds'] if task['skill']=='escucha' else None,'responses':{},'recordings':{},'reviews':{},'events':[]})
    db.add(attempt);db.commit()
    return {'token':token,**public(attempt)}

@router.get('/session')
def state(a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    sync(db,a);return public(a)

def editable(a,db,revision=None):
    sync(db,a)
    if a.data['status']!='active' or a.data.get('break_until'):raise HTTPException(409,'La respuesta está cerrada / Antwoord is gesloten')
    if revision is not None and revision!=a.revision:raise HTTPException(409,'Revisión antigua; recarga / Verouderde versie; vernieuw')

@router.post('/response')
def save_response(body:Save,a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    editable(a,db,body.revision);t=current(a.data);valid={q['id']:q for q in t['questions']}
    if any(k not in valid or isinstance(v,bool) or not 0<=v<len(valid[k]['options']) for k,v in body.answers.items()):raise HTTPException(422,'Respuesta no válida / Ongeldig antwoord')
    if t.get('maxSelections') and sum(v==1 for v in body.answers.values())>t['maxSelections']:raise HTTPException(422,'Demasiadas selecciones / Te veel selecties')
    allowed={t['id']} if t.get('choices') else set()
    if t['id']=='eio-3':allowed={t['id']+'-0',t['id']+'-1'}
    if any(k not in allowed or v not in (0,1) for k,v in body.choices.items()):raise HTTPException(422,'Opción no válida / Ongeldige keuze')
    data=copy.deepcopy(a.data)
    if any(k.startswith(t['id']+':') for k in data['recordings']) and body.choices!=data['responses'].get(t['id'],{}).get('choices',{}):raise HTTPException(409,'La opción oral ya está fijada / Mondelinge keuze ligt vast')
    data['responses'][t['id']]={'answers':body.answers,'text':body.text if t['skill']=='escritura' else '', 'choices':body.choices,'saved_at':time.time()}
    commit(db,a,data,a.revision);return public(a)

@router.post('/next')
def advance(body:Rev,a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    editable(a,db,body.revision);data=copy.deepcopy(a.data);move(data);commit(db,a,data,a.revision);return public(a)

@router.post('/writing/{index}')
def select_writing(index:int,body:Rev,a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    editable(a,db,body.revision)
    if current(a.data)['skill']!='escritura' or not 0<=index<len(a.data['task_ids']) or task_for(a.data,a.data['task_ids'][index])['skill']!='escritura':raise HTTPException(409,'Navegación no permitida / Navigatie niet toegestaan')
    data=copy.deepcopy(a.data);data['index']=index;commit(db,a,data,a.revision);return public(a)

@router.post('/break/end')
def end_break(a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    sync(db,a)
    if not a.data.get('break_until'):raise HTTPException(409,'No hay descanso activo / Geen actieve pauze')
    data=copy.deepcopy(a.data);data['break_until']=None;data['deadline']=time.time()+TIMES[current(data)['skill']];commit(db,a,data,a.revision);return public(a)

@router.post('/events')
def event(body:Event,a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    data=copy.deepcopy(a.data)
    if len(data['events'])>=200:raise HTTPException(429,'Límite de incidencias / Incidentlimiet')
    data['events'].append({'kind':body.kind,'note':body.note,'server_at':time.time(),'not_proof_of_misconduct':True})
    commit(db,a,data,a.revision);return {'recorded':True}

@router.post('/oral',dependencies=[Depends(quota)])
async def receive_oral(part:int=Form(ge=0,le=3),revision:int=Form(ge=0),archivo:UploadFile=File(),a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    editable(a,db,revision);t=current(a.data)
    if t['skill']!='oral' or part>=len(t['prompts']):raise HTTPException(422,'Parte oral inválida / Ongeldig spreekonderdeel')
    extension={'audio/webm':'.webm','audio/ogg':'.ogg','audio/mp4':'.mp4','audio/wav':'.wav','audio/x-wav':'.wav'}.get((archivo.content_type or '').split(';')[0],'.invalid')
    target=settings.upload_dir/(uuid4().hex+extension)
    quality=await receive_audio(archivo,target)
    try:
        # Comprobar de nuevo el plazo después de decodificar, sin prolongarlo.
        db.refresh(a)
        if a.revision!=revision or a.data['status']!='active' or current(a.data)['id']!=t['id']:raise HTTPException(409,'Tarea cerrada / Taak gesloten')
        if quality['duration_seconds']>t.get('duration',300)+2:raise HTTPException(422,'Respuesta demasiado larga / Antwoord te lang')
        data=copy.deepcopy(a.data);key=f'{t["id"]}:{part}'
        if key in data['recordings']:raise HTTPException(409,'Respuesta ya recibida / Antwoord al ontvangen')
        data['recordings'][key]={'file':target.name,'quality':quality,'received_at':time.time()}
        commit(db,a,data,a.revision)
    except Exception:target.unlink(missing_ok=True);raise
    return public(a)

@router.post('/review/{task_id}',dependencies=[Depends(quota)])
async def propose_review(task_id:str,request:Request,a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    sync(db,a)
    if a.data['status']!='finished':raise HTTPException(409,'Termina primero el recorrido / Rond eerst de toets af')
    if task_id not in a.data['task_ids'] or task_for(a.data,task_id)['skill'] not in {'escritura','oral'}:raise HTTPException(422,'Tarea no evaluable / Taak niet te beoordelen')
    if a.data.get('reviews',{}).get(task_id,{}).get('estado')=='revisado_por_docente':raise HTTPException(409,'Revisión humana ya cerrada / Docentbeoordeling al afgesloten')
    previous=a.data.get('reviews',{}).get(task_id,{})
    if previous.get('estado')=='pendiente_revision_humana':return public(a)
    if previous.get('estado')=='procesando' and time.time()-previous.get('started_at',0)<180:raise HTTPException(409,'Evaluación en curso / Beoordeling loopt')
    t=task_for(a.data,task_id);response=a.data['responses'].get(task_id,{});choices=response.get('choices',{})
    if t['skill']=='escritura' and not response.get('text','').strip():raise HTTPException(422,'Sin respuesta / Geen antwoord')
    if t['skill']=='oral' and not any(key.startswith(task_id+':') for key in a.data['recordings']):raise HTTPException(422,'Sin grabación / Geen opname')
    working=copy.deepcopy(a.data);working['reviews'][task_id]={'estado':'procesando','started_at':time.time(),'rubrica_version':RUBRICA_VERSION}
    commit(db,a,working,a.revision)
    try:
        if t['skill']=='escritura':
            text=response.get('text','')
            if not text.strip():raise HTTPException(422,'Sin respuesta / Geen antwoord')
            result={'tipo':'escritura','estado':'pendiente_revision_humana','modelo':settings.openai_model,'rubrica_version':RUBRICA_VERSION,'evaluacion':(await evaluate(text,stimulus(t,choices.get(task_id,0)))).model_dump()}
        else:
            result={'tipo':'oral','estado':'pendiente_revision_humana','partes':{},'partes_esperadas':len(t['prompts'])}
            topic=a.data['responses'].get('eio-4',{}).get('choices',{}).get('eio-4',0)
            for key,record in a.data['recordings'].items():
                if not key.startswith(task_id+':'):continue
                part=int(key.split(':')[1]);consigna=stimulus(t,choices.get(task_id,0),part,topic,choices.get(task_id+f'-{part}',0))
                result['partes'][key]=await evaluate_oral(settings.upload_dir/record['file'],consigna,record['quality'])
            if not result['partes']:raise HTTPException(422,'Sin grabación / Geen opname')
    except (EvaluationUnavailable,HTTPException) as exc:
        db.refresh(a);failed=copy.deepcopy(a.data);failed['reviews'][task_id]={'estado':'no_disponible','rubrica_version':RUBRICA_VERSION}
        commit(db,a,failed,a.revision)
        if isinstance(exc,HTTPException):raise
        raise HTTPException(503,str(exc)) from exc
    # Conservar eventos que hayan llegado mientras el proveedor trabajaba.
    db.refresh(a);data=copy.deepcopy(a.data);data['reviews'][task_id]=result;commit(db,a,data,a.revision)
    return public(a)

@router.get('/oral/{task_id}/{part}')
def download_oral(task_id:str,part:int,a:SecureAttempt=Depends(authorized)):
    record=a.data['recordings'].get(f'{task_id}:{part}')
    if not record:raise HTTPException(404,'Audio no disponible / Audio niet beschikbaar')
    from .admin import audio_file
    return audio_file(a,f'{task_id}:{part}')

@router.delete('/session')
def erase(a:SecureAttempt=Depends(authorized),db:Session=Depends(get_db)):
    for record in a.data['recordings'].values():(settings.upload_dir/record['file']).unlink(missing_ok=True)
    db.execute(delete(SecureAttempt).where(SecureAttempt.id==a.id));db.commit();return {'deleted':True}
