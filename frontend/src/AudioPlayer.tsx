import {Localized} from './i18n';
import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
export function AudioPlayer({ text, plays = 0, onPlay, unlimited = false, autoRepeat = false }: {
    text: string;
    plays?: number;
    onPlay?: (count: number) => void;
    unlimited?: boolean;
    autoRepeat?: boolean;
}) {
    const [playing, setPlaying] = useState(false);
    const [error, setError] = useState('');
    const generation = useRef(0);
    const utterances = useRef<SpeechSynthesisUtterance[]>([]);
    useEffect(() => () => { generation.current++; if ('speechSynthesis' in window)
        speechSynthesis.cancel(); }, [text]);
    function stop() { generation.current++; speechSynthesis.cancel(); setPlaying(false); }
    function play() {
        if (!('speechSynthesis' in window)) {
            setError('La síntesis de voz no está disponible. Usa un navegador compatible o el modo de práctica con transcripción.');
            return;
        }
        if (!unlimited && plays >= 2)
            return;
        const token = ++generation.current;
        setError('');
        setPlaying(true);
        speechSynthesis.cancel();
        let count = plays + 1;
        onPlay?.(count);
        const pieces = text.match(/[^.!?\n]+[.!?]?/gu) || [text];
        const voices = speechSynthesis.getVoices();
        const voice = voices.find(v => v.lang.startsWith('es'));
        let i = 0;
        function speak() {
            if (token !== generation.current)
                return;
            if (i >= pieces.length) {
                if (autoRepeat && count < 2) {
                    count++;
                    i = 0;
                    onPlay?.(count);
                }
                else {
                    setPlaying(false);
                    return;
                }
            }
            const u = new SpeechSynthesisUtterance(pieces[i++]);
            u.lang = 'es-ES';
            u.rate = .94;
            if (voice)
                u.voice = voice;
            u.onend = speak;
            u.onerror = e => { if (token === generation.current && e.error !== 'canceled' && e.error !== 'interrupted') {
                setError('No se pudo reproducir la voz. Comprueba las voces de español instaladas.');
                setPlaying(false);
            } };
            utterances.current = [u];
            speechSynthesis.speak(u);
        }
        speak();
    }
    return <Localized><div className="audio-player"><div className={`sound-bars ${playing ? 'moving' : ''}`}>{Array.from({ length: 24 }, (_, i) => <i key={i} style={{ height: `${12 + (i * 17 % 31)}px`, animationDelay: `${i * .05}s` }}/>)}</div><div><strong>{playing ? 'Escuchando…' : 'Audio de práctica'}</strong><small>Voz sintética · {unlimited ? 'reproducción libre' : `${plays}/2 reproducciones iniciadas`}</small></div><button className="icon-button" aria-label={playing ? 'Detener audio' : 'Reproducir audio'} disabled={!playing && !unlimited && plays >= 2} onClick={playing ? stop : play}><Icon name={playing ? 'close' : 'play'}/></button>{error && <p role="alert" className="error">{error}</p>}</div></Localized>;
}
