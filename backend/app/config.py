from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./simulador.db'
    upload_dir: Path = Path('./uploads')
    ai_mode: str = 'demo'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    frontend_origin: str = 'http://localhost:5173'
    max_audio_bytes: int = 10 * 1024 * 1024
    environment: str = 'development'
    transcription_model: str = 'gpt-transcribe'
    ffmpeg_path: str = 'ffmpeg'
    ffprobe_path: str = 'ffprobe'
    ai_requests_per_minute: int = 4
    secure_bank_path: str = ''
    static_dir: Path = Path('./static')
    admin_username: str = 'docente'
    admin_password_hash: str = ''
    tts_model: str = 'gpt-4o-mini-tts'
    tts_voice: str = 'marin'

settings = Settings()
