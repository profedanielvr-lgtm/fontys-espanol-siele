"""Revisión humana administrativa en el servidor; nunca aceptada del candidato."""
import argparse,json,copy,time
from pathlib import Path
from pydantic import BaseModel,Field
from .database import SessionLocal
from .models import SecureAttempt

class HumanReview(BaseModel):
    reviewer:str=Field(min_length=3,max_length=100)
    task_id:str=Field(pattern=r'^(eie-[12]|eio-[1-5])$')
    criterios:dict[str,int]
    observaciones_es:str=Field(min_length=10,max_length=5000)
    observaciones_nl:str=Field(min_length=10,max_length=5000)
    audio_escuchado:bool=False

def main():
    parser=argparse.ArgumentParser();parser.add_argument('attempt_id');parser.add_argument('review_json');args=parser.parse_args()
    review=HumanReview.model_validate_json(Path(args.review_json).read_text(encoding='utf-8'))
    if not review.criterios or any(isinstance(v,bool) or not 0<=v<=4 for v in review.criterios.values()):parser.error('Bandas propias 0–4 requeridas')
    if review.task_id.startswith('eio') and not review.audio_escuchado:parser.error('La revisión oral exige escuchar la grabación original')
    with SessionLocal() as db:
        a=db.get(SecureAttempt,args.attempt_id)
        if not a or a.data['status']!='finished' or review.task_id not in a.data['task_ids']:parser.error('Intento o tarea no revisable')
        data=copy.deepcopy(a.data);previous=data['reviews'].get(review.task_id)
        data['reviews'][review.task_id]={'estado':'revisado_por_docente','revision_humana':review.model_dump(),'ai_proposal':previous,'reviewed_at':time.time(),'official':False}
        a.data=data;a.revision+=1;db.commit()
    print('Revisión guardada; no constituye certificación SIELE.')
if __name__=='__main__':main()
