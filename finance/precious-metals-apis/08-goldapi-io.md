# 08 · GoldAPI.io（商业实时贵金属 API，免费层）

## 渠道概况

| 项目 | 内容 |
|---|---|
| 提供方 | GoldAPI.io（https://www.goldapi.io） |
| 官方程度 | 商业第三方（数据来自权威行情源） |
| 鉴权 | 请求头 x-access-token: {API_KEY}（免费注册获取） |
| 实时性 | 实时现货价 + 历史 / LBMA 定盘 |
| 币种 | 72 种（含 CNY、BTC） |
| 文档 | 官方 llms.txt、OpenAPI（本文件全部参数均解析自官方 OpenAPI） |

## 认证

- 注册：https://www.goldapi.io/dashboard 获取 API Key；
- 所有请求携带请求头：x-access-token: YOUR_API_KEY；
- 免费层额度以官网 pricing 为准（社区常见口径约 100 次/月）。

## 端点总表

| 端点 | 说明 |
|---|---|
| GET /api/price/{metal}/{currency} | 最新现货价 |
| GET /api/price/{metal}/{currency}/{date} | 指定日期历史价 |
| GET /api/history/{metal}/{currency}?from=&to= | 历史区间（≤90 天） |
| GET /api/rates/{base}/{quote} | 货币对汇率 |
| GET /api/lbma/{metal}/{date} | LBMA 官方定盘价 |
| GET /api/stat | 账户配额统计 |
| GET /api/status | 服务状态 |
| GET /api/currencies、GET /api/metals | 当前支持的币种/金属×货币矩阵 |

## 参数详解

### path 参数

| 参数 | 必填 | 枚举/格式 |
|---|---|---|
| metal | 是 | XAU 金、XAG 银、XPT 铂、XPD 钯 |
| currency | 是 | 三字母 ISO 码（下表） |
| date | 是（含日期端点） | YYYY-MM-DD（兼容 YYYYMMDD） |
| base / quote | 是（rates 端点） | 任意货币码 |

### query 参数（/api/price 系列）

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| melt_price | boolean | true | 是否返回按克/成色（karat）的熔炼金价表 |
| currency_info | boolean | true | 是否返回货币名称与符号信息 |
| purity | boolean | false | 是否返回按成色的纯度比率 |

### query 参数（/api/history）

| 参数 | 必填 | 格式 | 说明 |
|---|---|---|---|
| from | 是 | YYYY-MM-DD（兼容 YYYYMMDD） | 区间起点（含） |
| to | 是 | 同上 | 区间终点（含），区间最长 90 天 |

## 枚举清单

### metal（4 个）

XAU（金）、XAG（银）、XPT（铂）、XPD（钯）

### currency（官方 OpenAPI 枚举，72 个）

AED ARS AUD BDT BGN BHD BOB BRL BTC CAD CHF CLP CNY COP CZK DKK DOP DZD EGP EUR FJD GBP GHS GTQ HKD IDR ILS INR IQD IRR ISK JOD JPY KES KHR KRW KWD LAK LBP LKR MAD MMK MXN MYR NGN NOK NPR NZD OMR PEN PHP PKR PLN PYG QAR RON RUB SAR SEK SGD SYP THB TRY TWD UAH USD UYU UZS VND XAG YER ZAR

> 含 CNY（人民币）与 BTC（比特币计价）；不同金属×货币组合可用性不同，实时矩阵查 /api/currencies 与 /api/metals。

## 响应字段（/api/price，LivePriceResponse）

| 字段 | 含义 |
|---|---|
| price | 最新价 |
| change / change_percent | 涨跌额 / 涨跌幅% |
| bid / ask | 买卖价 |
| open_price / high_price / low_price / prev_close_price | 开/高/低/昨收 |
| open_time | 开盘时间戳 |
| timestamp / datetime | 行情时间 |
| metal / currency / exchange / symbol | 品种/币种/交易所/符号 |
| melt_price_per_gram | 按克熔炼价表（受 melt_price 控制） |
| currency_info | 货币信息对象（受 currency_info 控制） |
| purity | 纯度比率（受 purity 控制） |

### /api/lbma 响应（LbmaResponse）

timestamp, date, metal, currency, exchange, am, pm, price —— 一次拿 LBMA 当日 AM/PM 定盘。

### /api/history 响应（MetalHistoryResponse）

metal, currency, from, to, prices（日期→价格映射）。

### /api/rates 响应（RateResponse）

timestamp, base, quote, exchange, symbol, price, bid, ask。

## 请求示例

```bash
# 最新金价（人民币，精简响应）
curl -H "x-access-token: YOUR_API_KEY" "https://www.goldapi.io/api/price/XAU/CNY?melt_price=false&currency_info=false"

# 指定日期银价
curl -H "x-access-token: YOUR_API_KEY" "https://www.goldapi.io/api/price/XAG/USD/2026-09-04"

# 90 天内金价历史
curl -H "x-access-token: YOUR_API_KEY" "https://www.goldapi.io/api/history/XAU/USD?from=2026-06-05&to=2026-09-05"

# LBMA 定盘（指定日期）
curl -H "x-access-token: YOUR_API_KEY" "https://www.goldapi.io/api/lbma/XAU/2026-09-04"

# 汇率
curl -H "x-access-token: YOUR_API_KEY" "https://www.goldapi.io/api/rates/USD/CNY"
```

## 注意事项

1. 免费层额度很小（约百次/月量级），先跑 /api/stat 确认余额；
2. melt_price / currency_info 默认开，响应偏大，程序化取价建议显式关掉；
3. 官方集成生态：RapidAPI、Postman、Zapier、MCP、WordPress 插件；
4. 商业第三方服务，非交易所官方；历史深度与数据源细节以官网为准；
5. 本会话未实测调用（无 Key），全部参数来自官方 OpenAPI/llms.txt 解析。
