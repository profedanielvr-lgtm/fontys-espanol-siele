"""Public stimulus MP3s only. Never publish uploads or private exam transcripts."""
import hashlib, json, os
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from .config import settings
from .admin import admin
from .guards import quota
from .media import command

VARIANTS={'mexicano':'español de México, seseo natural', 'rioplatense':'español rioplatense de Buenos Aires, voseo y yeísmo rehilado naturales', 'caribeño':'español caribeño de Puerto Rico, ritmo natural', 'andino':'español andino de Bogotá, articulación natural', 'espanol_peninsular':'español centro-norte de España, distinción entre s y z'}
router=APIRouter(prefix='/api',tags=['Audio de estímulos públicos'])
def public_texts():
    # This file is already public. Do not use settings.secure_bank_path here.
    from pathlib import Path
    tasks=json.loads((Path(__file__).resolve().parents[2]/'frontend/public/bank.json').read_text(encoding='utf-8'))['tasks']
    texts=set()
    for t in tasks:
        texts.add(t.get('stimulus',''))
        texts.update(t.get('prompts',[]));texts.update(t.get('alternativePrompts',[]))
    return texts
def name(text,variant):return hashlib.sha256((variant+'\n'+text).encode()).hexdigest()+'.mp3'
@router.get('/audio-estimulo')
def locate(texto:str=Query(max_length=4096),variante_geolectal:str='espanol_peninsular'):
    if variante_geolectal not in VARIANTS or texto not in public_texts():raise HTTPException(404,'Estímulo público no encontrado / Publieke audio niet gevonden')
    filename=name(texto,variante_geolectal)
    if not (settings.static_dir/'audio'/filename).is_file():raise HTTPException(404,'Audio pendiente de preparación docente / Audio moet nog worden voorbereid')
    return {'url':'/static/audio/'+filename,'mime':'audio/mpeg','variante_geolectal':variante_geolectal,'voz_sintetica':True,'validacion_geolectal':'pendiente de escucha humana'}
class Generate(BaseModel):
    texto:str=Field(min_length=1,max_length=4096)
    variante_geolectal:str='espanol_peninsular'
@router.post('/admin/audio-estimulo',dependencies=[Depends(admin),Depends(quota)])
async def generate(body:Generate):
    if body.variante_geolectal not in VARIANTS or body.texto not in public_texts():raise HTTPException(422,'Texto o variante no admitidos')
    if not settings.openai_api_key:raise HTTPException(503,'TTS no configurado / TTS niet ingesteld')
    folder=settings.static_dir/'audio';folder.mkdir(parents=True,exist_ok=True)
    target=folder/name(body.texto,body.variante_geolectal)
    if not target.exists():
        temporary=folder/(uuid4().hex+'.tmp')
        encoded=folder/(uuid4().hex+'.mp3')
        try:
            async with AsyncOpenAI(api_key=settings.openai_api_key,timeout=60,max_retries=1) as client:
                async with client.audio.speech.with_streaming_response.create(model=settings.tts_model,voice=settings.tts_voice,input=body.texto,response_format='mp3',instructions='Lee literalmente sin añadir ni cambiar palabras. Voz de '+VARIANTS[body.variante_geolectal]+'. Sin caricaturas ni estereotipos. Ritmo claro, natural.') as response:
                    await response.stream_to_file(temporary)
            # Decode before atomic publication: HTML, JSON and truncated media cannot become MP3 assets.
            await command([settings.ffmpeg_path,'-v','error','-nostdin','-i',str(temporary),'-vn','-codec:a','libmp3lame','-b:a','128k','-f','mp3',str(encoded)])
            os.replace(encoded,target)
        except HTTPException:raise
        except Exception as exc:raise HTTPException(503,'No se pudo preparar el MP3 / MP3 kon niet worden voorbereid') from exc
        finally:
            temporary.unlink(missing_ok=True)
            encoded.unlink(missing_ok=True)
    return locate(body.texto,body.variante_geolectal)
