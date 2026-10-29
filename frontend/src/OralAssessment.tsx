import type {OralResult} from './types';
import { useState } from 'react';
import { Bi, bilingualConfirm, Localized } from './i18n';
import { getAudio } from './storage';
import { Feedback } from './Runner';
export function OralAssessment({ apiUrl, audioKey, taskId, part, choice, topic,initialResult,onResult }: {
    apiUrl: string;
    audioKey: string;
    taskId: string;
    part: number;
    choice: number;
    topic: number;
    initialResult?:OralResult;onResult?:(result:OralResult)=>void;
}) {
    const [busy, setBusy] = useState(false);
    const [result, setResult] = useState<OralResult|undefined>(initialResult);
    const [error, setError] = useState('');
    async function assess() {
        if (!bilingualConfirm('¿Enviar el audio al servidor y al proveedor para transcripción y feedback? No se califican automáticamente pronunciación ni fluidez.', 'Audio naar de server en aanbieder sturen voor transcriptie en feedback? Uitspraak en vloeiendheid worden niet automatisch beoordeeld.'))
            return;
        setBusy(true);
        setError('');
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 90000);
        try {
            const url = new URL(apiUrl);
            if (url.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(url.hostname))
                throw new Error('HTTPS requerido / HTTPS vereist');
            const audio = await getAudio(audioKey);
            if (!audio)
                throw new Error('Audio no disponible / Audio niet beschikbaar');
            const form = new FormData();
            form.append('task_id', taskId);
            form.append('parte', String(part));
            form.append('opcion', String(choice));
            form.append('tema', String(topic));
            form.append('archivo', audio, 'respuesta');
            const response = await fetch(`${apiUrl.replace(/\/$/, '')}/api/evaluar-audio`, { method: 'POST', body: form, signal: controller.signal });
            const data = await response.json();
            if (!response.ok)
                throw new Error(typeof data.detail === 'string' ? data.detail : `Servidor / Server: ${response.status}`);
            setResult(data);onResult?.(data);
        }
        catch (e) {
            setError(String(e));
        }
        finally {
            clearTimeout(timer);
            setBusy(false);
        }
    }
    return <Localized><div className="oral-assessment"><button className="secondary" disabled={busy} onClick={() => void assess()}><Bi es={busy ? 'Analizando audio…' : 'Solicitar análisis de audio'} nl={busy ? 'Audio wordt geanalyseerd…' : 'Audioanalyse aanvragen'}/></button><p className="fine-print"><Bi es="Feedback parcial: transcripción y contenido. La evaluación oral global sigue pendiente de escucha humana." nl="Gedeeltelijke feedback: transcriptie en inhoud. Een totale spreekbeoordeling vereist nog beoordeling van de audio door een mens."/></p>{error && <p className="error" role="alert">{error}</p>}{result && <div className="card mt"><h3><Bi es="Propuesta de IA · revisión pendiente" nl="AI-voorstel · beoordeling nog nodig"/></h3><p className="stimulus" data-spanish-material>{result.transcripcion || '—'}</p><p><Bi es={result.limitacion_es} nl={result.limitacion_nl}/></p>{result.analisis_textual && <Feedback result={{ modo: 'openai', modelo: result.transcription_model, rubrica_version: 'formativa-mcer-2.0 · solo transcripción', evaluacion: result.analisis_textual }}/>}</div>}</div></Localized>;
}
