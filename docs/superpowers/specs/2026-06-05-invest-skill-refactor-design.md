# Invest Skill 重构设计

**日期**：2026-06-05
**目标**：提升数据准确性、扩展技术面分析维度、多元化数据获取渠道

---

## 一、背景与问题

### 现状问题

1. **数据准确性不足**：依赖 agent-browser 爬取财经网站（东方财富/同花顺），反爬机制导致成功率低，数据经常退化到 L2/L3 级别
2. **技术面分析维度单一**：仅有均线+偏离度+动量+成交量+MACD 五个指标，缺少资金面、情绪面、多周期等维度
3. **数据获取渠道单一**：主要依赖网页爬取和搜索引擎摘要，无结构化数据源

### 改造原则

- 方法论（产业链拆解、基本面三维度、风险管理规则等）**保留不变**
- 重构"数据怎么来"和"技术面怎么算"
- 所有模块的数据获取流程统一改为"脚本为主、搜索为辅"

---

## 二、整体架构

```
用户输入 → Skill 意图识别 → 调度对应模块 → 脚本获取数据(JSON) → AI分析逻辑 → Markdown 输出
```

核心变化：从"AI 爬网页猜数据"变为"脚本精确获取 → AI 分析解读"。

---

## 三、目录结构

```
invest/
├── SKILL.md                          # 主入口（重写）
├── README.md                         # 更新
├── scripts/
│   ├── fetch_a_stock.py              # A股数据（AKShare）
│   ├── fetch_hk_stock.py             # 港股数据（AKShare + yfinance）
│   ├── fetch_us_stock.py             # 美股数据（yfinance）
│   └── requirements.txt              # akshare, yfinance
├── references/
│   ├── data-sources.md               # 重写：脚本为主，搜索为辅
│   ├── technical.md                  # 重写：多因子框架
│   ├── fundamental.md                # 重写数据获取流程
│   ├── radar.md                      # 重写数据获取流程
│   ├── industry.md                   # 重写数据获取流程
│   ├── report-template.md            # 适配新技术面维度
│   ├── risk-management.md            # 方法论不变
│   └── examples/
│       ├── few-shots.md              # 更新示例
│       └── meituan-03690.md          # 更新示例
```

---

## 四、脚本设计

### 4.1 统一接口规范

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/fetch_a_stock.py <股票代码> <数据类型>
python3 ${CODEBUDDY_SKILL_DIR}/scripts/fetch_hk_stock.py <股票代码> <数据类型>
python3 ${CODEBUDDY_SKILL_DIR}/scripts/fetch_us_stock.py <股票代码> <数据类型>
```

**数据类型参数**：`quote` | `finance` | `technical` | `fund_flow` | `valuation` | `all`

**输出**：JSON 到 stdout

### 4.2 自动依赖安装

脚本顶部检测依赖，缺失时自动安装：

```python
import subprocess
import sys

def ensure_dependencies():
    required = ["akshare", "yfinance"]
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

ensure_dependencies()
```

### 4.3 fetch_a_stock.py

| 数据类型 | 输出内容 | AKShare 接口 |
|----------|----------|--------------|
| `quote` | 最新价、涨跌幅、成交量、成交额、换手率、量比 | `ak.stock_zh_a_spot_em()` |
| `finance` | 营收、净利润、EBIT、经营现金流、自由现金流（近3年） | `ak.stock_financial_analysis_indicator()` |
| `technical` | 日K线（近120日）、均线(5/10/20/60)、MACD、RSI、KDJ、布林带、ATR | `ak.stock_zh_a_hist()` + 计算 |
| `fund_flow` | 主力资金净流入(近5日/20日)、北向资金、融资余额变化 | `ak.stock_individual_fund_flow()` + `ak.stock_hsgt_north_net_flow_in_em()` |
| `valuation` | PE/PB/PS 当前值、历史分位(近3年)、行业均值对比 | `ak.stock_a_indicator_lg()` |
| `all` | 以上全部合并 | 全部调用 |

**JSON 输出示例（quote）**：

```json
{
  "code": "000001",
  "name": "平安银行",
  "market": "A",
  "timestamp": "2026-06-05T15:00:00",
  "data": {
    "price": 12.35,
    "change_pct": 1.23,
    "volume": 58230000,
    "turnover_rate": 0.87,
    "volume_ratio": 1.15
  },
  "status": "ok"
}
```

**JSON 输出示例（technical）**：

```json
{
  "code": "000001",
  "name": "平安银行",
  "market": "A",
  "timestamp": "2026-06-05",
  "data": {
    "ma": {"ma5": 12.20, "ma10": 12.05, "ma20": 11.88, "ma60": 11.45},
    "ma_arrangement": "bullish",
    "deviation_60": 7.86,
    "momentum_20d": 5.2,
    "momentum_60d": 12.8,
    "macd": {"dif": 0.15, "dea": 0.08, "histogram": 0.07, "signal": "golden_cross"},
    "rsi": {"rsi6": 62.3, "rsi12": 58.7, "rsi24": 55.1},
    "kdj": {"k": 71.2, "d": 65.8, "j": 82.0},
    "boll": {"upper": 12.80, "mid": 12.05, "lower": 11.30, "position_pct": 68.5},
    "atr": {"atr14": 0.32, "atr_pct": 2.6},
    "volume_state": "normal",
    "volume_ratio_5_20": 1.15,
    "high_52w": 14.20,
    "low_52w": 9.80
  },
  "status": "ok"
}
```

**JSON 输出示例（fund_flow）**：

```json
{
  "code": "000001",
  "name": "平安银行",
  "market": "A",
  "timestamp": "2026-06-05",
  "data": {
    "main_net_inflow_5d": -12500000,
    "main_net_inflow_20d": 35000000,
    "north_net_flow_today": 890000000,
    "north_net_flow_5d": 2300000000,
    "margin_balance": 15600000000,
    "margin_balance_change_5d": 230000000
  },
  "status": "ok"
}
```

### 4.4 fetch_hk_stock.py

| 数据类型 | 输出内容 | 数据源 |
|----------|----------|--------|
| `quote` | 最新价、涨跌幅、成交量、换手率 | AKShare `ak.stock_hk_spot_em()` |
| `finance` | 营收、净利润、经营现金流（近3年） | yfinance |
| `technical` | 日K线（近120日）、均线、MACD、RSI、KDJ、布林带、ATR | AKShare `ak.stock_hk_hist()` + 计算 |
| `fund_flow` | 南向资金流向 | AKShare `ak.stock_hsgt_south_net_flow_in_em()` |
| `valuation` | PE/PB/PS、历史数据 | yfinance |
| `all` | 全部 | 组合 |

**代码格式**：输入 `00700` 或 `09988`（五位数字）

### 4.5 fetch_us_stock.py

| 数据类型 | 输出内容 | 数据源 |
|----------|----------|--------|
| `quote` | 最新价、涨跌幅、市值 | yfinance |
| `finance` | 营收、净利润、EBIT、现金流（近3年） | yfinance |
| `technical` | 日K线、均线、MACD、RSI | yfinance + 计算 |
| `valuation` | PE/PB/PS、市值 | yfinance |
| `all` | 全部 | yfinance |

**代码格式**：输入 `NVDA`、`MSFT`、`GOOGL` 等 ticker

### 4.6 错误处理

脚本统一错误输出格式：

```json
{
  "code": "000001",
  "market": "A",
  "status": "error",
  "error": "网络超时，AKShare 接口无响应",
  "fallback_hint": "建议使用 WebSearch 获取近似数据"
}
```

Skill 收到 `status: "error"` 时，自动触发降级策略（L2/L3）。

---

## 五、技术面多因子框架

### 5.1 评分权重

```
技术面总分 = 趋势方向(30%) + 资金面(30%) + 市场情绪(20%) + 周期位置(10%) + 板块比较(10%)
```

### 5.2 各维度评分标准

#### 趋势方向（30%）

| 分数 | 条件 |
|------|------|
| 5 | 均线多头 + 偏离度 +5~+15% + MACD DIF>0 金叉 |
| 4 | 均线多头 + 偏离度 +5~+20% + MACD DIF>0 |
| 3 | 均线缠绕 + 偏离度 -5~+5% + MACD 零轴附近 |
| 2 | 均线空头 + 偏离度 -5~-20% + MACD DIF<0 |
| 1 | 均线空头 + 偏离度 < -20% + MACD DIF<0 死叉 |

#### 资金面（30%）

| 分数 | 条件 |
|------|------|
| 5 | 主力5日净流入>0 + 北向连续买入 + 融资余额增加 |
| 4 | 三项中两项为正 |
| 3 | 资金面中性，无明显方向 |
| 2 | 三项中两项为负 |
| 1 | 主力持续流出 + 北向卖出 + 融资余额减少 |

#### 市场情绪（20%）

| 分数 | 条件 |
|------|------|
| 5 | 换手率适中(3-8%) + ATR收敛 + 量比>1.5温和放量 |
| 4 | 换手率正常 + 量价配合 |
| 3 | 换手率平淡 + 缩量 |
| 2 | 换手率过高(>15%)或过低(<1%) + 量价背离 |
| 1 | 恐慌性放量/极度冷清 |

#### 周期位置（10%）

| 分数 | 条件 |
|------|------|
| 5 | RSI 40-60 + KDJ 金叉 + 布林带中轨附近 |
| 4 | RSI 30-70 + 未超买超卖 |
| 3 | 中性区间 |
| 2 | RSI>70 或 <30，接近超买超卖 |
| 1 | RSI>80 或 <20，极端位置 |

#### 板块比较（10%）

| 分数 | 条件 |
|------|------|
| 5 | 个股20日涨幅 > 行业指数 + 10% 以上（强alpha） |
| 4 | 个股跑赢行业 5-10% |
| 3 | 个股与行业基本同步 |
| 2 | 个股跑输行业 5-10% |
| 1 | 个股大幅跑输行业 > 10% |

### 5.3 综合判断

| 总分 | 趋势阶段 | 操作建议 |
|------|----------|----------|
| 4.0-5.0 | 强势/健康上行 | 买入/持有 |
| 3.0-3.9 | 偏多/震荡偏强 | 轻仓试探/持有 |
| 2.0-2.9 | 震荡/偏弱 | 观望 |
| 1.0-1.9 | 弱势/超跌 | 回避/等待 |

---

## 六、各模块数据获取流程（重写）

### 统一模式

```
Step 1: 脚本获取结构化数据 → JSON（精确、可靠）
Step 2: AI 解读数据 + 应用方法论逻辑（分析、判断）
Step 3: WebSearch 补充定性信息（最新事件/研报/政策，脚本无法覆盖）
Step 4: 综合输出 Markdown
```

### 基本面模块

```bash
# Step 1: 获取财务+估值数据
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py 000001 finance
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py 000001 valuation

# Step 2: AI 分析商业模式（定性，用搜索）
WebSearch: "[公司名] 商业模式 护城河 竞争格局"

# Step 3: AI 综合评估
```

### 技术面模块

```bash
# Step 1: 获取全部技术+资金数据
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py 000001 technical
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py 000001 fund_flow

# Step 2: AI 计算五维度评分
# Step 3: WebSearch 补充板块指数数据（如需要）
```

### 趋势雷达模块

```
# 政策面/海外映射/技术拐点 — 仍以 WebSearch 为主（新闻/政策类信息无API）
# 脚本辅助：获取相关板块近期涨幅，评估"定价程度"
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py <板块ETF代码> quote
```

### 产业链模块

```
# 逻辑推演 — WebSearch 为主
# 脚本辅助：获取产业链相关公司财务数据做横向对比
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py <公司1> finance
python3 ${SKILL_DIR}/scripts/fetch_a_stock.py <公司2> finance
```

### 综合研报模块

按顺序调用以上各模块，汇总输出。

---

## 七、数据降级策略（更新）

| 级别 | 条件 | 处理方式 | 标注 |
|------|------|----------|------|
| L1 精确 | 脚本返回 `status: "ok"` | 直接使用精确数值 | `[AKShare/yfinance, 日期]` |
| L2 近似 | 脚本失败，WebSearch 获取到相关数据 | 使用近似数据 | `[搜索摘要, 日期, 可能存在偏差]` |
| L3 缺失 | 脚本+搜索均失败 | N/A + 定性逻辑替代 | `N/A（获取失败）` |

**预期覆盖率提升**：L1 从 ~20% → **80%+**

---

## 八、SKILL.md allowed-tools 更新

```yaml
allowed-tools: WebSearch, WebFetch, Bash(python3:*), Read, Write
```

移除 `Bash(agent-browser:*)` 依赖，改为 `Bash(python3:*)` 调用脚本。

---

## 九、不变的部分

以下方法论内容保持原样：
- 产业链拆解逻辑（上中下游、瓶颈型/增量型、环节评分）
- 基本面三维度（商业模式、财务表现、市场定价）
- "伟大公司四条件"
- 风险管理规则（图形优先、计划先行、仓位管理、止损、盈利保护）
- 趋势五阶段模型（保留定义，扩展判断指标）
- 买入三条件
- 强制规则（MUST/MUST NOT）
- 自检清单

---

## 十、实施步骤

1. 编写 `scripts/fetch_a_stock.py`（A股数据获取）
2. 编写 `scripts/fetch_hk_stock.py`（港股数据获取）
3. 编写 `scripts/fetch_us_stock.py`（美股数据获取）
4. 编写 `scripts/requirements.txt`
5. 重写 `references/technical.md`（多因子框架）
6. 重写 `references/data-sources.md`（脚本为主的数据体系）
7. 重写 `references/fundamental.md`（数据获取流程部分）
8. 重写 `references/radar.md`（数据获取流程部分）
9. 重写 `references/industry.md`（数据获取流程部分）
10. 更新 `references/report-template.md`（适配新技术面维度）
11. 重写 `SKILL.md`（主入口）
12. 更新 `references/examples/few-shots.md`
13. 更新 `references/examples/meituan-03690.md`
14. 更新 `README.md`

---

## 十一、风险与注意事项

1. **AKShare 接口稳定性**：开源库接口可能变动，需要脚本内做异常捕获
2. **yfinance 限流**：短时间大量调用可能被限制，需要加延时
3. **Python 3.14 兼容性**：AKShare/yfinance 可能尚未完全适配 Python 3.14，需测试
4. **网络环境**：部分数据源可能需要科学上网（yfinance 依赖 Yahoo）
5. **数据时效**：收盘后数据才完整，盘中数据可能有延迟

---

> 仅供研究参考，不构成投资建议。
