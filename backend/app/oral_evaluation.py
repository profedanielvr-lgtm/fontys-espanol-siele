from pathlib import Path
from openai import AsyncOpenAI
from .config import settings
from .evaluation import evaluate, EvaluationUnavailable

async def evaluate_oral(path:Path,consigna:str,quality:dict):
    base={'tipo':'oral_transcripcion','estado':'pendiente_revision_humana','nivel_oral_global':None,
          'pronunciacion':None,'fluidez':None,'calificacion_oficial':False,'quality':quality,
          'transcription_model':settings.transcription_model,
          'limitacion_es':'Una transcripción no permite valorar pronunciación, prosodia ni fluidez acústica. No es una calificación oral global.',
          'limitacion_nl':'Een transcriptie volstaat niet om uitspraak, prosodie of akoestische vloeiendheid te beoordelen. Dit is geen totaalscore voor spreken.'}
    if quality.get('likely_silent'):
        return {**base,'estado':'muestra_insuficiente','transcripcion':'','analisis_textual':None}
    if settings.ai_mode!='openai' or not settings.openai_api_key:
        raise EvaluationUnavailable('Evaluación de audio no configurada / Audiobeoordeling niet ingesteld')
    try:
        async with AsyncOpenAI(api_key=settings.openai_api_key,timeout=60,max_retries=0) as client:
            with path.open('rb') as audio:
                result=await client.audio.transcriptions.create(model=settings.transcription_model,file=audio,response_format='json',extra_body={'languages':['es']})
        text=result.text.strip()
        if not text or len(text)>15000:
            return {**base,'estado':'muestra_insuficiente','transcripcion':'','analisis_textual':None}
        analysis=await evaluate(text,consigna+'\nSe trata de la transcripción de una respuesta oral. Analiza solo lo conservado en el texto; no infieras pronunciación ni pausas.')
        analysis.revision_humana=True
        # El nivel textual no se promueve a nivel oral global.
        return {**base,'transcripcion':text,'analisis_textual':analysis.model_dump()}
    except EvaluationUnavailable:raise
    except Exception as exc:raise EvaluationUnavailable('Transcripción no disponible / Transcriptie niet beschikbaar') from exc
