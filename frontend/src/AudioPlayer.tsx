import {Bi} from './i18n';
import {useEffect,useRef,useState} from 'react';
import {load} from './storage';
type Props={text:string;src?:string;variante_geolectal?:string;plays?:number;onPlay?:(count:number)=>void;unlimited?:boolean;autoRepeat?:boolean};
export function AudioPlayer({text,src,variante_geolectal='espanol_peninsular',plays=0,onPlay,unlimited=false,autoRepeat=false}:Props){
 const audio=useRef<HTMLAudioElement>(null),count=useRef(plays);
 const [url,setUrl]=useState(src||''),[error,setError]=useState(''),[playing,setPlaying]=useState(false);
 useEffect(()=>{count.current=plays;},[plays]);
 useEffect(()=>{const controller=new AbortController();setUrl(src||'');setError('');setPlaying(false);
   if(!src){let base='';try{base=load().preferences.apiUrl.replace(/\/$/,'');}catch{}
     if(base)fetch(`${base}/api/audio-estimulo?${new URLSearchParams({texto:text,variante_geolectal})}`,{signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error();return r.json();}).then(data=>setUrl(new URL(data.url,base).href)).catch(e=>{if(e.name!=='AbortError')setError('missing');});
     else setError('missing');
   }
   return()=>controller.abort();
 },[src,text,variante_geolectal]);
 useEffect(()=>{const player=audio.current;if(player){player.pause();player.load();}return()=>player?.pause();},[url]);
 async function play(){if(!audio.current||(!unlimited&&count.current>=2))return;
   setError('');try{await audio.current.play();count.current++;onPlay?.(count.current);setPlaying(true);}catch{setError('play');setPlaying(false);}}
 return <div className="audio-player"><div><strong><Bi es="Audio de la actividad" nl="Audio bij de taak"/></strong><small><Bi es="Voz sintética · variante sujeta a revisión docente" nl="Synthetische stem · taalvariant vereist docentcontrole"/></small>
 <audio ref={audio} src={url||undefined} preload="metadata" aria-label="Audio / Audio" onError={()=>{setError('play');setPlaying(false);}} onEnded={()=>{setPlaying(false);if(autoRepeat&&count.current<2){if(audio.current)audio.current.currentTime=0;void play();}}}/>
 <button disabled={!url||(!playing&&!unlimited&&plays>=2)} onClick={()=>{if(playing){audio.current?.pause();setPlaying(false);}else void play();}}><Bi es={playing?'Detener':'Reproducir'} nl={playing?'Stoppen':'Afspelen'}/></button><small>{unlimited?'∞':`${plays}/2`}</small></div>
 {error&&<p role="alert" className="error"><Bi always es={error==='missing'?'MP3 no disponible. El docente debe preparar el audio y conectar el servidor en Ajustes. En práctica puedes consultar la transcripción.':'No se pudo reproducir el archivo. Comprueba la conexión y el formato; vuelve a intentarlo.'} nl={error==='missing'?'MP3 niet beschikbaar. De docent moet de audio voorbereiden en de server bij Instellingen aansluiten. Bij oefenen kun je het transcript bekijken.':'Afspelen mislukt. Controleer de verbinding en het bestandsformaat en probeer opnieuw.'}/></p>}</div>;
}
