import type { Session, Preferences } from './types';
const KEY='fontys-ele-v2';
export const DEFAULT_PREFS:Preferences={alias:'Estudiante',target:'B2',contrast:false,largeText:false,apiUrl:''};
export type AppData={version:2;sessions:Session[];preferences:Preferences;notes:Record<string,string>};
export function load():AppData {
  const raw=localStorage.getItem(KEY);
  if(!raw)return {version:2,sessions:[],preferences:DEFAULT_PREFS,notes:{}};
  const data=JSON.parse(raw);
  if(data.version!==2 || !Array.isArray(data.sessions)||typeof data.notes!=='object') throw new Error('El formato del almacenamiento no es compatible. Exporta o borra los datos desde Ajustes.');
  return {...data,preferences:{...DEFAULT_PREFS,...data.preferences}};
}
export function save(data:AppData) {
  const raw=localStorage.getItem(KEY);
  if(raw){
    try{const existing=JSON.parse(raw);if(existing.version!==2||!Array.isArray(existing.sessions)||typeof existing.notes!=='object')throw new Error();}
    catch{throw new Error('Datos anteriores ilegibles: se conservan para evitar sobrescribirlos.');}
  }
  localStorage.setItem(KEY,JSON.stringify(data));
}
export function rawBackup(){return localStorage.getItem(KEY)||'{}';}
export function resetStore(){localStorage.removeItem(KEY);}
function openDb():Promise<IDBDatabase>{return new Promise((resolve,reject)=>{
  const r=indexedDB.open('fontys-ele-audio',1);
  r.onupgradeneeded=()=>r.result.createObjectStore('recordings');
  r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(new Error('No se pudo abrir el almacenamiento de audio.'));
});}
export async function putAudio(key:string,blob:Blob) {
  const db=await openDb();
  return new Promise<void>((resolve,reject)=>{const tx=db.transaction('recordings','readwrite');tx.objectStore('recordings').put(blob,key);tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>{db.close();reject(new Error('No se pudo guardar el audio. Comprueba el espacio disponible.'));};});
}
export async function getAudio(key:string):Promise<Blob|undefined> {
  const db=await openDb();return new Promise((resolve,reject)=>{const tx=db.transaction('recordings','readonly');const r=tx.objectStore('recordings').get(key);r.onsuccess=()=>{resolve(r.result);db.close();};r.onerror=()=>{db.close();reject(new Error('No se pudo recuperar la grabación.'));};});
}
export async function clearAudio(keys?:string[]) {
  const db=await openDb();return new Promise<void>((resolve,reject)=>{const tx=db.transaction('recordings','readwrite');const store=tx.objectStore('recordings');if(keys)keys.forEach(k=>store.delete(k));else store.clear();tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>{db.close();reject(new Error('No se pudo borrar el audio.'));};});
}
export function download(filename:string,content:string,type='application/json'){
  downloadBlob(filename,new Blob([content],{type}));
}
export function downloadBlob(filename:string,blob:Blob){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
