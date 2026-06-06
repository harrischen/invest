# 数据获取方法

## 核心策略：腾讯/新浪 API 为主，WebSearch 为辅

| 数据类型 | 获取方式 | 来源 |
|----------|----------|------|
| 行情/K线/估值/基础财务 | **脚本获取（L1精确）** | 腾讯 `qt.gtimg.cn` + 新浪 `hq.sinajs.cn` |
| 资金流向 | **脚本获取（L1精确）** | AKShare（仅资金流向模块） |
| 政策/新闻/研报/深度财务 | 搜索获取（L2近似） | WebSearch |

**禁止使用的数据源**：
- ~~yfinance / Yahoo Finance~~（严重限流）
- ~~东方财富 push2 系列 API~~（Python 3.14 不兼容 + 限流）

## 脚本使用方法

### 统一入口

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/run.py <market> <code> <data_type>
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| market | 市场：`a`(A股) / `hk`(港股) / `us`(美股) | a |
| code | 股票代码 | 000001, 00700, NVDA |
| data_type | 数据类型 | quote, finance, technical, fund_flow, valuation, all |

### 数据类型

| 类型 | 内容 | A股 | 港股 | 美股 |
|------|------|-----|------|------|
| `quote` | 最新行情、涨跌幅、成交量、市值、PE/PB | ✓ | ✓ | ✓ |
| `finance` | EPS、净利润、ROE（A股）/ 基础信息（港美） | ✓ | ✓ | ✓ |
| `technical` | 均线、MACD、RSI、KDJ、布林带、ATR、成交量 | ✓ | ✓ | ✓ |
| `fund_flow` | 主力资金、北向/南向资金 | ✓ | 部分 | ✗ |
| `valuation` | PE/PB/股息率、52周高低、市值 | ✓ | ✓ | ✓ |
| `all` | 以上全部 | ✓ | ✓ | ✓ |

### 代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| A股 | 6位数字 | 000001, 600519, 300750 |
| 港股 | 5位数字 | 00700, 09988, 03690 |
| 美股 | Ticker | NVDA, MSFT, GOOGL |

### 调用示例

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/run.py a 600519 all
python3 ${CODEBUDDY_SKILL_DIR}/scripts/run.py hk 00700 technical
python3 ${CODEBUDDY_SKILL_DIR}/scripts/run.py us NVDA quote
```

### 输出格式

JSON 到 stdout，统一结构：

```json
{
  "code": "000001",
  "name": "平安银行",
  "market": "A",
  "timestamp": "2026-06-05T15:00:00",
  "data": { ... },
  "status": "ok"
}
```

---

## 数据底层来源

### 行情数据 - 腾讯 `qt.gtimg.cn`

| 市场 | 接口格式 | 特点 |
|------|----------|------|
| A股 | `http://qt.gtimg.cn/q=sz000001` | 无限流、毫秒响应 |
| 港股 | `http://qt.gtimg.cn/q=r_hk00700` | 无限流 |
| 美股 | `http://qt.gtimg.cn/q=usNVDA` | 无限流 |

### K线数据 - 腾讯 `proxy.finance.qq.com`

| 市场 | 接口 | 特点 |
|------|------|------|
| A股 | `proxy.finance.qq.com/...?param=sz000001,day,,,250,qfq` | 前复权日K |
| 港股 | `proxy.finance.qq.com/...?param=hk00700,day,,,250,qfq` | 前复权日K |
| 美股 | `proxy.finance.qq.com/...?param=usNVDA.OQ,day,,,250,` | 日K |

### 财务/估值 - 新浪 `hq.sinajs.cn`

| 数据 | 接口 | 内容 |
|------|------|------|
| A股扩展行情 | `hq.sinajs.cn/list=sz000001_i` | PE/PB/EPS/ROE/净利润/总市值 |
| 港股行情 | `hq.sinajs.cn/list=rt_hk00700` | PE/PB/EPS/股息率 |

### 资金流向 - AKShare（仅此一处）

| 数据 | AKShare 接口 |
|------|--------------|
| 个股资金流向 | `stock_individual_fund_flow()` |
| 北向资金 | `stock_hsgt_hist_em()` |

> 注：AKShare 资金流向模块走的是东方财富 `datacenter` 系列 API（非 push2），经验证稳定无限流。

---

## 搜索补充（脚本无法覆盖的信息）

| 类型 | 搜索模板 |
|------|----------|
| 商业模式/竞争格局 | `"[公司名] 商业模式 护城河 竞争格局"` |
| 详细财报（年报） | `"[公司名] 2025 年报 营收 净利润"` |
| 最新政策 | `"[领域] 政策 2025 site:gov.cn"` |
| 研报观点 | `"[公司名] 研报 评级 2025"` |
| 海外映射 | `"[公司] earnings capex guidance 2025"` |

---

## 数据降级策略

| 级别 | 条件 | 处理方式 | 标注 |
|------|------|----------|------|
| L1 精确 | 脚本返回 `status: "ok"` | 直接使用精确数值 | `[腾讯/新浪API, 日期]` |
| L2 近似 | 脚本失败，WebSearch 获取到数据 | 使用搜索摘要数据 | `[搜索摘要, 日期, 可能存在偏差]` |
| L3 缺失 | 脚本+搜索均失败 | N/A + 定性逻辑替代 | `N/A（获取失败）` |

---

## 注意事项

- 脚本首次运行会自动创建虚拟环境并安装依赖（约20秒），后续运行秒级返回
- 腾讯/新浪 API 无限流限制，可连续密集调用
- 收盘后数据最完整，盘中实时更新
- A股深度财务数据（年报详细科目）需通过 WebSearch 补充
