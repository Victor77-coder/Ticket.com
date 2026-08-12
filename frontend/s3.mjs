import { chromium } from '@playwright/test';
const S='/private/tmp/claude-501/-Users-victormedeirossantos-Documents-platform-ingressos-eventos/aaf989fd-8c02-4d5a-b6f1-5db9318447e4/scratchpad';
const b=await chromium.launch();
const p=await b.newPage({viewport:{width:1280,height:1000},deviceScaleFactor:1.6});
await p.goto('file://'+S+'/proto.html',{waitUntil:'networkidle'});
await p.waitForTimeout(800);
const alvo=await p.locator('.breve').boundingBox();
await p.screenshot({path:S+'/p-resto.png',clip:{x:0,y:alvo.y,width:1280,height:1700}});
await b.close(); console.log('ok');
