# Audio, administración e informes - actualización 2026-10-29

El reproductor usa archivos MP3 reales, recarga la fuente y muestra errores ES/NL. Se eliminó la dependencia de las voces del navegador. La política de la página permite audio HTTPS del backend. Sin MP3 preparado, se indica expresamente su ausencia; no se simula reproducción.

## Arranque

Desde `backend`: instalar `requirements.lock.txt`, instalar FFmpeg y FFprobe (Docker ya los incluye), copiar `.env.example` a `.env`, ejecutar `python -m app.admin_password` y guardar su resultado en `ADMIN_PASSWORD_HASH` dentro del servidor. Nunca publicar `.env`, contraseñas ni bases de datos. Arrancar con `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. En producción usar HTTPS y configurar `FRONTEND_ORIGIN` al origen exacto de la web, `STATIC_DIR` y `UPLOAD_DIR` en carpetas distintas de un volumen persistente. Configurar el banco privado mediante `SECURE_BANK_PATH`.

En la web, Ajustes: indicar la dirección del backend. Laboratorio docente: iniciar sesión con `ADMIN_USERNAME` y la contraseña elegida. Las sesiones docentes son opacas de 256 bits, con hash en SQLite y caducidad de una hora; el navegador conserva el token en memoria. Cerrar sesión lo revoca. Sin contraseña configurada el acceso está cerrado. No hay contraseña predeterminada. Los permisos de alumno y docente son independientes. El límite por IP protege el acceso y la IA; para despliegues de varios procesos se necesita un limitador compartido en el proxy.

## Preparar audios

En el panel, «Preparar MP3 públicos», pegar el estímulo exacto del banco público, seleccionar variante y generar. Requiere `OPENAI_API_KEY`, `TTS_MODEL`, `TTS_VOICE` y FFmpeg. El servidor recodifica a MP3 estándar antes de publicar atómicamente en `/static/audio`. El endpoint público devuelve URL y MIME; no genera audio ni acepta textos privados. Nunca se monta `UPLOAD_DIR` como estático.

Las variedades disponibles son mexicano, rioplatense, caribeño, andino y espanol_peninsular. El modelo `Pregunta` incorpora `variante_geolectal`; al arrancar se migra la columna SQLite antigua de manera aditiva. En los ítems JSON, `variante_geolectal` determina la variante solicitada y `audio_url` permite una grabación preparada externamente. El banco existente sigue marcado como peninsular pendiente de revisión: cambiar una etiqueta no demuestra un acento. Los prompts de TTS especifican referencias regionales concretas, lectura literal y ausencia de caricaturas. Escuchar y validar tanto el acento como la pertinencia léxica; caribeño y andino abarcan múltiples variedades y no representan un único acento. Las voces del proveedor no garantizan por sí solas una procedencia regional. No se modifican respuestas ni claves al generar voz.

Compatibilidad temporal: el adaptador Speech API usa `gpt-4o-mini-tts`, aún disponible a esta fecha. El proveedor anuncia su retirada para el 6 de enero de 2027 y recomienda migrar al flujo Realtime. `gpt-realtime-2.1-mini` NO es un reemplazo directo del parámetro TTS_MODEL en este adaptador. Antes de esa fecha hay que migrar el adaptador o usar audios pregrabados; estos continúan funcionando sin proveedor.

Grabación: MediaRecorder selecciona WebM/Opus, Ogg/Opus o MP4 según soporte; espera el último `dataavailable`, conserva el MIME real y envía el Blob por FormData sin forzar Content-Type. La sesión controlada permite reintentar el envío del audio local sin volver a grabar. El servidor decodifica todos los envíos, rechaza vídeo, corrupción, tamaño o duración inválidos y sirve el original privado con MIME correcto, disposición inline y soporte de rangos. Un audio local no confirma recepción por el servidor.

## Corrección y PDF

El panel muestra intentos y tareas pendientes, textos y grabaciones autorizadas. La IA formula una propuesta; la transcripción no califica pronunciación o fluidez. El docente debe escuchar los originales y rellenar seis criterios orales o cuatro escritos, feedback ES/NL y, opcionalmente, nivel orientativo A1-C1. El servidor verifica criterios, versión del intento y rol, conservando la propuesta previa. No se convierte automáticamente la media de bandas en nivel MCER ni puntuación SIELE.

`GET /api/generar-reporte-pdf/{intento_id}` acepta el token del alumno propietario vigente o el docente. Funciona para intentos controlados con UUID finalizados; los intentos locales no se envían automáticamente ni reciben un informe servidor. El PDF muestra comprensión como aciertos/total y producción como estado de revisión y bandas propias detalladas por tarea. Se denomina informe formativo, no certificado oficial. Las tareas pendientes no reciben notas inventadas. Ejemplo ilustrativo sin datos personales: `output/pdf/informe-formativo-ejemplo.pdf`.

## Comprobación

`python -m pytest -q` en backend; `pnpm test` y `pnpm build` en frontend. Las pruebas reales convierten una señal de dos segundos a WebM/Opus, Ogg/Opus y MP4/AAC, la envían y rechazan archivos corruptos. Requieren FFmpeg/FFprobe; CI los instala explícitamente. Las pruebas de roles comprueban separación alumno/docente, revocación, conflictos de revisión, informe privado y MIME. La generación de voz real exige credenciales y revisión auditiva humana; no está validada por pruebas con dobles.

Fuentes: https://fastapi.tiangolo.com/tutorial/static-files/ ; https://developers.openai.com/api/docs/guides/text-to-speech ; https://www.coe.int/en/web/common-european-framework-reference-languages . Fecha de consulta: 29-10-2026. Los descriptores MCER son la referencia general; los criterios y bandas implementados son propios y no rúbricas oficiales SIELE.
