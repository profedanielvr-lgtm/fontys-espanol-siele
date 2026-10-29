"""Run locally: python -m app.admin_password. Never put passwords in CLI arguments."""
from getpass import getpass
from .admin import password_hash
if __name__=='__main__':
    password=getpass('Contraseña docente / Docentwachtwoord (mín. 14): ')
    if len(password)<14:raise SystemExit('Usa al menos 14 caracteres / Gebruik minstens 14 tekens')
    if password!=getpass('Repetir / Herhalen: '):raise SystemExit('No coincide / Komt niet overeen')
    print('ADMIN_PASSWORD_HASH='+password_hash(password))
