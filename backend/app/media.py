"""Decodificación aislada con timeout y argumentos constantes; sin shell."""
import asyncio
import json
import math
import struct
import hashlib
from pathlib import Path
from fastapi import HTTPException, UploadFile
from .config import settings

async def command(args, timeout=20):
    try:
        process=await asyncio.create_subprocess_exec(*args,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    except FileNotFoundError as exc:raise HTTPException(503,'Falta el decodificador de audio / Audiodecoder ontbreekt') from exc
    try:out,err=await asyncio.wait_for(process.communicate(),timeout)
    except asyncio.TimeoutError as exc:
        process.kill();await process.communicate()
        raise HTTPException(422,'No se pudo decodificar el audio a tiempo / Audioverwerking duurde te lang') from exc
    if process.returncode:raise HTTPException(422,'Archivo de audio no decodificable / Ongeldig audiobestand')
    return out

async def receive_audio(upload:UploadFile,target:Path):
    mime=(upload.content_type or '').split(';')[0]
    if mime not in {'audio/webm','audio/ogg','audio/mp4','audio/wav','audio/x-wav'}:
        await upload.close();raise HTTPException(415,'Formato de audio no permitido / Audioformaat niet toegestaan')
    total=0;hasher=hashlib.sha256()
    try:
        with target.open('xb') as out:
            while chunk:=await upload.read(65536):
                total+=len(chunk)
                if total>settings.max_audio_bytes:raise HTTPException(413,'Audio demasiado grande / Audio te groot')
                out.write(chunk);hasher.update(chunk)
        if not total:raise HTTPException(422,'Audio vacío / Lege audio')
        raw=await command([settings.ffprobe_path,'-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(target)])
        info=json.loads(raw)
        duration=float(info.get('format',{}).get('duration',0))
        # Algunos WebM no incluyen duración: la decodificación posterior sigue acotada.
        if duration and (not math.isfinite(duration) or not 1<=duration<=300):raise HTTPException(422,'Duración no permitida (1–300 s) / Ongeldige duur')
        streams=info.get('streams',[])
        if not streams or any(s.get('codec_type')!='audio' for s in streams):raise HTTPException(415,'El archivo debe contener solo audio / Alleen audio toegestaan')
        pcm=await command([settings.ffmpeg_path,'-v','error','-nostdin','-i',str(target),'-t','301','-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'])
        seconds=len(pcm)/32000
        if not 1<=seconds<=300:raise HTTPException(422,'Duración no permitida (1–300 s) / Ongeldige duur')
        samples=struct.unpack('<'+'h'*(len(pcm)//2),pcm)
        rms=math.sqrt(sum(v*v for v in samples)/max(1,len(samples)))
        return {'duration_seconds':round(seconds,2),'rms':round(rms,2),'likely_silent':rms<40,'bytes':total,'sha256':hasher.hexdigest()}
    except Exception:
        target.unlink(missing_ok=True);raise
    finally:await upload.close()
