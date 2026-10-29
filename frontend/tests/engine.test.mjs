import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {MODALITIES,newSession,nextTask,objectiveScore,finish,remaining,nextAdaptive,chooseAdaptive} from '../src/engine.ts';
const tasks=JSON.parse(readFileSync(new URL('../public/bank.json',import.meta.url),'utf8')).tasks;
test('seis modalidades con las destrezas y tareas esperadas',()=>{
  assert.deepEqual(Object.keys(MODALITIES),['Global','S1','S2','S3','S4','S5']);
  for(const [m,n] of Object.entries({Global:18,S1:11,S2:7,S3:11,S4:5,S5:7}))assert.equal(newSession(tasks,m).taskIds.length,n);
});
test('38 aciertos por comprensión, sin premiar la no selección en CA6',()=>{
  const s=newSession(tasks,'S1');
  assert.deepEqual(objectiveScore(s,tasks,'lectura'),{correct:0,total:38,answered:0});
  assert.deepEqual(objectiveScore(s,tasks,'escucha'),{correct:0,total:38,answered:0});
  for(const t of tasks)for(const q of t.questions)s.answers[q.id]=q.answer;
  assert.equal(objectiveScore(s,tasks,'lectura').correct,38);
  assert.equal(objectiveScore(s,tasks,'escucha').correct,38);
  const t=tasks.find(t=>t.id==='ca-6');for(const q of t.questions)s.answers[q.id]=0;
  assert.equal(objectiveScore(s,tasks,'escucha').correct,32);
  for(const q of t.questions)s.answers[q.id]=q.answer===0?1:0;
  assert.equal(objectiveScore(s,tasks,'escucha').correct,32);
});
test('Global activa descanso antes de escritura y bloquea reloj durante él',()=>{
  const s=newSession(tasks,'Global');s.index=s.taskIds.indexOf('ca-6');
  const next=nextTask(s,tasks);
  assert.equal(next.taskIds[next.index],'eie-1');assert.ok(next.breakUntil>Date.now());assert.equal(next.deadline,null);
});
test('al vencer una sección, salta todas sus tareas pendientes',()=>{
  const s=newSession(tasks,'Global');const next=nextTask(s,tasks,true);
  assert.equal(next.taskIds[next.index],'ca-1');assert.ok(next.deadline>Date.now());
  const oral=newSession(tasks,'S4');assert.equal(nextTask(oral,tasks,true).status,'finished');
});
test('el reloj conserva una fecha absoluta y se termina en cero',()=>{
  assert.equal(remaining(10000,5000),5);assert.equal(remaining(10000,15000),0);assert.equal(remaining(null),null);
  assert.equal(finish(newSession(tasks,'S4')).deadline,null);
});
test('ruta adaptativa sin repeticiones, límites y puntuación solo de 12 ítems',()=>{
  let s=newSession(tasks,'S2','adaptativa','lectura');let level=2;
  for(let i=0;i<12;i++){const item=chooseAdaptive(tasks,s,level);assert.ok(item);assert.equal(s.answers[item.q.id],undefined);s.answers[item.q.id]=item.q.answer;level=nextAdaptive(level,true);}
  assert.equal(objectiveScore(s,tasks).total,12);assert.equal(objectiveScore(s,tasks).correct,12);
  assert.equal(nextAdaptive(4,true),4);assert.equal(nextAdaptive(0,false),0);
});
test('banco coherente: claves válidas, IDs únicos y opciones orales completas',()=>{
  const ids=tasks.flatMap(t=>[t.id,...t.questions.map(q=>q.id)]);assert.equal(new Set(ids).size,ids.length);
  for(const t of tasks)for(const q of t.questions){assert.ok(q.answer>=0&&q.answer<q.options.length);assert.ok(q.explanation.length>10);}
  assert.equal(tasks.find(t=>t.id==='eio-1').prompts.length,4);
  assert.equal(tasks.find(t=>t.id==='eio-3').choices.length,4);
  assert.equal(tasks.find(t=>t.id==='eio-4').prompts.length,3);
  assert.equal(tasks.find(t=>t.id==='eio-5').choices.length,4);
});
