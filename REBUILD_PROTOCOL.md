# TCM-QM 全链重建协议（原始 OUT → 冻结主表）

更新时间：2026-09-05
适用范围：TCM-QM `1.1.0-rc1` 来源修订候选版

本协议把「从服务器原始 ORCA OUT 到冻结主表」的完整数据链拆成可执行步骤，作为待办第 2 项
（原始 OUT 归档 + 干净环境全链重建记录）的落地方案。它区分**现在可重跑**的脚本、**需要先归档**的
上游输入、以及**需要补写**的缺口，并以冻结哈希作为唯一验收标准。

## 0. 验收标准（不可妥协）

| 产物 | 验收判据 |
|---|---|
| `tables/tcm_qm_master.csv` | SHA-256 = `777094ed77ff8981c08dc2b4876d0ce84f6658f13b788379509391a9fb0e7b2c`，3,115,653 字节，3,196 行，79 字段 |
| `structures_xyz/*.xyz` | 3,196 个文件，与主表 CID 一一对应 |
| `tables/tcm_source_provenance.csv` | 16,930 条接受证据记录，对应 16,918 条唯一药材–CID 边、495 味药材和 3,196 个 CID |
| `audits/legacy_382_adjudication_ledger.csv` | 382 条旧版独有关系逐条裁决：全部排除（174 冲突 CID + 111 无锚点 + 97 页面药材列表不一致） |
| `audits/multi_mol_id_9_adjudication_ledger.csv` | 9 个多 MOL_ID CID 的源记录保留与 CID–药材并集规则 |
| `tables/selection_decisions.csv` | 6,948 行（逐候选判定） |
| 整包 | `manifests/files_sha256.csv` 的每一行 SHA-256 均可复算通过 |

> 主表 SHA 是**字节级**验收：解析脚本、PubChem 快照、字段顺序、CID 排序、以及
> **UTF-8 BOM + CRLF 行尾**任一不同，都会导致哈希不一致。冻结表产自 Windows，
> Linux 干净环境重建必须强制 BOM + CRLF（见 §4 与 `code/build_master.py`）。

## 1. 数据流总览

```
Stage 0  上游（需归档，不在 release 内）
  原始 ORCA OUT(3,196+154) ─┐
  PubChem 冻结快照(19字段) ─┤
  TCMSP 完整分子页 + 历史药材页来源证据 ─┤
  判定总表(6,948) + 最终合格(3,196) ─┤
  PubChem3D 起始结构(3,196) ─┘

Stage 1  解析            code/parse_orca_out.py          → orca_descriptors.csv(60字段)
Stage 2  组装（本协议补写）code/build_master.py            → tcm_qm_master.csv(79字段)
Stage 3  打包+审计        code/build_finalization_audit.py → release 目录(provenance/closure/manifest)
Stage 4  v5 校正          code/build_corrected_freeze_v5.py → 154 占位 XYZ 替换
Stage 5  字典/ML/几何     generate_data_dictionary.py / build_ml_benchmark.py / audit_all_initial_geometries_pubchem3d.py
Stage 6  来源裁决          `TCMSP_PROVENANCE_RULES.md` 所述规则 → 16,930 条证据 / 16,918 条唯一边
```

主表 79 字段 = **字段 0–59（60 个 ORCA 解析列，与 `parse_orca_out.py` 的 `FIELDS` 逐列相同）**
+ **字段 60–78（19 个 PubChem 身份列）**。60 列清单、19 列清单、字段顺序见 `code/build_master.py` 顶部常量。

## 2. 需归档的上游输入（先决条件）

见 `manifests/raw_input_archive_manifest.csv`。最小闭合集（只复现主表）：

1. **原始 OUT**：3,196 个最终分子（`<CID>.out`）+ 154 个补全 OUT。
   其中 3 个身份修复分子必须归档**修复版** OUT：`248_charge_fix.out`、`5571_charge_fix.out`、
   `10946210_stereo_fix.out`（与主表 `source_file` 列一致；原始 `248/5571/10946210.out`
   是修复前旧版，不能用于重建）。
2. **PubChem 冻结快照**：每个 CID 的 19 个身份字段（`compound_master.csv` 或 PUG 快照导出）。

复现完整 provenance/筛选链，还需：药材映射、判定总表、最终合格表、PubChem3D 起始结构。
归档后把 SHA-256 回填进 manifest CSV 的 `sha256` 列，并把 `archived` 改为 `yes`。

## 3. 逐步重建命令

假设归档后的原始输入放在 `ARCHIVE_ROOT/`，重建目录为 `REBUILD/`（必须为不存在的空路径）。

```bash
# 环境（ORCA 仅新计算需要；重解析/组装只需标准库 + pandas/scipy/numpy）
conda env create -f environment.yml && conda activate tcm-qm

# Stage 1 — 解析 3,196 个 OUT → 60 列描述符表
python code/parse_orca_out.py ARCHIVE_ROOT/out_final_3196 REBUILD/parsed

# Stage 2 — 组装 79 列主表（本协议补写的缺口脚本；强制 BOM+CRLF+数值CID升序）
python code/build_master.py \
    --descriptors REBUILD/parsed/orca_descriptors.csv \
    --pubchem    ARCHIVE_ROOT/pubchem_snapshot.csv \
    --output     REBUILD/tables/tcm_qm_master.csv

# Stage 3 — 打包 + 审计（provenance / closure / manifest / README）
python code/build_finalization_audit.py \
    --output REBUILD \
    --master REBUILD/tables/tcm_qm_master.csv \
    --herb-mapping ARCHIVE_ROOT/herb_compound_mapping.csv \
    --judgment-ledger ARCHIVE_ROOT/judgment_ledger.csv \
    --final-qualified ARCHIVE_ROOT/final_qualified_3196.csv \
    --xyz-directory ARCHIVE_ROOT/optimized_xyz \
    --ml-directory ARCHIVE_ROOT/ml_benchmark

# Stage 4 — v5 校正：154 占位 XYZ 用补全 OUT 的 DFT 坐标替换
python code/build_corrected_freeze_v5.py \
    --source-release REBUILD \
    --output-release REBUILD_v5 \
    --optimized-xyz ARCHIVE_ROOT/optimized_xyz \
    --replacement-audit ARCHIVE_ROOT/placeholder_xyz_replacement_audit.csv \
    --recovered-out ARCHIVE_ROOT/out_recovered_154

# Stage 5 — 字典 / ML / 几何溯源
python code/generate_data_dictionary.py REBUILD_v5/tables/tcm_qm_master.csv REBUILD_v5/tables/data_dictionary.csv REBUILD_v5/tables/schema.json
python code/build_ml_benchmark.py REBUILD_v5/tables/tcm_qm_master.csv REBUILD_v5/machine_learning_rebuilt
python code/audit_all_initial_geometries_pubchem3d.py ARCHIVE_ROOT

# 验收 — 主表字节级比对
python code/verify_rebuild.py \
    --frozen  02_数据冻结最新版_v5/tables/tcm_qm_master.csv \
    --rebuilt REBUILD_v5/tables/tcm_qm_master.csv
```

`verify_rebuild.py` 退出码 0 且打印 `"verdict": "PASS"` 即主表重建成功；若 `FAIL`，
其 `field_diffs` 会指出首个漂移字段与 CID，用于定位是解析、快照还是排序/行尾问题。

## 4. 已知缺口与闭合方式

| 缺口 | 状态 | 闭合方式 |
|---|---|---|
| 主表组装脚本（60 列 ORCA + 19 列 PubChem 的左连接） | **已补写** `code/build_master.py` | 本协议新增；语义见其 docstring |
| PubChem 冻结快照 | **未归档** | 需从服务器导出与冻结时同版的 `compound_master.csv`/PUG 快照 |
| 原始 OUT（3,196 + 154） | **未归档** | 需打包 `ARCHIVE_ROOT/out_final_3196` 与 `out_recovered_154` 并记录 SHA |
| 判定总表 / 最终合格表 / 药材映射原始账本 | **未归档** | 需归档，否则 provenance/筛选链只能复现派生表而非源账本 |
| 字节可复现性（BOM+CRLF） | **已记录** | `build_master.py` 强制 `utf-8-sig` + `\r\n`；`parse_orca_out.py` 在 Linux 上可能产出 `\n`，见下 |

**跨平台字节一致性**：`parse_orca_out.py` 的 `write_csv` 用 `newline=""`（Windows 下 `\r\n`，
Linux 下 `\n`）。要在 Linux 干净环境复现冻结哈希，需在解析后把 `orca_descriptors.csv` 归一为
`\r\n`，或对 `parse_orca_out.py` 加 `lineterminator="\r\n"`。`build_master.py` 已内置强制
`\r\n`，但**上游解析步**同样需要对齐。验收以 `verify_rebuild.py` 的 SHA 为准。

## 5. 状态

- 归档清单、重建协议、组装脚本、校验脚本：**本轮已落盘**（本文件 + `manifests/raw_input_archive_manifest.csv`
  + `code/build_master.py` + `code/verify_rebuild.py`）。
- **组装脚本已自洽验证**：用 `05_审计证据最新版/orca_descriptors.csv`（60 列）+ 从冻结主表抽取的
  PubChem 快照跑通 `build_master.py` → 3,196 行 × 79 字段，与冻结主表**3,193/3,196 行字节一致**；
  唯一 3 处差异正是 CID `248` / `5571`（formal charge +1 修复）与 `10946210`（E/Z 立体修复）——
  即 `05` 描述符表相对这 3 个修复分子是**陈旧旧版**。这证明 `build_master.py` 的字段顺序、连接、
  排序、BOM+CRLF 全部正确，且重建时**必须使用修复版 OUT 文件名**（见 §2）。
- 原始 OUT / PubChem 快照 / 上游账本的**实际归档**：仍待服务器侧执行，执行后回填 manifest 的 `sha256` 与 `archived`。
- 在归档与干净环境全链跑通并复现主表 SHA 之前，本项**不得标记为已完成**。
