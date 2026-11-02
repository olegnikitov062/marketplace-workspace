// Локальный интерфейс перед настоящим тестовым Django; пользователь и SQLite вымышлены.
import { createServer } from 'vite';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const ready=JSON.parse(readFileSync(process.env.BASEWORK_ROOMS_BROWSER_READY,'utf8'));
const target=new URL(ready.url);
if(!ready.synthetic_only || target.hostname!=='127.0.0.1' || target.protocol!=='http:')throw new Error('Только локальный тестовый backend');
const root=fileURLToPath(new URL('../',import.meta.url));
const server=await createServer({root,server:{host:'127.0.0.1',port:5195,strictPort:true,open:false,
  proxy:{'/api':{target:target.origin,changeOrigin:true},'/auth':{target:target.origin,changeOrigin:true}}},
  plugins:[{name:'rooms-fixture-banner',transformIndexHtml(html){return html.replace('<body>','<body><aside style="padding:10px 16px;font:14px Segoe UI,sans-serif;border-bottom:1px solid currentColor">Локальная проверка. Аккаунт и брони вымышлены.</aside>');}}]});
await server.listen();
console.log('Локальный стенд: http://127.0.0.1:5195/basework/apps/rooms');
