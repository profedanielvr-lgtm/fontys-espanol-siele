import json
from functools import lru_cache
from pathlib import Path
from .config import settings

@lru_cache
def bank():
    path=Path(settings.secure_bank_path) if settings.secure_bank_path else Path(__file__).resolve().parents[2]/'frontend/public/bank.json'
    return json.loads(path.read_text(encoding='utf-8'))['tasks']

def get_task(task_id):
    return next((t for t in bank() if t['id']==task_id),None)

def stimulus(task, choice=0, part=0, topic=0, situation=0):
    if task is None:
        raise ValueError('Tarea desconocida')
    text=task['instruction']+'\n'+task['stimulus']
    options=task.get('choices',[])
    if options:
        index=choice
        if task['id']=='eio-3': index=part*2+situation
        if task['id']=='eio-5': index=topic*2+choice
        if index<0 or index>=len(options):raise ValueError('Opción inválida')
        text+='\n'+options[index]['stimulus']
    prompts=task.get('alternativePrompts') if task['id']=='eio-4' and choice==1 else task.get('prompts')
    if prompts:
        if part<0 or part>=len(prompts):raise ValueError('Parte inválida')
        text+='\n'+prompts[part]
    return text
