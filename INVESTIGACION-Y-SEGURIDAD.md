# Investigación y revisión · Onderzoek en herziening

Versión 3 · consulta: 29 de octubre de 2026. Diseñado por Daniel Valle Robles.

## Qué se ha contrastado / Wat is vergeleken

| Fuente primaria | Hallazgo aplicado | Límite |
|---|---|---|
| [SIELE: guía operativa 2021](https://seul.cervantes.es/imagenes/File/guia_de_examen_SIELE.pdf) | Estructura por tareas, navegación, grabación y descanso; comprensión y producción se corrigen de distinta forma. | Documento histórico; no prueba identidad con la aplicación actual. |
| [SIELE: guía de preparadores 2016](https://info.siele.org/GuiaOficialPreparadores/SIELE_GuiaOficialPreparadores_20161028.pdf) | Escritura considera cohesión, corrección, alcance y cumplimiento; oral integra uso lingüístico y cumplimiento con descriptores según tarea. | No se copian escalas completas, muestras ni coeficientes como si fueran una rúbrica validada para IA. |
| [Universidad de Salamanca: calificadores](https://cursosinternacionales.usal.es/es/%C2%BFqui%C3%A9nes-califican-las-pruebas-de-expresi%C3%B3n-e-interacci%C3%B3n-orales-y-escritas-del-siele) | Las pruebas productivas oficiales las valoran expertos acreditados. | La IA de este proyecto es una propuesta formativa, no el calificador SIELE. |
| [ETS, FAQ docente 2026](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-faq.pdf) | Los sistemas de evaluación automatizada de otros exámenes se integran con supervisión y datos de calificación humana. | Un prompt, una transcripción y JSON no reproducen esa validación. |
| [IELTS: automarcación y validez](https://ielts.org/news-and-insights/what-automarking-means-for-language-test-validity-and-integrity) | La comparación invita a exigir evidencia de validez y acuerdo antes de usar automarcación. | Se consultó el texto indexado; la apertura directa no se pudo completar. No se usa para afirmar una especificación operativa. |
| [Consejo de Europa: fonología](https://www.coe.int/en/web/common-european-framework-reference-languages/phonological-competence) | La inteligibilidad y los rasgos acústicos importan; no se penaliza una variedad por no parecer nativa. | Inferencia técnica: la transcripción pierde información necesaria para juzgar prosodia y pronunciación. |
| [OWASP: autorización](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) y [sesiones ASVS 5](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x16-V7-Session-Management.md) | Autorizar cada solicitud, tokens aleatorios, caducidad y decisiones en servidor. | Aplicar controles no equivale a una certificación ASVS ni a una auditoría de penetración. |
| [OWASP: recepción de archivos](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) | Limitar tamaño, validar por decodificación, usar nombres internos y almacenamiento privado. | FFmpeg debe mantenerse actualizado y ejecutarse en un entorno aislado. |
| [Autoriteit Persoonsgegevens: recomendaciones sobre proctoring](https://www.autoriteitpersoonsgegevens.nl/uploads/imported/aanbevelingen_online_proctoring_onderwijs.pdf) | Minimización e intervención humana; no añadir vigilancia biométrica como solución predeterminada. | PDF histórico, indexado pero con acceso directo 403. No es prueba de cumplimiento jurídico actual. |

**NL:** De vergelijking maakt onderscheid tussen historische examenhandleidingen, actuele beveiligingsprincipes en eigen oefenfuncties. Er wordt geen officiële equivalentie, certificering of volledige kopie van SIELE geclaimd.

## Experiencia del candidato / Ervaring van de kandidaat

Las 18 tareas tienen instrucciones neerlandesas redactadas expresamente. El selector ofrece ES, NL y ES+NL para la interfaz; las instrucciones operativas de las tareas se mantienen visibles en ambos idiomas. Los estímulos, opciones de contenido, consignas lingüísticas y respuestas permanecen en español para conservar el constructo. Traducir un texto de lectura cambiaría lo que se evalúa.

**NL:** Alle 18 taken hebben expliciete Nederlandse instructies. De interface biedt ES, NL en ES+NL; de procedurele taakinstructies blijven tweetalig. Teksten, inhoudelijke keuzen en antwoorden blijven Spaans, zodat niet een andere vaardigheid wordt gemeten.

La plataforma conserva Global y S1–S5. No afirma que SIELE seleccione ítems adaptativamente después de cada respuesta. La ruta adaptativa es solo una regla de entrenamiento propia. Se conservan las limitaciones ya declaradas: banco original sin calibración, audio sintético e ilustraciones en lugar de fotografías oficiales, y diferencias entre tiempos de distintas guías. No se han adquirido ítems oficiales ni acceso a un navegador de examen propietario.

## Corrección productiva / Beoordeling van productieve vaardigheden

1. **Escritura:** rúbrica propia versionada `formativa-mcer-2.0`; puntuaciones 0–4 por campo, evidencia literal verificable, justificación y feedback ES/NL. Se consideran registro y cumplimiento de la consigna. El sistema se abstiene cuando falta evidencia, sin fabricar una nota.
2. **Audio:** valida y decodifica el contenedor, comprueba duración y detecta muestras probablemente silenciosas. El proveedor transcribe y el evaluador analiza únicamente la información conservada en el texto.
3. **Límite acústico explícito:** `pronunciacion`, `fluidez` y `nivel_oral_global` permanecen null. Una transcripción no permite una valoración completa de la voz. El análisis textual no se convierte en nivel oral global ni en puntos SIELE.
4. **Revisión humana:** las propuestas de la sesión controlada quedan pendientes. Un administrador local puede registrar una revisión docente bilingüe; para oral debe confirmar que escuchó el original. La ruta del candidato no permite validarse una nota humana.
5. **Trazabilidad:** consigna elegida, modelo, versión, estado de propuesta, calidad y huella SHA-256 del audio. Los fallos de proveedor generan un error explícito; no se sustituyen por notas de demostración.

**NL:** AI levert een onderbouwd voorstel. Alleen een docent kan een menselijke beoordeling vastleggen. Uitspraak, prosodie en akoestische vloeiendheid worden niet uit een transcriptie afgeleid. Er is geen automatische officiële spreekscore of SIELE-certificering.

Antes de utilizar estas propuestas para decisiones académicas se necesitan corpus representativos con consentimiento, doble corrección y adjudicación, análisis de acuerdo y sesgo por variedad/nivel, pruebas acústicas reales y criterios de abstención validados. Esos estudios no se han realizado en este proyecto.

## Dos niveles de garantías / Twee soorten waarborgen

| Práctica publicada en GitHub Pages | Sesión con backend |
|---|---|
| Tiempo y datos en navegador; se pueden manipular. | Tiempo, secuencia, recepción y puntuación decididos por servidor. |
| Banco y claves públicos. | API no entrega claves. En producción exige un banco privado diferente, que no se publica en GitHub. |
| Identidad libre mediante alias. | Acceso con código aleatorio de un uso; es autorización, **no verificación de identidad**. |
| Textos y audio locales. | Token aleatorio de 256 bits, guardado como hash en servidor; autorización de cada sesión/archivo. |
| Feedback requiere un backend configurado. | Cuota para entrada/IA, límites de cuerpo y archivo, validación multimedia y control de revisión. |
| Sin garantía de examen supervisado. | Controles técnicos de referencia; no navegador de bloqueo validado, auditoría institucional ni supervisión humana en directo. |

**NL:** Een toegangscode bewijst niet wie er achter het scherm zit. De servergestuurde modus is technisch strenger dan lokaal oefenen, maar is geen erkend hoog-risico-examen of biometrische identiteitscontrole.

## Privacidad y seguridad operativa / Privacy en operationele beveiliging

- No se activa cámara, reconocimiento facial, seguimiento ocular ni inspección del escritorio. La pantalla completa es opcional y no garantiza integridad.
- La pérdida de foco se registra como incidencia técnica sin penalización automática. El candidato puede aportar una explicación; un humano debe interpretar el contexto.
- Las respuestas cerradas no se reabren por una recarga. Una copia de emergencia en la sesión del navegador permite conservar un borrador, pero no permite enviarlo fuera del plazo.
- Se recibe audio solo dentro de una sesión autorizada. Un archivo se decodifica con procesos sin shell y timeout; se rechazan vídeo, duraciones fuera de límites y archivos inválidos. La petición en curso no amplía el plazo de producción: puede terminar su validación tras haberse recibido a tiempo.
- Producción deshabilita los endpoints heredados sin autorización. La nueva API devuelve `no-store`, `nosniff` y otras cabeceras de protección. La web añade CSP y referrer policy. GitHub Pages no permite imponer todas las cabeceras de servidor; no se afirma protección completa contra framing desde un meta-tag.
- Las sesiones técnicas caducan a las 24 horas; el proceso de mantenimiento elimina sesiones expiradas y audios asociados cada hora mientras el servidor sigue activo. Puede ejecutarse manualmente `python -m app.cleanup`. La caducidad del token por sí sola no es un borrado instantáneo ni sustituye una política de conservación institucional.
- El candidato puede borrar su sesión autorizada del servidor. Los datos locales se gestionan por separado desde Preferencias. Exportar JSON no incluye los Blobs de audio.
- Un despliegue real necesita TLS, volumen protegido/cifrado, aislamiento de FFmpeg, cuotas compartidas en el proxy, control administrativo, monitorización y copias con retención definida. El limitador incluido vive en un proceso y no protege por sí solo un clúster. No se ha realizado pentest ni evaluación legal/DPIA.

**NL:** De instelling blijft verantwoordelijk voor doel, rechtsgrond, toegang, bewaartermijnen, toegankelijkheid, bezwaar en menselijke beoordeling. Deze softwarewijzigingen bewijzen geen AVG-conformiteit.

## Activación / Activeren

GitHub Pages sirve solo la interfaz. No ejecuta FastAPI, no guarda secretos y no puede alojar el motor de IA. Hasta conectar un backend HTTPS y configurar allí una clave válida, la web debe indicar que la evaluación real y el control del servidor no están activos. No introducir claves del proveedor en el navegador, el repositorio ni una URL.

**NL:** GitHub Pages host alleen de interface. Voor echte AI-feedback en servercontrole zijn een HTTPS-backend en een uitsluitend op de server ingestelde sleutel nodig. Zonder die verbinding blijft het een lokale oefenomgeving.
