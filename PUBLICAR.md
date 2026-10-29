# Publicar la plataforma

Autoría visible: **Diseñado por Daniel Valle Robles**.

El frontend funciona en GitHub Pages sin servidor: banco original, simulacros, voz del navegador, grabación local, informes y portafolio. FastAPI se publica aparte solo si se desea IA o recepción centralizada de audios. GitHub Pages no ejecuta Python ni protege datos del lado del cliente.

1. Subir el contenido de esta carpeta a la raíz del repositorio elegido. No incluir `.env`, bases de datos, grabaciones, `.packages`, `.venv`, `node_modules` ni `.pnpm-store`.
2. En Settings → Pages → Build and deployment, seleccionar **GitHub Actions**.
3. La acción `.github/workflows/pages.yml` comprueba backend, motor e interfaz y publica al actualizar `main`. Si la rama predeterminada tiene otro nombre, adaptar el disparador.
4. Consultar Actions y el entorno `github-pages` para obtener la URL real. No considerar la web publicada hasta que el despliegue termine correctamente.

El `base` relativo de Vite permite servir la web tanto en la raíz de un dominio como en una subcarpeta de repositorio. No necesita tokens ni claves de IA en el frontend o en el flujo de Pages.

## Backend opcional

Para uso local, seguir el README. Para construir la imagen desde la raíz:

```sh
docker build -f backend/Dockerfile -t fontys-espanol-api .
docker run --rm -p 8000:8000 --env-file backend/.env -v fontys-data:/data fontys-espanol-api
```

Antes de exponerlo a usuarios reales: autenticación y autorización por usuario, cuotas en los endpoints de IA, límites de tamaño de solicitud en el proxy, HTTPS, copia de seguridad, política de retención y consentimiento. El backend de este repositorio es un servicio de referencia local; la interfaz publicada no lo necesita para funcionar. No se han implementado cuentas institucionales ni sincronización de estudiantes. No presentar el almacenamiento local como un registro académico institucional.

En Preferencias, introducir el origen HTTPS del backend y configurar `FRONTEND_ORIGIN` con el origen de Pages (sin ruta). `POST /api/evaluar-tarea` valida la referencia de consigna contra el banco del servidor; la evaluación utiliza las dos consignas nuevas. `POST /api/evaluar-escritura` y `POST /api/audio` conservan el contrato inicial con intentos y preguntas en SQLite.

## Abrir sin instalar

`Abrir plataforma.html` contiene interfaz, banco e ilustraciones. Se puede abrir directamente para leer, escribir, practicar y revisar. El micrófono y el almacenamiento de audio pueden estar restringidos en `file://`; para ellos se recomienda localhost o HTTPS. No requiere una clave de IA. La voz depende de que el navegador tenga una voz de español disponible.

Para regenerarlo después de cambios:

```sh
cd frontend
npm install
npm run build
cd ..
node scripts/standalone.mjs
```
