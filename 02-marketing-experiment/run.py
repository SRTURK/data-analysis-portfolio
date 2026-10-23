"""Retrospective three-arm randomized experiment analysis with honest policy holdout."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
from statsmodels.stats.multitest import multipletests
from sklearn.model_selection import train_test_split
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import setup, save_table, table, report, metadata, plt

BASE=Path(__file__).resolve().parent
OUT=BASE/'reports'
SEED=20261023
ARMS=['No E-Mail','Mens E-Mail','Womens E-Mail']

def difference(x,y):
    """Independent mean contrast x-y, Welch CI; valid for continuous and binary means."""
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    a=x.var(ddof=1)/len(x); b=y.var(ddof=1)/len(y)
    se=np.sqrt(a+b)
    df=(a+b)**2/(a*a/(len(x)-1)+b*b/(len(y)-1))
    effect=x.mean()-y.mean()
    critical=stats.t.ppf(.975,df)
    p=2*stats.t.sf(abs(effect/se),df)
    return {'effect':effect,'se':se,'ci_low':effect-critical*se,'ci_high':effect+critical*se,'p_raw':p}

def bootstrap_difference(x,y,rng,repetitions=2000):
    """Resample customers independently within original randomized groups."""
    x=np.asarray(x); y=np.asarray(y); values=[]
    for start in range(0,repetitions,25):
        b=min(25,repetitions-start)
        values.extend((rng.choice(x,(b,len(x)),replace=True).mean(axis=1)-
                       rng.choice(y,(b,len(y)),replace=True).mean(axis=1)).tolist())
    return np.quantile(values,[.025,.975])

def main():
    setup(); OUT.mkdir(exist_ok=True)
    processed=BASE/'data/processed'; processed.mkdir(parents=True,exist_ok=True)
    data=pd.read_csv(BASE/'data/raw/hillstrom.csv')
    data.insert(0,'row_id',np.arange(len(data)))
    checks=[]
    def check(name,passed,detail):
        checks.append({'check':name,'passed':bool(passed),'detail':str(detail)})
        if not passed: raise AssertionError(name+': '+str(detail))
    check('row count',len(data)==64000,len(data))
    check('no missing values',not data.isna().any().any(),int(data.isna().sum().sum()))
    check('three treatment arms',set(data.segment)==set(ARMS),sorted(data.segment.unique()))
    for col in ['visit','conversion','mens','womens','newbie']:
        check(col+' binary',data[col].isin([0,1]).all(),sorted(data[col].unique()))
    check('nonnegative spend',data.spend.ge(0).all(),data.spend.min())
    check('conversion implies visit',(data.conversion<=data.visit).all(),int((data.conversion>data.visit).sum()))
    check('positive spend equals conversion',((data.spend>0)==(data.conversion==1)).all(),int(((data.spend>0)!=(data.conversion==1)).sum()))
    disc_ids,val_ids=train_test_split(np.arange(len(data)),test_size=.5,stratify=data.segment,random_state=SEED)
    data['split']='discovery'; data.loc[val_ids,'split']='validation'
    check('disjoint partition',len(set(disc_ids)&set(val_ids))==0,f'{len(disc_ids)} / {len(val_ids)}')
    check('partition covers all',len(disc_ids)+len(val_ids)==len(data),len(data))
    save_table(data[['row_id','split']],processed,'split_assignment')
    db=duckdb.connect(str(processed/'experiment.duckdb')); db.register('input_data',data)
    db.execute('CREATE OR REPLACE TABLE customers AS SELECT * FROM input_data')
    group=db.execute((BASE/'sql/01_group_metrics.sql').read_text(encoding='utf-8')).df()
    save_table(group,OUT,'group_metrics')
    seg=db.execute((BASE/'sql/02_segment_metrics.sql').read_text(encoding='utf-8')).df()
    save_table(seg,OUT,'segment_metrics')
    n=data.segment.value_counts().reindex(ARMS)
    srm=stats.chisquare(n.to_numpy(),np.full(3,len(data)/3))
    # Numerical and one-hot baseline covariate balance against control.
    cols=['recency','history','mens','womens','newbie','zip_code','channel']
    cov=pd.get_dummies(data[cols],columns=['zip_code','channel'],dtype=float)
    balance=[]
    for arm in ARMS[1:]:
        x=cov[data.segment==arm]; y=cov[data.segment==ARMS[0]]
        sd=np.sqrt((x.var(ddof=1)+y.var(ddof=1))/2)
        for col in cov:
            balance.append({'arm':arm,'feature':col,'standardized_mean_difference':(x[col].mean()-y[col].mean())/sd[col]})
    balance=pd.DataFrame(balance); save_table(balance,OUT,'baseline_balance')
    rng=np.random.default_rng(SEED)
    effects=[]
    for arm,control in [(ARMS[1],ARMS[0]),(ARMS[2],ARMS[0]),(ARMS[1],ARMS[2])]:
        for metric in ['spend','conversion','visit']:
            x=data.loc[data.segment==arm,metric].to_numpy(); y=data.loc[data.segment==control,metric].to_numpy()
            r=difference(x,y)
            r.update(arm=arm,control=control,metric=metric,n_treatment=len(x),n_control=len(y),treatment_mean=x.mean(),control_mean=y.mean(),relative_lift=r['effect']/y.mean())
            r['family']='exploratory_head_to_head' if control!=ARMS[0] else ('primary_spend' if metric=='spend' else 'secondary')
            if metric=='spend':
                lo,hi=bootstrap_difference(x,y,rng); r.update(bootstrap_ci_low=lo,bootstrap_ci_high=hi)
            effects.append(r)
    effects=pd.DataFrame(effects)
    for family,idx in effects.groupby('family').groups.items():
        effects.loc[idx,'p_holm']=multipletests(effects.loc[idx,'p_raw'],method='holm')[1]
    save_table(effects,OUT,'treatment_effects')
    # Next-experiment planning: conservative alpha .025 per primary contrast.
    power=[]
    for metric,delta in [('spend',.20),('conversion',.002),('visit',.01)]:
        control=data.loc[data.segment==ARMS[0],metric]
        variance=control.var(ddof=1)
        n_required=int(np.ceil(2*variance*(stats.norm.ppf(1-.025/2)+stats.norm.ppf(.8))**2/delta**2))
        power.append({'metric':metric,'target_absolute_effect':delta,'alpha_two_sided':.025,'power':.8,'required_per_arm_approx':n_required})
    save_table(pd.DataFrame(power),OUT,'next_experiment_sample_size')
    # Freeze the simple policy using discovery only.
    data['purchase_type']=np.select([(data.mens==1)&(data.womens==1),data.mens==1,data.womens==1],['both','mens_only','womens_only'],default='neither')
    discovery=data[data.split=='discovery']; validation=data[data.split=='validation'].copy()
    decisions=[]
    for kind,sub in discovery.groupby('purchase_type'):
        means=sub.groupby('segment').spend.mean().reindex(ARMS)
        chosen=means.idxmax()
        decisions.append({'purchase_type':kind,'chosen_arm':chosen,'discovery_customers':len(sub),
                          'discovery_no_email_mean':means.iloc[0],'discovery_mens_mean':means.iloc[1],
                          'discovery_womens_mean':means.iloc[2]})
    decisions=pd.DataFrame(decisions); rule=dict(zip(decisions.purchase_type,decisions.chosen_arm))
    save_table(decisions,OUT,'frozen_policy')
    (processed/'frozen_policy.json').write_text(json.dumps(rule,indent=2),encoding='utf-8')
    chosen=validation.purchase_type.map(rule).fillna(ARMS[0])
    check('policy uses available arms',chosen.isin(ARMS).all(),rule)
    # Horvitz-Thompson: match observed random treatment to frozen policy, weight by 1/(1/3).
    scores={'personalized':np.where(validation.segment==chosen,3*validation.spend,0)}
    for arm in ARMS: scores[arm]=np.where(validation.segment==arm,3*validation.spend,0)
    policy=[]
    for name,values in scores.items():
        values=np.asarray(values); se=values.std(ddof=1)/np.sqrt(len(values))
        policy.append({'policy':name,'holdout_value':values.mean(),'ci_low':values.mean()-1.96*se,'ci_high':values.mean()+1.96*se})
    policy=pd.DataFrame(policy); save_table(policy,OUT,'holdout_policy_values')
    comparisons=[]
    for arm in ARMS:
        diff=scores['personalized']-scores[arm]; se=diff.std(ddof=1)/np.sqrt(len(diff)); effect=diff.mean()
        p=2*stats.norm.sf(abs(effect/se)) if se else 1.
        comparisons.append({'comparison':'personalized vs '+arm,'effect':effect,'ci_low':effect-1.96*se,'ci_high':effect+1.96*se,'p_raw':p})
    comparisons=pd.DataFrame(comparisons); comparisons['p_holm']=multipletests(comparisons.p_raw,method='holm')[1]
    save_table(comparisons,OUT,'holdout_policy_comparisons')
    fixed_discovery=discovery.groupby('segment').spend.mean().idxmax()
    fixed_comparison=comparisons[comparisons.comparison=='personalized vs '+fixed_discovery].iloc[0]
    better=fixed_comparison.effect>0 and fixed_comparison.p_holm<.05
    decision='人群策略在留出样本优于 discovery 选出的固定策略，但仍需新一轮线上实验' if better else '人群策略未证明优于 discovery 选出的固定策略；优先保留简单方案并继续验证'
    # Segment-specific contrasts show uncertainty, not a claim that groups differ causally.
    segments=[]
    for split,part in data.groupby('split'):
        for kind,sub in part.groupby('purchase_type'):
            for arm in ARMS[1:]:
                x=sub.loc[sub.segment==arm,'spend']; y=sub.loc[sub.segment==ARMS[0],'spend']
                if len(x)>1 and len(y)>1:
                    row=difference(x,y); row.update(split=split,purchase_type=kind,arm=arm,n_treatment=len(x),n_control=len(y)); segments.append(row)
    save_table(pd.DataFrame(segments),OUT,'segment_spend_effects')
    scenarios=[]
    for _,r in effects[(effects.metric=='spend')&(effects.control==ARMS[0])].iterrows():
        for margin in [.2,.4,.6]:
            for cost in [0,.05,.1,.2]:
                scenarios.append({'arm':r.arm,'assumed_margin':margin,'assumed_contact_cost':cost,
                  'incremental_profit_per_customer':r.effect*margin-cost,
                  'ci_low':r.ci_low*margin-cost,'ci_high':r.ci_high*margin-cost,
                  'break_even_contact_cost':r.effect*margin})
    save_table(pd.DataFrame(scenarios),OUT,'cost_sensitivity')
    save_table(pd.DataFrame(checks),OUT,'validation_checks')
    # Figures deliberately separate currency from percentage points.
    fig,axes=plt.subplots(1,3,figsize=(12,4.3))
    for ax,metric,title in zip(axes,['spend','conversion','visit'],['人均消费增量（美元）','购买率增量（百分点）','访问率增量（百分点）']):
        e=effects[(effects.metric==metric)&(effects.control==ARMS[0])].set_index('arm').loc[ARMS[1:]]
        factor=1 if metric=='spend' else 100
        ax.errorbar(e.effect*factor,[1,0],xerr=np.vstack([(e.effect-e.ci_low)*factor,(e.ci_high-e.effect)*factor]),fmt='o',capsize=5,color='#176B87')
        ax.set_yticks([1,0],['男装邮件','女装邮件']); ax.axvline(0,color='#888',linestyle='--'); ax.set_title(title,fontsize=11); ax.set_ylim(-.5,1.5)
    fig.suptitle('相对不发邮件的 ITT 效果 · 点态 95% 置信区间',fontsize=14); fig.tight_layout(); fig.savefig(OUT/'treatment_effects.png'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.6)); y=np.arange(len(policy))
    ax.errorbar(policy.holdout_value,y,xerr=np.vstack([policy.holdout_value-policy.ci_low,policy.ci_high-policy.holdout_value]),fmt='o',capsize=6)
    ax.set_yticks(y,['冻结的人群策略','统一不发邮件','统一男装邮件','统一女装邮件']); ax.set(title='独立留出样本：策略人均消费估计',xlabel='美元/客户（IPW；点态95% CI）'); ax.invert_yaxis()
    fig.tight_layout(); fig.savefig(OUT/'policy_holdout.png'); plt.close(fig)
    male=effects[(effects.arm==ARMS[1])&(effects.control==ARMS[0])&(effects.metric=='spend')].iloc[0]
    female=effects[(effects.arm==ARMS[2])&(effects.control==ARMS[0])&(effects.metric=='spend')].iloc[0]
    summary={'customers':len(data),'srm_p':float(srm.pvalue),'max_abs_baseline_smd':float(balance.standardized_mean_difference.abs().max()),
      'mens_spend_lift':float(male.effect),'mens_ci':[float(male.ci_low),float(male.ci_high)],
      'womens_spend_lift':float(female.effect),'womens_ci':[float(female.ci_low),float(female.ci_high)],
      'frozen_policy':rule,'discovery_best_fixed':fixed_discovery,'policy_vs_best_fixed_effect':float(fixed_comparison.effect),
      'policy_vs_best_fixed_ci':[float(fixed_comparison.ci_low),float(fixed_comparison.ci_high)],
      'policy_vs_best_fixed_p_holm':float(fixed_comparison.p_holm),'personalization_supported':bool(better),
      'checks_passed':len(checks)}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    e=effects[['arm','control','metric','effect','ci_low','ci_high','p_holm']]
    boot=effects[effects.metric=='spend'][['arm','control','bootstrap_ci_low','bootstrap_ci_high']]
    body=f'''完成日期：2026-10-23 · 公开随机实验复盘 · 50% 独立策略验证样本

## 决策结论

1. **64,000 名客户**的三组随机实验中，男装邮件相对不发邮件，两周人均消费增加 **${male.effect:.3f}**（95% CI **[{male.ci_low:.3f}, {male.ci_high:.3f}]**），女装邮件增加 **${female.effect:.3f}**（95% CI **[{female.ci_low:.3f}, {female.ci_high:.3f}]**）。主检验 Holm 校正 p 值分别为 **{male.p_holm:.3g}** 和 **{female.p_holm:.3g}**。
2. discovery 样本选出的最佳固定策略为 **{fixed_discovery}**。冻结的人群策略相对它，在 validation 样本的人均消费差为 **${fixed_comparison.effect:.3f}**，95% CI **[{fixed_comparison.ci_low:.3f}, {fixed_comparison.ci_high:.3f}]**。
3. **{decision}。** 不能凭训练样本中某些分组均值更高就承诺个性化投放有效。

## 数据、质量与设计

来源：[Kevin Hillstrom 原始数据发布](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)。原始下载、大小和 SHA256 见根目录 data_manifest.json。该数据发布于 2008 年，结论仅针对该历史实验；不能外推到今日中国互联网营销。

邮件内容分为男装、女装；这不是客户性别。实验前客户特征和实验后两周结果分开使用。全部未购买客户的 spend=0 保留在分母中；以购买客户为条件计算的消费均值仅供描述。

- 三组人数：{ {k:int(v) for k,v in n.items()} }。1:1:1 SRM 卡方检验 p={srm.pvalue:.4f}，数值与分类基线特征最大绝对标准化差异为 {balance.standardized_mean_difference.abs().max():.4f}。平衡检查不能证明一切实验风险都不存在。
- **{len(checks)} 项数据与划分断言通过**。原数据无客户 ID，以源文件行号保持可复现对应；相同特征/结果行不代表重复客户，未盲目去重。
- 方案见 ANALYSIS_PLAN.md，实施前冻结，但属于公开历史数据的回顾性方案，不声称原始预注册或自己上线实验。

{table(group)}

## 平均处理效果

![平均效果](treatment_effects.png)

{table(e,6)}

spend 单位为美元/被分配客户；conversion、visit 的 effect 为概率差，乘 100 得到百分点。相对提升另见 treatment_effects.csv。Welch 均值差检验用于金额与二元指标，大样本二元均值差采用渐近近似。CI 为点态 95%；显著性用对应检验族的 Holm p 值，两者含义不同。

主检验族为两项 spend vs control；四项辅助指标比较单独校正；三项男装 vs 女装直接比较单独列为探索性检验族。未通过“某组显著、另一组不显著”推断组间差异。

长尾消费金额补充用户级组内独立重采样 2,000 次：

{table(boot)}

## 人群策略：先学习，再验证

按实验组分层，用固定随机种子 {SEED} 切分 discovery / validation，各 32,000 人。只用实验前购买类型在 discovery 中选择人均消费最高动作，并保存规则；validation 不参与选择。

{table(decisions)}

![策略验证](policy_holdout.png)

{table(comparisons)}

策略评估使用已知随机分配概率 1/3 的 Horvitz–Thompson/IPW：只有客户实际接受的处理与策略推荐一致时，贡献为 3×消费金额，否则为零。与固定策略比较时对同一客户的两个伪结果做差，计算配对标准误；没有把相关策略当独立样本比较。

已知分配概率来自原始设计；实际分组人数并非恰好相等，有限样本 IPW 值不必等于直接组均值。金额长尾及分群样本少使验证区间较宽。分组点估计不等同于已证明处理效果异质性；未进行正式交互检验或宣称模型识别出“必被说服”的个人。

## 成本敏感性与下一轮实验

真实成本和毛利缺失，按假设毛利率 20%/40%/60%、单次触达成本 $0/$0.05/$0.10/$0.20 输出 cost_sensitivity.csv。净增益 = 消费增量×假设毛利率−假设触达成本；零成本不代表生产触达实际免费。以 40% 毛利率为例，男装邮件点估计的单次触达盈亏平衡成本为 **${male.effect*.4:.3f}**，不是实测利润。

下一轮实验样本量的正态近似规划（每组人数；两侧 alpha=.025，power=.80）：

{table(pd.DataFrame(power))}

规划使用本次对照组方差作为未来基线近似，未计算误导性的“事后 observed power”；正式新实验需重新确认人群、转化基线与金额分布。spend 的目标差为美元，二元指标的目标差为概率。

建议继续验证 discovery 选出的简单固定策略与不发邮件，同时增加退订、投诉和长期复购护栏。两周数据不能回答长期效果。

## 复现

在根目录运行 `python run_all.py --project experiment`。原始 CSV → 数据质量与分层划分 → SQL 分组指标 → 总体统计推断 → discovery 冻结策略 → validation 评估 → 图表与本报告。全部分析离线运行，不需要 LLM API 或密钥。
'''
    report(OUT,'营销实验效果评估与人群策略',body)
    metadata(OUT,{'project':'hillstrom','seed':SEED,'bootstrap_repetitions':2000,'checks_passed':len(checks),'validation_fraction':.5})
    db.close(); print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
