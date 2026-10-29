from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Pregunta(Base):
    __tablename__ = 'pregunta'
    __table_args__ = (CheckConstraint("destreza IN ('lectura','escucha','escritura','oral')"), CheckConstraint("nivel_mcer IN ('A1','A2','B1','B2','C1')"))
    id: Mapped[int] = mapped_column(primary_key=True)
    destreza: Mapped[str] = mapped_column(String(16))
    nivel_mcer: Mapped[str] = mapped_column(String(2))
    contenido_estimulo: Mapped[str] = mapped_column(Text)
    variante_geolectal: Mapped[str] = mapped_column(String(32), default='espanol_peninsular', server_default='espanol_peninsular')
    opciones_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    respuesta_correcta: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadatos_calibracion: Mapped[dict] = mapped_column(JSON, default=dict)

class IntentoExamen(Base):
    __tablename__ = 'intento_examen'
    __table_args__ = (CheckConstraint("estado IN ('en_curso','finalizado')"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[str] = mapped_column(String(64))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    estado: Mapped[str] = mapped_column(String(16), default='en_curso')
    puntaje_global: Mapped[float | None] = mapped_column(Float, nullable=True)

class RespuestaUsuario(Base):
    __tablename__ = 'respuesta_usuario'
    id: Mapped[int] = mapped_column(primary_key=True)
    intento_id: Mapped[int] = mapped_column(ForeignKey('intento_examen.id'), index=True)
    pregunta_id: Mapped[int] = mapped_column(ForeignKey('pregunta.id'), index=True)
    respuesta_dada: Mapped[str] = mapped_column(Text)
    calificacion_ia: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retroalimentacion_ia: Mapped[str | None] = mapped_column(Text, nullable=True)

class ExamTicket(Base):
    __tablename__='exam_ticket'
    code_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    modality: Mapped[str]=mapped_column(String(16))
    expires_at: Mapped[float]=mapped_column(Float)
    used: Mapped[int]=mapped_column(default=0)

class SecureAttempt(Base):
    __tablename__='secure_attempt'
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True)
    expires_at: Mapped[float]=mapped_column(Float)
    revision: Mapped[int]=mapped_column(default=0)
    data: Mapped[dict]=mapped_column(JSON)

class AdminSession(Base):
    __tablename__='admin_session'
    token_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    expires_at: Mapped[float]=mapped_column(Float)
