import { useEffect, useState } from 'react';
import { Bi } from './i18n';
export function BackendStatus({ url }: {
    url: string;
}) {
    const [status, setStatus] = useState<'empty' | 'loading' | 'demo' | 'ai' | 'error'>('empty');
    useEffect(() => { if (!url) {
        setStatus('empty');
        return;
    } let live = true; const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 5000); setStatus('loading'); try {
        const parsed = new URL(url);
        if (parsed.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(parsed.hostname))
            throw new Error();
        fetch(`${url.replace(/\/$/, '')}/api/salud`, { signal: controller.signal, cache: 'no-store' }).then(r => { if (!r.ok)
            throw new Error(); return r.json(); }).then(r => { if (live)
            setStatus(r.ai_configured ? 'ai' : 'demo'); }).catch(() => { if (live)
            setStatus('error'); });
    }
    catch {
        setStatus('error');
    } return () => { live = false; clearTimeout(timer); controller.abort(); }; }, [url]);
    const labels = { empty: ['Sin backend conectado: solo práctica local. La IA y el control del servidor no están activos.', 'Geen backend verbonden: alleen lokaal oefenen. AI en servercontrole zijn niet actief.'], loading: ['Comprobando backend…', 'Backend controleren…'], demo: ['Backend conectado en modo demostración: sin calificación de IA real.', 'Backend verbonden in demonstratiemodus: geen echte AI-beoordeling.'], ai: ['Backend conectado e IA configurada. Las propuestas siguen requiriendo revisión humana.', 'Backend verbonden en AI ingesteld. De voorstellen blijven menselijke beoordeling vereisen.'], error: ['No se pudo conectar al backend. La práctica local sigue disponible.', 'Geen verbinding met de backend. Lokaal oefenen blijft beschikbaar.'] } as const;
    return <div className="notice backend-status" role="status"><Bi es={labels[status][0]} nl={labels[status][1]} always/></div>;
}
