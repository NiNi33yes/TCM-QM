# TCM-QM Atlas 界面研究与设计依据

研究日期：2026-08-25  
研究范围：中药数据库、天然产物数据库、化学/量子化学数据库与科研检索规范。

## 本轮重点参考

- ccTCM：药材详情以基础信息、成分谱、相似药材和定量成分表分层；化合物详情把身份、分类、交叉引用与关系网络放在同一记录；资源分析使用逐级分类选择。
- HERB 2.0：围绕药材、成分、方剂、靶点、疾病等实体建立统一入口，并把证据类型与关系网络放入详情页。
- TCMBank / TCMM：首页支持实体类型切换和模糊检索；浏览页提供筛选、统计与表格；详情页同时展示属性和关系。
- PubChem：记录页采用粘性目录、可定位章节、交叉数据库链接和显式来源说明。
- Materials Project Molecules Explorer：搜索与属性筛选并列，详情按概览、性质、热化学、振动和计算条件分区。
- ChEBI / LOTUS / HMDB：首页优先放置统一搜索和示例查询；高级筛选与下载、文档、API 分开呈现。

## 落地原则

1. 首页第一屏先回答“这是什么、能查什么、数据从哪里来”，搜索是主动作。
2. 检索入口分为“化合物身份”和“药材来源”，对应用户的两种真实起点。
3. 所有筛选必须作用于完整数据集，不能只过滤当前页面。
4. 结果页显示总数、当前条件、排序和分页；条件变化回到第一页。
5. 详情页按身份、电子结构、热化学、振动、药材关系和溯源组织，并提供页内目录。
6. 每个数值都显示单位；近似量与不可直接比较的量在邻近位置说明。
7. 药材关联不写成药效关系；教育科研用途声明保持可见。
8. 视觉使用米白、本草深绿和朱砂色，避免通用企业仪表盘风格；装饰不冒充科学结构图。
9. 使用语义化表格、可见键盘焦点、清楚标签与移动端退化布局。

## 主要来源

- ccTCM: https://pmc.ncbi.nlm.nih.gov/articles/PMC10781882/
- HERB 2.0: https://pmc.ncbi.nlm.nih.gov/articles/PMC11701625/
- TCMBank: https://pmc.ncbi.nlm.nih.gov/articles/PMC10566508/
- SymMap: https://pmc.ncbi.nlm.nih.gov/articles/PMC6323958/
- ETCM 2.0: https://pmc.ncbi.nlm.nih.gov/articles/PMC10326295/
- TCM 数据库批判性综述: https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2024.1303693/full
- PubChem Compound Summary: https://pubchem.ncbi.nlm.nih.gov/docs/compound-page
- Materials Project Molecules Explorer: https://docs.materialsproject.org/apps/explorer-apps/molecules-explorer/tutorial
- EMBL-EBI Search Guidelines: https://www.ebi.ac.uk/style-lab/websites/meta-patterns/search-guidelines.html
- ChEBI: https://www.ebi.ac.uk/chebi
- LOTUS: https://lotus.naturalproducts.net/
- FAIR Principles: https://www.gofair.foundation/fair-principles
