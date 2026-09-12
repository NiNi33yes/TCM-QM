import {SiteFooter,SiteHeader} from "../components/SiteChrome";
export default function About(){return <><SiteHeader active="about"/><main id="main-content" className="text-page"><article>
  <p className="eyebrow">ABOUT THE DATASET</p><h1>一套为检索、比较和可追溯复用而组织的量子化学数据资源</h1>
  <p className="lead">TCM-QM Atlas 以 PubChem CID 为主键，将化学身份、DFT 性质、质量标记与药材来源证据置于同一记录，并显示来源证据等级、MOL_ID 与裁决状态。</p>
  <div className="about-numbers"><div><b>3,196</b><span>具有来源关系的 CID</span></div><div><b>16,918</b><span>唯一药材—CID 边</span></div><div><b>495</b><span>TCMSP 药材实体</span></div></div>
  <section><span className="chapter-no">01</span><h2>资源定位</h2><p>本资源不是中药成分全集，也不是药效数据库。它提供统一理论水平的分子级量子化学记录，并将可核查的 TCMSP 来源边按直接证据分层发布，便于比较、建模、异常筛查和后续实验设计。</p></section>
  <section><span className="chapter-no">02</span><h2>当前发布状态</h2><ul><li>3,196 个计算均正常终止、优化收敛且关键量子字段齐全；其中 3,191 个满足严格零虚频条件。</li><li>发布包含 3,196 个 DFT 优化 XYZ、79 字段主表、来源边表、数据字典、机器可读 Schema、审计结果与哈希清单。</li><li>版本为 <b>1.1.0-rc1</b>。来源层已完成全表重建和冲突裁决；新版本 DOI 尚待铸造，因此当前页面属于研究预览。</li></ul></section>
  <section><span className="chapter-no">03</span><h2>推荐引用</h2><p>在 DOI 和作者顺序正式确定前，请在内部材料中引用为：<b>TCM-QM Atlas, version 1.1.0-rc1, accessed 2026</b>，并注明数据仍处于 release-candidate 阶段。正式公开后应以仓储记录和论文给出的引用格式为准。</p></section>
  <section><span className="chapter-no">04</span><h2>责任边界</h2><p>本数据库用于科学研究与教学，不用于疾病诊断、处方决策或临床建议。任何药材—成分关系都应结合来源定位和证据等级复核；量子化学性质不能单独证明生物活性、安全性或疗效。</p></section>
</article></main><SiteFooter/></>}
