"""Controles de frontera; no equivalen a certificación ni supervisión biométrica."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse
from .config import settings

windows=defaultdict(deque)
def quota(request:Request):
    # No confiar en X-Forwarded-For. Configurar un único proxy confiable al desplegar.
    now=time.monotonic()
    if len(windows)>5000:
        for key in list(windows):
            if not windows[key] or windows[key][-1]<now-60:windows.pop(key,None)
        if len(windows)>5000:raise HTTPException(503,'Servicio ocupado / Dienst bezet')
    key=request.client.host if request.client else 'unknown'
    times=windows[key]
    while times and times[0]<now-60:times.popleft()
    if len(times)>=settings.ai_requests_per_minute:raise HTTPException(429,'Demasiadas solicitudes / Te veel verzoeken',headers={'Retry-After':'60'})
    times.append(now)

class RequestGuard:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        path=scope['path'];headers=dict(scope.get('headers',[]))
        limit=settings.max_audio_bytes+131072 if ('audio' in path or 'oral' in path) else 100000
        if scope['method'] in {'POST','PUT','PATCH'}:
            try:length=int(headers.get(b'content-length',b'0'))
            except ValueError:length=limit+1
            if length>limit:return await JSONResponse({'detail':'Solicitud demasiado grande / Verzoek te groot'},413)(scope,receive,send)
            messages=[];total=0
            while True:
                message=await receive()
                if message['type']=='http.disconnect':return
                total+=len(message.get('body',b''))
                if total>limit:return await JSONResponse({'detail':'Solicitud demasiado grande / Verzoek te groot'},413)(scope,receive,send)
                messages.append(message)
                if not message.get('more_body',False):break
            original_receive=receive
            async def bounded_receive():
                return messages.pop(0) if messages else await original_receive()
            receive=bounded_receive
        # Los endpoints heredados son solo de desarrollo, sin autorización por usuario.
        legacy=path.startswith('/api/') and not path.startswith(('/api/secure/','/api/admin/','/api/generar-reporte-pdf/')) and path not in {'/api/salud','/api/audio-estimulo'}
        if settings.environment=='production' and legacy:
            return await JSONResponse({'detail':'Usa una sesión autorizada / Gebruik een bevoegde sessie'},403)(scope,receive,send)
        async def guarded_send(message):
            if message['type']=='http.response.start':
                message['headers']=list(message.get('headers',[]))+[(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),(b'referrer-policy',b'no-referrer'),(b'x-frame-options',b'DENY'),(b'permissions-policy',b'camera=(), geolocation=()')]
            await send(message)
        await self.app(scope,receive,guarded_send)
