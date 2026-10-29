// Migración única a una capa React declarativa, sin traducción de estímulos.
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import {readFile,writeFile} from 'node:fs/promises';
const files=['App','Runner','Results','Recorder','AudioPlayer','EvaluateButton'];
for(const name of files){
 const path=new URL(`../frontend/src/${name}.tsx`,import.meta.url);let source=await readFile(path,'utf8');
 if(source.includes("import {Localized"))continue;
 if(name==='App'){
  source=source.replace('<StrictMode><App/></StrictMode>','<StrictMode><I18nProvider><App/></I18nProvider></StrictMode>');
  source=source.replace('<div className="topbar-right">','<div className="topbar-right"><LanguageSelector/>');
 }
 if(name==='Runner')source=source.replace('<p className="task-instruction">{task.instruction}</p>','<p className="task-instruction"><Bi es={task.instruction} nl={task.instruction_nl||"Nederlandse instructie ontbreekt; vraag ondersteuning vóór de start."} always/></p>');
 const file=ts.createSourceFile(path.pathname,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const result=ts.transform(file,[context=>root=>{
  const visit=node=>{
   if(ts.isReturnStatement(node)&&node.expression&&(ts.isJsxElement(node.expression)||ts.isJsxFragment(node.expression)||ts.isJsxSelfClosingElement(node.expression))){
    return ts.factory.updateReturnStatement(node,ts.factory.createJsxElement(ts.factory.createJsxOpeningElement(ts.factory.createIdentifier('Localized'),undefined,ts.factory.createJsxAttributes([])),[node.expression],ts.factory.createJsxClosingElement(ts.factory.createIdentifier('Localized'))));
   }return ts.visitEachChild(node,visit,context);
  };return ts.visitNode(root,visit);
 }]);
 const extra=name==='App'?',I18nProvider,LanguageSelector':name==='Runner'?',Bi':'';
 const output=`import {Localized${extra}} from './i18n';\n`+ts.createPrinter({newLine:ts.NewLineKind.LineFeed}).printFile(result.transformed[0]);
 await writeFile(path,output);result.dispose();
}
