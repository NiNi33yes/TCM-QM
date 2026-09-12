import {SiteFooter,SiteHeader} from "../components/SiteChrome";

const files=[
  {name:"完整发布候选包",file:"TCM-QM_v1.1.0-rc1.zip",size:"生成后见文件",desc:"1.1.0-rc1：稳定量子主表、3,196 个 XYZ、经裁决来源层、质控表、代码、字段字典和校验清单。"},
  {name:"量子性质主表",file:"tcm_qm_master.csv",size:"约 3 MB",desc:"以 PubChem CID 为主键的化学身份、量子性质、来源分层与质量状态。"},
  {name:"TCMSP 来源证据表",file:"tcm_source_provenance.csv",size:"约 4.4 MB",desc:"16,930 条接受的逐证据记录，保留证据等级、MOL_ID、方法和来源定位。"},
  {name:"TCMSP 唯一边表",file:"tcm_source_edges.csv",size:"约 2.2 MB",desc:"16,918 条经裁决的唯一药材—CID 边，适合知识图谱和统计分析。"},
  {name:"含来源字段的联接主表",file:"tcm_qm_master_with_tcmsp.csv",size:"约 3.5 MB",desc:"在稳定 79 字段量子主表基础上附加 CID 级 TCMSP 汇总字段。"},
  {name:"性质汇总便利表",file:"TCM-QM_property_summary_3196.csv",size:"约 2.1 MB",desc:"每个 CID 一行的 56 字段宽表，汇总 SMILES、药材来源、四气、归经及主要量子化学性质。"},
  {name:"79 字段数据字典",file:"data_dictionary.csv",size:"约 13 KiB",desc:"逐字段给出类型、单位、来源、空值语义、定义和关键误用边界。"},
  {name:"机器可读 Schema",file:"schema.json",size:"约 27 KiB",desc:"主表 79 个字段的 JSON Schema 与发布口径。"},
  {name:"SHA-256 文件清单",file:"files_sha256.csv",size:"约 309 KiB",desc:"候选包载荷文件的相对路径、字节数和 SHA-256。"},
];

export default function Downloads(){return <><SiteHeader active="downloads"/><main id="main-content" className="download-page">
  <section className="page-intro"><p className="eyebrow">FAIR DATA ACCESS</p><h1>机器可读，<br/><em>可校验、可复用</em></h1><p>下载 1.1.0-rc1 候选包或按用途选择表格。分析时建议将主表、来源边表、数据字典和 Schema 一并保存，并记录版本号与筛选条件。</p></section>
  <section className="download-grid">{files.map(item=><article key={item.file}><small>DATA FILE · {item.size}</small><h2>{item.name}</h2><p>{item.desc}</p><code>{item.file}</code><a href={`/downloads/${item.file}`} download>下载文件 →</a></article>)}</section>
  <section className="download-note"><b>原始 ORCA OUT 归档状态</b><p>3,196 个 OUT 已完成服务器端归档与完整性校验，归档大小约 1.2 GiB，SHA-256 为 <code>c24933581aa93112b64ebbe33768b8cd6c5bcd8ac509c5079bece87097ff08bf</code>。该大文件当前未嵌入网页下载包；待上传公共仓储后，将以持久链接替换此状态说明。</p></section>
  <section className="download-note"><b>引用与使用边界</b><p>药材—成分边仅表示两个本地物化 TCMSP 快照中的候选来源关系，不代表含量、活性、靶点或临床因果。新版本 DOI 确定前，请把本站视为研究预览。</p><a href="/downloads/TCM-QM_v1.1.0-rc1.zip.sha256" download>下载完整包校验值 →</a></section>
</main><SiteFooter/></>}
