import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Pregunta
from app.config import settings

@pytest.fixture
def client(tmp_path):
    from app.guards import windows
    windows.clear()
    engine = create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    def db():
        with sessions() as s: yield s
    app.dependency_overrides[get_db] = db
    original = settings.upload_dir, settings.ai_mode, settings.max_audio_bytes
    settings.upload_dir, settings.ai_mode = tmp_path, 'demo'
    with sessions() as s:
        s.add_all([Pregunta(id=1,destreza='escritura',nivel_mcer='A2',contenido_estimulo='Invita a una amiga.'),Pregunta(id=2,destreza='oral',nivel_mcer='A2',contenido_estimulo='Preséntate.')]); s.commit()
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()
    settings.upload_dir, settings.ai_mode, settings.max_audio_bytes = original

def test_demo_and_validations(client):
    intento = client.post('/api/intentos',json={'usuario_id':'demo'}).json()['id']
    body = {'intento_id':intento,'pregunta_id':1,'texto':'Hola, ¿vienes a mi casa?'}
    r = client.post('/api/evaluar-escritura',json=body)
    assert r.status_code == 200
    assert r.json()['evaluacion']['nivel_estimado'] is None
    assert client.post('/api/evaluar-escritura',json={**body,'texto':'  '}).status_code == 422
    assert client.post('/api/evaluar-escritura',json={**body,'pregunta_id':2}).status_code == 422
    assert client.post('/api/evaluar-escritura',json={**body,'intento_id':999}).status_code == 404
    assert 'respuesta_correcta' not in client.get('/api/preguntas').json()[0]

def test_audio_limits_and_container(client):
    i = client.post('/api/intentos',json={'usuario_id':'demo'}).json()['id']
    data = {'intento_id':str(i),'pregunta_id':'2'}
    assert client.post('/api/audio',data=data,files={'archivo':('x.webm',b'bad','audio/webm')}).status_code == 415
    assert client.post('/api/audio',data=data,files={'archivo':('x.webm',b'','audio/webm')}).status_code == 422
    settings.max_audio_bytes = 8
    assert client.post('/api/audio',data=data,files={'archivo':('x.webm',b'\x1aE\xdf\xa3'+b'x'*20,'audio/webm')}).status_code == 413
    assert not list(settings.upload_dir.iterdir())
    r = client.post('/api/audio',data=data,files={'archivo':('../../x.webm',b'\x1aE\xdf\xa3test','audio/webm')})
    assert r.status_code == 201
    assert r.json()['estado'] == 'recibido_no_evaluado'

def test_static_frontend_task_adapter(client):
    r = client.post('/api/evaluar-tarea',json={'task_id':'eie-2','opcion':1,'texto':'Hola, esta es una muestra.'})
    assert r.status_code == 200
    assert r.json()['modo'] == 'demo'
    assert r.json()['evaluacion']['nivel_estimado'] is None
    assert client.post('/api/evaluar-tarea',json={'task_id':'cl-1','texto':'Hola'}).status_code == 422
    assert client.post('/api/evaluar-tarea',json={'task_id':'eie-1','texto':'  '}).status_code == 422

def test_static_audio_adapter(client):
    data={'task_id':'eio-1','parte':'0'}
    r=client.post('/api/audio-practica',data=data,files={'archivo':('respuesta.webm',b'\x1aE\xdf\xa3test','audio/webm')})
    assert r.status_code==201
    assert r.json()['estado']=='recibido_no_evaluado'
    assert client.post('/api/audio-practica',data={'task_id':'eio-2','parte':'3'},files={'archivo':('respuesta.webm',b'\x1aE\xdf\xa3test','audio/webm')}).status_code==422
