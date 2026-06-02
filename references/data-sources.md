# 数据获取方法

## 获取策略

| 数据复杂度 | 工具 | 场景 |
|------------|------|------|
| 简单查询 | WebSearch | 搜索公司信息、行业数据、新闻 |
| 特定页面 | WebFetch | 已知URL的内容抓取 |
| 需JS渲染 | agent-browser | 东方财富、同花顺等财经网站 |

## 数据源优先级

### 财务数据
| 优先级 | 来源 | 适合 |
|--------|------|------|
| 1 | 东方财富 (eastmoney.com) | A股财报、估值、行情 |
| 2 | 同花顺 (10jqka.com.cn) | A股数据、行业对比 |
| 3 | 雪球 (xueqiu.com) | 港美股、讨论 |
| 4 | 巨潮资讯 (cninfo.com.cn) | 公司公告原文 |
| 5 | Yahoo Finance | 美股/港股数据 |

### 行业数据
| 来源 | 适合 |
|------|------|
| 券商研报（搜索"行业+研报"） | 深度分析、预测 |
| 行业协会 | 官方统计 |
| 国家统计局 (stats.gov.cn) | 宏观数据 |

### 政策信息
| 来源 | 适合 |
|------|------|
| 中国政府网 (gov.cn) | 国务院政策 |
| 发改委 (ndrc.gov.cn) | 产业政策 |
| 政府采购网 (ccgp.gov.cn) | 采购方向 |

## 搜索模板

```
# 公司财务
"[公司名] [年份] 营收 净利润 财报"
"[代码] 财务分析"

# 估值
"[公司名] PE PB 估值 历史分位"
"[公司名] 估值 同行业 对比"

# 行业
"[行业] 市场规模 增速 2025"
"[行业] 产业链 竞争格局"
"[行业] 景气度 订单 产能"

# 政策
"[领域] 政策 site:gov.cn 2025"
"[领域] 征求意见稿 2025"

# 海外
"[company] earnings revenue guidance Q[X] 2025"
"[company] capex capital expenditure"
```

## agent-browser 抓取模式

```bash
# 东方财富 - 个股财务
agent-browser open "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=[SH/SZ][代码]"
agent-browser wait --load networkidle
agent-browser snapshot -i

# 雪球 - 个股
agent-browser open "https://xueqiu.com/S/[代码]"
agent-browser wait --load networkidle
agent-browser snapshot -i

# 港股代码格式: 0XXXX → xueqiu.com/S/0XXXX.HK
```

## 注意事项

- 部分网站有反爬限制，连续抓取间隔2-3秒
- 财经网站大量JS动态渲染，必须等 networkidle
- 数据找不到就如实说明，不编造
- 从多源交叉验证关键数据
- 标注数据来源和时间
