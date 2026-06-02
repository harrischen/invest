# 趋势雷达模块

## 数据获取流程

趋势雷达需要从三个维度获取信息，以下是具体的数据获取步骤：

### 获取步骤

```
Step 1: 政策面扫描
  → WebSearch: "国务院常务会议 2025 [最近月份]"
  → WebSearch: "发改委 重大政策 2025 [最近月份]"
  → WebSearch: "[领域] 征求意见稿 2025"
  → WebFetch: https://www.ndrc.gov.cn （查看最新动态）
  → WebFetch: https://www.gov.cn/zhengce/ （查看最新政策）

Step 2: 海外映射扫描
  → WebSearch: "NVIDIA earnings data center revenue 2025"
  → WebSearch: "Microsoft Google Meta capex AI 2025"
  → WebSearch: "big tech capital expenditure guidance"
  → WebSearch: "TSMC advanced packaging CoWoS capacity"

Step 3: 技术拐点扫描
  → WebSearch: "[领域] 技术突破 量产 2025"
  → WebSearch: "[领域] 新标准 发布 升级"
  → WebSearch: "[技术] cost reduction commercial breakthrough"

Step 4: 交叉验证
  → 同一个方向是否有多个维度同时出现信号？
  → 政策+海外+技术 三重验证 = 最高确定性

Step 5: 定价程度评估
  → WebSearch: "[相关板块] 涨幅 估值 2025"
  → 判断市场是否已经充分反映
```

### 按维度的详细数据源

---

## 三维扫描框架

### 维度一：国家政策

**四大渠道**：

#### 渠道一：国家级核心源头

| 来源 | 网址 | 重点关注 |
|------|------|----------|
| 中国政府网 | https://www.gov.cn | 国务院常务会议、国家级政策文件 |
| 国务院政策文件库 | https://www.gov.cn/zhengce/ | 行政法规、部门规章、政策解读 |
| 国家发改委 | https://www.ndrc.gov.cn | 产业政策、项目审批、规划发布 |
| 工信部 | https://www.miit.gov.cn | 制造业/科技/通信/新材料政策 |
| 科技部 | https://www.most.gov.cn | 科技创新方向、重点研发计划 |
| 财政部 | https://www.mof.gov.cn | 税收优惠、财政补贴 |
| 国家能源局 | https://www.nea.gov.cn | 能源/电力/新能源政策 |
| 证监会 | https://www.csrc.gov.cn | 资本市场政策、IPO/再融资 |

#### 渠道二：本地落地渠道

| 来源 | 示例网址 | 重点关注 |
|------|----------|----------|
| 省级发改委 | 各省ndrc网站（如 https://fgw.gd.gov.cn 广东） | 地方产业规划、重大项目 |
| 地方经信局 | 各省市经信局官网 | 制造业转型、产业集群 |
| 高新区管委会 | 各高新区官网 | 招商引资政策、补贴方向 |
| 地方政府采购 | 各省政府采购网 | 地方大额采购 |

#### 渠道三：行业风向标

| 来源 | 网址 | 重点关注 |
|------|------|----------|
| 中国政府采购网 | https://www.ccgp.gov.cn | 大额采购项目（>1亿=重大方向） |
| 巨潮资讯网 | https://www.cninfo.com.cn | 上市公司公告（扩产/中标/战略合作） |
| 中国招标投标公共服务平台 | https://www.cebpubservice.com | 大型工程/设备招标 |
| 全国标准信息公共服务平台 | https://std.samr.gov.cn | 行业标准制定/升级动态 |
| 中国半导体行业协会 | https://www.csia.net.cn | 芯片行业数据 |
| 中国光伏行业协会 | https://www.chinapv.org.cn | 光伏行业数据 |
| 中国汽车工业协会 | https://www.caam.org.cn | 汽车/新能源车销量数据 |
| 中国通信企业协会 | https://www.cace.org.cn | 通信行业动态 |

#### 渠道四：提前准备窗口（征求意见稿）

| 来源 | 网址 | 说明 |
|------|------|------|
| 发改委征求意见 | https://www.ndrc.gov.cn/yjzx/ | 产业政策征求意见稿（早3-6个月） |
| 工信部征求意见 | https://www.miit.gov.cn/gzcy/yjzj/ | 制造业/通信政策征求意见 |
| 司法部征求意见 | https://www.moj.gov.cn/lfyjzj/ | 法规/条例征求意见 |
| 国家能源局征求意见 | https://www.nea.gov.cn/yjzq/ | 能源政策征求意见 |
| 中国政府法制信息网 | https://www.chinalaw.gov.cn | 综合性征求意见平台 |

> **策略**：定期浏览征求意见稿页面，发现新领域的意见稿 = 提前3-6个月的布局窗口

**搜索模板**：
```
"国务院常务会议 [月份] 2025"
"发改委 [领域] 2025 site:ndrc.gov.cn"
"[领域] 征求意见稿 2025"
"[领域] site:ccgp.gov.cn"
"[省份] [领域] 产业政策 2025"
"[领域] 征求意见 site:miit.gov.cn"
```

**政策力度判断**：
- ★★★★★ 写入五年规划（5年确定性）
- ★★★★ 国务院常务会议讨论（配套政策1-3个月内出）
- ★★★ 多部委联合发文
- ★★ 单部委发文 / 征求意见稿
- ★ 地方性政策

---

### 维度二：海外映射

**核心逻辑**：海外巨头投钱 → 中国供应链受益 → A股/港股映射标的上涨（时间差3-6个月）

**数据源**：

| 数据类型 | 来源 | 网址 | 获取方式 |
|----------|------|------|----------|
| 美股财报/指引 | Yahoo Finance | https://finance.yahoo.com/quote/NVDA/ | WebFetch |
| 财报电话会纪要 | Seeking Alpha | https://seekingalpha.com | WebSearch |
| 科技巨头资本开支 | Macrotrends | https://www.macrotrends.net | WebFetch |
| 半导体行业数据 | TrendForce | https://www.trendforce.com | WebSearch |
| 供应链动态 | DigiTimes | https://www.digitimes.com | WebSearch |

**重点跟踪**：

| 海外公司 | 关注指标 | A股/港股映射方向 |
|----------|----------|-----------------|
| NVIDIA | 数据中心收入、GPU出货 | 光模块、PCB、服务器、液冷 |
| Microsoft | Azure capex | 数据中心全链 |
| Google | Cloud capex | 光模块、交换机 |
| TSMC | CoWoS产能、先进制程 | 半导体设备、封装 |
| Arista | 交换机指引 | A股交换机 |
| Tesla | 交付量、储能 | 电池、电驱 |
| Apple | 新品/供应链订单 | 果链公司 |
| Broadcom | 定制ASIC、网络芯片 | 网络设备链 |

**搜索模板**：
```
"NVIDIA earnings data center revenue 2025"
"Microsoft Azure capital expenditure 2025"
"big tech capex AI infrastructure 2025"
"TSMC advanced packaging capacity"
"[公司] earnings call transcript Q[X] 2025"
"[公司] investor day capex guidance"
```

**港股 vs A股映射差异**：
- 港股反应快（与美股同步），A股滞后1-3个月
- 港股估值通常更低，A股有溢价
- 直接供应商（确定性高）> 间接受益 > 概念映射

---

### 维度三：技术拐点

**数据源**：

| 数据类型 | 来源 | 网址 | 获取方式 |
|----------|------|------|----------|
| 技术论文/突破 | MIT Technology Review | https://www.technologyreview.com | WebFetch |
| 行业标准发布 | 全国标准信息平台 | https://std.samr.gov.cn | WebFetch |
| 技术产品发布 | 各公司官网/发布会 | WebSearch | WebSearch |
| 量产/成本数据 | 券商研报 | WebSearch "[技术] 量产 成本 研报" | WebSearch |
| 专利动态 | 国家知识产权局 | https://www.cnipa.gov.cn | WebSearch |

**三类拐点**：

| 类型 | 定义 | 搜索方式 |
|------|------|----------|
| 成本突破 | 技术成本降到商用门槛 | "[技术] cost reduction commercial 2025" |
| 新产品发布 | 革命性产品创造新需求 | "[公司] new product launch 2025" |
| 标准升级 | 行业强制升级换代 | "[领域] 新标准 升级 next generation" |

**当前值得关注的方向**：
```
"AI agent 商用 2025"
"人形机器人 量产"
"固态电池 量产 成本"
"1.6T 光模块 商用"
"卫星互联网 商用"
"核聚变 商用进展"
"具身智能 机器人 突破"
"脑机接口 临床 商用"
```

---

## 信号评估标准

| 维度 | ⭐⭐⭐ 强 | ⭐⭐ 中 | ⭐ 弱 |
|------|-----------|---------|-------|
| 确定性 | 多维度交叉验证 | 逻辑清晰但缺验证 | 早期概念 |
| 定价程度 | 尚未被定价 | 部分定价 | 已充分定价 |
| 时间窗口 | 6-12个月兑现 | 12-24个月 | >24个月 |

## 输出格式

```markdown
## 趋势雷达扫描报告

**日期**：[YYYY-MM-DD]

### 强信号（⭐⭐⭐）
#### 1. [趋势名称]
- **来源**：[政策/海外/技术]
- **核心证据**：[1] [2] [3]
- **定价程度**：[未定价/部分/充分]
- **时间窗口**：[xxx]
- **A股/港股方向**：[xxx]
- **下一步**：产业链拆解（见 industry 模块）

### 中信号（⭐⭐） / 弱信号（⭐）
...

### 总结
| 排序 | 趋势 | 强度 | 建议动作 |
|------|------|------|----------|
| 1 | xxx | ⭐⭐⭐ | 立即拆解产业链 |
| 2 | xxx | ⭐⭐ | 持续跟踪 |
```
