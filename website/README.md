# 本草量化图谱（TCM-QM Atlas）

面向中药天然产物研究的可追溯量子化学性质数据库网站。当前版本收录 3,196 个具有唯一 PubChem CID 的分子；完整来源审计为每个 CID 保留至少一条经裁决的 TCMSP 药材关系。

> 本数据库仅用于教育与科学研究，不构成医疗建议、疗效证明或临床证据。药材—成分映射表示数据来源关系，不等同于药效关系。

## 主要功能

- 按 PubChem CID、英文名、分子式或 InChIKey 检索化合物
- 按中药材中文名检索相关成分
- 按质量状态、药材映射、HOMO–LUMO 能隙和分子量筛选
- 对完整数据集执行服务器端排序与分页
- 分子详情页分层展示电子性质、热化学、振动、来源与计算条件
- 2D、3D 分子查看器及知识图谱引擎按页面动态加载，不进入无关页面的首屏代码
- 方法、质量控制、单位和版本信息独立说明
- 基础请求限流及只返回列表所需字段的 API

## 数据概况

- 具有经裁决 TCMSP 来源关系的 CID：3,196
- 分子总数：3,196
- 无虚频结构：3,191
- 药材实体：495 味；唯一药材—CID 关联边：16,918 条（对应 16,930 条接受的来源证据记录）
- 证据分层：16,918 条均为分子页直接边；382 条旧版独有关系全部排除并保留在审计账本
- 核心字段覆盖率：100%
- 计算软件版本：ORCA 6.0.1 / 6.1.1
- 理论水平：B3LYP-D3BJ / def2-TZVP

## 本地运行

需要 Node.js 22.13 或更高版本。

```bash
npm install
npm run dev
```

打开 `http://localhost:3000`。

## 质量检查

```bash
npm run lint
npm run build
npm test
```

测试覆盖主页、方法页、化合物详情页，以及服务器端质量筛选、药材筛选、排序和分页。

## 主要目录

- `app/`：页面、组件、API 与样式
- `app/lib/data.ts`：数据加载、检索、筛选和排序
- `app/data/`：网站运行时使用的紧凑 JSON 数据
- `public/structures/`：按 CID 命名的 3,196 个 XYZ 文件
- `public/downloads/`：网页提供的机器可读下载文件
- `scripts/`：数据同步与网站资源生成脚本
- `tests/`：渲染与 API 回归测试
- `DESIGN_RESEARCH.md`：同类数据库调研和设计依据

## 数据脚本

脚本不依赖某台电脑的固定绝对路径。输入文件可通过参数指定：

```bash
python scripts/build_site_data.py \
  --source /path/to/data_release/tables/tcm_qm_master.csv \
  --provenance /path/to/data_release/tables/cid_tcm_provenance_summary.csv \
  --closure-summary /path/to/data_release/tables/numerical_closure_summary.csv \
  --target /path/to/staging/compounds.json
python scripts/build_graph_data.py \
  --source /path/to/data_release/tables/tcm_source_provenance.csv \
  --output-dir /path/to/staging
```

这两个命令不读取旧 JSON，也不访问网络。先在 staging 中生成、核对，再替换 `app/data` 的对应文件。主表须使用发布版字段名（如 `pubchem_SMILES`、`pubchem_InChIKey`），来源摘要 CID 集合必须与主表一致；12 项闭合检查必须完整通过。缺列、重复 CID、身份缺失、非有限数值或检查失败会中止，不会输出半成品。

未给定来源摘要/闭合表参数时，从主表同目录读取；本提交材料目录下可省略所有参数。独立下载的网站仓库须显式传入数据路径。数字标题可为空，XLogP 等可选描述符可为 null，不能将其误作数值零。当前 schema 不把总体闭合检查解释为实验精度验证。

`enrich_compounds_pubchem.py` 和 `sync_web_to_frozen_release.py` 是旧资产增量同步工具，不是从零重建步骤；完整构建请使用以上两个命令。

`patch_web_v12.py` 是历史内容迁移工具，不适用于当前 v1.1 来源层；不要作为当前构建流程运行：

```bash
python scripts/patch_web_v12.py --root /path/to/website
```

## 数据引用与版本

公开发布时应同时提供固定版本号、发布日期、数据字典、计算方法、质量控制规则、机器可读下载文件和推荐引用格式。若后续修订数据，应保留旧版本并记录变更内容，避免静默覆盖。
