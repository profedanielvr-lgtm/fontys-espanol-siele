import type { Skill, Modality, Session, Task, Question } from './types';
export const SKILLS: Skill[] = ['lectura','escucha','escritura','oral'];
export const LABELS: Record<Skill,string> = {lectura:'Comprensión de lectura',escucha:'Comprensión auditiva',escritura:'Expresión e interacción escritas',oral:'Expresión e interacción orales'};
export const SHORT: Record<Skill,string> = {lectura:'CL',escucha:'CA',escritura:'EIE',oral:'EIO'};
export const LEVELS = ['A1','A2','B1','B2','C1'] as const;
export const MODALITIES: Record<Modality, Skill[]> = {Global:SKILLS,S1:['lectura','escucha'],S2:['lectura','escritura'],S3:['escucha','oral'],S4:['oral'],S5:['escritura','oral']};
// Duraciones de referencia del simulacro; oral 20 min según guía 2021.
export const MINUTES: Record<Skill,number> = {lectura:60,escucha:55,escritura:50,oral:20};
export function newSession(tasks:Task[], modality:Modality, mode:Session['mode']='simulacro', skill?:Skill, level?:string):Session {
  const selected = tasks.filter(t => skill ? t.skill === skill && (!level || t.level === level) : MODALITIES[modality].includes(t.skill));
  return {id:crypto.randomUUID(),modality:skill ? LABELS[skill] : modality,mode,createdAt:new Date().toISOString(),status:'active',taskIds:selected.map(t=>t.id),index:0,answers:{},texts:{},choices:{},flags:[],deadline:mode==='simulacro'&&selected[0] ? Date.now()+MINUTES[selected[0].skill]*60000 : null,plays:{},audioKeys:{},feedback:{},reflection:''};
}
export function countWords(text:string) { return text.trim() ? text.trim().split(/\s+/u).length : 0; }
export function remaining(deadline:number|null, now=Date.now()) {return deadline ? Math.max(0, Math.ceil((deadline-now)/1000)) : null;}
export function formatTime(seconds:number) {return `${Math.floor(seconds/60).toString().padStart(2,'0')}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;}
export function answerCorrect(q:Question, answers:Session['answers']) {return answers[q.id] === q.answer;}
export function objectiveScore(session:Session, tasks:Task[], skill?:Skill) {
  return tasks.filter(t=>session.taskIds.includes(t.id)&&(!skill||t.skill===skill)).reduce((score,t)=>{
    if(t.maxSelections) {
      const selected=t.questions.filter(q=>session.answers[q.id]===1);
      return {correct:score.correct+selected.filter(q=>q.answer===1).length,total:score.total+t.maxSelections,answered:score.answered+selected.length};
    }
    const questions=session.mode==='adaptativa'?t.questions.filter(q=>session.answers[q.id]!==undefined):t.questions;
    return {correct:score.correct+questions.filter(q=>answerCorrect(q,session.answers)).length,total:score.total+questions.length,answered:score.answered+questions.filter(q=>session.answers[q.id]!==undefined).length};
  },{correct:0,total:0,answered:0});
}
export function finish(session:Session):Session { return {...session,status:'finished',finishedAt:new Date().toISOString(),deadline:null}; }
export function nextTask(session:Session,tasks:Task[],skipSection=false):Session {
  const current=tasks.find(t=>t.id===session.taskIds[session.index]);
  let index=session.index+1;
  if(skipSection) while(index<session.taskIds.length && tasks.find(t=>t.id===session.taskIds[index])?.skill===current?.skill) index++;
  if(index>=session.taskIds.length)return finish(session);
  const next=tasks.find(t=>t.id===session.taskIds[index])!;
  const sectionChanged=next.skill!==current?.skill;
  const takeBreak=session.modality==='Global' && current?.skill==='escucha' && next.skill==='escritura' && !session.breakDone && session.mode==='simulacro';
  return {...session,index,deadline:sectionChanged && session.mode==='simulacro' ? (takeBreak?null:Date.now()+MINUTES[next.skill]*60000) : session.deadline,...(takeBreak?{breakUntil:Date.now()+15*60000}:{})};
}
// Regla pedagógica propia, sin estimación IRT ni equivalencia MCER.
export function nextAdaptive(level:number, correct:boolean) {return Math.max(0,Math.min(4,level+(correct?1:-1)));}
export function chooseAdaptive(tasks:Task[], session:Session, level:number) {
  const questions=tasks.filter(t=>t.skill==='lectura').flatMap(t=>t.questions.map(q=>({q,task:t})));
  const fresh=questions.filter(x=>session.answers[x.q.id]===undefined);
  return fresh.sort((a,b)=>Math.abs(LEVELS.indexOf(a.task.level)-level)-Math.abs(LEVELS.indexOf(b.task.level)-level))[0];
}
