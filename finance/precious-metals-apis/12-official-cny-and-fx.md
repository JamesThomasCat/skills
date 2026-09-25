# 12 · 官方与人民币口径补充源（CFETS / NBP / Frankfurter / 黄金ETF / 上期所 / fawazahmed）

本篇收录 6 个"配角但关键"的来源：它们不直接提供伦敦金实时价，却决定**人民币换算是否可信**、**是否有官方口径兜底**、**境内金价是否有第二条独立链路**。

| 编号 | 来源 | 作用 | 鉴权 |
|---|---|---|---|
| 12.1 | CFETS 人民币汇率中间价 | **官方汇率口径**（换算元/克的首选汇率） | 无 |
| 12.2 | 波兰央行 NBP 金价 | 官方机构金价（非美、非人民币的第三方锚） | 无 |
| 12.3 | Frankfurter（ECB） | 市场汇率（与 CFETS 中间价互为对照） | 无 |
| 12.4 | fawazahmed currency-api | 免费批量取 XAU/XAG/XPT/XPD 的多币种交叉价 | 无 |
| 12.5 | 腾讯黄金 ETF（518880/518800） | 境内 CNY 金价的 ETF 代理链路 | 无 |
| 12.6 | 上海期货交易所日线 | 沪金/沪银期货官方日线 | 无 |

## 12.1 CFETS 人民币汇率中间价（官方）

中国外汇交易中心（CFETS）每日 9:15 发布的官方中间价——07 号文档提到"官方口径以 CFETS 为准"但没给端点，这里补上。

```http
GET https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/fx/ccpr.json
```

- 无参数、无请求头、无鉴权；返回 25 个货币对。
- 记录数组 `records[]` 中 `vrtEName == "USD/CNY"` 的那条即美元兑人民币中间价。

实测（2026-09-25 会话）：

```json
{"head": {"version": "2.0", "provider": "CWAP", "rep_code": "200", "ts": 1790213140627},
 "data": {"lastDateEn": "24/09/2026 9:15", "lastDate": "2026-09-24 9:15"},
 "records": [
   {"vrtCode": "1", "vrtName": "美元/人民币", "vrtEName": "USD/CNY", "price": "6.7489", "bp": "21.00", "bpDouble": 21.0},
   {"vrtCode": "2", "vrtName": "欧元/人民币", "vrtEName": "EUR/CNY", "price": "7.6631", "bp": "304.00", "bpDouble": -304.0}
 ]}
```

| 字段 | 含义 |
|---|---|
| `data.lastDate` | 报价日期（北京时间 9:15） |
| `records[].vrtEName` | 货币对（`USD/CNY`、`EUR/CNY`、`100JPY/CNY`…） |
| `records[].price` | 中间价（**字符串**） |
| `records[].bp` / `bpDouble` | 相对上日的基点变动（字符串 / 数值） |

实测值：**USD/CNY = 6.7489（2026-09-24 9:15）**。

> 用途：这是人民币换算的**官方口径**，也是区分"中间价 vs 市场汇率"两条换算线的关键（见 README）。注意它是每日一次的定盘价，日内不更新。

## 12.2 波兰央行 NBP 金价（官方机构）

```http
GET https://api.nbp.pl/api/cenyzlota/last/?format=json
```

| 变体 | 说明 |
|---|---|
| `/cenyzlota/last/` | 最新一条 |
| `/cenyzlota/{YYYY-MM-DD}/` | 指定日期 |
| `/cenyzlota/{start}/{end}/` | 区间（≤93 天） |
| `?format=json` / `xml` | 格式，默认 json |

实测：`[{"data":"2026-09-24","cena":529.95}]` —— **529.95 PLN/克**（波兰央行公布的黄金价，克计价，非盎司）。

- 官方机构（央行）发布，免 Key，日更，工作日约 8:00–9:00 CET 更新。
- 用途：第三方"官方机构"锚点；也适合做**单位换算的教学样例**（它本身就是"每克价"，无需除 31.1034768）。
- 注意：以 PLN 计价，需再经 USD/PLN 折算才能与美元金价比对。

## 12.3 Frankfurter（ECB 参考汇率）

```http
GET https://api.frankfurter.dev/v1/latest?base=USD&symbols=CNY
```

实测：`{"amount":1.0,"base":"USD","date":"2026-09-24","rates":{"CNY":6.7126}}`

**两个坑**：

1. 旧域名 `api.frankfurter.app` 会 **302 重定向到 `api.frankfurter.dev`**；
2. 新域名路径**必须带版本段 `/v1/`** —— `https://api.frankfurter.dev/latest` 直接 404 `{"status":404,"message":"not found"}`。

历史区间用 `/v1/{start}..{end}?base=USD&symbols=CNY`；币种列表 `/v1/currencies`。数据源为欧洲央行每日参考汇率（约 16:00 CET），周末与节假日不更新。

## 12.4 fawazahmed currency-api（jsdelivr CDN，免费批量）

```http
GET https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/xau.json
```

- 无需 Key，经 jsdelivr CDN 分发（本环境 GitHub 直连被屏蔽，jsdelivr 可用）。
- 文件以**基准币种**命名，内容为"1 单位基准 = N 单位目标"。取 `xau.json` 即"1 金衡盎司黄金 = N 单位某资产"。
- 可用日期锁定版本：`@2026-09-24/v1/currencies/xau.json`。

实测（2026-09-25 会话，`date: "2026-09-24"`）：

| 键 | 值 | 含义 |
|---|---|---|
| `xau.usd` | 4284.17810185 | 1 oz 金 = 4284.18 美元 |
| `xau.cny` | 28765.45645861 | 1 oz 金 = 28765.46 元 → **924.83 元/克** |
| `xau.xag` | 66.82988814 | 金银比（1 oz 金 = 66.83 oz 银） |
| `xau.xpt` | 2.43924264 | 1 oz 金 = 2.439 oz 铂 → 铂 ≈ **1756.4 美元/盎司** |
| `xau.xpd` | 3.37992905 | 1 oz 金 = 3.380 oz 钯 → 钯 ≈ **1267.5 美元/盎司** |

> 用法要点：**其他金属价 = `xau.usd` ÷ `xau.{metal}`**（该文件是"以金为基准"的交叉表）。除 xau 外还可用 `xag.json`、`xpt.json`、`xpd.json` 直接以对应金属为基准。
> `xau.btc`（0.051087616）可用于"金价折 BTC"这类冷门换算。

## 12.5 腾讯黄金 ETF（境内 CNY 金价代理）

复用 03 号文档的主机，代码换成 ETF：

```http
GET https://qt.gtimg.cn/q=sh518880,sh518800
```

实测（2026-09-25 会话，行情时间 20260924161451）：

| 代码 | 名称 | 最新价 | 昨收 |
|---|---|---|---|
| `sh518880` | 黄金ETF华安 | 8.788 | 8.897 |
| `sh518800` | 黄金ETF国泰 | 9.215 | 9.326 |

⚠️ **格式与 03 号文档不同**：`hf_` 前缀的品种返回**逗号分隔 14 字段**，而 ETF 走的是**波浪号 `~` 分隔的 A 股字段格式**：

```text
v_sh518880="1~黄金ETF华安~518880~8.788~8.897~8.838~4218092~…~~20260924161451~-0.109~-1.23~8.846~8.783~…";
```

实测推断的下标（以返回报文核对，非官方文档）：

| 下标 | 含义 |
|---|---|
| 1 | 名称 |
| 2 | 代码 |
| 3 | **最新价** |
| 4 | 昨收 |
| 5 | 今开 |
| 6 | 成交量（手） |
| 30 | 时间戳 `YYYYMMDDHHMMSS` |
| 31 / 32 | 涨跌额 / 涨跌幅% |
| 33 / 34 | 最高 / 最低 |

- 仍需 **GBK 解码**（同 03 号文档）。
- 用途：ETF 净值 ≈ AU9999 现货（每份对应固定克数），是"只想要一个人民币金价"的省事代理。但有**折溢价、管理费、申赎机制**造成的偏差，不能当基准价用。

## 12.6 上海期货交易所（SHFE）日线数据

```http
GET https://www.shfe.com.cn/data/tradedata/future/dailydata/kx{YYYYMMDD}.dat
```

实测 `kx20260924.dat` 返回全品种期货日线 JSON：

```json
{"o_IMChangeDate":"20150813","showlength":"1","o_day":"24","o_weekday":"四",
 "o_curinstrument":[{"OPENINTEREST":110988,"HIGHESTPRICE":111160,"TURNOVER":3725303.215,
   "PRODUCTGROUPID":"cu","PRODUCTCLASS":"1","CLOSEPRICE":110700,"VOLUME":67255,
   "OPENINTERESTCHG":-19117,"PRODUCTID":"cu_f","PRODUCTNAME":"铜","ZD2_CHG":-550,
   "OPENPRICE":110790,"ZD1_CHG":-630,"SETTLEMENTPRICE":110780,"DELIVERYMONTH":"2610",
   "PRESETTLEMENTPRICE":111330,"LOWESTPRICE":110560}]}
```

| 字段 | 含义 |
|---|---|
| `PRODUCTID` / `PRODUCTNAME` | 品种代码（如 `cu_f`）/ 中文名 |
| `DELIVERYMONTH` | 交割月（`小计` 表示该品种汇总行） |
| `OPENPRICE` / `HIGHESTPRICE` / `LOWESTPRICE` / `CLOSEPRICE` / `SETTLEMENTPRICE` | 开/高/低/收/结算价 |
| `PRESETTLEMENTPRICE` / `ZD1_CHG` / `ZD2_CHG` | 昨结算 / 相对昨收变动 / 相对昨结算变动 |
| `VOLUME` / `OPENINTEREST` / `OPENINTERESTCHG` / `TURNOVER` | 成交量 / 持仓量 / 持仓变化 / 成交额 |

- 价格单位：金属多为**元/吨**，贵金属品种口径以交易所为准。
- ⚠️ **黄金需要自行按 `"PRODUCTID":"au_f"` 过滤，本次未逐条确认 au/ag 记录是否在列**（响应体超大、被会话工具截断）。接入请先本地验证。
- ⚠️ **旧路径已失效**：`https://www.shfe.com.cn/data/dailydata/kx/kx20260924.dat` 实测 **404**，必须用上面的 `tradedata/future/dailydata/` 新路径。
- 非交易日请求会 404；建议按交易日历回溯最近一个交易日。

## 12.7 失败与受限记录（避免重复踩坑）

| 端点 | 结果 | 原因 |
|---|---|---|
| `data-asg.goldprice.org/dbXRates/USD` | 403 | 需带 `User-Agent`（本会话 fetch 工具不支持自定义请求头） |
| `query1.finance.yahoo.com/v8/finance/chart/GC=F` | 403 | Yahoo 自 2021-11 起停止中国大陆服务 |
| `stooq.com/q/l/?s=xauusd&…csv` | 404 | 路径/符号已变更 |
| `api.metals.live/v1/spot` | 连接失败 | 服务疑似下线 |
| `data.nasdaq.com/api/v3/datasets/LBMA/GOLD.json` | 403 | 需 API Key |
| `api.exchangerate.host/latest?base=XAU` | 101 | 已改为强制 `access_key` |
| Alpha Vantage `CURRENCY_EXCHANGE_RATE`（`apikey=demo`） | 提示需 Key | demo 额度不覆盖 XAU |
| `api.binance.com` / `api.coingecko.com` / `api.kraken.com`（代币化黄金 PAXG/XAUT） | 连接失败 | 本会话网络环境不可达 |
| `www.okx.com/api/v5/market/ticker` | 拒绝 | 被判定解析到非公网 IP |

## 注意事项

1. **汇率决定换算可信度**：CFETS 中间价（12.1）与 ECB 市场汇率（12.3）实测相差约 0.54%，折算到 4274 美元/盎司上相差约 **5 元/克**。境内对比用 12.1，跨境估值用 12.3，别混用。
2. NBP（12.2）是**每克**报价，不要重复除 31.1034768。
3. fawazahmed（12.4）是"以基准金属计价"的**交叉表**，取其他金属价要**除**而不是乘。
4. 黄金 ETF（12.5）有折溢价与管理费，只能当代理价；SHFE（12.6）是期货口径，与现货有基差。
5. 以上全部免鉴权，但均无 SLA、无官方 API 文档；生产环境务必保留多源降级。
