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
