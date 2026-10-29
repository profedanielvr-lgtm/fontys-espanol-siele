"""Caducidad técnica: elimina intentos controlados expirados y sus audios privados."""
import re,time
from pathlib import Path
from sqlalchemy import select,delete
from .database import SessionLocal
from .models import SecureAttempt,ExamTicket
from .config import settings

def cleanup_expired():
    count=0;root=settings.upload_dir.resolve()
    with SessionLocal() as db:
        for attempt in db.scalars(select(SecureAttempt).where(SecureAttempt.expires_at<time.time())):
            for recording in attempt.data.get('recordings',{}).values():
                name=recording.get('file','')
                if re.fullmatch(r'[0-9a-f]{32}\.(webm|ogg|mp4|wav)',name):
                    path=(root/name).resolve()
                    if path.parent==root:path.unlink(missing_ok=True)
            db.delete(attempt);count+=1
        db.execute(delete(ExamTicket).where(ExamTicket.expires_at<time.time()))
        db.commit()
    return count
if __name__=='__main__':print(f'Intentos expirados eliminados: {cleanup_expired()}')
