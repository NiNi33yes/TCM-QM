/* eslint-disable @next/next/no-html-link-for-pages */
export function SiteHeader({active}:{active?:"explore"|"graph"|"methods"|"about"|"downloads"}){
  const links=[
    ["explore","数据探索","/#explore"],
    ["graph","关系图谱","/graph"],
    ["methods","方法与质控","/methods"],
    ["downloads","数据下载","/downloads"],
    ["about","数据说明","/about"],
  ] as const;
  return <>
    <a className="skip-link" href="#main-content">跳到主要内容</a>
    <div className="research-notice">研究数据预览 · 不构成医疗建议、药效证据或临床结论</div>
    <header className="site-header">
      <a className="brand" href="/" aria-label="TCM-QM Atlas 首页"><span className="brand-seal">QM<small>ATLAS</small></span><span className="brand-name"><b>TCM-QM Atlas</b><small>中药相关分子量子化学数据集</small></span></a>
      <nav aria-label="主导航">{links.map(([key,label,href])=><a key={key} className={active===key?"active":""} href={href}>{label}</a>)}</nav>
      <span className="release-pill"><i/> v1.1.0-rc1 · 3,196 records</span>
    </header>
  </>;
}

export function SiteFooter(){return <footer className="site-footer"><div><span className="footer-mark">QM</span><p><b>TCM-QM Atlas</b><small>Traceable quantum chemistry for TCM-associated compounds</small></p></div><p>PubChem identity · B3LYP-D3BJ/def2-TZVP · ORCA 6</p><nav><a href="/methods">方法</a><a href="/downloads">下载</a><a href="/about">引用与边界</a></nav></footer>}
