import assert from "node:assert/strict";
import test from "node:test";

async function render(path="/") {
  const url=new URL("../dist/server/index.js",import.meta.url);
  url.searchParams.set("test",`${process.pid}-${Date.now()}-${Math.random()}`);
  const {default:worker}=await import(url.href);
  return worker.fetch(new Request(`http://localhost${path}`,{headers:{accept:"text/html"}}),{ASSETS:{fetch:async()=>new Response("Not found",{status:404})}},{waitUntil(){},passThroughOnException(){}});
}

test("homepage renders dataset narrative",async()=>{const response=await render();assert.equal(response.status,200);const html=await response.text();assert.match(html,/TCM-QM Atlas/);assert.match(html,/3,196/)});

test("core routes render",async()=>{for(const path of ["/graph","/methods","/about","/downloads","/compound/1001"]){const response=await render(path);assert.equal(response.status,200,path)}});

test("dataset filters remain coherent",async()=>{const review=await(await render("/api/compounds?qc=review&limit=12")).json();assert.equal(review.total,5);const herb=await(await render("/api/compounds?q=%E4%B8%B9%E5%8F%82&scope=herb&limit=12")).json();assert.ok(herb.total>0);const cid=await(await render("/api/compounds?q=1001&scope=compound&limit=12")).json();assert.equal(cid.items[0].cid,"1001")});

test("graph sorting and evidence remain global",async()=>{const graph=await(await render("/api/graph?q=%E4%B8%B9%E5%8F%82&sort=gap_asc&page=1&limit=20")).json();assert.ok(graph.total>0);assert.equal(graph.items[0].edge.sourceDatabase,"TCMSP")});

test("structure and download surfaces are present",async()=>{const detail=await(await render("/compound/72")).text();assert.match(detail,/二维与三维结构/);assert.match(detail,/\/structures\/72\.xyz/);const downloads=await(await render("/downloads")).text();assert.match(downloads,/机器可读/);assert.match(downloads,/tcm_qm_master\.csv/)});
