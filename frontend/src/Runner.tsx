import {bilingualConfirm,Localized,Bi} from './i18n';
import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { AudioPlayer } from './AudioPlayer';
import { Recorder } from './Recorder';
import { LABELS, SHORT, LEVELS, MINUTES, countWords, remaining, formatTime, nextTask, finish, chooseAdaptive, nextAdaptive } from './engine';
import type { Session, Task, Question, EvaluationResult } from './types';
type Props = {
    session: Session;
    tasks: Task[];
    apiUrl: string;
    patch: (p: Partial<Session>) => void;
    onExit: () => void;
    onFinish: () => void;
};
export function Runner({ session: s, tasks, apiUrl, patch, onExit, onFinish }: Props) {
    const [now, setNow] = useState(Date.now());
    const [busy, setBusy] = useState(false);
    const [confirmNext, setConfirmNext] = useState(false);
    const [apiBusy, setApiBusy] = useState(false);
    const [error, setError] = useState('');
    const [adaptiveAnswer, setAdaptiveAnswer] = useState<number>();
    const [oralIndex, setOralIndex] = useState(0);
    const advancing = useRef(false);
    const adaptive = s.mode === 'adaptativa';
    const adaptiveItem = adaptive ? chooseAdaptive(tasks, s, s.adaptiveLevel ?? 2) : undefined;
    const task = adaptiveItem?.task || tasks.find(t => t.id === s.taskIds[s.index]);
    const timed = s.mode === 'simulacro';
    const seconds = remaining(s.deadline, now);
    const chosen = task ? s.choices[task.id] ?? 0 : 0;
    const taskEnd = task ? s.taskEnds?.[task.id] : undefined;
    const taskSeconds = taskEnd ? remaining(taskEnd, now) : null;
    useEffect(() => { const t = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(t); }, []);
    useEffect(() => { setOralIndex(0); setConfirmNext(false); setError(''); advancing.current = false; window.scrollTo(0, 0); }, [task?.id]);
    useEffect(() => { if (s.status === 'finished')
        onFinish(); }, [s.status, onFinish]);
    useEffect(() => {
        if (!task || !timed || task.skill !== 'escucha' || s.breakUntil || s.taskEnds?.[task.id])
            return;
        patch({ taskEnds: { ...s.taskEnds, [task.id]: Date.now() + (task.audioSeconds ?? 600) * 1000 } });
    }, [task?.id, timed, s.breakUntil]);
    useEffect(() => {
        if (!timed || s.status !== 'active' || s.breakUntil || advancing.current)
            return;
        if (seconds === 0 || taskSeconds === 0) {
            if (busy) {
                window.dispatchEvent(new Event('exam-deadline'));
                return;
            }
            advancing.current = true;
            const next = nextTask(s, tasks, seconds === 0);
            patch(next);
        }
    }, [seconds, taskSeconds, busy, s, tasks]);
    useEffect(() => { if (s.breakUntil && s.breakUntil <= now && task) {
        patch({ breakUntil: undefined, breakDone: true, deadline: Date.now() + MINUTES[task.skill] * 60000 });
    } }, [now, s.breakUntil]);
    useEffect(() => { const prevent = (event: BeforeUnloadEvent) => { if (busy) {
        event.preventDefault();
        event.returnValue = '';
    } }; window.addEventListener('beforeunload', prevent); return () => window.removeEventListener('beforeunload', prevent); }, [busy]);
    if (!task)
        return <Localized><div className="empty card"><h1>No se encontró la actividad</h1><button onClick={onExit}>Volver al inicio</button></div></Localized>;
    if (s.breakUntil)
        return <Localized><section className="card break-screen"><Icon name="clock" size={50}/><p className="eyebrow">HAS TERMINADO LA COMPRENSIÓN AUDITIVA</p><h1>Un momento para respirar</h1><p>Descanso opcional antes de las tareas de producción. El progreso está guardado.</p><div className="big-timer">{formatTime(remaining(s.breakUntil, now) ?? 0)}</div><button onClick={() => patch({ breakUntil: undefined, breakDone: true, deadline: Date.now() + MINUTES[task.skill] * 60000 })}>Continuar con escritura <Icon name="arrow"/></button></section></Localized>;
    function answer(q: Question, value: number) { patch({ answers: { ...s.answers, [q.id]: value } }); }
    function advance() { if (busy)
        return; const n = nextTask(s, tasks); patch(n); setConfirmNext(false); }
    function selectChoice(value: number, key = task!.id) { patch({ choices: { ...s.choices, [key]: value } }); }
    async function evaluate() {
        if (!task || !apiUrl)
            return;
        if (!bilingualConfirm('Se enviarán tu texto y la referencia de la tarea al backend configurado y, si está activado, a su proveedor de IA. Evita datos personales. ¿Enviar para feedback formativo?','Je tekst en taakreferentie gaan naar de ingestelde backend en, indien actief, de AI-aanbieder. Vermijd persoonsgegevens. Versturen voor formatieve feedback?'))
            return;
        setApiBusy(true);
        setError('');
        try {
            const address = new URL(apiUrl);
            if (!['http:', 'https:'].includes(address.protocol))
                throw new Error('Dirección del servidor inválida.');
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 65000);
            try {
                const response = await fetch(`${apiUrl.replace(/\/$/, '')}/api/evaluar-tarea`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: task.id, opcion: chosen, texto: s.texts[task.id] || '' }), signal: controller.signal });
                const data = await response.json();
                if (!response.ok)
                    throw new Error(typeof data.detail === 'string' ? data.detail : 'El servidor rechazó la solicitud.');
                patch({ feedback: { ...s.feedback, [task.id]: data as EvaluationResult } });
            }
            finally {
                clearTimeout(timeout);
            }
        }
        catch (e) {
            setError(`No se pudo obtener feedback: ${String(e)}`);
        }
        finally {
            setApiBusy(false);
        }
    }
    const currentPrompts = task.id === 'eio-4' && chosen === 1 ? task.alternativePrompts! : task.prompts || [];
    const topic = s.choices['eio-4'] ?? 0;
    const oralChoiceIndex = task.id === 'eio-5' ? topic * 2 + chosen : chosen;
    const key = `${task.id}-${oralIndex}`;
    const isAnswered = task.skill === 'escritura' ? Boolean(s.texts[task.id]?.trim()) : task.skill === 'oral' ? currentPrompts.every((_, i) => s.audioKeys[`${task.id}-${i}`]) : task.maxSelections ? task.questions.filter(q => s.answers[q.id] === 1).length === task.maxSelections : task.questions.every(q => s.answers[q.id] !== undefined);
    return <Localized><>
    <div className="runner-heading"><button className="text-button" disabled={busy || apiBusy} onClick={onExit}>← Guardar y salir</button><span className="chip">{s.modality} · {s.mode === 'simulacro' ? 'Simulacro' : adaptive ? 'Ruta propia' : 'Práctica flexible'}</span><div className={`section-timer ${seconds !== null && seconds < 60 ? 'urgent' : ''}`}><Icon name="clock"/>{seconds === null ? 'A tu ritmo' : formatTime(seconds)}<small>{seconds === null ? '' : SHORT[task.skill]}</small></div></div>
    <div className="runner-layout"><aside className="task-sidebar card"><p className="eyebrow">TU RECORRIDO</p><strong>{adaptive ? `${Object.keys(s.answers).length}/12 preguntas` : LABELS[task.skill]}</strong>{adaptive ? <p>La dificultad objetivo cambia según tus respuestas. El recorrido no certifica tu nivel.</p> : <nav aria-label="Tareas del recorrido">{s.taskIds.map((id, i) => { const t = tasks.find(t => t.id === id)!; const allowed = !busy && !apiBusy && (s.mode === 'practica' || (task.skill === 'escritura' && t.skill === 'escritura')); return <button key={id} disabled={!allowed} aria-current={i === s.index ? 'step' : undefined} className={i === s.index ? 'task-nav current' : 'task-nav'} onClick={() => patch({ index: i })}><span>{String(i + 1).padStart(2, '0')}</span><div><small>{SHORT[t.skill]} · {t.level}</small>{t.title}</div>{s.flags.includes(id) && <Icon name="flag" size={14}/>}</button>; })}</nav>}<div className="save-label"><Icon name="check"/> Progreso local</div><p className="fine-print">{timed ? 'El reloj sigue aunque cierres la página. Cambiar de sección la cierra.' : 'Puedes salir y continuar desde Mi espacio.'}</p></aside>
    <section className="task-content"><div className="task-title"><div><p className="eyebrow">{SHORT[task.skill]} · {adaptive ? `PREGUNTA ${Object.keys(s.answers).length + 1} DE 12` : `TAREA ${task.order}`} · OBJETIVO {task.level}</p><h1>{task.title}</h1></div><button className={`icon-button ${s.flags.includes(task.id) ? 'flagged' : ''}`} aria-label="Marcar tarea para revisar" aria-pressed={s.flags.includes(task.id)} onClick={() => patch({ flags: s.flags.includes(task.id) ? s.flags.filter(id => id !== task.id) : [...s.flags, task.id] })}><Icon name="flag"/></button></div>
    <p className="task-instruction"><Bi es={task.instruction} nl={task.instruction_nl || "Nederlandse instructie ontbreekt; vraag ondersteuning vóór de start."} always/></p>
    {task.skill === 'escucha' && <><AudioPlayer key={task.id} text={task.stimulus} src={task.audio_url} variante_geolectal={task.variante_geolectal} plays={s.plays[task.id] || 0} onPlay={count => patch({ plays: { ...s.plays, [task.id]: count } })} unlimited={!timed} autoRepeat={timed}/>{timed ? <p className="fine-print">Tras pulsar, se reproduce hasta dos veces. Detener consume la reproducción iniciada. Tiempo de esta tarea: {formatTime(taskSeconds ?? task.audioSeconds ?? 0)}. Al agotarse avanza automáticamente. Este control de audio es una adaptación de práctica.</p> : <details className="transcript"><summary>Ver transcripción · ayuda de práctica</summary><div className="stimulus">{task.stimulus}</div></details>}</>}
    {task.skill === 'lectura' && task.stimulus && <div className="card stimulus">{task.stimulus}</div>}
    {task.choices && task.id !== 'eio-3' && <div className="choices-grid">{task.choices.filter((_, i) => task.id !== 'eio-5' || Math.floor(i / 2) === topic).map((c, i) => <button key={c.title} className={`choice-card ${chosen === i ? 'chosen' : ''}`} onClick={() => selectChoice(i)} disabled={busy || apiBusy || Object.keys(s.audioKeys).some(k => k.startsWith(task.id + '-'))}><span><b>{c.title}</b>{chosen === i && <Icon name="check"/>}</span>{c.image && <img src={(window as Window & {
        FONTYS_ASSETS?: Record<string, string>;
    }).FONTYS_ASSETS?.[c.image] || `${import.meta.env.BASE_URL}${c.image}`} alt={c.stimulus}/>}<p>{c.stimulus}</p></button>)}</div>}
    {task.id === 'eio-3' && <>{['Situación personal', 'Situación pública'].map((title, group) => <div key={title}><h2>{title}</h2><div className="choices-grid">{task.choices!.slice(group * 2, group * 2 + 2).map((c, i) => <button key={c.title} className={`choice-card ${(s.choices[`${task.id}-${group}`] ?? 0) === i ? 'chosen' : ''}`} disabled={busy || Object.keys(s.audioKeys).some(k => k.startsWith(task.id + '-'))} onClick={() => selectChoice(i, `${task.id}-${group}`)}><b>{c.title}</b><p>{c.stimulus}</p></button>)}</div></div>)}</>}
    {task.skill === 'escritura' && <><div className="card writing-area">{task.stimulus && <blockquote>{task.stimulus}</blockquote>}<div className="section-heading"><label htmlFor="written-response"><strong>Tu respuesta</strong></label><span className="fine-print">Referencia: {task.words?.join('–')} palabras</span></div><textarea id="written-response" spellCheck={!timed} autoComplete="off" autoCorrect={timed?"off":undefined} autoCapitalize="off" maxLength={15000} value={s.texts[task.id] || ''} disabled={apiBusy} onChange={e => patch({ texts: { ...s.texts, [task.id]: e.target.value }, feedback: { ...s.feedback, [task.id]: undefined as unknown as EvaluationResult } })} placeholder="Escribe aquí. Tu borrador se guarda automáticamente…"/><div className="section-heading"><span>{countWords(s.texts[task.id] || '')} palabras</span><span className="save-label"><Icon name="check"/> Borrador local</span></div></div>{!timed && <div className="notice"><Icon name="info"/><div>{apiUrl ? <><p>Feedback opcional de IA con rúbrica propia; no es una calificación oficial.</p><button className="secondary" disabled={apiBusy || !s.texts[task.id]?.trim()} onClick={() => void evaluate()}>{apiBusy ? 'Solicitando feedback…' : 'Solicitar feedback de IA'}</button></> : <p>Para feedback de IA, conecta el backend en Preferencias. Puedes completar y exportar tu texto sin conexión con IA.</p>}</div></div>}{s.feedback[task.id] && <Feedback result={s.feedback[task.id]}/>}</>}
    {task.skill === 'oral' && <div className="card oral-area"><div className="segmented oral-tabs">{currentPrompts.map((_, i) => <button disabled={busy} className={oralIndex === i ? 'selected' : ''} key={i} onClick={() => setOralIndex(i)}>{s.audioKeys[`${task.id}-${i}`] ? '✓ ' : ''}Respuesta {i + 1}</button>)}</div><h2>{currentPrompts[oralIndex]}</h2>{task.id === 'eio-3' && <p>{task.choices![(s.choices[`${task.id}-${oralIndex}`] ?? 0) + oralIndex * 2].stimulus}</p>}{task.id === 'eio-5' && <p>{task.choices![oralChoiceIndex].stimulus}</p>}<AudioPlayer key={`${task.id}-${oralIndex}-${chosen}`} text={currentPrompts[oralIndex]} unlimited/>
      <Recorder key={`${s.id}-${key}`} audioKey={`${s.id}-${key}`} duration={task.duration ?? 120} preparation={task.preparation ?? 0} existing={s.audioKeys[key]} onBusy={setBusy} onSaved={id => patch({ audioKeys: { ...s.audioKeys, [key]: id } })} disabled={timed && seconds === 0}/><p className="fine-print">Preparación y duración por respuesta son ajustes de práctica. El navegador puede solicitar permiso. No se asignan notas automáticas al audio.</p></div>}
    {(adaptive ? adaptiveItem ? [adaptiveItem.q] : [] : task.questions).map((q, i) => <div className="card question" key={q.id}>{q.stimulus && <div className="message-stimulus">{q.stimulus}</div>}<div className="question-heading"><span className="question-number">{i + 1}</span><h2>{q.prompt}</h2></div>{task.maxSelections ? <label className="option"><input type="checkbox" aria-label={`Seleccionar: ${q.prompt}`} checked={s.answers[q.id] === 1} disabled={s.answers[q.id] !== 1 && task.questions.filter(x => s.answers[x.id] === 1).length >= task.maxSelections} onChange={e => answer(q, e.target.checked ? 1 : 0)}/>Seleccionar esta idea</label> : <fieldset><legend className="sr-only">{q.prompt}</legend>{q.options.map((o, j) => <label className={`option ${(adaptive ? adaptiveAnswer : s.answers[q.id]) === j ? 'checked' : ''}`} key={j}><input type="radio" name={q.id} checked={(adaptive ? adaptiveAnswer : s.answers[q.id]) === j} onChange={() => adaptive ? setAdaptiveAnswer(j) : answer(q, j)}/><span className="option-letter">{String.fromCharCode(65 + j)}</span>{o}</label>)}</fieldset>}</div>)}
    {task.maxSelections && <p className="save-label">{task.questions.filter(q => s.answers[q.id] === 1).length}/{task.maxSelections} ideas seleccionadas</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <div className="runner-bottom"><span className="fine-print">{busy ? 'Guardando una respuesta oral; espera antes de salir.' : isAnswered ? 'Respuesta preparada. Puedes continuar.' : 'Puedes continuar aunque queden respuestas en blanco.'}</span>{adaptive ? <button disabled={adaptiveAnswer === undefined} onClick={() => { if (!adaptiveItem || adaptiveAnswer === undefined)
        return; const answers = { ...s.answers, [adaptiveItem.q.id]: adaptiveAnswer }; const updated = { ...s, answers, adaptiveLevel: nextAdaptive(s.adaptiveLevel ?? 2, adaptiveAnswer === adaptiveItem.q.answer) }; patch(Object.keys(answers).length >= 12 ? finish(updated) : updated); setAdaptiveAnswer(undefined); }}>Confirmar y continuar <Icon name="arrow"/></button> : <button disabled={busy || apiBusy} onClick={() => setConfirmNext(true)}>{s.index === s.taskIds.length - 1 ? 'Terminar recorrido' : 'Siguiente tarea'} <Icon name="arrow"/></button>}</div>
    {confirmNext && <div className="inline-confirm" role="alert"><strong>{s.index === s.taskIds.length - 1 ? '¿Terminar y ver tu informe?' : '¿Continuar a la siguiente tarea?'}</strong><p>{!isAnswered ? 'Quedan respuestas sin completar. ' : ''}{timed && task.skill !== 'escritura' ? 'No podrás volver a esta tarea en este simulacro.' : 'El borrador permanecerá guardado.'}</p><div className="button-row"><button onClick={advance}>Sí, continuar</button><button className="secondary" onClick={() => setConfirmNext(false)}>Seguir revisando</button></div></div>}
    </section></div>
  </></Localized>;
}
export function Feedback({ result }: {
    result: EvaluationResult;
}) { return <Localized><section className="card feedback"><span className="chip">{result.modo === 'demo' ? 'Demostración sin evaluación' : 'Feedback formativo de IA'}</span><h2>{result.evaluacion.nivel_estimado ? `Estimación de esta muestra: ${result.evaluacion.nivel_estimado}` : 'Sin nivel estimable'}</h2><p>{result.evaluacion.feedback_formativo}</p>{(['gramatica', 'coherencia', 'vocabulario', 'cumplimiento'] as const).map(k => <div className="feedback-criterion" key={k}><strong>{k} · {result.modo === 'demo' ? 'Sin evaluar' : `${result.evaluacion[k].puntuacion}/4`}</strong><p>{result.evaluacion[k].evidencia && `«${result.evaluacion[k].evidencia}» `}{result.evaluacion[k].justificacion}</p></div>)}<p className="fine-print">{result.evaluacion.limitaciones} {result.evaluacion.revision_humana ? 'Requiere revisión humana.' : ''}</p><small>{result.rubrica_version} · {result.modelo || 'Sin modelo'}</small></section></Localized>; }
