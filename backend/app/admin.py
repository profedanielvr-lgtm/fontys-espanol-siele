"""Opaque, expiring teacher sessions. Student credentials cannot grant teacher access."""
import copy, hashlib, hmac, secrets, time
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import AdminSession, SecureAttempt
from .guards import quota

router=APIRouter(prefix='/api',tags=['Administración docente'])
def password_hash(password, salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
def admin(authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    token=(authorization or '').removeprefix('Bearer ')
    session=db.get(AdminSession,hashlib.sha256(token.encode()).hexdigest()) if 32<=len(token)<=128 else None
    if not session or session.expires_at<time.time():raise HTTPException(401,'Acceso docente requerido / Docentlogin vereist')
    return session
class Login(BaseModel):
    username:str=Field(max_length=100)
    password:str=Field(min_length=1,max_length=256)
@router.post('/admin/login',dependencies=[Depends(quota)])
def login(body:Login,db:Session=Depends(get_db)):
    stored=settings.admin_password_hash
    salt=stored.split(':')[0] if ':' in stored else 'unconfigured'
    valid=hmac.compare_digest(password_hash(body.password,salt),stored)
    if not valid or not hmac.compare_digest(body.username.encode(),settings.admin_username.encode()):raise HTTPException(401,'Credenciales incorrectas / Onjuiste inloggegevens')
    db.execute(delete(AdminSession).where(AdminSession.expires_at<time.time()))
    token=secrets.token_urlsafe(32)
    db.add(AdminSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=time.time()+3600));db.commit()
    return {'token':token,'expires_in':3600}
@router.post('/admin/logout')
def logout(s:AdminSession=Depends(admin),db:Session=Depends(get_db)):
    db.delete(s);db.commit();return {'ok':True}
@router.get('/admin/intentos',dependencies=[Depends(admin)])
def attempts(db:Session=Depends(get_db)):
    return [{'id':a.id,'estado':a.data['status'],'modalidad':a.data['modality'],'pendientes':[t for t in a.data['task_ids'] if t.startswith(('eie','eio')) and a.data.get('reviews',{}).get(t,{}).get('estado')!='revisado_por_docente']} for a in db.scalars(select(SecureAttempt).limit(200))]
def attempt(db,id):
    a=db.get(SecureAttempt,id)
    if not a:raise HTTPException(404,'Intento inexistente / Poging niet gevonden')
    return a
@router.get('/admin/intentos/{id}',dependencies=[Depends(admin)])
def detail(id:str,db:Session=Depends(get_db)):
    a=attempt(db,id)
    return {'id':a.id,'revision':a.revision,**{k:v for k,v in a.data.items() if k not in {'recordings','events','bank_snapshot'}},'grabaciones':list(a.data.get('recordings',{})), 'tareas':[{k:t.get(k) for k in ('id','title','instruction','stimulus')} for t in a.data.get('bank_snapshot',[]) ]}
def audio_file(a,key):
    record=a.data.get('recordings',{}).get(key)
    if not record:raise HTTPException(404,'Audio inexistente / Audio niet gevonden')
    root=settings.upload_dir.resolve();path=(root/record['file']).resolve()
    if path.parent!=root or not path.is_file():raise HTTPException(404,'Audio no disponible / Audio niet beschikbaar')
    mime={'.mp4':'audio/mp4','.webm':'audio/webm','.ogg':'audio/ogg','.wav':'audio/wav','.mp3':'audio/mpeg'}.get(path.suffix)
    if not mime:raise HTTPException(415,'Formato no admitido')
    return FileResponse(path,media_type=mime,filename=path.name,content_disposition_type='inline')
@router.get('/admin/intentos/{id}/audio/{task}/{part}',dependencies=[Depends(admin)])
def audio(id:str,task:str,part:int,db:Session=Depends(get_db)):
    return audio_file(attempt(db,id),f'{task}:{part}')
class Grade(BaseModel):
    revision:int=Field(ge=0)
    criterios:dict[str,Annotated[StrictInt,Field(ge=0,le=4)]]
    observaciones_es:str=Field(min_length=10,max_length=5000)
    observaciones_nl:str=Field(min_length=10,max_length=5000)
    audio_escuchado:bool=False
    nivel_estimado:str|None=Field(default=None,pattern=r'^(A1|A2|B1|B2|C1)$')
@router.post('/admin/intentos/{id}/propuesta-ia/{task}',dependencies=[Depends(admin),Depends(quota)])
async def proposal(id:str,task:str,request:Request,db:Session=Depends(get_db)):
    from .secure_exam import propose_review
    return await propose_review(task,request,attempt(db,id),db)
@router.post('/admin/intentos/{id}/calificar/{task}',dependencies=[Depends(admin)])
def grade(id:str,task:str,body:Grade,db:Session=Depends(get_db)):
    from sqlalchemy import update
    a=attempt(db,id)
    if a.data['status']!='finished' or task not in a.data['task_ids'] or not task.startswith(('eie-','eio-')):raise HTTPException(409,'Tarea no revisable / Taak niet beoordeelbaar')
    expected={'gramatica','coherencia','vocabulario','cumplimiento'}|({'pronunciacion','fluidez'} if task.startswith('eio') else set())
    if set(body.criterios)!=expected:raise HTTPException(422,'Criterios incompletos / Onvolledige criteria')
    if task.startswith('eio') and (not body.audio_escuchado or not any(k.startswith(task+':') for k in a.data.get('recordings',{}))):raise HTTPException(422,'Escucha el audio original / Beluister de oorspronkelijke opname')
    data=copy.deepcopy(a.data);previous=data.get('reviews',{}).get(task)
    data.setdefault('reviews',{})[task]={'estado':'revisado_por_docente','revision_humana':{**body.model_dump(exclude={'revision'}),'reviewer':settings.admin_username},'ai_proposal':previous.get('ai_proposal',previous) if previous else None,'reviewed_at':time.time(),'official':False}
    changed=db.execute(update(SecureAttempt).where(SecureAttempt.id==id,SecureAttempt.revision==body.revision).values(data=data,revision=body.revision+1)).rowcount
    if not changed:db.rollback();raise HTTPException(409,'Actualiza el intento / Vernieuw de poging')
    db.commit();return {'ok':True}
@router.get('/generar-reporte-pdf/{intento_id}')
def report(intento_id:str,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    a=attempt(db,intento_id)
    token=(authorization or '').removeprefix('Bearer ')
    if not hmac.compare_digest(a.token_hash,hashlib.sha256(token.encode()).hexdigest()) or a.expires_at<time.time():admin(authorization,db)
    if a.data['status']!='finished':raise HTTPException(409,'Examen en curso / Toets loopt nog')
    from .reports import make_report
    return Response(make_report(a),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="informe-{a.id}.pdf"'})
