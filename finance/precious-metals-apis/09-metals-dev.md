# 09 · Metals.dev（商业实时金属价格 API，免费层）

## 渠道概况

| 项目 | 内容 |
|---|---|
| 提供方 | Metals.dev（https://metals.dev） |
| 官方程度 | 商业第三方（数据源：LBMA、LME、MCX、IBJA 等权威机构） |
| 鉴权 | query 参数 api_key（区别于其他家的请求头） |
| 实时性 | 实时现货 + 机构价 + 汇率 + 历史（5 年+） |
| Base URL | https://api.metals.dev/v1 |
| 免费层 | 有（额度以官网 pricing 为准） |

> 说明：本文件端点与枚举解析自 api-evangelist 维护的 metals.dev OpenAPI 镜像（2026-08-28 生成，经 jsdelivr 镜像获取；GitHub 直连在本环境被屏蔽）。与官网 docs 可能略有出入，接入前用免费请求验证。

## 认证

- 注册获取 Key（https://metals.dev/sign-up）；
- 所有请求在 URL query 中传 api_key=YOUR_KEY（OpenAPI securitySchemes: apiKey in query）；
- 免费层额度见 /pricing，账户用量查 /v1/usage。

## 端点总表

| 端点 | 用途 | 必填参数 | 可选参数 |
|---|---|---|---|
| GET /v1/latest | 全部金属现价 + 170+ 汇率 | — | currency、unit |
| GET /v1/metal/spot | 单金属现货（价/买卖/高低/涨跌） | metal | currency |
| GET /v1/metal/authority | 权威机构定价 | authority | currency、unit |
| GET /v1/currencies | 汇率换算 | — | base |
| GET /v1/timeseries | 历史日线 | start_date、end_date | — |
| GET /v1/usage | 账户配额 | — | — |

## 参数枚举

### metal（9 种，注意用全名小写，不是 XAU）

| 值 | 品种 | 值 | 品种 |
|---|---|---|---|
| gold | 金 | copper | 铜 |
| silver | 银 | nickel | 镍 |
| platinum | 铂 | lead | 铅 |
| palladium | 钯 | zinc | 锌 |
| aluminum | 铝 | | |

### authority（4 个）

lbma（伦敦金银市场协会）、lme（伦敦金属交易所）、mcx（印度多种商品交易所）、ibja（印度金银珠宝协会）

### unit（4 个）

| 值 | 单位 | 说明 |
|---|---|---|
| toz | 金衡盎司 | 贵金属默认 |
| g | 克 | |
| kg | 千克 | |
| mt | 公吨 | 工业金属默认 |

### currency

三字母 ISO 码，默认 USD（覆盖 170+ 币种，含 CNY）。

### 日期参数（/v1/timeseries）

start_date、end_date：YYYY-MM-DD，单次区间最长 30 天。

## 响应结构

### 公共字段（BaseResponse，所有端点都有）

{"status": "success", "currency": "USD", "unit": "toz", "timestamp": "2026-09-05T02:30:00Z", "error_code": 0, "error_message": ""}

### /v1/latest 特有

{
  "metals": {"gold": 4482.05, "silver": 66.9, "platinum": 0, "palladium": 0, "aluminum": 0, "copper": 0, "nickel": 0, "lead": 0, "zinc": 0},
  "currencies": {"USD": 1, "CNY": 6.72, "EUR": 0.86, "...": "..."}
}

### /v1/metal/spot 特有（rate 对象）

price, ask, bid, high, low, change, change_percent

### /v1/metal/authority 特有

authority（机构名）+ metals（金属→价格映射）

### /v1/timeseries 特有

start_date, end_date, rates（日期→{金属/货币: 价格} 嵌套映射）

### /v1/usage 特有

plan, usage, limit, remaining

## 请求示例

```bash
# 全部现价 + 汇率（人民币、克）
curl "https://api.metals.dev/v1/latest?api_key=YOUR_KEY&currency=CNY&unit=g"

# 黄金现货
curl "https://api.metals.dev/v1/metal/spot?api_key=YOUR_KEY&metal=gold&currency=USD"

# LBMA 机构定价
curl "https://api.metals.dev/v1/metal/authority?api_key=YOUR_KEY&authority=lbma&currency=USD&unit=toz"

# 历史 30 天
curl "https://api.metals.dev/v1/timeseries?api_key=YOUR_KEY&start_date=2026-08-06&end_date=2026-09-05"

# 汇率（美元基准）
curl "https://api.metals.dev/v1/currencies?api_key=YOUR_KEY&base=USD"

# 账户配额
curl "https://api.metals.dev/v1/usage?api_key=YOUR_KEY"
```

## 注意事项

1. api_key 走 query 而非请求头——与 GoldAPI.io 相反，别搞混；
2. 金属用全名（gold）而非 ISO 符号（XAU）——与 GoldAPI.io 相反；
3. /v1/timeseries 单次 ≤30 天，长历史需循环分片请求；
4. 数据源为 LBMA/LME/MCX/IBJA 官方机构，权威性好；
5. 本会话未实测调用（无 Key），规范来自镜像 OpenAPI，接前先用 /v1/usage 验证 Key 与端点；
6. 免费层额度以官网 /pricing 为准（注册后 /v1/usage 可实时查剩余）。
