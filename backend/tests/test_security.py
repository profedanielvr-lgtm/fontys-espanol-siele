import time,json,asyncio
from contextlib import contextmanager
from starlette.datastructures import UploadFile,Headers
from io import BytesIO
import pytest
from fastapi import HTTPException
from test_api import client
from app.main import app
from app.database import get_db
from app.models import ExamTicket,SecureAttempt
from app.secure_exam import digest
from app.config import settings
from app import media
from app.oral_evaluation import evaluate_oral

def db_session():return contextmanager(app.dependency_overrides[get_db])()
def ticket(mode='S4',code='single-use-exam-code-12345'):
    with db_session() as db:db.add(ExamTicket(code_hash=digest(code),modality=mode,expires_at=time.time()+3600));db.commit()
    return code
def enter(client,mode='S4',code='single-use-exam-code-12345'):
    r=client.post('/api/secure/sessions',json={'code':ticket(mode,code)});assert r.status_code==201,r.text
    return r.json(),{'Authorization':'Bearer '+r.json()['token']}

def test_codes_are_one_use_and_token_required(client):
    a,h=enter(client)
    assert len(a['token'])>=43
    assert client.post('/api/secure/sessions',json={'code':'single-use-exam-code-12345'}).status_code==409
    assert client.get('/api/secure/session').status_code==401
    assert client.get('/api/secure/session',headers={'Authorization':'Bearer '+'x'*43}).status_code==401
    assert client.get('/api/secure/session',headers=h).json()['id']==a['id']

def test_no_answer_keys_and_no_future_task_answers(client):
    a,h=enter(client,'S1')
    assert all('answer' not in q and 'explanation' not in q for q in a['task']['questions'])
    assert client.post('/api/secure/response',headers=h,json={'revision':0,'answers':{'cl2-1':0}}).status_code==422
    assert client.post('/api/secure/writing/6',headers=h,json={'revision':0}).status_code==409
    assert client.post('/api/secure/response',headers=h,json={'revision':0,'answers':{'cl1-1':999}}).status_code==422

def test_attempt_pins_bank_snapshot(client,monkeypatch):
    from app import secure_exam
    a,h=enter(client,'S1')
    original=a['task']['questions'][0]['prompt']
    monkeypatch.setattr(secure_exam,'get_task',lambda task_id: {'id':task_id,'skill':'lectura','questions':[],'title':'changed'})
    state=client.get('/api/secure/session',headers=h).json()
    assert state['task']['questions'][0]['prompt']==original
    assert len(state['bank_sha256'])==64
    assert 'bank_snapshot' not in state

def test_revision_and_deadline_are_server_authoritative(client):
    a,h=enter(client)
    r=client.post('/api/secure/response',headers=h,json={'revision':0});assert r.status_code==200
    assert client.post('/api/secure/response',headers=h,json={'revision':0}).status_code==409
    with db_session() as db:
        row=db.get(SecureAttempt,a['id']);row.data={**row.data,'deadline':time.time()-1};db.commit()
    assert client.post('/api/secure/response',headers=h,json={'revision':1,'text':'tarde'}).status_code==409
    assert client.get('/api/secure/session',headers=h).json()['status']=='finished'
    assert client.post('/api/secure/response',headers=h,json={'revision':2,'calificacion_final':1000}).status_code==422

def test_private_records_not_addressable_by_another_token(client):
    a,ha=enter(client,code='candidate-code-number-one')
    b,hb=enter(client,code='candidate-code-number-two')
    assert client.get('/api/secure/session',headers=hb).json()['id']==b['id']!=a['id']
    assert client.get('/api/secure/oral/eio-1/0',headers=hb).status_code==404
    assert client.delete('/api/secure/session',headers=ha).status_code==200
    assert client.get('/api/secure/session',headers=ha).status_code==401
    assert client.get('/api/secure/session',headers=hb).status_code==200

def test_incidents_do_not_penalize_and_review_requires_finish(client):
    a,h=enter(client)
    assert client.post('/api/secure/events',headers=h,json={'kind':'candidate_note','note':'Se cayó la conexión.'}).status_code==200
    s=client.get('/api/secure/session',headers=h).json()
    assert s['event_count']==1 and s['scores']=={} and s['status']=='active'
    assert client.post('/api/secure/review/eio-1',headers=h,json={}).status_code==409

def test_expiry_and_production_blocks_open_endpoints(client,monkeypatch):
    a,h=enter(client)
    with db_session() as db:row=db.get(SecureAttempt,a['id']);row.expires_at=time.time()-1;db.commit()
    assert client.get('/api/secure/session',headers=h).status_code==401
    monkeypatch.setattr(settings,'environment','production')
    assert client.get('/api/preguntas').status_code==403
    assert client.get('/api/salud').status_code==200
    assert client.post('/api/secure/sessions',json={'code':'long-enough-code-123456'}).status_code==503

def test_request_bounds_and_rate_limit(client,monkeypatch):
    assert client.post('/api/evaluar-tarea',content=b'x'*100001,headers={'Content-Type':'application/json'}).status_code==413
    monkeypatch.setattr(settings,'ai_requests_per_minute',1)
    assert client.post('/api/secure/sessions',json={'code':'unknown-but-long-enough'}).status_code==401
    assert client.post('/api/secure/sessions',json={'code':'unknown-but-long-enough'}).status_code==429

def test_audio_decoder_checks_video_and_silence(tmp_path,monkeypatch):
    async def video(args,timeout=20):return json.dumps({'streams':[{'codec_type':'video'}],'format':{'duration':10}}).encode()
    monkeypatch.setattr(media,'command',video)
    target=tmp_path/'a.webm'
    with pytest.raises(HTTPException) as e:asyncio.run(media.receive_audio(UploadFile(BytesIO(b'fake'),headers=Headers({'content-type':'audio/webm'})),target))
    assert e.value.status_code==415 and not target.exists()
    async def silent(args,timeout=20):return json.dumps({'streams':[{'codec_type':'audio'}],'format':{'duration':1}}).encode() if 'ffprobe' in str(args[0]) else b'\0'*32000
    monkeypatch.setattr(media,'command',silent)
    quality=asyncio.run(media.receive_audio(UploadFile(BytesIO(b'fake'),headers=Headers({'content-type':'audio/webm'})),target))
    result=asyncio.run(evaluate_oral(target,'Preséntate',quality))
    assert quality['likely_silent'] and len(quality['sha256'])==64
    assert result['pronunciacion'] is None and result['fluidez'] is None and result['nivel_oral_global'] is None
    assert result['estado']=='muestra_insuficiente'
