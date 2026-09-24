# 07 · open.er-api.com（免费汇率 API，用于 ￥/克 换算）

## 渠道概况

| 项目 | 内容 |
|---|---|
| 提供方 | open.er-api.com（开放汇率项目） |
| 数据源 | 欧洲央行（ECB）每日参考汇率等公开来源 |
| 官方程度 | 公开免费服务（非人民币官方中间价） |
| 鉴权 | 无（免费层） |
| 更新频率 | 每日更新 |
| 覆盖 | 160+ 货币对，以 USD 等为基准 |
| 作用 | 把美元/盎司贵金属价换算为人民币/克 |

## 请求

GET https://open.er-api.com/v6/latest/{base}

| 参数 | 必填 | 说明 |
|---|---|---|
| base（path） | 是 | 三字母基准货币码，如 USD |
| 请求头 | 否 | 无要求 |

其他版本：/v6/latest/USD（全部货币）、/v6/latest/USD/CNY（单货币对，路径带目标货币）。

## 响应格式

{
  "result": "success",
  "provider": "https://www.exchangerate-api.com",
  "documentation": "https://www.exchangerate-api.com/docs/free",
  "terms_of_use": "https://www.exchangerate-api.com/terms",
  "time_last_update_unix": 1787788952,
  "time_last_update_utc": "Sat, 05 Sep 2026 00:02:32 +0000",
  "time_next_update_unix": 1787875352,
  "time_next_update_utc": "Sun, 06 Sep 2026 00:02:32 +0000",
  "time_eol_unix": 0,
  "base_code": "USD",
  "rates": {
    "USD": 1,
    "CNY": 6.728858,
    "GBP": 0.739612,
    "EUR": 0.861117,
    "...": "..."
  }
}

| 字段 | 含义 |
|---|---|
| rates | 各货币兑基准货币汇率（rates.CNY 即 USD→CNY） |
| time_last_update_utc | 汇率更新时刻 |
| time_next_update_utc | 下次更新时刻 |
| result | success / error（失败附 error-type） |

## 实测快照（2026-09-05 会话）

USD→CNY = 6.728858
USD→GBP = 0.739612
USD→EUR = 0.861117
更新时间: 2026-09-05 00:02 UTC

## 贵金属换算公式

元/克 = 美元/盎司 × USDCNY ÷ 31.1034768

- 1 金衡盎司（oz t）= 31.1034768 克（金、银、铂、钯报价均用金衡盎司）；
- 系数（2026-09-05 汇率）= 6.728858 ÷ 31.1034768 ≈ 0.216338；
- 例：伦敦金 4415.40 USD/oz → 4415.40 × 0.216338 = 955.22 元/克。

## 代码示例

import requests

j = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10).json()
usdcny = j["rates"]["CNY"]
OZT = 31.1034768

def to_cny_per_gram(usd_per_oz):
    return usd_per_oz * usdcny / OZT

print("USD/CNY:", usdcny, "| 4415.40 USD/oz =", round(to_cny_per_gram(4415.40), 2), "元/克")

## 注意事项

1. 人民币官方口径：国家层面以中国外汇交易中心（CFETS）每日 9:15 发布的中间价为准（本服务为市场参考价，两者可能有数点差异；贵金属换算影响 <1 元/克）。
2. 汇率每日更新一次，日内剧烈波动时换算值偏旧；对精度敏感的场景（如交易）建议用银行/券商实时牌价（新浪 USDCNY 延迟约 10–15 分钟，见 05 号文档）。
3. 免费层有调用频率限制（公开口径约每月 1,500 次左右，以官网 terms 为准）；商业高并发需付费版。
4. 与贵金属 API 组合时注意两边的数据时点对齐（行情是准实时的、汇率是日更的）。
