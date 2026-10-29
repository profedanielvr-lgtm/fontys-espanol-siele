import {useEffect,useRef,useState} from 'react';
import {getAudio,putAudio,downloadBlob} from './storage';
import {formatTime} from './engine';
import {Icon} from './Icon';
type Props={audioKey:string;duration:number;preparation:number;onSaved:(key:string)=>void;onBusy?:(busy:boolean)=>void;existing?:string;disabled?:boolean};
export function Recorder({audioKey,duration,preparation,onSaved,onBusy,existing,disabled=false}:Props){
  const [phase,setPhase]=useState<'ready'|'preparing'|'requesting'|'recording'|'saving'|'saved'>('ready');
  const [left,setLeft]=useState(duration);const [url,setUrl]=useState('');const [error,setError]=useState('');
  const recorder=useRef<MediaRecorder|null>(null);const stream=useRef<MediaStream|null>(null);const alive=useRef(true);const deadline=useRef(0);const blob=useRef<Blob|null>(null);
  const savedCallback=useRef(onSaved);savedCallback.current=onSaved;const busyCallback=useRef(onBusy);busyCallback.current=onBusy;
  function reportBusy(value:boolean){busyCallback.current?.(value);window.dispatchEvent(new CustomEvent('fontys-recording-state',{detail:value}));}
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;if(recorder.current){recorder.current.onstop=null;if(recorder.current.state!=='inactive')recorder.current.stop();}stream.current?.getTracks().forEach(t=>t.stop());reportBusy(false);};},[]);
  useEffect(()=>{const stop=()=>{if(recorder.current?.state==='recording')recorder.current.stop();};window.addEventListener('exam-deadline',stop);return()=>window.removeEventListener('exam-deadline',stop);},[]);
  useEffect(()=>{let active=true;let objectUrl='';if(existing)getAudio(existing).then(b=>{if(active&&b){blob.current=b;objectUrl=URL.createObjectURL(b);setUrl(objectUrl);setPhase('saved');}}).catch(e=>setError(String(e)));return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl);};},[existing]);
  useEffect(()=>()=>{if(url)URL.revokeObjectURL(url);},[url]);
  useEffect(()=>{
    if(phase!=='recording'&&phase!=='preparing')return;
    const timer=setInterval(()=>{const seconds=Math.max(0,Math.ceil((deadline.current-Date.now())/1000));setLeft(seconds);if(!seconds){if(phase==='recording')recorder.current?.stop();else{setPhase('ready');setLeft(duration);}}},200);
    return()=>clearInterval(timer);
  },[phase,duration]);
  async function persist(b:Blob){
    setPhase('saving');setError('');
    try{await putAudio(audioKey,b);if(!alive.current)return;setUrl(URL.createObjectURL(b));setPhase('saved');savedCallback.current(audioKey);}
    catch(e){if(alive.current){setError(`${String(e)} Tu audio sigue en memoria: descárgalo antes de salir.`);setPhase('ready');}}
    finally{reportBusy(false);}
  }
  async function record(){
    if(disabled)return;
    setError('');setPhase('requesting');reportBusy(true);
    try{
      if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined')throw new Error('El micrófono necesita HTTPS o localhost y un navegador compatible.');
      const type=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
      if(!type)throw new Error('No se encontró un formato de grabación compatible.');
      const media=await navigator.mediaDevices.getUserMedia({audio:true});
      if(!alive.current){media.getTracks().forEach(t=>t.stop());return;}
      stream.current=media;const r=new MediaRecorder(media,{mimeType:type,audioBitsPerSecond:64000});recorder.current=r;const chunks:Blob[]=[];
      r.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      r.onerror=()=>{r.onstop=null;media.getTracks().forEach(t=>t.stop());if(alive.current){setError('La grabación falló. Comprueba el micrófono e inténtalo de nuevo.');setPhase('ready');reportBusy(false);}};
      r.onstop=()=>{media.getTracks().forEach(t=>t.stop());if(!alive.current)return;const b=new Blob(chunks,{type:r.mimeType});blob.current=b;if(!b.size){setError('No se ha capturado audio.');setPhase('ready');reportBusy(false);return;}void persist(b);};
      deadline.current=Date.now()+duration*1000;setLeft(duration);r.start(1000);setPhase('recording');
    }catch(e){stream.current?.getTracks().forEach(t=>t.stop());if(alive.current){setPhase('ready');setError(String(e));reportBusy(false);}}
  }
  return <div className={`recorder ${phase==='recording'?'is-recording':''}`}>
    <div className="recorder-top"><span className="round-icon"><Icon name="mic" size={26}/></span><div><strong>{phase==='saved'?'Respuesta guardada':phase==='preparing'?'Prepara tu respuesta':phase==='recording'?'Grabando tu respuesta':'Tu turno de hablar'}</strong><small>{phase==='saved'?'Almacenada en este navegador':'El audio se guarda solo en este dispositivo.'}</small></div><span className="timer" role="timer">{formatTime(left)}</span></div>
    {url&&<audio controls src={url} aria-label="Escuchar tu respuesta"/>}
    <div className="button-row">
      {phase==='recording'?<button className="danger" onClick={()=>recorder.current?.stop()}>■ Detener y guardar</button>:<button disabled={disabled||phase==='requesting'||phase==='saving'||phase==='preparing'||phase==='saved'} onClick={()=>void record()}><Icon name="mic"/> {phase==='saving'?'Guardando…':phase==='requesting'?'Abriendo micrófono…':'Grabar respuesta'}</button>}
      {phase==='ready'&&preparation>0&&<button className="secondary" disabled={disabled} onClick={()=>{deadline.current=Date.now()+preparation*1000;setLeft(preparation);setPhase('preparing');}}>Preparar · {preparation}s</button>}
      {phase==='preparing'&&<button className="secondary" onClick={()=>{setPhase('ready');setLeft(duration);}}>Terminar preparación</button>}
      {blob.current&&<button className="secondary" onClick={()=>downloadBlob(`${audioKey}.${blob.current?.type.includes('mp4')?'mp4':blob.current?.type.includes('ogg')?'ogg':'webm'}`,blob.current!)}><Icon name="download"/> Descargar audio</button>}
      {phase==='saved'&&!disabled&&<button className="text-button" onClick={()=>{setPhase('ready');setLeft(duration);}}>Volver a grabar</button>}
      {error&&blob.current&&<button className="secondary" onClick={()=>void persist(blob.current!)}>Reintentar guardado</button>}
    </div>{error&&<p role="alert" className="error">{error}</p>}
  </div>;
}
