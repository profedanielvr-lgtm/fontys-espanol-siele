from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Nivel = Literal['A1','A2','B1','B2','C1']
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class CrearIntento(Strict):
    usuario_id: str = Field(min_length=1, max_length=64, pattern=r'^[\w-]+$')

class Escritura(Strict):
    intento_id: int = Field(gt=0)
    pregunta_id: int = Field(gt=0)
    texto: str = Field(min_length=1, max_length=15000)

class EvaluarTarea(Strict):
    task_id: Literal['eie-1','eie-2']
    opcion: int = Field(default=0,ge=0,le=1)
    texto: str = Field(min_length=1,max_length=15000)

class Criterio(Strict):
    puntuacion: int = Field(ge=0, le=4)
    evidencia: str
    justificacion: str

class Evaluacion(Strict):
    nivel_estimado: Nivel | None
    gramatica: Criterio
    coherencia: Criterio
    vocabulario: Criterio
    cumplimiento: Criterio
    feedback_formativo: str
    limitaciones: str
    revision_humana: bool

class Resultado(Strict):
    respuesta_id: int
    modo: Literal['demo','openai']
    modelo: str | None
    rubrica_version: str
    evaluacion: Evaluacion
