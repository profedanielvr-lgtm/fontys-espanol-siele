from contextlib import asynccontextmanager
from contextlib import suppress
import asyncio
from pathlib import Path
from typing import Literal
from uuid import uuid4
import json
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, engine, get_db, SessionLocal
from .models import Pregunta, IntentoExamen, RespuestaUsuario
from .schemas import CrearIntento, Escritura, Resultado, EvaluarTarea
from .evaluation import evaluate, EvaluationUnavailable, RUBRICA_VERSION
from .guards import RequestGuard, quota
from .secure_exam import router as secure_router
from .bank import get_task,stimulus
from .media import receive_audio
from .oral_evaluation import evaluate_oral
from .cleanup import cleanup_expired
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from .admin import router as admin_router
from .stimulus_audio import router as stimulus_router

@asynccontextmanager
async def lifespan(_):
    Base.metadata.create_all(engine)
    if 'variante_geolectal' not in {c['name'] for c in inspect(engine).get_columns('pregunta')}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE pregunta ADD COLUMN variante_geolectal VARCHAR(32) NOT NULL DEFAULT 'espanol_peninsular'"))
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        if db.scalar(select(Pregunta.id).limit(1)) is None:
            for nivel in ['A1','A2','B1','B2','C1']:
                db.add(Pregunta(destreza='escritura', nivel_mcer=nivel,
                    contenido_estimulo={'A1':'Escribe un mensaje para presentarte: nombre, ciudad y aficiones.',
                    'A2':'Responde a una invitación: agradece, explica si puedes asistir y propone qué llevar.',
                    'B1':'Escribe a una amiga: relata un viaje, explica un problema y cómo lo resolviste.',
                    'B2':'Escribe un artículo de opinión sobre el teletrabajo: argumenta ventajas y límites con ejemplos.',
                    'C1':'Redacta una propuesta para reducir el tráfico urbano: contrasta alternativas y defiende una solución considerando objeciones.'}[nivel],
                    metadatos_calibracion={'calibrado':False,'origen':'original','nivel_objetivo':nivel}))
            db.add(Pregunta(destreza='oral', nivel_mcer='A2', contenido_estimulo='Describe tu rutina y explica qué te gustaría cambiar. Tienes dos minutos.', metadatos_calibracion={'calibrado':False,'duracion_segundos':120}))
            db.commit()
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)
            await asyncio.to_thread(cleanup_expired)
    cleaner=asyncio.create_task(cleanup_loop())
    try:yield
    finally:
        cleaner.cancel()
        with suppress(asyncio.CancelledError):await cleaner

app = FastAPI(title='Práctica de español A1–C1', lifespan=lifespan)
app.add_middleware(RequestGuard)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=['GET','POST','DELETE'], allow_headers=['Content-Type','Authorization'])
app.include_router(secure_router)
app.include_router(admin_router)
app.include_router(stimulus_router)
settings.static_dir.mkdir(parents=True,exist_ok=True)
app.mount('/static',StaticFiles(directory=settings.static_dir),name='static')

@app.post('/api/evaluar-audio',dependencies=[Depends(quota)])
async def evaluar_audio(task_id:Literal['eio-1','eio-2','eio-3','eio-4','eio-5']=Form(),parte:int=Form(ge=0,le=3),
                        opcion:int=Form(default=0,ge=0,le=1),tema:int=Form(default=0,ge=0,le=1),archivo:UploadFile=File()):
    task=get_task(task_id)
    try:consigna=stimulus(task,opcion,parte,tema,opcion)
    except ValueError as exc:await archivo.close();raise HTTPException(422,'Consigna inválida / Ongeldige taak') from exc
    ext={'audio/webm':'.webm','audio/ogg':'.ogg','audio/mp4':'.mp4','audio/wav':'.wav','audio/x-wav':'.wav'}.get((archivo.content_type or '').split(';')[0],'.invalid')
    target=settings.upload_dir/(uuid4().hex+ext)
    try:
        quality=await receive_audio(archivo,target)
        result=await evaluate_oral(target,consigna,quality)
        return result
    except EvaluationUnavailable as exc:raise HTTPException(503,str(exc)) from exc
    finally:target.unlink(missing_ok=True)

@app.get('/api/salud')
def salud():
    return {'estado':'ok','modo':settings.ai_mode,'uso':'formativo no oficial','secure_sessions':True,'ai_configured':bool(settings.ai_mode=='openai' and settings.openai_api_key)}

@app.get('/api/preguntas')
def preguntas(db: Session = Depends(get_db)):
    # Nunca exponer claves de corrección ni metadatos internos al cliente.
    return [{'id':p.id,'destreza':p.destreza,'nivel_mcer':p.nivel_mcer,'contenido_estimulo':p.contenido_estimulo,'variante_geolectal':p.variante_geolectal,'opciones':p.opciones_json} for p in db.scalars(select(Pregunta))]

@app.post('/api/intentos', status_code=201)
def crear_intento(body: CrearIntento, db: Session = Depends(get_db)):
    intento = IntentoExamen(usuario_id=body.usuario_id)
    db.add(intento); db.commit()
    return {'id':intento.id,'estado':intento.estado}

def comprobar(db, intento_id, pregunta_id, destreza):
    intento, pregunta = db.get(IntentoExamen, intento_id), db.get(Pregunta, pregunta_id)
    if not intento or not pregunta:
        raise HTTPException(404, 'Intento o pregunta inexistente')
    if intento.estado != 'en_curso':
        raise HTTPException(409, 'Intento cerrado')
    if pregunta.destreza != destreza:
        raise HTTPException(422, 'Destreza incompatible')
    return pregunta

@app.post('/api/evaluar-escritura', response_model=Resultado,dependencies=[Depends(quota)])
async def escritura(body: Escritura, db: Session = Depends(get_db)):
    pregunta = comprobar(db, body.intento_id, body.pregunta_id, 'escritura')
    if not body.texto.strip():
        raise HTTPException(422, 'Texto vacío')
    try:
        evaluacion = await evaluate(body.texto, pregunta.contenido_estimulo)
    except EvaluationUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    registro = {'modo':settings.ai_mode,'modelo':settings.openai_model if settings.ai_mode=='openai' else None,
                'rubrica_version':RUBRICA_VERSION,'evaluacion':evaluacion.model_dump()}
    respuesta = RespuestaUsuario(intento_id=body.intento_id,pregunta_id=body.pregunta_id,
        respuesta_dada=body.texto,calificacion_ia=registro,retroalimentacion_ia=evaluacion.feedback_formativo)
    db.add(respuesta); db.commit()
    return {'respuesta_id':respuesta.id, **registro}

@app.post('/api/evaluar-tarea',dependencies=[Depends(quota)])
async def evaluar_tarea(body: EvaluarTarea):
    """Adaptador opcional del frontend estático; no guarda datos personales."""
    if not body.texto.strip():
        raise HTTPException(422,'Texto vacío')
    bank_path = Path(__file__).resolve().parents[2] / 'frontend' / 'public' / 'bank.json'
    if not bank_path.exists():
        raise HTTPException(503,'Banco de tareas no disponible en el servidor')
    bank = json.loads(bank_path.read_text(encoding='utf-8'))
    task = next(t for t in bank['tasks'] if t['id']==body.task_id)
    consigna = task['instruction'] + '\n' + task['stimulus']
    if task.get('choices'):
        consigna += '\n' + task['choices'][body.opcion]['stimulus']
    try:
        evaluacion = await evaluate(body.texto, consigna)
    except EvaluationUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
    return {'modo':settings.ai_mode,'modelo':settings.openai_model if settings.ai_mode=='openai' else None,
            'rubrica_version':RUBRICA_VERSION,'evaluacion':evaluacion.model_dump()}

@app.post('/api/audio', status_code=201)
async def audio(intento_id: int = Form(gt=0), pregunta_id: int = Form(gt=0),
                archivo: UploadFile = File(), db: Session = Depends(get_db)):
    comprobar(db, intento_id, pregunta_id, 'oral')
    mime=(archivo.content_type or '').split(';')[0].lower()
    extension={'audio/webm':'.webm','audio/ogg':'.ogg','audio/mp4':'.mp4','audio/wav':'.wav','audio/x-wav':'.wav'}.get(mime,'.invalid')
    destino=settings.upload_dir/(uuid4().hex+extension)
    try:
        quality=await receive_audio(archivo,destino)
        respuesta=RespuestaUsuario(intento_id=intento_id,pregunta_id=pregunta_id,respuesta_dada=destino.name,calificacion_ia={'quality':quality},retroalimentacion_ia='Audio recibido; pendiente de revisión humana. No evaluado.')
        db.add(respuesta);db.commit()
    except Exception:
        db.rollback();destino.unlink(missing_ok=True);raise
    return {'respuesta_id':respuesta.id,'bytes':quality['bytes'],'estado':'recibido_no_evaluado'}

@app.post('/api/audio-practica', status_code=201)
async def audio_practica(task_id: Literal['eio-1','eio-2','eio-3','eio-4','eio-5'] = Form(),
                         parte: int = Form(ge=0,le=3), archivo: UploadFile = File(),
                         db: Session = Depends(get_db)):
    bank_path = Path(__file__).resolve().parents[2] / 'frontend' / 'public' / 'bank.json'
    if not bank_path.exists():
        await archivo.close()
        raise HTTPException(503,'Banco de tareas no disponible')
    task = next(t for t in json.loads(bank_path.read_text(encoding='utf-8'))['tasks'] if t['id']==task_id)
    if parte>=len(task.get('prompts',[])):
        await archivo.close()
        raise HTTPException(422,'Parte oral inexistente')
    pregunta = db.scalar(select(Pregunta).where(Pregunta.metadatos_calibracion['task_id'].as_string()==task_id))
    if pregunta is None:
        pregunta = Pregunta(destreza='oral',nivel_mcer=task['level'],contenido_estimulo=task['instruction'],
                            metadatos_calibracion={'task_id':task_id,'calibrado':False,'origen':'fontys-original-2.0'})
        db.add(pregunta)
    intento = IntentoExamen(usuario_id='practica-local')
    db.add(intento)
    db.flush()
    result = await audio(intento.id,pregunta.id,archivo,db)
    respuesta = db.get(RespuestaUsuario,result['respuesta_id'])
    respuesta.calificacion_ia={'task_id':task_id,'parte':parte,'estado':'no_evaluado'}
    db.commit()
    return result
