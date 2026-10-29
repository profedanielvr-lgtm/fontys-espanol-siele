import { useEffect, useRef, useState } from 'react';
import { Bi, Localized, bilingualConfirm } from './i18n';
import { Recorder } from './Recorder';
import { AudioPlayer } from './AudioPlayer';
import { Feedback } from './Runner';
import { getAudio, download } from './storage';
import { formatTime, countWords } from './engine';
import type { Task, EvaluationResult } from './types';
type Draft = {
    answers: Record<string, number>;
    text: string;
    choices: Record<string, number>;
};
type State = {
    id: string;
    revision: number;
    server_now: number;
    deadline: number | null;
    task_deadline: number | null;
    break_until: number | null;
    status: string;
    index: number;
    total_tasks: number;
    task: Task | null;
    response: Partial<Draft>;
    scores: Record<string, {
        correct: number;
        total: number;
    }>;
    reviews: Record<string, any>;
    writing_tasks: {
        id: string;
        index: number;
        title: string;
    }[];
    reviewable_tasks: string[];
    recording_parts: string[];
    oral_topic: number;
    event_count: number;
};
const empty: Draft = { answers: {}, text: '', choices: {} };
export function SecureExam({ apiUrl }: {
    apiUrl: string;
}) {
    const [code, setCode] = useState('');
    const [state, setState] = useState<State>();
    const [draft, setDraft] = useState<Draft>(empty);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const [recording, setRecording] = useState(false);
    const [now, setNow] = useState(Date.now());
    const [part, setPart] = useState(0);
    const [agreed, setAgreed] = useState(false);
    const [plays, setPlays] = useState(0);
    const dirty = useRef(false);
    const token = useRef('');
    const latest = useRef<State | undefined>(undefined);
    const currentDraft = useRef(draft);
    currentDraft.current = draft;
    const lastSync = useRef(0);
    const offset = useRef(0);
    const queue = useRef(Promise.resolve());
    function update(s: State) { latest.current = s; offset.current = s.server_now * 1000 - Date.now(); setNow(Date.now()); setState(s); }
    async function request(path: string, body?: unknown, method = body ? 'POST' : 'GET') {
        const base = new URL(apiUrl);
        if (base.protocol !== 'https:' && !(base.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(base.hostname)))
            throw new Error('Se requiere HTTPS / HTTPS is vereist');
        const headers: Record<string, string> = {};
        if (token.current)
            headers.Authorization = `Bearer ${token.current}`;
        if (body && !(body instanceof FormData))
            headers['Content-Type'] = 'application/json';
        const abort = new AbortController();
        const timeout = setTimeout(() => abort.abort(), 90000);
        try {
            const r = await fetch(`${apiUrl.replace(/\/$/, '')}/api/secure${path}`, { method, headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined, signal: abort.signal, cache: 'no-store' });
            const data = await r.json();
            if (!r.ok)
                throw new Error(typeof data.detail === 'string' ? data.detail : `Servidor / Server: ${r.status}`);
            return data;
        }
        finally {
            clearTimeout(timeout);
        }
    }
    function enqueue(action: () => Promise<void>) { queue.current = queue.current.catch(() => { }).then(action); return queue.current; }
    async function save() {
        const id = latest.current?.task?.id;
        const captured = structuredClone(currentDraft.current);
        await enqueue(async () => { const s = latest.current; if (!s || s.task?.id !== id)
            throw new Error('Tarea cerrada; conserva tu borrador / Taak gesloten; bewaar je concept'); update(await request('/response', { revision: s.revision, ...captured })); if (JSON.stringify(currentDraft.current) === JSON.stringify(captured)) {
            dirty.current = false;
            try {
                sessionStorage.removeItem(`fontys-draft:${s.id}:${id}`);
            }
            catch { }
        } });
    }
    async function perform(action: () => Promise<void>) { setBusy(true); setError(''); try {
        await action();
    }
    catch (e) {
        setError(String(e));
    }
    finally {
        setBusy(false);
    } }
    useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 500); return () => clearInterval(timer); }, []);
    useEffect(() => { const s = state; if (!s?.task)
        return; let restored: Draft = { answers: s.response.answers || {}, text: s.response.text || '', choices: s.response.choices || {} }; dirty.current = false; try {
        const saved = sessionStorage.getItem(`fontys-draft:${s.id}:${s.task.id}`);
        if (saved) {
            const candidate = JSON.parse(saved);
            if (typeof candidate.text === 'string' && typeof candidate.answers === 'object' && typeof candidate.choices === 'object') {
                restored = candidate;
                dirty.current = true;
            }
        }
    }
    catch { } currentDraft.current = restored; setDraft(restored); setPart(0); setPlays(0); }, [state?.task?.id]);
    useEffect(() => { if (!apiUrl)
        return; try {
        const stored = sessionStorage.getItem(`fontys-secure:${apiUrl}`);
        if (stored) {
            token.current = stored;
            void perform(async () => update(await request('/session')));
        }
    }
    catch { } }, [apiUrl]);
    useEffect(() => { if (!state || state.status !== 'active' || busy || recording)
        return; const timer = setInterval(() => { void perform(async () => { await save(); await enqueue(async () => update(await request('/session'))); }); }, 20000); return () => clearInterval(timer); }, [state?.id, state?.status, busy, recording]);
    useEffect(() => { if (!state || state.status !== 'active')
        return; const hidden = () => { if (document.hidden)
        void enqueue(async () => { try {
            await request('/events', { kind: 'visibility_hidden', note: '' });
            update(await request('/session'));
        }
        catch { } }); }; const fullscreen = () => { if (!document.fullscreenElement)
        void enqueue(async () => { try {
            await request('/events', { kind: 'fullscreen_exit', note: '' });
            update(await request('/session'));
        }
        catch { } }); }; document.addEventListener('visibilitychange', hidden); document.addEventListener('fullscreenchange', fullscreen); return () => { document.removeEventListener('visibilitychange', hidden); document.removeEventListener('fullscreenchange', fullscreen); }; }, [state?.id, state?.status]);
    useEffect(() => { if (!state || state.status !== 'active' || busy || recording)
        return; const deadlines = [state.deadline, state.task_deadline, state.break_until].filter((n): n is number => Boolean(n)); if (deadlines.length && Math.min(...deadlines) * 1000 <= now + offset.current && now - lastSync.current > 10000) {
        lastSync.current = now;
        void perform(async () => update(await request('/session')));
    } }, [now, state?.deadline, state?.task_deadline, state?.break_until, busy, recording]);
    useEffect(() => { if (dirty.current && state?.task)
        try {
            sessionStorage.setItem(`fontys-draft:${state.id}:${state.task.id}`, JSON.stringify(currentDraft.current));
        }
        catch {
            setError('No se pudo guardar la copia de emergencia / Noodkopie kon niet worden opgeslagen');
        } }, [draft, state?.task?.id]);
    const t = state?.task;
    const choice = t ? draft.choices[t.id] ?? 0 : 0;
    const left = state?.deadline ? Math.max(0, Math.ceil(state.deadline - (now + offset.current) / 1000)) : null;
    const prompts = t ? (t.id === 'eio-4' && choice === 1 ? t.alternativePrompts! : t.prompts || []) : [];
    function edit(p: Partial<Draft>) { dirty.current = true; setDraft(d => ({ ...d, ...p })); }
    if (!apiUrl)
        return <Localized><section className="card"><h1>Sesión controlada</h1><p><Bi always es="Conecta un backend HTTPS en Preferencias. GitHub Pages ofrece práctica local, no un servidor de exámenes. Nunca introduzcas claves del proveedor en la página." nl="Verbind bij Voorkeuren een HTTPS-backend. GitHub Pages biedt lokale oefeningen, geen examenserver. Voer nooit een API-sleutel van de aanbieder in op de website."/></p></section></Localized>;
    if (!state)
        return <Localized><section className="card form-stack"><h1>Sesión controlada</h1><Bi always es="Utiliza un código de acceso de un solo uso emitido por tu docente. El servidor controla el tiempo y el cierre de las respuestas. Las incidencias técnicas se registran para revisión, nunca como prueba automática de fraude." nl="Gebruik een eenmalige toegangscode van je docent. De server beheert de tijd en het afsluiten van antwoorden. Technische incidenten worden geregistreerd voor beoordeling, nooit als automatisch bewijs van fraude."/><label><Bi es="Código de acceso" nl="Toegangscode"/><input value={code} onChange={e => setCode(e.target.value)} autoComplete="off" maxLength={128}/></label><label className="checkbox-label"><input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)}/><Bi always es="He leído las instrucciones, dispongo de un lugar tranquilo y comprendo qué datos se envían al servidor. Las respuestas productivas pueden requerir revisión humana." nl="Ik heb de instructies gelezen, heb een rustige werkplek en begrijp welke gegevens naar de server gaan. Productieve antwoorden kunnen menselijke beoordeling vereisen."/></label><button disabled={!agreed || code.length < 16 || busy} onClick={() => void perform(async () => { const result = await request('/sessions', { code }); token.current = result.token; sessionStorage.setItem(`fontys-secure:${apiUrl}`, result.token); update(result); })}><Bi es="Entrar y empezar" nl="Aanmelden en starten"/></button>{error && <p className="error" role="alert">{error}</p>}</section></Localized>;
    if (state.break_until)
        return <section className="card break-screen"><h1><Bi es="Descanso" nl="Pauze"/></h1><strong>{formatTime(Math.max(0, Math.ceil(state.break_until - (now + offset.current) / 1000)))}</strong><button disabled={busy} onClick={() => void perform(async () => update(await request('/break/end', {})))}><Bi es="Terminar descanso" nl="Pauze beëindigen"/></button></section>;
    if (state.status === 'finished')
        return <Localized><section className="card"><h1><Bi es="Informe del servidor" nl="Serververslag"/></h1><Bi always es="Los aciertos proceden del servidor. La propuesta de IA no es una calificación oficial. La revisión humana se publica por separado." nl="Correcte antwoorden worden op de server bepaald. Het AI-voorstel is geen officiële score. De menselijke beoordeling wordt afzonderlijk gepubliceerd."/>{Object.entries(state.scores).map(([skill, s]) => <p key={skill}>{skill}: <strong>{s.correct}/{s.total}</strong></p>)}<div className="button-row"><button onClick={() => download('informe-sesion.json', JSON.stringify(state, null, 2))}>Descargar informe</button><button className="secondary" disabled={busy} onClick={() => void perform(async () => update(await request('/session')))}><Bi es="Actualizar revisión" nl="Beoordeling vernieuwen"/></button></div><h2 className="mt"><Bi es="Solicitar propuesta de IA tras el examen" nl="Na de toets een AI-voorstel aanvragen"/></h2><p><Bi always es="Se envían respuestas al proveedor configurado. La pronunciación y la fluidez requieren escuchar el audio original; una transcripción no basta. La IA puede fallar y nunca certifica el nivel oral." nl="Antwoorden worden naar de ingestelde aanbieder gestuurd. Uitspraak en vloeiendheid vereisen beoordeling van de originele audio; een transcriptie volstaat niet. AI kan fouten maken en certificeert nooit het spreekniveau."/></p><div className="button-row">{state.reviewable_tasks.map(id => <button key={id} className="secondary" disabled={busy} onClick={() => { if (bilingualConfirm('¿Enviar esta respuesta al proveedor para una propuesta formativa de IA?', 'Dit antwoord naar de aanbieder sturen voor een formatief AI-voorstel?'))
            void perform(async () => update(await request(`/review/${id}`, {}))); }}>{id}</button>)}</div>{Object.entries(state.reviews).map(([id, r]) => <details className="card mt" key={id}><summary>{id} · {r.estado}</summary>{r.evaluacion ? <Feedback result={{ modo: 'openai', modelo: r.modelo, rubrica_version: r.rubrica_version, evaluacion: r.evaluacion } as EvaluationResult}/> : <pre className="review-json">{JSON.stringify(r, null, 2)}</pre>}</details>)}<div className="mt"><button className="danger" onClick={() => { if (bilingualConfirm('¿Borrar este intento, sus audios y la revisión del servidor?', 'Deze poging, de audio en de beoordeling van de server verwijderen?'))
            void perform(async () => { await request('/session', undefined, 'DELETE'); sessionStorage.removeItem(`fontys-secure:${apiUrl}`); token.current = ''; setState(undefined); }); }}><Bi es="Borrar mi sesión del servidor" nl="Mijn sessie van de server verwijderen"/></button></div>{error && <p className="error" role="alert">{error}</p>}</section></Localized>;
    if (!t)
        return null;
    return <Localized><section className="secure-session"><div className="runner-heading"><span className="chip"><Bi es="Sesión controlada por servidor" nl="Servergestuurde sessie"/> · {state.index + 1}/{state.total_tasks}</span><strong className="timer">{left === null ? '—' : formatTime(left)}</strong><button className="secondary" onClick={() => document.documentElement.requestFullscreen?.().catch(() => setError('Pantalla completa no disponible / Volledig scherm niet beschikbaar'))}><Bi es="Pantalla completa opcional" nl="Optioneel volledig scherm"/></button></div><div className="notice"><Bi always es="No uses ayudas externas. Desactiva notificaciones y comprueba auriculares y micrófono antes de empezar. La pantalla completa y la pérdida de foco no prueban ni impiden fraude. No se activa cámara ni reconocimiento facial." nl="Gebruik geen externe hulpmiddelen. Schakel meldingen uit en controleer hoofdtelefoon en microfoon vooraf. Volledig scherm en focusverlies bewijzen of voorkomen geen fraude. Er wordt geen camera of gezichtsherkenning gebruikt."/></div><h1>{t.title}</h1><p className="task-instruction"><Bi always es={t.instruction} nl={t.instruction_nl || 'Vraag je docent vóór de start om een Nederlandse instructie.'}/></p><p className="fine-print"><Bi es="Los estímulos y respuestas permanecen en español para conservar lo que se evalúa." nl="Teksten, vragen en antwoorden blijven Spaans om de beoogde vaardigheid te behouden."/></p>
 {t.skill === 'escritura' && <div className="segmented mb">{state.writing_tasks.map(x => <button key={x.id} disabled={busy || recording} onClick={() => void perform(async () => { await save(); await enqueue(async () => update(await request(`/writing/${x.index}`, { revision: latest.current!.revision }))); })}>{x.title}</button>)}</div>}
 {t.skill === 'escucha' ? <AudioPlayer key={t.id} text={t.stimulus} plays={plays} onPlay={setPlays} autoRepeat/> : t.stimulus && <div className="card stimulus" data-spanish-material>{t.stimulus}</div>}
 {t.choices && <div className="choices-grid">{t.choices.filter((_, i) => t.id !== 'eio-5' || Math.floor(i / 2) === state.oral_topic).map((c, i) => <button className={`choice-card ${(t.id === 'eio-3' ? (draft.choices[t.id + '-' + Math.floor(i / 2)] ?? 0) : choice) === i % 2 ? 'chosen' : ''}`} disabled={busy || recording || state.recording_parts.some(k => k.startsWith(t.id + ':'))} key={c.title} onClick={() => edit({ choices: { ...draft.choices, ...(t.id === 'eio-3' ? { [t.id + '-' + Math.floor(i / 2)]: i % 2 } : { [t.id]: i % 2 }) } })}><strong>{c.title}</strong><p>{c.stimulus}</p>{c.image && <img src={`${import.meta.env.BASE_URL}${c.image}`} alt={c.stimulus}/>}</button>)}</div>}
 {t.skill === 'escritura' && <div className="card writing-area"><label htmlFor="secure-text">Tu respuesta</label><textarea id="secure-text" disabled={busy} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" maxLength={15000} value={draft.text} onChange={e => edit({ text: e.target.value })}/><p>{countWords(draft.text)} palabras</p></div>}
 {t.questions.map(q => <fieldset className="card question" key={q.id}><legend>{q.prompt}</legend>{q.stimulus && <p className="stimulus" data-spanish-material>{q.stimulus}</p>}{t.maxSelections ? <label><input type="checkbox" checked={draft.answers[q.id] === 1} disabled={draft.answers[q.id] !== 1 && Object.values(draft.answers).filter(n => n === 1).length >= t.maxSelections} onChange={e => edit({ answers: { ...draft.answers, [q.id]: e.target.checked ? 1 : 0 } })}/> <Bi es="Seleccionar esta idea" nl="Deze gedachte selecteren"/></label> : q.options.map((o, i) => <label className="option" key={o}><input type="radio" disabled={busy} name={q.id} checked={draft.answers[q.id] === i} onChange={() => edit({ answers: { ...draft.answers, [q.id]: i } })}/><span data-spanish-material>{o}</span></label>)}</fieldset>)}
 {t.skill === 'oral' && <div className="card"><div className="segmented">{prompts.map((_, i) => <button disabled={recording || busy} onClick={() => setPart(i)} key={i}>Respuesta {i + 1}</button>)}</div><h2 className="mt">{prompts[part]}</h2><Recorder key={`${t.id}-${part}`} audioKey={`secure-${state.id}-${t.id}-${part}`} duration={Math.max(1, Math.min(t.duration || 120, left ?? 300))} preparation={t.preparation || 0} onBusy={setRecording} disabled={busy || state.recording_parts.includes(`${t.id}:${part}`)} onSaved={key => void perform(async () => { await save(); const blob = await getAudio(key); if (!blob)
        throw new Error('Audio no disponible / Audio niet beschikbaar'); const form = new FormData(); form.append('part', String(part)); form.append('revision', String(latest.current!.revision)); form.append('archivo', blob, 'respuesta'); await enqueue(async () => update(await request('/oral', form))); })}/><p className="fine-print"><Bi always es="Una grabación local no confirma su recepción. Comprueba que aparece como recibida por el servidor antes de avanzar." nl="Een lokale opname bevestigt de ontvangst niet. Controleer vóór je doorgaat of de server de opname heeft ontvangen."/></p><p>{state.recording_parts.includes(`${t.id}:${part}`) ? <Bi es="Audio recibido por el servidor" nl="Audio ontvangen door de server"/> : <Bi es="Pendiente de recepción" nl="Wacht op ontvangst"/>}</p></div>}
 <div className="button-row mt"><button className="secondary" disabled={busy || recording} onClick={() => void perform(save)}><Bi es="Guardar en servidor" nl="Opslaan op de server"/></button><button disabled={busy || recording} onClick={() => { if (bilingualConfirm('¿Cerrar esta tarea y continuar? Las respuestas en blanco se conservan como tales.', 'Deze taak afsluiten en doorgaan? Onbeantwoorde vragen blijven leeg.'))
        void perform(async () => { await save(); await enqueue(async () => update(await request('/next', { revision: latest.current!.revision }))); }); }}>Siguiente tarea</button><button className="text-button" disabled={busy || recording} onClick={() => void perform(async () => { const note = window.prompt('Explica la incidencia / Licht het incident toe'); if (note) {
        await request('/events', { kind: 'candidate_note', note: note.slice(0, 500) });
        update(await request('/session'));
    } })}><Bi es="Explicar una incidencia" nl="Een incident toelichten"/></button></div><small><Bi es="Incidencias registradas (sin penalización automática)" nl="Geregistreerde incidenten (geen automatische aftrek)"/>: {state.event_count}</small>{error && <div className="error" role="alert">{error}<button className="secondary" onClick={() => download('borrador-no-enviado.json', JSON.stringify(currentDraft.current, null, 2))}><Bi es="Descargar borrador de emergencia" nl="Noodkopie van concept downloaden"/></button><button className="secondary" onClick={() => void perform(async () => update(await request('/session')))}><Bi es="Sincronizar con servidor" nl="Met server synchroniseren"/></button></div>}</section></Localized>;
}
