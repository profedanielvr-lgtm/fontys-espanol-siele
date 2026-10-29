import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const bank=JSON.parse(readFileSync(new URL('../public/bank.json',import.meta.url),'utf8'));
const nl=JSON.parse(readFileSync(new URL('../src/nl.json',import.meta.url),'utf8'));
test('las 18 tareas tienen instrucciones neerlandesas explícitas',()=>{
 assert.equal(bank.tasks.length,18);
 for(const t of bank.tasks){assert.ok(t.instruction_nl.length>25,t.id);assert.notEqual(t.instruction,t.instruction_nl);}
});
test('las acciones principales y todas las destrezas tienen traducción',()=>{
 for(const key of ['Mi espacio','Simulacros','Por destrezas','Sesión controlada','Protocolos de examen','Mi portafolio','Laboratorio docente','Guía y recursos','Tu respuesta','Grabar respuesta','Siguiente tarea','Terminar recorrido','Comprensión de lectura','Comprensión auditiva','Expresión e interacción escritas','Expresión e interacción orales'])assert.ok(nl[key],key);
 assert.ok(Object.keys(nl).length>200);
});
test('los estímulos no se convierten a traducciones para responder la prueba',()=>{
 for(const t of bank.tasks){assert.equal(t.stimulus_nl,undefined);for(const q of t.questions)assert.equal(q.options_nl,undefined);}
});
