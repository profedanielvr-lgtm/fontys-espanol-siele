"""Uso administrativo LOCAL. No exponer este comando como endpoint público."""
import argparse,secrets,time
from .database import Base,engine,SessionLocal
from .models import ExamTicket
from .secure_exam import digest,MODES

def main():
    p=argparse.ArgumentParser();p.add_argument('--modality',choices=MODES,default='Global');p.add_argument('--hours',type=int,default=24);args=p.parse_args()
    if not 1<=args.hours<=168:p.error('hours: 1–168')
    Base.metadata.create_all(engine);code=secrets.token_urlsafe(24)
    with SessionLocal() as db:db.add(ExamTicket(code_hash=digest(code),modality=args.modality,expires_at=time.time()+args.hours*3600));db.commit()
    print(code)
if __name__=='__main__':main()
