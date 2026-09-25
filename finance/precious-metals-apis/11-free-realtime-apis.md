# 11 · 免鉴权实时贵金属接口（gold-api.com / Swissquote / goldprice.dev）

## 渠道概况

| 项目 | gold-api.com | Swissquote 公共报价 | goldprice.dev |
|---|---|---|---|
| 主机 | `api.gold-api.com` | `forex-data-feed.swissquote.com` | `api.goldprice.dev` |
| 性质 | 商业免费（无需注册） | 瑞士持牌银行公开报价页接口 | 商业（免费层 + 免鉴权端点） |
| 鉴权 | 无 | 无 | **部分端点无**，其余需 `Authorization: Bearer ga_live_…` |
| 实时性 | 秒级 | 实时（银行 BBO） | 实时 |
| 覆盖 | XAU / XAG（实测） | XAU / XPT / XPD（实测），XAG 未测 | 金/银/铜、31 币种、分国别实物金 |
| 计价 | 仅 USD（**不支持币种参数**） | USD | 多币种（含 CNY） |

> 三家共同价值：**不需要 Key、不需要请求头**，可直接作为 03/04 号文档（腾讯/东财）的交叉校验源；其中 Swissquote 是本次实测中**唯一免费提供铂、钯实时价**的渠道，填补了 03 号文档"`hf_PA`/`hf_PL` 代码未探明"的空白。

## 11.1 gold-api.com

### 请求

```http
GET https://api.gold-api.com/price/{symbol}
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `symbol`（path） | ✅ | `XAU`（金）、`XAG`（银）实测有效 |

### 响应

```json
{"currency":"USD","currencySymbol":"$","exchangeRate":1.0,"name":"Gold",
 "price":4274.299805,"symbol":"XAU",
 "updatedAt":"2026-09-25T05:48:27Z","updatedAtReadable":"a few seconds ago"}
```

| 字段 | 含义 |
|---|---|
| `price` | 最新价（USD/盎司） |
| `name` / `symbol` | 品种名 / 符号 |
| `currency` / `currencySymbol` / `exchangeRate` | 固定 USD / `$` / 1.0 |
| `updatedAt` | ISO 8601 行情时间（UTC） |
| `updatedAtReadable` | 人类可读相对时间 |

### 实测快照（2026-09-25）

| 品种 | price | updatedAt |
|---|---|---|
| XAU | **4274.299805** | 2026-09-25T05:48:27Z |
| XAG | **63.868999** | 2026-09-25T05:49:57Z |

### 坑

- `GET /price/XAU?currency=CNY` → **404** `{"error": "Symbol not found"}`：**不支持币种参数**，人民币价自行用 README 的换算公式处理。
- 未提供历史、未提供买卖价；`XPT`/`XPD` 是否支持未实测。
- 响应时间戳是"行情时间"，与请求时间同分钟，可放心当实时源。

## 11.2 Swissquote 公共报价（免费铂/钯实时价）

### 请求

```http
GET https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/{PAIR}
```

| PAIR | 品种 | 实测 |
|---|---|---|
| `XAU/USD` | 伦敦金 | ✅ |
| `XPT/USD` | 铂金 | ✅ |
| `XPD/USD` | 钯金 | ✅ |
| `XAG/USD` | 白银 | ⚠️ 未实测 |

### 响应

返回**数组**（实测 3 个报价平台），每个元素：

```json
[{"topo": {"platform": "SwissquoteCapitalMarkets", "server": "Live7"},
  "spreadProfilePrices": [
    {"spreadProfile": "premium", "bidSpread": 25.40, "askSpread": 25.40, "bid": 4271.571, "ask": 4272.229},
    {"spreadProfile": "prime",   "bidSpread": 24.40, "askSpread": 24.40, "bid": 4271.581, "ask": 4272.219},
    {"spreadProfile": "elite",   "bidSpread": 17.70, "askSpread": 17.70, "bid": 4271.648, "ask": 4272.152}
  ],
  "ts": 1790315336492}]
```

| 字段 | 含义 |
|---|---|
| `topo.platform` / `topo.server` | 报价平台（SwissquoteLtd / AT / SwissquoteCapitalMarkets）与撮合实例 |
| `spreadProfile` | 账户档位：standard / premium / prime / elite |
| `bidSpread` / `askSpread` | **点差（点），不是价格** |
| `bid` / `ask` | 买卖价（USD/盎司） |
| `ts` | epoch **毫秒**（实测 `1790315336492` → 2026-09-25 05:48:56 UTC） |

**取价建议**：跨 3 个平台 × 各档位取 `bid`/`ask` 的中位数；或固定用 `premium` 档（实测三平台 premium 档几乎完全一致，差异 < 0.1 美元）。

### 实测快照（2026-09-25 05:48–05:49 UTC，premium 档）

| 品种 | bid | ask | 折合 ￥/克（CFETS 中间价口径，系数 0.216982） |
|---|---|---|---|
| XAU/USD | 4271.571 | 4272.229 | **926.85 – 927.00** |
| XPT/USD | 1748.769 | 1751.591 | **379.45 – 380.06** |
| XPD/USD | 1257.351 | 1260.999 | **272.82 – 273.61** |

## 11.3 goldprice.dev

### 免鉴权端点（无需任何 Key）

| 端点 | 用途 | 实测 |
|---|---|---|
| `GET /v1/carat?currency={CCY}` | 按成色（24K→10K）的**元/克**价 | ✅ |
| `GET /v1/convert?from=XAU&to={CCY}&amount=1&unit=oz` | 金属↔货币↔单位换算 | ✅ |
| `GET /v1/status` | 上游抓取健康度（含各数据源新鲜度） | ✅ |
| `GET /v1/prices/divergence?threshold=50` | 跨源价差告警 | ⚠️ 文档未实测 |
| `GET /v1/metadata/tiers` | 套餐目录 | ⚠️ 文档未实测 |

实测报文：

```json
GET https://api.goldprice.dev/v1/carat?currency=CNY
{"currency":"CNY","timestamp":"2026-09-25T05:50:02.137951Z",
 "price_gram_24k":"921.97","price_gram_22k":"845.14","price_gram_21k":"806.72",
 "price_gram_20k":"768.31","price_gram_18k":"691.48","price_gram_16k":"614.64",
 "price_gram_14k":"537.81","price_gram_10k":"384.15"}

GET https://api.goldprice.dev/v1/convert?from=XAU&to=CNY&amount=1&unit=oz
{"from":"XAU","to":"CNY","amount":"1.0","rate":"28676.375788815","result":"28676.38",
 "unit":"oz","timestamp":"2026-09-25T05:50:02.137951Z"}
```

- 价格均为**字符串**，请用 `Decimal` 解析，勿直接做浮点运算。
- `/v1/carat` 一次给出"元/克 × 成色"，是国内零售、回收、金饰折算场景**最省事的免鉴权来源**。

### 需鉴权端点（`Authorization: Bearer ga_live_…`）

`/v1/prices?symbol=XAU-USD-SPOT`、`/v1/spot/{symbol}`、`/v1/bars`（OHLCV，1m–1d）、`/v1/bars/latest`、`/v1/settlements`、`/v1/forward-view/{asset}`、`/v1/physical/{country}`、`/v1/download`（Parquet/CSV 批量）。

免费层（需注册）：**30 次/分、1000 次/月、仅 XAU、历史 30 天**；付费档见官网 pricing。

### 交叉验证线索

其 `/v1/status` 会暴露上游数据源名与新鲜度，实测包含 `wgc-spot`（即 **02 号文档的 WGC fsapi**）、`yahoo-futures`、`frankfurter-fx`、`physical-cn-sge` 等。也就是说：**goldprice.dev 自己就在消费本目录 02 号文档的接口**——当你的 WGC 取数异常时，可用它的 `/v1/status` 反向确认是上游挂了还是自己网络问题。

## 多源交叉验证（2026-09-25 05:48–05:50 UTC）

| 来源 | XAU/USD |
|---|---|
| gold-api.com | 4274.30 |
| 腾讯 `hf_XAU`（03 号文档） | 4273.02 |
| Swissquote（买卖中间价） | 4271.90 |
| goldprice.dev（由 CNY 反推） | 4271.9 |
| **极差** | **≈2.7 美元/盎司（0.06%）** |

四源在同一分钟收敛在 0.06% 以内 → 可作为上线前的常规自检基线。

## 代码示例

```python
import requests, statistics

# 1) gold-api.com
g = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
print("gold-api XAU", g["price"], g["updatedAt"])

# 2) Swissquote：跨平台取中位数
sq = requests.get("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", timeout=10).json()
bids = [p["bid"] for s in sq for p in s["spreadProfilePrices"] if p["spreadProfile"] == "premium"]
asks = [p["ask"] for s in sq for p in s["spreadProfilePrices"] if p["spreadProfile"] == "premium"]
print("Swissquote XAU", round(statistics.median(bids), 3), "/", round(statistics.median(asks), 3))

# 3) goldprice.dev 免鉴权：直接拿元/克
c = requests.get("https://api.goldprice.dev/v1/carat", params={"currency": "CNY"}, timeout=10).json()
print("24K", c["price_gram_24k"], "元/克")

# 4) 统一换算（双汇率口径见 README）
OZT = 31.1034768
for name, rate in (("CFETS 中间价", 6.7489), ("ECB 市场汇率", 6.7126)):
    print(name, round(g["price"] * rate / OZT, 2), "元/克")
```

```powershell
(Invoke-RestMethod 'https://api.gold-api.com/price/XAU').price
(Invoke-RestMethod 'https://api.goldprice.dev/v1/carat?currency=CNY').price_gram_24k
```

## 注意事项

1. 三家都不需要 Key，但都**没有 SLA**：gold-api.com 与 goldprice.dev 是商业公司（免费层配额与条款可能随时调整），Swissquote 是银行公开报价页接口（字段可能随前端改版变动）。
2. 上线前务必做一次"同刻多源比对"（本会话四源极差 2.7 美元）；差异突然放大说明某一源已异常。
3. **CORS 均未实测**；浏览器前端直连大概率受限，建议经后端代理。
4. goldprice.dev 的 CNY 报价使用**市场汇率**，与境内 CFETS 中间价口径相差约 0.5%（折算到金价约 4–5 元/克），不要当作境内基准价（详见 README「统一换算公式与双汇率口径」）。
5. 本目录 08/09 号文档（GoldAPI.io / Metals.dev）为**需注册 Key** 的商业渠道；本文件收录的是**免 Key** 渠道，二者定位不同、可互为备份。
