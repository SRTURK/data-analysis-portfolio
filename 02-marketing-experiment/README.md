# 营销实验效果评估与人群策略

**问题：活动增加了多少真实购买和消费？是否值得按客户历史偏好选择邮件？**

直接阅读 [分析报告](reports/REPORT.md) 或打开 [HTML 图文报告](reports/REPORT.html)。先读 [冻结的回顾性分析方案](ANALYSIS_PLAN.md)，再看结果。

## 完整分析链路

64,000 名客户三组随机实验 → 数据校验与 SRM/基线平衡 → SQL 指标 → ITT 均值差与置信区间 → Holm 多重比较校正 → bootstrap 金额敏感性 → 50% discovery 冻结人群策略 → 50% validation IPW 评估 → 成本情景和下一轮样本量规划。

核心发现：男装、女装邮件的人均消费增量分别约 $0.770 和 $0.424。按历史购买偏好选邮件的人群策略，没有在独立验证样本证明优于统一男装邮件。未把负面或不确定结果包装为提升。

## 数据字典

| 字段 | 含义 | 可用于策略特征？ |
|---|---|---|
| recency | 距离上次购买月数 | 是，实验前 |
| history / history_segment | 前一年消费额 / 分档 | 是，实验前 |
| mens / womens | 前一年是否买过男装 / 女装 | 是，不代表性别 |
| newbie | 前一年是否新客户 | 是 |
| zip_code / channel | 地区类别 / 过去购买渠道 | 是 |
| segment | 原始随机分配的邮件组 | 是处理分配，不作为普通预测特征 |
| visit / conversion / spend | 之后两周是否访问 / 购买 / 消费额 | 结果变量，不能泄漏到策略输入 |
| row_id / split | 本项目添加的源文件行号 / discovery或validation | 仅用于可复现追踪 |

## 核心定义

- ITT：按最初被分配的组比较，保留未访问和未购买客户。
- 增量：邮件组均值减不发邮件组均值；不是邮件组全部收入。
- 主指标：每位被分配客户消费金额。购买后的平均消费只作描述，不替代主指标。
- Holm：两个主要金额比较为一个检验族，四个辅助指标比较另一个族；95% CI 是点态区间，不宣称同时覆盖。
- 人群规则：仅用 discovery 的历史购买类型选择平均消费最高的处理；没有根据 validation 调参。
- IPW：每位验证客户若实际处理与策略一致，贡献其消费额除以随机分配概率1/3；否则为0。估计的是策略平均结果，而非逐个客户真实反事实。
- 对比策略差值使用同一客户的配对伪结果，不把两策略当独立样本。

## 运行与文件

在作品集根目录执行：

```bash
python run_all.py --project experiment
```

- `sql/`：总体指标与 discovery/validation 分群指标。
- `run.py`：数据质量、推断、策略和报告生成。
- `data/processed/split_assignment.csv`：固定样本划分。
- `data/processed/frozen_policy.json`：由 discovery 单独确定的规则。
- `reports/treatment_effects.csv`：点估计、标准误、置信区间、原始及校正p值。
- `reports/holdout_policy_comparisons.csv`：独立验证结论。
- `reports/cost_sensitivity.csv`：全部成本与毛利假设情景。
- `reports/next_experiment_sample_size.csv`：下一轮实验每组人数的近似规划。

## 面试讲解

1. 为什么消费总额要除以所有分配客户，而不是只除以购买客户？
2. 为什么“男装显著，女装不显著”不能直接说明男装优于女装？本项目另做直接对比。
3. 为什么必须区分绝对百分点、相对提升，以及销售额和利润？
4. 为什么训练样本挑选出的最佳人群规则要独立验证？展示本项目没有胜过简单策略的结果。
5. 为什么只看两周指标不能回答长期价值？下一轮需加入退订、投诉和复购护栏。

## 数据归属与边界

[Kevin Hillstrom 原始发布](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)。原文件保留来源和SHA256；旧站通过公开HTTP提供下载。未查到单独的标准开源数据许可，因此发布包只包含获取脚本、分析代码和汇总结果，不打包原始客户数据。

这是公开历史随机实验的回顾性分析，没有实际营销成本、长期复购或投诉数据。代码由AI辅助实现，统计方法、校验和结果表均可核查。
