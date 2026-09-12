import {Explorer} from "./components/Explorer";
import {SiteFooter,SiteHeader} from "./components/SiteChrome";

export default function Home(){return <>
  <SiteHeader active="explore"/>
  <main id="main-content">
    <section className="home-hero">
      <div className="hero-copy">
        <p className="eyebrow">A CURATED QUANTUM-CHEMICAL RESOURCE</p>
        <h1>沿着来源证据出发，<br/><em>读懂可追溯的量子性质</em></h1>
        <p className="hero-lead">统一组织 3,196 个 PubChem 索引化合物；完整来源审计为每个 CID 保留至少一条经裁决的 TCMSP 药材关系，并公开证据等级与冲突处理规则。</p>
        <div className="hero-actions"><a className="primary-action" href="#explore">探索数据 <span>→</span></a><a href="/methods">查看方法与适用边界</a></div>
      </div>
      <div className="evidence-path">
        <p>DATA EVIDENCE CHAIN</p><h2>不是“性质表”，而是一条可核查的数据证据链</h2>
        <ol>
          <li><b>01</b><span><strong>身份规范化</strong><small>PubChem CID · InChIKey · 形式电荷 · 立体化学</small></span></li>
          <li><b>02</b><span><strong>统一量子计算</strong><small>B3LYP-D3BJ/def2-TZVP · Opt + Freq</small></span></li>
          <li><b>03</b><span><strong>分层质量控制</strong><small>收敛 · 字段完整性 · 虚频 · 修复记录</small></span></li>
          <li><b>04</b><span><strong>可复用发布</strong><small>结构化字段 · XYZ · 审计结果 · 建模基准</small></span></li>
        </ol>
      </div>
    </section>
    <section className="dataset-vitals">
      <div><strong>16,918</strong><span>经裁决的药材—CID 边</span></div>
      <div><strong>495</strong><span>TCMSP 药材实体</span></div>
      <div><strong>3,191</strong><span>严格零虚频结构</span></div>
      <div><strong>79</strong><span>结构化字段（并非独立描述符数）</span></div>
      <div><strong>100%</strong><span>必需量子字段覆盖</span></div>
      <p><i/> 三项身份修复已纳入<br/><small>2 个电荷态 · 1 个 E/Z 结构</small></p>
    </section>
    <section id="explore" className="explore-section">
      <div className="section-heading"><div><p>EXPLORE THE DATA</p><h2>从身份、来源和性质进入数据</h2></div><p>搜索会作用于完整记录集。建议先用 CID、名称或分子式定位，再用能隙、分子量与质量状态缩小范围。</p></div>
      <Explorer/>
    </section>
    <section className="property-map">
      <div className="section-heading inverse"><div><p>RECORD ARCHITECTURE</p><h2>每条记录包含四层信息</h2></div><a href="/methods">查看字段解释与限制 →</a></div>
      <div className="property-grid">
        <article><small>IDENTITY</small><h3>化学身份</h3><p>CID、名称、分子式、SMILES、InChIKey、形式电荷与结构状态。</p></article>
        <article><small>ELECTRONIC</small><h3>电子结构</h3><p>HOMO、LUMO、轨道能隙、偶极矩及清晰标注的派生指标。</p></article>
        <article><small>THERMOCHEMISTRY</small><h3>热化学与振动</h3><p>电子能、零点能、焓、Gibbs 自由能、频率与红外摘要。</p></article>
        <article><small>PROVENANCE</small><h3>质控与溯源</h3><p>ORCA 版本、收敛标志、虚频、警告、修复历史和来源注释。</p></article>
      </div>
    </section>
  </main><SiteFooter/>
</>}
