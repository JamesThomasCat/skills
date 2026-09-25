# 02 · 世界黄金协会（WGC）官方 API fsapi.gold.org

## 渠道概况

| 项目 | 内容 |
|---|---|
| 机构 | World Gold Council（世界黄金协会，黄金行业官方机构） |
| 主机 | `fsapi.gold.org` |
| 官方程度 | ★★★★★ 官方数据服务（其页面 gold.org 直接调用） |
| 鉴权 | 无（公开端点） |
| 更新频率 | 日更（定盘/基准价在当日定盘完成后更新） |
| 数据范围 | 近 3 年（实测 `startDate: 2023-09-04` → `endDate: 2026-09-04`） |
| 数据内容 | LBMA 伦敦金定盘（USD/GBP/EUR）、**上海金人民币基准价**、印度 MCX 卢比价、现货金价 |

## 端点

### 主端点：`/api/goldprice/v13/chart/main`

```http
GET https://fsapi.gold.org/api/goldprice/v13/chart/main
```

- 方法 GET；无请求头、无参数、无鉴权。
- 返回 `chartData` 对象，包含多条序列。

### 辅助端点：`/api/goldprice/v13/chart/price/`

```http
GET https://fsapi.gold.org/api/goldprice/v13/chart/price/
```

- 返回 `chartData.USD` 现货金价序列、`asOfDate`、`breaks`。
- **参数实测**：`?currency=CNY` 与 `?ccy=cny` 均被忽略（返回仍为 USD）。

### 无效路径（404 实测）

`/api/silverprice/v13/chart/main`、`/api/goldprice/v13/chart/silver` 均为 WGC 站点 404 页——白银在 `chart/main` 的 `lme_*` 键下（实测为空对象，见下）。

## 响应格式

### 外层结构

```json
{
  "system": {
    "request_time": "2026-09-05 02:21:07",
    "APIserverHostname": "fsapi.gold.org",
    "protocol": "https",
    "uri": "https://fsapi.gold.org/api/goldprice/v13/chart/main",
    "route": "fsapi.gold.org",
    "cached": false,
    "q": false,
    "params": {},
    "user": null,
    "response_size": 88947,
    "time_start": "2026-09-05 02:21:07",
    "time_stop": "2026-09-05 02:21:07",
    "source": "hapi",
    "time": "0.044 secs",
    "mem_start": 5338720,
    "mem_stop": 7465472,
    "mem_used": "2076.91 KB",
    "size": "86.95 KB"
  },
  "chartData": { ... }
}
```

### chartData 键清单（2026-09-05 实测）

| 键 | 类型 | 内容 | 最新值（2026-09-04） |
|---|---|---|---|
| `lbma_am_usd` / `lbma_pm_usd` | 数组 | 伦敦金定盘，美元/盎司 | AM 4466.25 / PM 4415.40 |
| `lbma_am_gbp` / `lbma_pm_gbp` | 数组 | 同上，英镑/盎司 | AM 3301.90 / PM 3269.16 |
| `lbma_am_eur` / `lbma_pm_eur` | 数组 | 同上，欧元/盎司 | AM 3842.76 / PM 3803.43 |
| `sge_am_cny` / `sge_pm_cny` | 数组 | **上海金基准价，元/克** | 上午 968.30 / 下午 963.44 |
| `mcx_am_inr` / `mcx_pm_inr` | 数组 | 印度 MCX，卢比/10克 | AM 154257 / PM 154425 |
| `lme_AM_usd` / `lme_Midday_usd` / `lme_PM_usd` | 对象 | 白银相关（实测为空对象 `{}`） | — |
| `period` | string | 周期（如 `Daily`） | — |
| `startDate` / `endDate` | string | 数据起止 | 2023-09-04 / 2026-09-04 |
| `asOfDate` | string | 数据截止日 | 2026-09-04 |

### 序列元素格式

```
[epoch毫秒时间戳, 价格]
```

例：`[1786608000000, 4415.4]` → `new Date(1786608000000)` = 2026-09-04。

## 实测记录（2026-09-05 02:21 UTC）

- `chart/main` 响应 88,947 字节，未被截断，JSON 可直接 `JSON.parse`；
- `lme_*` 三个键存在但为空对象（白银数据未在此端点提供）；
- `asOfDate: 2026-09-04`——当日定盘完成后（北京时间晚上）数据才会更新。

## 代码示例

```python
import requests

j = requests.get("https://fsapi.gold.org/api/goldprice/v13/chart/main", timeout=15).json()
cd = j["chartData"]

def last(seq):
    ts, price = seq[-1]
    return price  # 序列末位即最新定盘/基准价

print("LBMA 伦敦金 AM(USD/oz):", last(cd["lbma_am_usd"]))
print("LBMA 伦敦金 PM(USD/oz):", last(cd["lbma_pm_usd"]))
print("上海金 上午基准(元/克):", last(cd["sge_am_cny"]))
print("上海金 下午基准(元/克):", last(cd["sge_pm_cny"]))
print("数据截至:", cd["asOfDate"])
```

```powershell
$j = Invoke-RestMethod 'https://fsapi.gold.org/api/goldprice/v13/chart/main'
$j.chartData.lbma_pm_usd[-1][1]   # 伦敦金 PM 最新美元价
$j.chartData.sge_pm_cny[-1][1]    # 上海金下午基准价（元/克）
```

## 注意事项

1. **这是"上海金"官方人民币价的免费捷径**：`sge_*` 序列即上海黄金交易所基准价（元/克），SGE 官方本身也有两个直出的免费 JSON 端点（分时 + 历史日线），见 10 号文档；本行的 `sge_*` 序列仍是获取"日频基准价"的最省事途径。
2. 数据为**日频定盘/基准价**，不是实时行情。
3. 仅保留近 3 年，更早历史用 LBMA 官方 JSON（01 号文档，1968 年起）。
4. 无官方文档与 SLA，端点路径含版本号（`v13`），升级可能改路径。
5. 白银定盘不在本端点；用 LBMA 官方 `silver.json`（01 号文档）或 metals.dev 的 `authority=lbma`（09 号文档）。
