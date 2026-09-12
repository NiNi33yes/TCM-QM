"use client";
import {FormEvent,useEffect,useState} from "react";

type Item={cid:string;title:string;formula:string;molecularWeight:number;homoEv:number;lumoEv:number;gapEv:number;dipoleDebye:number;qcStatus:string;herbCount:number};
const qcText:Record<string,string>={pass:"通过",pass_with_warning:"通过（有提示）",review:"建议复核"};
const PAGE_SIZE=12;

export function Explorer(){
  const[query,setQuery]=useState(""); const[items,setItems]=useState<Item[]>([]); const[total,setTotal]=useState(0);
  const[loading,setLoading]=useState(true); const[error,setError]=useState("");
  const[qc,setQc]=useState("all"); const[sort,setSort]=useState("cid"); const[herb,setHerb]=useState("all");
  const[gapMin,setGapMin]=useState(""); const[gapMax,setGapMax]=useState("");
  const[massMin,setMassMin]=useState(""); const[massMax,setMassMax]=useState("");
  const[page,setPage]=useState(1);

  async function fetchData(overrides:Partial<{q:string;qc:string;sort:string;herb:string;page:number;gapMin:string;gapMax:string;massMin:string;massMax:string}>={}){
    const p={q:query,qc,sort,herb,page,gapMin,gapMax,massMin,massMax,...overrides};
    setLoading(true);setError("");
    try{
      const sp=new URLSearchParams({q:p.q,scope:"compound",qc:p.qc,sort:p.sort,herb:p.herb,limit:String(PAGE_SIZE),page:String(p.page)});
      if(p.gapMin)sp.set("gapMin",p.gapMin);if(p.gapMax)sp.set("gapMax",p.gapMax);
      if(p.massMin)sp.set("massMin",p.massMin);if(p.massMax)sp.set("massMax",p.massMax);
      const r=await fetch(`/api/compounds?${sp}`);const d=await r.json();
      if(!r.ok)throw new Error(d.error||"数据加载失败");
      setItems(d.items||[]);setTotal(d.total||0);setPage(p.page);
    }catch(e){setError(e instanceof Error?e.message:"数据加载失败")}finally{setLoading(false)}
  }
  useEffect(()=>{void Promise.resolve().then(()=>fetchData())},[]);// eslint-disable-line react-hooks/exhaustive-deps

  function submit(e:FormEvent){e.preventDefault();fetchData({page:1})}
  function changeQc(v:string){setQc(v);fetchData({qc:v,page:1})}
  function changeSort(v:string){setSort(v);fetchData({sort:v,page:1})}
  function changeHerb(v:string){setHerb(v);fetchData({herb:v,page:1})}
  function applyFilters(e?:FormEvent){e?.preventDefault();fetchData({page:1})}
  function clearFilters(){setGapMin("");setGapMax("");setMassMin("");setMassMax("");setHerb("all");fetchData({herb:"all",gapMin:"",gapMax:"",massMin:"",massMax:"",page:1})}
  function goPage(p:number){fetchData({page:p})}
  const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
  const filtered=gapMin||gapMax||massMin||massMax||herb!=="all";

  return <div className="explorer-shell">
    <form className="search-station" onSubmit={submit}>
      <div className="search-kicker"><span>SEARCH 3,196 RECORDS</span><b>身份优先，性质筛选</b></div>
      <div className="search-bar"><span className="search-symbol"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="输入 PubChem CID、英文名称、分子式或 InChIKey"/><button className="submit-search">搜索 <span>→</span></button></div>
      <div className="search-examples"><span>示例</span>{["1001","caffeine","C8H10N4O2"].map(x=><button type="button" key={x} onClick={()=>{setQuery(x);fetchData({q:x,page:1})}}>{x}</button>)}</div>
    </form>
    <div className="result-toolbar"><div><p>{query?`“${query}” 的结果`:"全部分子"}</p><span>找到 <b>{total.toLocaleString()}</b> 条记录{filtered&&<em>（已应用范围筛选）</em>}</span></div><div className="toolbar-fields"><label>质量状态<select value={qc} onChange={e=>changeQc(e.target.value)}><option value="all">全部</option><option value="pass">通过</option><option value="pass_with_warning">有提示</option><option value="review">建议复核</option></select></label><label>排序<select value={sort} onChange={e=>changeSort(e.target.value)}><option value="cid">CID</option><option value="gap_asc">能隙：低到高</option><option value="gap_desc">能隙：高到低</option><option value="mass_asc">分子量：低到高</option><option value="mass_desc">分子量：高到低</option><option value="dipole_desc">偶极矩：高到低</option></select></label></div></div>
    <form className="filter-bar" onSubmit={applyFilters}>
      <span className="filter-title">范围筛选</span>
      <label className="filter-range">能隙<input type="number" step="0.1" inputMode="decimal" value={gapMin} onChange={e=>setGapMin(e.target.value)} placeholder="min"/><i>–</i><input type="number" step="0.1" inputMode="decimal" value={gapMax} onChange={e=>setGapMax(e.target.value)} placeholder="max"/><em>eV</em></label>
      <label className="filter-range">分子量<input type="number" step="0.1" inputMode="decimal" value={massMin} onChange={e=>setMassMin(e.target.value)} placeholder="min"/><i>–</i><input type="number" step="0.1" inputMode="decimal" value={massMax} onChange={e=>setMassMax(e.target.value)} placeholder="max"/><em>Da</em></label>
      <label className="filter-herb">药材关联<select value={herb} onChange={e=>changeHerb(e.target.value)}><option value="all">全部</option><option value="mapped">已映射药材</option><option value="unmapped">未映射药材</option></select></label>
      <span className="filter-actions"><button type="submit">应用</button><button type="button" onClick={clearFilters}>重置</button></span>
    </form>
    {loading?<div className="loading-state"><i/><b>正在读取数据</b></div>:error?<div className="empty-state"><b>暂时无法加载</b><span>{error}</span></div>:<div className="compound-card-grid">{items.map(item=><a className="compound-card" href={`/compound/${item.cid}`} key={item.cid}><header><span className="formula-tile">{item.formula||"—"}</span><span className={`status-label ${item.qcStatus}`}><i/>{qcText[item.qcStatus]||item.qcStatus}</span></header><h3>{item.title||`CID ${item.cid}`}</h3><p>PubChem CID {item.cid} · {item.molecularWeight.toFixed(2)} Da</p><dl><div><dt>HOMO</dt><dd>{item.homoEv.toFixed(3)} eV</dd></div><div><dt>LUMO</dt><dd>{item.lumoEv.toFixed(3)} eV</dd></div><div><dt>能隙</dt><dd>{item.gapEv.toFixed(3)} eV</dd></div><div><dt>偶极矩</dt><dd>{item.dipoleDebye.toFixed(3)} D</dd></div></dl><footer>查看完整记录 <span>→</span></footer></a>)}</div>}
    {!loading&&!error&&items.length===0&&<div className="empty-state"><b>没有匹配记录</b><span>请缩短关键词或放宽范围筛选。</span></div>}
    {!loading&&!error&&items.length>0&&<div className="explorer-pager"><button type="button" disabled={page<=1} onClick={()=>goPage(page-1)}>← 上一页</button><span>第 {page} / {pages} 页 · 共 {total.toLocaleString()} 条</span><button type="button" disabled={page>=pages} onClick={()=>goPage(page+1)}>下一页 →</button></div>}
  </div>
}
