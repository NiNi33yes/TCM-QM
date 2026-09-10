# ORCA 6.0.1 / 6.1.1 同分子配对复算协议

更新时间：2026-08-29
适用范围：`02_数据冻结最新版_v5`，投稿前整改第 3 项
配套产物：`code/select_orca_version_paired_sample.py`、`code/rebuild_orca_input.py`、
`code/compare_orca_versions.py`、`audits/orca_version_paired_sample.csv`

## 0. 为什么需要这一步（不可跳过）

冻结数据集里 2,407 个分子用 ORCA 6.0.1 计算、789 个用 6.1.1 计算。论文现有的
「软件版本分层」分析（`audits/orca_version_analysis_summary.json`）是**分子间**比较：
两组分子不同，仅用元素计数校正，其 caveat 明确写着「版本分配未随机化，残余差异可能反映
未观测的批次或分子集合因素」。因此它**不能**建立版本因果效应。

本项补的是**分子内**比较：把**同一个分子、同一份输入几何、同一组关键词**分别在 6.0.1
和 6.1.1 下跑一遍，逐描述符求差。若差异可忽略，就正面回答了审稿人最可能的追问——
「6.0.1 → 6.1.1 的版本升级是否引入了数值漂移」，并把论文中「版本作为协变量保留」的
保守表述升级为「配对复算证实版本差异低于阈值」。

## 1. 验收标准（不可妥协）

`code/compare_orca_versions.py` 退出码为 0，且 `orca_version_paired_summary.json`
的顶层 `"verdict": "PASS"`。判定规则：

| 字段类 | 规则 |
|---|---|
| 恒等字段（charge/multiplicity/原子数/分子式/质量/基组/关键词/正常终止/收敛/频率与IR计数） | 两版本**逐值相等**（同一输入必得同一结果） |
| 数值描述符（能量/热化学/轨道/偶极/转动常数/振动频率/IR 强度） | `\|Δ\| = \|6.1.1 − 6.0.1\|` 落入容差（见下） |
| 运行相关字段（版本号/文件名/字节数/runtime/warning 计数） | **不参与判定**（机器与打印差异，非版本一致性判据） |

关键容差（完整表见 `compare_orca_versions.py` 顶部 `TOLERANCE`，可用
`--tolerance-config` 覆盖）：

| 描述符 | 容差 |
|---|---|
| 电子能 / 焓 / Gibbs / 热化学修正（Eh） | ≤ 1e-4 Eh |
| HOMO/LUMO/gap（eV） | ≤ 1e-3 eV |
| 偶极（Debye / a.u.） | ≤ 1e-2 D / 1e-4 a.u. |
| 最低/最高振动频率（cm⁻¹） | ≤ 1.0 cm⁻¹ |
| 转动常数 | 相对 ≤ 1e-3（0.1%） |
| 最大 IR 强度 | 相对 ≤ 1e-2 或绝对 ≤ 0.5 km/mol |

容差统一取「比预期优化器舍入宽松 2–3 个数量级」：PASS 意味着版本效应低于阈值、可忽略；
任何 FAIL 都指向需追查的真实回归，而非数值噪声。

## 2. 抽样（已落盘）

`audits/orca_version_paired_sample.csv` 已生成（40 个 CID，`--n` 可调 30–50）。分层：

1. **修复块（3）**：CID 248、5571（数据集仅有的两个 +1 带电分子）、10946210（E/Z 立体修复）。
   复算它们同时顺带验证修复路径在旧版本下同样成立。
2. **稀有/重元素（27）**：覆盖 I(2)、F(2)、Si(3)、Br(7) 全量，P/Cl/S 各取配额——重元素
   恰好是 def2 基组与 ECP 处理最可能受版本影响之处，故意过采样。
3. **CHNO 主体（10）**：按重原子数三分位 × 原版本批次分层填满。

样本整体原版本批次 6.0.1:6.1.1 = 30:10（75/25），与全库 2407:789 一致；覆盖全部 11 种
元素、重原子数 2–42、两种电荷态。抽样脚本 `--seed` 固定，完全可复现。

## 3. 重建输入（`code/rebuild_orca_input.py`）

每个选中 OUT 的 `INPUT FILE` 段回显了原始输入。脚本提取原始 `!` 关键词行、`%pal`/`%maxcore`
、`* xyz <charge> <mult>` 与坐标块（逐字保留元素记号与坐标），写出干净 `.inp`：

```bash
python code/rebuild_orca_input.py \
    --out-dir ARCHIVE_ROOT/out_final_3196 \
    --sample audits/orca_version_paired_sample.csv \
    --output-dir REBUILD/inp
    # 可选：--nprocs 48 --maxcore 2000 覆盖并行/内存行（默认复现原始值）
```

重建出的 `.inp` 保留 `noautostart`，即两个版本都从归档**起始几何**冷启动重新优化+频率，
对完整管线（优化+频率）做版本一致性检验，而非仅单点。修复分子按 `source_file`（
`248_charge_fix.out` 等）定位原始 OUT。

## 4. 运行配对计算（服务器侧）

前提：同一台机器上同时具备 ORCA 6.0.1 与 6.1.1 两个可执行文件，且输入几何一致。

```bash
# 对每个选中 CID，用同一份 .inp 各跑一个版本。
# 样本 CSV 用 CRLF 行尾（Windows 冻结惯例），`tr -d '\r'` 去掉回车避免 CID 带 \r。
for cid in $(cut -d, -f1 audits/orca_version_paired_sample.csv | tail -n +2 | tr -d '\r'); do
    /path/to/orca_6.0.1/orca REBUILD/inp/${cid}.inp > REBUILD/out_601/${cid}_601.out
    /path/to/orca_6.1.1/orca REBUILD/inp/${cid}.inp > REBUILD/out_611/${cid}_611.out
done
```

输出文件**必须**命名为 `<cid>_601.out` / `<cid>_611.out`（比较脚本按此后缀配对）。

## 5. 比较与判定（`code/compare_orca_versions.py`）

复用 `parse_orca_out.py` 的同一套字段提取（与冻结发布一致）：

```bash
python code/compare_orca_versions.py \
    --dir601 REBUILD/out_601 \
    --dir611 REBUILD/out_611 \
    --sample audits/orca_version_paired_sample.csv \
    --output-dir audits/orca_version_paired
```

产物：`orca_version_paired_consistency.csv`（逐 CID × 逐字段的 6.0.1 值 / 6.1.1 值 / Δ /
是否容差内）、`orca_version_paired_summary.json`（逐字段 Δ 统计 + 顶层 verdict）。
`echo $?` 为 0 且 verdict=PASS 即通过；FAIL 时 `per_field` 的 `failures` 给出具体
(字段, CID) 定位。

## 6. 回写论文与整改状态

配对复算跑通并 PASS 后：

1. 论文 `01_论文最新版_v6/TCM-QM_manuscript_v6.2.md` 的 §「Software-version
   stratification」**追加**一段配对复算结论（40 个分子跨两版本，恒等字段全等、数值字段
   Δ 全部落入容差，给出最大 |Δ| 与对应字段），把「不能建立因果」的 caveat 降级为
   「分子间分层提示的成分混杂，由分子内配对复算正面证实版本差异可忽略」。
2. 新增附表 `Supplementary_Table_S5_orca_version_paired.csv`（即
   `orca_version_paired_consistency.csv` 的投稿版），SI 加一条说明。
3. 更新 `投稿前整改状态.md`：把第 3 项从「仍未完成」移至「已完成」，并注明样本规模、
   最大差异与 PASS 结论。

## 7. 状态

- 抽样、输入重建、比较三个脚本与样本 CSV：**本轮已落盘并自测通过**（重建脚本对格式样本
  逐字节还原输入；比较脚本对同源副本给出全字段 Δ=0 的 PASS）。
- 配对 ORCA 实际计算：**待服务器侧执行**（需 6.0.1 与 6.1.1 两个二进制并存）。
- 在服务器跑通并拿到 verdict=PASS 之前，本项**不得标记为已完成**。
