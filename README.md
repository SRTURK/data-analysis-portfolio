# 数据分析实习作品集

两个项目已拆分为可独立安装、运行和测试的仓库，建议直接访问：

- [电商履约与客户体验诊断 · olist-operations-analysis](https://github.com/SRTURK/olist-operations-analysis)
- [营销实验效果评估与人群策略 · marketing-experiment-analysis](https://github.com/SRTURK/marketing-experiment-analysis)

本仓库保留最初的合并版本与作品集索引；后续项目更新以各独立仓库为准。

两个完整、可复现的公开数据分析项目，覆盖 SQL 业务诊断和随机实验效果评估。

| 项目 | 展示能力 | 阅读入口 |
|---|---|---|
| 电商履约与客户体验诊断 | SQL多表建模、窗口函数、数据核验、指标异动分解 | [项目说明](01-olist-operations/README.md) · [分析报告](01-olist-operations/reports/REPORT.md) · [HTML](01-olist-operations/reports/REPORT.html) |
| 营销实验效果评估与人群策略 | ITT、置信区间、bootstrap、多重比较、独立策略验证 | [项目说明](02-marketing-experiment/README.md) · [分析报告](02-marketing-experiment/reports/REPORT.md) · [HTML](02-marketing-experiment/reports/REPORT.html) |

## 实际结果

- **Olist**：99,441笔原始订单；订单明细与支付明细直接关联会将商品金额高估 **4.54%**。修复后，2017-01至2018-08的96,203笔有效已送达订单延迟率为 **6.79%**；2018-02比前月上升 **8.43个百分点**，地区内变化贡献 **8.15个百分点**。
- **Hillstrom**：64,000名客户；男装邮件、女装邮件相对不发邮件的两周人均消费增量分别为 **$0.770**、**$0.424**。独立验证中，人群策略相对discovery选出的统一男装邮件差值为 **−$0.033**，95% CI **[−$0.316, $0.250]**，没有证据支持它更优。

数值由真实原始文件计算。报告区分相关性与因果结论，并保留未支持预期策略收益的结果。项目实现使用AI辅助，提供可复现代码、检查与结果表供核查。

## 已配置环境时复现

下载原始数据并安装独立虚拟环境后，在此文件所在目录执行 PowerShell：

```powershell
.\.venv\Scripts\python.exe run_all.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

也可在任意目录使用完整路径调用 run_all.py。每次运行覆盖生成的数据库、图表与报告，不修改原始数据。

## 从 GitHub 开始

建议 Python 3.12；本次实际环境版本见 requirements-lock.txt 与各项目 reports/run_metadata.json。

```bash
git clone https://github.com/SRTURK/data-analysis-portfolio.git
cd data-analysis-portfolio
python -m venv .venv
# Windows PowerShell
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe download_data.py
.venv/Scripts/python.exe run_all.py
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

macOS/Linux将Python入口改为 `.venv/bin/python`。若锁定版本无法适配平台，可安装 requirements.txt 中的兼容范围，记录新的环境并重新核对结果；严格数值复现优先使用锁定环境。

```bash
python run_all.py --project olist
python run_all.py --project experiment
python package_portfolio.py
```

只有下载数据/安装依赖需要网络。日常分析不需要服务器、API key、Kaggle登录或LLM调用；若来源未来变更访问限制，以原始发布页面为准。

## 结构

```text
data-analysis-portfolio/
  README.md
  requirements.txt / requirements-lock.txt
  download_data.py / data_manifest.json
  run_all.py / common.py
  tests/test_analysis.py
  01-olist-operations/
    README.md / run.py / sql/
    data/raw/       原始文件，未纳入发布包
    data/processed/ 可重建数据库
    reports/        中文报告、结果表、PNG图表和运行元数据
  02-marketing-experiment/
    ANALYSIS_PLAN.md / README.md / run.py / sql/
    data/raw/ / data/processed/ / reports/
```

## 验证范围

- Olist 20项质量/一致性断言，包含主键、外键、金额对账、指标总量、分解恒等式。
- Hillstrom 14项质量/划分断言，包含结果一致性、分组、零结果保留和策略动作合法性。
- 5项测试覆盖真实SQL在一对多关联与日期边界上的行为、Welch统计量、零结果分母、独立复算策略值、下载文件SHA256。
- 固定随机种子20261023；bootstrap 2,000次。图表由Matplotlib生成，HTML和Markdown报告均自动构建。

## 数据来源与发布范围

1. [Olist / Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)：历史匿名订单数据，遵循来源 CC BY-NC-SA 4.0。
2. [Kevin Hillstrom / MineThatData](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)：公开邮件实验；未将原始数据重新声明为开源许可。

仓库只包含代码、项目文档、来源清单与汇总结果。原始数据、个人求职准备材料、虚拟环境和数据库由 .gitignore 排除。下载清单保存实际文件哈希，可通过测试核对本地下载是否与本次分析一致。
