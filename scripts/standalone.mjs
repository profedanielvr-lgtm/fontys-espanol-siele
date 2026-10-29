// Empaqueta la interfaz y sus materiales en un HTML que se puede abrir directamente.
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const assets=path.join(root,'frontend/dist/assets');
const files=await readdir(assets);
const css=(await Promise.all(files.filter(f=>f.endsWith('.css')).map(f=>readFile(path.join(assets,f),'utf8')))).join('\n');
const js=(await Promise.all(files.filter(f=>f.endsWith('.js')).map(f=>readFile(path.join(assets,f),'utf8')))).join('\n');
const bank=JSON.parse(await readFile(path.join(root,'frontend/public/bank.json'),'utf8'));
const images={};
for(const name of ['scene-classroom.svg','scene-cafe.svg'])images[name]=`data:image/svg+xml;base64,${(await readFile(path.join(root,'frontend/public',name))).toString('base64')}`;
const safe=value=>JSON.stringify(value).replaceAll('<','\\u003c');
const html=`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fontys Español · Daniel Valle Robles</title><style>${css}</style></head><body><div id="root"></div><script>window.FONTYS_BANK=${safe(bank)};window.FONTYS_ASSETS=${safe(images)};</script><script type="module">${js.replaceAll('</script','<\\/script')}</script></body></html>`;
const filename=path.join(root,'Abrir plataforma.html');
await writeFile(filename,html,'utf8');
console.log('Creado: Abrir plataforma.html');
