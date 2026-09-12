"use client";

import { useEffect, useRef, useState } from "react";

export function MoleculeViewers({cid,smiles,formula}:{cid:string;smiles:string;formula:string}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewerRef = useRef<HTMLDivElement>(null);
  const [mode,setMode] = useState<"stick"|"sphere">("stick");
  const [xyz,setXyz] = useState("");
  const [error,setError] = useState("");

  useEffect(() => {
    let active = true;
    import("smiles-drawer").then(module => {
      if (!active || !canvasRef.current) return;
      const SmilesDrawer = module.default;
      const drawer = new SmilesDrawer.Drawer({width:360,height:280,bondThickness:1.2,fontSizeLarge:11,fontSizeSmall:7,padding:22,compactDrawing:true});
      SmilesDrawer.parse(smiles, (tree:unknown) => drawer.draw(tree,canvasRef.current!,"light",false), () => setError("二维结构解析失败"));
    }).catch(() => setError("二维结构组件加载失败"));
    return () => { active=false; };
  }, [smiles]);

  useEffect(() => {
    fetch(`/structures/${cid}.xyz`).then(response => {
      if (!response.ok) throw new Error();
      return response.text();
    }).then(setXyz).catch(() => setError("三维坐标暂不可用"));
  }, [cid]);

  useEffect(() => {
    if (!xyz || !viewerRef.current) return;
    let active = true;
    let viewer: {clear:()=>void;addModel:(data:string,format:string)=>void;setStyle:(selection:object,style:object)=>void;zoomTo:()=>void;render:()=>void;spin:(axis:string|boolean,speed?:number)=>void;resize:()=>void} | undefined;
    import("3dmol").then(module => {
      if (!active || !viewerRef.current) return;
      viewerRef.current.replaceChildren();
      viewer = module.createViewer(viewerRef.current,{backgroundColor:"#fbfbf7",antialias:true});
      viewer.addModel(xyz,"xyz");
      viewer.setStyle({},mode==="sphere"?{sphere:{scale:0.34},stick:{radius:0.11}}:{stick:{radius:0.16},sphere:{scale:0.22}});
      viewer.zoomTo(); viewer.render();
    }).catch(() => setError("三维查看器加载失败"));
    const resize = () => viewer?.resize(); window.addEventListener("resize",resize);
    return () => { active=false; window.removeEventListener("resize",resize); viewer?.clear(); };
  }, [xyz,mode]);

  return <div className="structure-viewers">
    <article><header><span><small>2D DEPICTION</small><b>二维结构</b></span><em>由本条 SMILES 本地绘制</em></header><div className="structure-canvas"><canvas ref={canvasRef} width="360" height="280" aria-label={`${formula} 二维结构图`}/></div></article>
    <article><header><span><small>DFT-OPTIMIZED 3D</small><b>三维优化结构</b></span><span className="viewer-buttons"><button type="button" className={mode==="stick"?"active":""} onClick={()=>setMode("stick")}>球棍</button><button type="button" className={mode==="sphere"?"active":""} onClick={()=>setMode("sphere")}>空间填充</button></span></header><div ref={viewerRef} className="molecule-3d" aria-label={`${formula} DFT 优化三维结构`}/><footer>拖动旋转 · 滚轮缩放 · 坐标来自冻结发布包</footer></article>
    {error&&<p className="viewer-error">{error}</p>}
  </div>;
}
