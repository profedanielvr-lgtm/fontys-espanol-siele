import {bilingualConfirm,Localized} from './i18n';
import { useState } from 'react';
import type { EvaluationResult } from './types';
export function EvaluateButton({ apiUrl, taskId, choice, text, onResult }: {
    apiUrl: string;
    taskId: string;
    choice: number;
    text: string;
    onResult: (r: EvaluationResult) => void;
}) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    async function evaluate() {
        if (!bilingualConfirm('Se enviará tu texto al backend configurado y, si está activo, a su proveedor de IA para feedback formativo. Evita datos personales. ¿Enviar?','Je tekst gaat naar de ingestelde backend en, indien actief, de AI-aanbieder voor formatieve feedback. Vermijd persoonsgegevens. Versturen?'))
            return;
        setBusy(true);
        setError('');
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 65000);
        try {
            const address = new URL(apiUrl);
            if (!['http:', 'https:'].includes(address.protocol))
                throw new Error('Dirección inválida');
            const r = await fetch(`${apiUrl.replace(/\/$/, '')}/api/evaluar-tarea`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId, opcion: choice, texto: text }), signal: controller.signal });
            const body = await r.json();
            if (!r.ok)
                throw new Error(typeof body.detail === 'string' ? body.detail : `Servidor: ${r.status}`);
            onResult(body as EvaluationResult);
        }
        catch (e) {
            setError(String(e));
        }
        finally {
            clearTimeout(timeout);
            setBusy(false);
        }
    }
    return <Localized><div className="mt"><button className="secondary" disabled={busy || !text.trim()} onClick={() => void evaluate()}>{busy ? 'Solicitando feedback…' : 'Solicitar feedback de IA'}</button>{error && <p role="alert" className="error">{error}</p>}</div></Localized>;
}
