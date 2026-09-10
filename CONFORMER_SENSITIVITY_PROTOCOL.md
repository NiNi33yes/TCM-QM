# 柔性分子构象敏感性验证协议

更新时间：2026-08-29
适用范围：`02_数据冻结最新版_v5`，投稿前整改第 4 项（前半）
配套产物：`code/select_conformer_sample.py`、`code/generate_conformers.py`、
`code/compare_conformers.py`、`audits/conformer_sensitivity_sample.csv`

## 0. 为什么需要这一步

冻结数据集每个 CID 只存**一个** DFT 优化构象，来自**一个**起始几何。论文第
49 段已诚实声明「每行应理解为对单一 CID 解析起始几何的 DFT 优化，而非构象系综或已证
明的全局极小」。审稿人可能的追问是：「对柔性分子，换一个起始构象，你报的能量/偶极/带隙
会不会变？」

本项用实证回答：对 15 个柔性分子各生成 5 个不同起始构象，同一组关键词分别优化，看
优化后描述符的离散度。若同一分子所有构象都收敛到同一极小（能量离散 ≈ 0），则报告值对
起始构象不敏感；若离散大，则该分子确有多个可及极小，单一几何是**已知局限**而非代表值。

## 1. 验收判据（供结果解读，非通过/失败门槛）

按同一分子各构象优化后 `final_electronic_energy_eh` 的极差（换算 kcal/mol）分类：

| 极差 ΔE (kcal/mol) | 分类 | 解读 |
|---|---|---|
| < 0.1 | single_minimum | 各构象收敛到同一极小，报告值对起始构象不敏感 |
| [0.1, 2.0) | near_degenerate | 多个近简并极小，热力学可达，需谨慎比较构象依赖量 |
| ≥ 2.0 | multi_minimum | 显著构象敏感，单一几何是明确局限 |

> 阈值可用 `compare_conformers.py --energy-thresholds "0.1,2.0"` 调整。所有 15 个分子
> 的 `normal_termination`/`optimization_converged` 必须全为 1，否则该分子需重跑。

## 2. 抽样与构象生成（已落盘，本地即可复现）

- **选样**：`select_conformer_sample.py` 已选出 15 个柔性分子——中性、重原子数 10–32、
  可旋转键数最高（均为 15），见 `audits/conformer_sensitivity_sample.csv`。
- **构象生成**：`generate_conformers.py` 用 RDKit ETKDGv3 对每个分子嵌入 5 个多样起始
  构象，并写出 `xyz/`（归档）与 `inp/`（ORCA 输入，复用该 CID 的 `!` 关键词、电荷与
  多重度，**仅起始几何不同**）。已生成于 `audits/conformer_sensitivity/`（15×5=75 组）。

```bash
python code/generate_conformers.py \
    --sample audits/conformer_sensitivity_sample.csv \
    --output-dir audits/conformer_sensitivity --n-confs 5
```

## 3. 运行（服务器侧，ORCA）

用与冻结数据集一致的 ORCA 版本（各 CID 原 `orca_version` 见样本 CSV）逐个优化：

```bash
# 样本 CSV 为 CRLF，`tr -d '\r'` 去回车
for cid in $(cut -d, -f1 audits/conformer_sensitivity_sample.csv | tail -n +2 | tr -d '\r'); do
  for k in 1 2 3 4 5; do
    orca audits/conformer_sensitivity/inp/${cid}_conf${k}.inp \
         > audits/conformer_sensitivity/out/${cid}_conf${k}.out
  done
done
```

输出文件必须命名为 `<cid>_conf<k>.out`（比较脚本按此后缀解析）。

## 4. 分析（`code/compare_conformers.py`）

```bash
python code/compare_conformers.py \
    --out-dir audits/conformer_sensitivity/out \
    --sample audits/conformer_sensitivity_sample.csv \
    --output-dir audits/conformer_sensitivity/result
```

产物：`conformer_sensitivity_results.csv`（逐 CID × 每描述符 min/max/range/std +
sensitivity_class）、`conformer_sensitivity_summary.json`（分类计数 + 最大能量极差）。

## 5. 回写论文

跑通后把结论写入论文 `01_论文最新版_v6/TCM-QM_manuscript_v6.2.md` 第 49 段附近：

- 若 15/15 落入 `single_minimum`：把「未证明全局极小」的表述加强为「对 15 个柔性分子
  各 5 个起始构象的配对复算，优化后能量极差均 < 0.1 kcal/mol，报告值对起始构象不敏感」。
- 若出现 `multi_minimum`：诚实报告数量与最大 ΔE，作为「单一几何」局限的量化边界。

同时更新 `投稿前整改状态.md` 第 4 项状态。

## 6. 状态

- 选样、构象生成、比较三个脚本与样本 CSV：**本轮已落盘并本地跑通**（15 分子 × 5 构象
  的 xyz+inp 已生成）。
- 构象 ORCA 优化：**待服务器侧执行**。
- 拿到 `conformer_sensitivity_summary.json` 并解读分类前，本项**不得标记为已完成**。
