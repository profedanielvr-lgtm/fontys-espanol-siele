import { Children, Fragment, cloneElement, createContext, isValidElement, useContext, useEffect, useState, type ReactNode, type ReactElement } from 'react';
import dictionary from './nl.json';
type Language = 'both' | 'es' | 'nl';
const Locale = createContext<{
    language: Language;
    setLanguage: (l: Language) => void;
}>({ language: 'both', setLanguage: () => { } });
const translations: Record<string, string> = dictionary;
function translation(key: string): string | undefined {
    if (translations[key])
        return translations[key];
    const patterns: [
        RegExp,
        (m: RegExpMatchArray) => string
    ][] = [
        [/^(\d+) de (\d+) respuestas objetivas$/, m => `${m[1]} van ${m[2]} objectieve antwoorden`],
        [/^(\d+) aciertos de (\d+)$/, m => `${m[1]} correcte antwoorden van ${m[2]}`],
        [/^(\d+) grabaciones guardadas$/, m => `${m[1]} opgeslagen opnamen`],
        [/^Prepara tu (Global|S[1-5])$/, m => `Bereid je ${m[1]} voor`],
        [/^PREGUNTA (\d+) DE (\d+)$/, m => `VRAAG ${m[1]} VAN ${m[2]}`],
        [/^TAREA (\d+)$/, m => `TAAK ${m[1]}`],
        [/^Respuesta (\d+)$/, m => `Antwoord ${m[1]}`],
        [/^Estimación de esta muestra: (A1|A2|B1|B2|C1)$/, m => `Schatting voor dit taalvoorbeeld: ${m[1]}`],
        [/^(\d+)\/2 reproducciones iniciadas$/, m => `${m[1]}/2 afspeelbeurten gestart`]
    ];
    for (const [pattern, format] of patterns) {
        const match = key.match(pattern);
        if (match)
            return format(match);
    }
    return undefined;
}
export function I18nProvider({ children }: {
    children: ReactNode;
}) {
    const [language, setLanguage] = useState<Language>(() => { try {
        const l = localStorage.getItem('fontys-language');
        return l === 'es' || l === 'nl' ? l : 'both';
    }
    catch {
        return 'both';
    } });
    useEffect(() => { document.documentElement.lang = language === 'nl' ? 'nl' : 'es'; try {
        localStorage.setItem('fontys-language', language);
    }
    catch { /* Lectura sigue disponible sin almacenamiento. */ } }, [language]);
    return <Locale.Provider value={{ language, setLanguage }}>{children}</Locale.Provider>;
}
export function LanguageSelector() { const { language, setLanguage } = useContext(Locale); return <label className="language-selector"><span className="sr-only">Idioma de las instrucciones / Taal van de instructies</span><select aria-label="Idioma / Taal" value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="both">ES + NL</option><option value="es">Español</option><option value="nl">Nederlands</option></select></label>; }
export function Bi({ es, nl, always = false }: {
    es: string;
    nl: string;
    always?: boolean;
}) { const { language } = useContext(Locale); return <span className="bilingual">{(always || language !== 'nl') && <span lang="es">{es}</span>}{(always || language !== 'es') && <span lang="nl" className={language === 'nl' && !always ? '' : 'translation-nl'}>{nl}</span>}</span>; }
export function bilingualConfirm(es: string, nl: string) { return window.confirm(`${es}\n\n${nl}`); }
// Traducción React declarativa, solo de cadenas conocidas de interfaz.
// No reescribe el DOM, estímulos, respuestas del candidato ni contenido de audio.
export function Localized({ children }: {
    children: ReactNode;
}) {
    const { language } = useContext(Locale);
    function text(value: string): ReactNode {
        const key = value.trim().replace(/\s+/g, ' ');
        const nl = translation(key);
        if (!nl)
            return value;
        const prefix = value.match(/^\s*/)?.[0] || '';
        const suffix = value.match(/\s*$/)?.[0] || '';
        return <>{prefix}{language === 'both' ? <span className="bi-inline"><span lang="es">{key}</span><span lang="nl" className="translation-nl">{nl}</span></span> : <span lang={language}>{language === 'nl' ? nl : key}</span>}{suffix}</>;
    }
    function walk(node: ReactNode): ReactNode {
        return Children.map(node, child => {
            if (typeof child === 'string')
                return text(child);
            if (!isValidElement(child))
                return child;
            const element = child as ReactElement<Record<string, unknown>>;
            if (typeof element.type !== 'string' && element.type !== Fragment)
                return child;
            if (element.props['data-spanish-material'] || element.props['aria-hidden'] === true || element.props['aria-hidden'] === 'true' || element.props.lang === 'es' || element.props.lang === 'nl')
                return child;
            const props: Record<string, unknown> = {};
            for (const key of ['placeholder', 'aria-label', 'title']) {
                const value = element.props[key];
                if (typeof value === 'string' && translations[value])
                    props[key] = language === 'es' ? value : language === 'nl' ? translations[value] : `${value} / ${translations[value]}`;
            }
            if (element.props.children !== undefined)
                props.children = walk(element.props.children as ReactNode);
            return cloneElement(element, props);
        });
    }
    return <>{walk(children)}</>;
}
