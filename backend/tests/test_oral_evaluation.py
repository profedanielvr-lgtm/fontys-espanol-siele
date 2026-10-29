import asyncio
from types import SimpleNamespace
import pytest
from app import oral_evaluation as oral
from app.schemas import Criterio,Evaluacion
from app.evaluation import EvaluationUnavailable

def test_transcript_never_becomes_global_or_acoustic_grade(tmp_path,monkeypatch):
    source=tmp_path/'audio.webm';source.write_bytes(b'fake-media-for-provider-double')
    transcript='Quiero proponer una actividad en parejas porque permite contrastar ideas. '
    class Client:
        def __init__(self,**kwargs):self.audio=self;self.transcriptions=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def create(self,**kwargs):
            assert kwargs['model']=='gpt-transcribe'
            assert kwargs['extra_body']=={'languages':['es']}
            return SimpleNamespace(text=transcript)
    criterion=Criterio(puntuacion=2,evidencia='actividad en parejas',justificacion='Observación de prueba.')
    async def evaluate(text,stimulus):
        assert text==transcript.strip()
        return Evaluacion(nivel_estimado='B1',gramatica=criterion,coherencia=criterion,vocabulario=criterion,cumplimiento=criterion,feedback_formativo='ES: Desarrolla. NL: Werk uit.',limitaciones='Muestra textual.',revision_humana=False)
    monkeypatch.setattr(oral,'AsyncOpenAI',Client);monkeypatch.setattr(oral,'evaluate',evaluate)
    monkeypatch.setattr(oral.settings,'ai_mode','openai');monkeypatch.setattr(oral.settings,'openai_api_key','unit-test-not-a-real-key')
    result=asyncio.run(oral.evaluate_oral(source,'Propón una actividad.',{'likely_silent':False}))
    assert result['analisis_textual']['nivel_estimado']=='B1'
    assert result['analisis_textual']['revision_humana'] is True
    assert result['nivel_oral_global'] is None and result['pronunciacion'] is None and result['fluidez'] is None
    assert result['calificacion_oficial'] is False and result['limitacion_nl']

def test_no_audio_grade_without_configured_provider(tmp_path,monkeypatch):
    monkeypatch.setattr(oral.settings,'ai_mode','demo')
    with pytest.raises(EvaluationUnavailable):asyncio.run(oral.evaluate_oral(tmp_path/'unused.webm','Habla.',{'likely_silent':False}))
