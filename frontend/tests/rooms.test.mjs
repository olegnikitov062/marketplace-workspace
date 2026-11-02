import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defaultRepeatUntil, conflictMessage, defaultBookingSlot, occurrences, monday, moscowDate, moscowTime, parseCalendar, readCalendar, writeBooking, pendingBooking, rememberBooking, settleBooking, calendarRange, shiftMonth, repeatOccurrences, layoutBookings, atMinute } from '../src/basework/roomsApi.ts';

const doc={events:[],rooms:[{id:'big',name:'Большая'}],user:{name:'Тест',role:'employee'},canWrite:true};
const response=(status,value)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
test('Месячная сетка сохраняет 42 дня и переходы через год',()=>{
  assert.deepEqual(calendarRange('2026-11-15','month'),{from:'2026-10-26',to:'2026-12-07'});
  assert.equal(shiftMonth('2026-12-31',1),'2027-01-01');
  assert.equal(atMinute('2026-11-02',540),'2026-11-02T06:00:00.000Z');
});
test('Настраиваемые дни недели, окончание по дате и число повторов восстановлены',()=>{
  const rule={unit:'week',interval:1,days:[1,3,5],until:'2026-11-06'};
  assert.deepEqual(repeatOccurrences('2026-11-02','09:00','10:00',rule).map(x=>x.start.slice(0,10)),['2026-11-02','2026-11-04','2026-11-06']);
  assert.equal(repeatOccurrences('2026-11-02','09:00','10:00',{...rule,until:undefined,count:6}).length,6);
  assert.throws(()=>repeatOccurrences('2026-11-02','09:00','10:00',{...rule,days:[]}));
});
test('Ежемесячный повтор пропускает несуществующее число, не переносит его на другое',()=>{
  const values=repeatOccurrences('2025-01-31','09:00','10:00',{unit:'month',interval:1,days:[],count:2});
  assert.deepEqual(values.map(x=>x.start.slice(0,10)),['2025-01-31','2025-03-31']);
});
test('Согласованные рабочие часы применяются ко всем новым правилам',()=>{
  assert.throws(()=>repeatOccurrences('2026-11-06','09:00','10:00',{unit:'day',interval:1,days:[],count:2}),/выходной/);
  assert.throws(()=>repeatOccurrences('2026-11-02','09:00','19:01',null));
  assert.throws(()=>repeatOccurrences('2026-02-30','09:00','10:00',null));
  assert.throws(()=>repeatOccurrences('2026-11-02','09:00','10:00',{unit:'week',interval:1,days:[1],until:'2032-11-02'}),/200/);
});
test('Сетка разносит пересечения, соседние интервалы используют ту же колонку',()=>{
  const event=(id,start,end,roomId='big')=>({id,roomId,start:atMinute('2026-11-02',start),end:atMinute('2026-11-02',end)});
  const values=layoutBookings([event('a',540,600),event('b',570,630,'small'),event('c',630,660)],'2026-11-02');
  assert.deepEqual(values.map(x=>[x.ev.id,x.column,x.columns]),[['a',0,2],['b',1,2],['c',0,1]]);
  assert.deepEqual(layoutBookings(values.map(x=>x.ev),'2026-11-02','small').map(x=>x.ev.id),['b']);
});
test('Месяц читается двумя ограниченными запросами, отказ не выдаёт частичный календарь',async()=>{
  const calls=[];
  const fetcher=async(url)=>{calls.push(url);return response(200,doc);};
  assert.equal((await readCalendar('2026-10-26','2026-12-07',new AbortController().signal,fetcher)).status,'ready');
  assert.equal(calls.length,2);
  for(const url of calls){const q=new URL(url,'https://test.invalid').searchParams;assert.equal((Date.parse(q.get('to'))-Date.parse(q.get('from')))/86400000,21);}
  let n=0;
  assert.equal((await readCalendar('2026-10-26','2026-12-07',new AbortController().signal,async()=>++n===1?response(200,doc):response(403,{}))).status,'forbidden');
});
test('Цвет переговорки принимается только в безопасном hex-формате',()=>{
  assert.equal(parseCalendar({...doc,rooms:[{id:'big',name:'Большая',color:'#7b5cf0'}]}).status,'ready');
  assert.equal(parseCalendar({...doc,rooms:[{id:'big',name:'Большая',color:'url(https://example.invalid)'}]}).status,'error');
});
test('Незавершённая запись сохраняет ключ при смене экрана и изолирована по аккаунту',()=>{
  const mutation={method:'POST',body:{title:'Тест'},operation:'pending-1'};
  rememberBooking('actor-a',mutation);
  assert.equal(pendingBooking('actor-a'),mutation);
  assert.equal(pendingBooking('actor-b'),undefined);
  settleBooking('actor-a','old-response');
  assert.equal(pendingBooking('actor-a'),mutation);
  settleBooking('actor-a','pending-1');
  assert.equal(pendingBooking('actor-a'),undefined);
});
test('Москва не зависит от зоны браузера, неделя начинается с понедельника',()=>{
  assert.equal(moscowDate(new Date('2026-11-01T22:00:00Z')),'2026-11-02');
  assert.equal(moscowTime('2026-11-02T06:00:00Z'),'09:00');
  assert.equal(monday('2026-11-08'),'2026-11-02');
});
test('Будние повторы пропускают выходные, соседние часы допустимы',()=>{
  const result=occurrences('2026-11-06','08:00','09:00','workdays',3);
  assert.deepEqual(result.map(x=>x.start.slice(0,10)),['2026-11-06','2026-11-09','2026-11-10']);
  assert.equal(occurrences('2026-11-02','18:00','19:00','weekly',2)[1].end,'2026-11-09T19:00:00+03:00');
});
test('Неверные часы, выходные и чрезмерная серия отклоняются',()=>{
  for(const args of [['2026-11-07','09:00','10:00','none',1],['2026-11-02','07:59','09:00','none',1],['2026-11-02','18:00','19:01','none',1],['2026-11-02','09:00','10:00','weekly',201]]) assert.throws(()=>occurrences(...args));
});
test('Пустой календарь отличается от испорченного ответа',()=>{
  assert.equal(parseCalendar(doc).status,'ready');
  assert.equal(parseCalendar({...doc,user:{role:'owner'}}).status,'error');
  assert.equal(parseCalendar({...doc,events:[{title:'Сломано'}]}).status,'error');
});
test('Чтение только same-origin, без кэша и перенаправлений',async()=>{
  const result=await readCalendar('2026-11-02','2026-11-09',new AbortController().signal,async(url,options)=>{
    assert.equal(options.credentials,'same-origin'); assert.equal(options.redirect,'error'); assert.equal(options.cache,'no-store');
    assert.equal(new URL(url,'https://test.invalid').searchParams.get('from'),'2026-11-02T00:00:00+03:00');return response(200,doc);
  });assert.equal(result.status,'ready');
});
test('Нет права, привязки или сессии — данные отсутствуют',async()=>{
  for(const [status,body,expected] of [[401,{},'expired'],[403,{},'forbidden'],[403,{status:'identity_unbound'},'unbound'],[503,{},'unavailable']]) {
    assert.deepEqual(await readCalendar('2026-11-02','2026-11-09',new AbortController().signal,async()=>response(status,body)),{status:expected});
  }
});
test('Повтор неопределённой записи сохраняет ключ и тело; CSRF передаётся',async()=>{
  for(const method of ['POST','PUT','DELETE']) {
    const mutation={method,id:method==='POST'?undefined:'a'.repeat(32),body:{title:'Тест',expectedRevision:'b'.repeat(64)},operation:`synthetic-${method}`};
    const requests=[];
    const fetcher=async(url,options)=>{
      requests.push({url,...options});
      if(requests.length===1) throw new Error('Ответ потерян');
      return response(method==='POST'?201:200,method==='POST'?{created:[],skipped:0}:method==='PUT'?{updated:1}:{deleted:1});
    };
    rememberBooking('retry-actor',mutation);
    assert.equal((await writeBooking(mutation,'csrf',new AbortController().signal,fetcher)).status,'unknown');
    // Календарь после выполненной отмены/переноса может быть пустым.
    assert.equal((await readCalendar('2026-11-02','2026-11-03',new AbortController().signal,async()=>response(200,doc))).data.events.length,0);
    assert.equal(pendingBooking('retry-actor'),mutation);
    assert.equal((await writeBooking(pendingBooking('retry-actor'),'csrf',new AbortController().signal,fetcher)).status,'ok');
    assert.equal(requests[0].url,requests[1].url); assert.equal(requests[0].method,requests[1].method);
    assert.equal(requests[0].body,requests[1].body); assert.equal(requests[0].headers['Idempotency-Key'],requests[1].headers['Idempotency-Key']);
    assert.equal(requests[1].headers['X-CSRFToken'],'csrf');
    settleBooking('retry-actor',mutation.operation); assert.equal(pendingBooking('retry-actor'),undefined);
  }
});
test('409 и 503 не становятся успехом, частичная серия показывает пропуски',async()=>{
  for(const [status,body,expected] of [[409,{status:'stale'},'stale'],[409,{},'conflict'],[503,{},'unknown'],[403,{},'forbidden'],[201,{created:[],skipped:2},'ok']]) {
    const result=await writeBooking({method:'POST',body:{},operation:'test'},'csrf',new AbortController().signal,async()=>response(status,body));
    assert.equal(result.status,expected);if(expected==='ok')assert.equal(result.skipped,2);
  }
});

test('Новая бронь выбирает последнюю видимую комнату и ближайший час по Москве',()=>{
  const rooms=[{id:'big',name:'Большая'},{id:'small',name:'Малая'}];
  assert.deepEqual(defaultBookingSlot('2026-11-02',rooms,new Set(),'small',new Date('2026-11-02T09:30:00Z')),
    {date:'2026-11-02',roomId:'small',start:'13:00',end:'14:00'});
  assert.equal(defaultBookingSlot('2026-11-02',rooms,new Set(['small']),'small').roomId,'big');
  assert.equal(defaultBookingSlot('2026-11-02',rooms,new Set(),'removed').roomId,'big');
  assert.equal(defaultBookingSlot('2026-11-03',rooms,new Set(),null,new Date('2026-11-02T09:30:00Z')).start,'10:00');
});
test('Предложенный час остаётся внутри согласованных рабочих часов',()=>{
  const rooms=[{id:'big',name:'Большая'}];
  assert.equal(defaultBookingSlot('2026-11-02',rooms,new Set(),null,new Date('2026-11-02T03:00:00Z')).start,'08:00');
  const late=defaultBookingSlot('2026-11-02',rooms,new Set(),null,new Date('2026-11-02T18:00:00Z'));
  assert.equal(late.start,'18:00'); assert.equal(late.end,'19:00');
});
test('Срок повторов сохраняет исходные три календарных месяца, включая границу года',()=>{
  assert.equal(defaultRepeatUntil('2026-11-02'),'2027-02-02');
  assert.equal(defaultRepeatUntil('2026-01-31'),'2026-05-01');
});
test('Конфликт показывает фактическую комнату, дату и время по Москве',async()=>{
  const conflict={roomId:'big',title:'Планёрка',start:'2026-11-02T07:00:00Z',end:'2026-11-02T08:00:00Z'};
  const result=await writeBooking({method:'POST',body:{},operation:'test'},'csrf',new AbortController().signal,
    async()=>response(409,{status:'conflict',conflicts:[conflict,{roomId:'bad'}]}));
  assert.equal(result.status,'conflict'); assert.deepEqual(result.conflicts,[conflict]);
  assert.match(conflictMessage(result.conflicts,doc.rooms),/Большая, 2026-11-02, 10:00–11:00 — «Планёрка»/);
});
