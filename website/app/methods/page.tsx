import {SiteFooter,SiteHeader} from "../components/SiteChrome";

export default function Methods(){return <><SiteHeader active="methods"/><main id="main-content" className="text-page"><article>
  <p className="eyebrow">METHODS &amp; TECHNICAL VALIDATION</p>
  <h1>数值只有与计算条件、证据层级和质量标记一起，才可被正确使用</h1>
  <p className="lead">本页给出计算口径、质量控制、严格子集定义与已知限制。网页用于发现数据，正式分析应下载冻结表并保留版本与字段定义。</p>
  <div className="method-summary"><div><small>理论水平</small><b>B3LYP-D3BJ</b><span>def2-TZVP · def2/J · RIJCOSX</span></div><div><small>热化学条件</small><b>298.15 K</b><span>1 atm · 气相 · QRRHO 100 cm⁻¹</span></div><div><small>计算软件</small><b>ORCA 6</b><span>6.0.1: 2,407 · 6.1.1: 789</span></div></div>
  <section><span className="chapter-no">01</span><h2>统一计算流程</h2><p>全部记录采用 TightSCF、TightOpt、DefGrid3，在 B3LYP-D3BJ/def2-TZVP 理论水平进行几何优化与谐振频率计算，并使用 def2/J 与 RIJCOSX。输入区未设置 CPCM、SMD 或其他隐式溶剂模型，因此均为气相结果。热化学量对应 298.15 K、1 atm，振动熵使用 100 cm⁻¹ 参考频率的 QRRHO 处理。</p></section>
  <section><span className="chapter-no">02</span><h2>四层质量控制</h2><div className="quality-levels"><div><b>文件层</b><p>文件存在、非零字节、CID 可读取。</p></div><div><b>计算层</b><p>正常终止、优化收敛、频率与必需字段齐全。</p></div><div><b>身份层</b><p>分子式、电荷、连接关系与立体化学核查。</p></div><div><b>数据集层</b><p>唯一性、单位、缺失值、修复历史与版本统计。</p></div></div></section>
  <section><span className="chapter-no">03</span><h2>质量子集怎么选</h2><ul><li><b>完整发布集：</b>3,196 条记录均正常终止、优化收敛且关键字段完整。</li><li><b>严格局部极小值集：</b>筛选 <code>imaginary_frequency_count = 0</code>，得到 3,191 条记录。</li><li><b>轻微负频记录：</b>5 条记录各含一个 −4.83 至 −2.08 cm⁻¹ 的小负频，保留并标记为 <code>minor_negative_mode_retained</code>。数据未进行振型归属，不应把这些模式解释成特定扭转或反应机理。</li><li><b>版本敏感分析：</b>保留 <code>orca_version</code> 字段。两个版本来自不同计算批次，未进行同分子配对复算，不能据此宣称版本等价或作因果解释。</li></ul></section>
  <section><span className="chapter-no">04</span><h2>来源边界</h2><ul><li>3,196 个 CID 均具有至少一条经裁决的 TCMSP 来源关系；这只是本地来源快照覆盖，不表示中药化学空间完整。</li><li>16,930 条接受的证据记录去重后形成 16,918 条药材—CID 边，覆盖 495 味药材；全部为直接证据。</li><li>来源关联仅表示当前快照中的候选映射，不代表含量、活性、靶点或临床因果。</li></ul></section>
  <section><span className="chapter-no">05</span><h2>字段使用边界</h2><ul><li>79 是发布字段总数，包含身份、来源、质量和派生字段，不等于 79 个独立量子描述符。</li><li>电子总能不适合跨不同化学计量直接排序；熵项字段是 <i>T·S</i> 能量项，不是 J·mol⁻¹·K⁻¹ 的熵。</li><li>Kohn–Sham HOMO–LUMO 差不是实验光学带隙；气相偶极矩和热化学量不可直接等同于溶液或固态测量。</li><li>每个 CID 提供一个发布构象，不代表完整构象系综。</li></ul></section>
  <section><span className="chapter-no">06</span><h2>验证与复用</h2><p>12 项轨道、单位换算和热化学数值闭合检查均为 3,196/3,196 通过。机器学习仅作为可用性演示，采用 Murcko scaffold 分组的重复划分；其结果不验证 DFT 绝对准确度，也不提供药理学结论。正式复用请同时下载主表、数据字典、Schema、结构文件和 SHA-256 清单。</p></section>
</article></main><SiteFooter/></>}
