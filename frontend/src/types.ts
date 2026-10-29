export type Skill = 'lectura' | 'escucha' | 'escritura' | 'oral';
export type Level = 'A1' | 'A2' | 'B1' | 'B2' | 'C1';
export type Question = { id: string; prompt: string; options: string[]; answer: number; explanation: string; stimulus?: string; group?: string };
export type Task = { id: string; skill: Skill; order: number; level: Level; title: string; instruction: string; stimulus: string; questions: Question[]; choices?: {title:string; stimulus:string; image?:string}[]; prompts?: string[]; alternativePrompts?: string[]; preparation?:number; duration?:number; words?:[number,number]; audioSeconds?:number; maxSelections?:number; };
export type Bank = { version: string; tasks: Task[] };
export type Modality = 'Global' | 'S1' | 'S2' | 'S3' | 'S4' | 'S5';
export type Session = {
  id:string; modality:string; mode:'simulacro'|'practica'|'adaptativa'; createdAt:string;
  finishedAt?:string; status:'active'|'finished'; taskIds:string[]; index:number;
  answers:Record<string,number>; texts:Record<string,string>; choices:Record<string,number>;
  flags:string[]; deadline:number|null; breakUntil?:number; breakDone?:boolean;
  plays:Record<string,number>; audioKeys:Record<string,string>; taskEnds?:Record<string,number>; scores?:Record<string,number>;
  feedback:Record<string,EvaluationResult>; reflection:string; adaptiveLevel?:number;
};
export type Criterion = {puntuacion:number;evidencia:string;justificacion:string};
export type EvaluationResult = { modo:string; modelo:string|null; rubrica_version:string; evaluacion:{nivel_estimado:Level|null;gramatica:Criterion;coherencia:Criterion;vocabulario:Criterion;cumplimiento:Criterion;feedback_formativo:string;limitaciones:string;revision_humana:boolean} };
export type Preferences = { alias:string; target:Level; contrast:boolean; largeText:boolean; apiUrl:string; };
