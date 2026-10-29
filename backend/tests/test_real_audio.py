"""Integration tests with actual encoders. Required in CI; optional on developer machines."""
import shutil,subprocess
import pytest
from test_api import client
from app.config import settings

@pytest.mark.parametrize('ext,mime,codec',[('webm','audio/webm;codecs=opus','libopus'),('ogg','audio/ogg','libopus'),('mp4','audio/mp4','aac')])
def test_actual_recording_containers(client,tmp_path,ext,mime,codec):
    if not shutil.which(settings.ffmpeg_path) or not shutil.which(settings.ffprobe_path):pytest.skip('FFmpeg/FFprobe required; installed in CI and Docker')
    path=tmp_path/('test.'+ext)
    subprocess.run([settings.ffmpeg_path,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-c:a',codec,str(path)],check=True,timeout=20)
    r=client.post('/api/audio-practica',data={'task_id':'eio-1','parte':'0'},files={'archivo':(path.name,path.read_bytes(),mime)})
    assert r.status_code==201,r.text
    assert r.json()['estado']=='recibido_no_evaluado'
    # A header that looks valid must still fail decoding.
    r=client.post('/api/audio-practica',data={'task_id':'eio-1','parte':'0'},files={'archivo':('bad.'+ext,b'\x1aE\xdf\xa3corrupt',mime)})
    assert r.status_code==422

def test_actual_mp3_playback_headers_and_ranges(client):
    if not shutil.which(settings.ffmpeg_path):pytest.skip('FFmpeg required; installed in CI and Docker')
    from uuid import uuid4
    folder=settings.static_dir/'audio';folder.mkdir(parents=True,exist_ok=True)
    filename='integration-'+uuid4().hex+'.mp3';path=folder/filename
    try:
        subprocess.run([settings.ffmpeg_path,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-c:a','libmp3lame',str(path)],check=True,timeout=20)
        r=client.get('/static/audio/'+filename,headers={'Origin':settings.frontend_origin,'Range':'bytes=0-31'})
        assert r.status_code==206 and len(r.content)==32
        assert r.headers['content-type']=='audio/mpeg'
        assert r.headers['access-control-allow-origin']==settings.frontend_origin
        assert r.headers['accept-ranges']=='bytes'
    finally:path.unlink(missing_ok=True)
