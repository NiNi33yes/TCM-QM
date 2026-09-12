import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Apply the archived v12 factual-copy patch to a selected website tree.")
parser.add_argument("--root", type=Path, required=True, help="Website source directory to patch")
args = parser.parse_args()
root=args.root.resolve()
p=root/"app/methods/page.tsx"
s=p.read_text(encoding="utf-8")
s=s.replace("本页区分已验证事实、需要保留的限制和投稿前仍需完成的分析。","本页区分已验证事实、统计关联和公开发布前仍需补充的元数据。")
s=s.replace('<section><span className="chapter-no">04</span><h2>投稿前仍需完成</h2><p>来源数据库逐 CID 追溯、纳入排除流程、ORCA 版本批次效应、数值闭合关系容差审计，以及完整发布包的文件计数与 SHA-256 清单。</p></section>', '<section><span className="chapter-no">04</span><h2>已完成的发布审计</h2><ul><li>来源表包含 6,567 条 TCMSP 候选关系，覆盖 1,022 个 CID 与 485 味中药；其余记录明确标为当前快照未映射。</li><li>纳排链从 6,948 条候选计算记录，经质量筛查与分组择优得到 3,196 个唯一 CID。</li><li>十二项轨道、单位换算和热化学数值闭合检查均为 3,196/3,196 通过。</li><li>ORCA 版本比较已控制元素组成并采用 HC3 稳健标准误和 FDR 校正；结果仅解释为版本相关批次差异，不作因果推断。</li><li>本地冻结包含 3,196 个 XYZ，逐文件 SHA-256 复算无不一致。</li></ul></section><section><span className="chapter-no">05</span><h2>公开投稿前仍需补充</h2><p>初始三维结构与构象选择设置、TCMSP/PubChem 准确访问日期、公共仓储 DOI、许可证、作者信息，以及是否公开远端 OUT/GBW 文件。这些内容需要项目记录或课题组决策，网站不会自行推断。</p></section>')
p.write_text(s,encoding="utf-8")

p=root/"app/about/page.tsx"
s=p.read_text(encoding="utf-8")
s=s.replace('<li>网站目前为研究预览；正式 DOI、许可证和数据包地址须在冻结发布后补充。</li>', '<li>6,567 条来源关系覆盖 1,022 个 CID；未映射记录不会被错误包装成已证实的药材成分。</li><li>本地数据、结构、验证代码与 SHA-256 清单已经冻结；正式 DOI、许可证和公共仓储地址仍待确定。</li>')
p.write_text(s,encoding="utf-8")

p=root/"tests/rendered-html.test.mjs"
s=p.read_text(encoding="utf-8")
s+='\ntest("frozen provenance facts are visible",async()=>{const methods=await(await render("/methods")).text();for(const fact of ["6,567","1,022","485","十二项","3,196/3,196","SHA-256"])assert.match(methods,new RegExp(fact));const about=await(await render("/about")).text();assert.match(about,/未映射记录/)});\n'
p.write_text(s,encoding="utf-8")

(root/"第一轮网站事实审核.md").write_text("""# 第一轮网站事实与功能审核

- 构建与服务端渲染测试通过后方可交付。
- 首页、详情、方法、关于、关系图和 API 路由均纳入测试。
- 已将刚完成的来源追溯、纳排流程、数值闭合、版本分析和 SHA-256 冻结状态同步到方法页。
- 中药关系统一口径：6,567 条关系、1,022 个有映射 CID、485 味中药。
- 映射关系仅表示来源候选关联，不表示含量、药效、靶点或因果关系。
- 公开 DOI、许可证、三维生成设置和原始 OUT/GBW 发布范围仍不得臆测。
""",encoding="utf-8")
