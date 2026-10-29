import asyncio
from types import SimpleNamespace
import pytest
from app import evaluation
from app.schemas import Evaluacion, Criterio

def test_provider_evidence_and_abstention(monkeypatch):
    texto = 'Hola amiga. ' * 35
    criterio = Criterio(puntuacion=2,evidencia='Hola amiga.',justificacion='Saludo observable.')
    result = Evaluacion(nivel_estimado='A2',gramatica=criterio,coherencia=criterio,
        vocabulario=criterio,cumplimiento=criterio,feedback_formativo='Amplía los detalles.',
        limitaciones='Solo una muestra.',revision_humana=False)
    class Client:
        def __init__(self, **kwargs): self.responses = self
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def parse(self, **kwargs):
            assert kwargs['store'] is False
            return SimpleNamespace(status='completed',output_parsed=result.model_copy(deep=True))
    monkeypatch.setattr(evaluation,'AsyncOpenAI',Client)
    monkeypatch.setattr(evaluation.settings,'ai_mode','openai')
    monkeypatch.setattr(evaluation.settings,'openai_api_key','test-only')
    assert asyncio.run(evaluation.evaluate(texto,'Saluda.')).nivel_estimado == 'A2'
    assert asyncio.run(evaluation.evaluate('Hola amiga.','Saluda.')).nivel_estimado is None
    with pytest.raises(evaluation.EvaluationUnavailable):
        asyncio.run(evaluation.evaluate('Otro texto ' * 40,'Saluda.'))

def test_missing_key_fails_explicitly(monkeypatch):
    monkeypatch.setattr(evaluation.settings,'ai_mode','openai')
    monkeypatch.setattr(evaluation.settings,'openai_api_key','')
    with pytest.raises(evaluation.EvaluationUnavailable):
        asyncio.run(evaluation.evaluate('Hola','Saluda.'))
