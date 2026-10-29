import time
from test_api import client
from test_security import enter,db_session
from app.config import settings
from app.models import SecureAttempt
from app.admin import password_hash

def teacher(client,monkeypatch):
    monkeypatch.setattr(settings,'admin_password_hash',password_hash('un-secret-test-long-123'))
    r=client.post('/api/admin/login',json={'username':'docente','password':'un-secret-test-long-123'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def test_teacher_roles_logout_and_expiry(client,monkeypatch):
    a,student=enter(client)
    assert client.get('/api/admin/intentos',headers=student).status_code==401
    h=teacher(client,monkeypatch)
    assert client.get('/api/admin/intentos',headers=h).status_code==200
    assert client.get('/api/secure/session',headers=h).status_code==401
    assert client.post('/api/admin/logout',headers=h).status_code==200
    assert client.get('/api/admin/intentos',headers=h).status_code==401

def test_grade_pdf_and_private_audio(client,monkeypatch):
    a,student=enter(client,'S5');h=teacher(client,monkeypatch)
    with db_session() as db:
        row=db.get(SecureAttempt,a['id']);data=dict(row.data);data['status']='finished';data['index']=len(data['task_ids']);row.data=data;db.commit()
    grade={'revision':0,'criterios':dict(gramatica=2,coherencia=2,vocabulario=3,cumplimiento=2),'observaciones_es':'Texto con ejemplos claros.','observaciones_nl':'Tekst met duidelijke voorbeelden.','nivel_estimado':'B1'}
    path=f"/api/admin/intentos/{a['id']}/calificar/eie-1"
    assert client.post(path,headers=student,json=grade).status_code==401
    assert client.post(path,headers=h,json={**grade,'criterios':{'gramatica':True}}).status_code==422
    assert client.post(path,headers=h,json=grade).status_code==200
    assert client.post(path,headers=h,json=grade).status_code==409
    url=f"/api/generar-reporte-pdf/{a['id']}"
    assert client.get(url).status_code==401
    for headers in [h,student]:
        r=client.get(url,headers=headers);assert r.status_code==200,r.text
        assert r.headers['content-type']=='application/pdf' and r.content.startswith(b'%PDF-')
    root=settings.upload_dir;filename='a'*32+'.webm';(root/filename).write_bytes(b'private recording fixture')
    with db_session() as db:
        row=db.get(SecureAttempt,a['id']);data=dict(row.data);data['recordings']={'eio-1:0':{'file':filename}};row.data=data;db.commit()
    url=f"/api/admin/intentos/{a['id']}/audio/eio-1/0"
    assert client.get(url).status_code==401
    r=client.get(url,headers=h);assert r.content==b'private recording fixture'
    assert r.headers['content-type']=='audio/webm' and 'inline' in r.headers['content-disposition']

def test_tts_missing_config_and_production_routes(client,monkeypatch):
    from app.stimulus_audio import public_texts
    h=teacher(client,monkeypatch)
    monkeypatch.setattr(settings,'environment','production');monkeypatch.setattr(settings,'openai_api_key','')
    text=next(t for t in public_texts() if t)
    assert client.post('/api/admin/audio-estimulo',headers=h,json={'texto':text,'variante_geolectal':'mexicano'}).status_code==503
    assert client.post('/api/admin/audio-estimulo',headers=h,json={'texto':'PRIVATE NOT PUBLIC','variante_geolectal':'mexicano'}).status_code==422
    assert client.get('/api/audio-estimulo',params={'texto':text}).status_code==404
    assert client.get('/static/../uploads/private.webm').status_code==404
