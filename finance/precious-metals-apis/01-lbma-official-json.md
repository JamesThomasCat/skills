# 01 · LBMA 官方 JSON（伦敦金银市场协会定盘价）

## 渠道概况

| 项目 | 内容 |
|---|---|
| 机构 | London Bullion Market Association（伦敦金银市场协会） |
| 定价计算 | ICE Benchmark Administration（洲际交易所基准管理公司）公开竞价产生 |
| 官方程度 | ★★★★★ 全球金价基准的官方发布方 |
| 鉴权 | 无（公开静态 JSON 文件） |
| 更新频率 | 每日 1–2 次定盘 |
| 覆盖品种 | 金、银、铂、钯 |
| 计价货币 | USD、GBP、EUR（每文件固定三列） |
| 起始历史 | 金/银 1968 年，铂/钯 1990 年 |
| 服务器 | Apache/2.4.68 (Debian)，主机 `prices.lbma.org.uk` |

## 定盘时点（伦敦时间）

| 品种 | AM 定盘 | PM 定盘 |
|---|---|---|
| 黄金（LBMA Gold Price） | 10:30 | 15:00 |
| 铂金（LBMA Platinum Price） | 09:45 | 14:00 |
| 钯金（LBMA Palladium Price） | 09:45 | 14:00 |
| 白银（LBMA Silver Price） | 12:00（每日仅一次） | — |

> 北京时间换算：伦敦 10:30 ≈ 北京 17:30（夏令时）/ 18:30（冬令时）。
> 2026-09-05 北京上午 10:16 时，伦敦为 03:16，当日上午定盘尚未产生，最新可查为 2026-09-04 的数据。

## 请求

```http
GET https://prices.lbma.org.uk/json/{文件名}.json
```

- **方法**：GET
- **请求头**：无要求
- **查询参数**：无。实测 6 种参数（`?start=`、`?from=`、`?date=`、`?limit=`、`?days=`、`?range=`）**全部被忽略**，返回内容不变（静态文件，Apache 直出）。
- **目录列表**：`GET https://prices.lbma.org.uk/json/` → **403 Forbidden**（无索引页，文件名需提前知道）。

### 文件名枚举（7 个有效端点，实测）

| 文件名 | 内容 | 实测首条 | 首条起始日期 |
|---|---|---|---|
| `gold_am.json` | 伦敦金上午定盘 | `[35.18,14.64,null]` | 1968-01-02 |
| `gold_pm.json` | 伦敦金下午定盘 | `[37.7,15.68,null]` | 1968-04-01 |
| `silver.json` | 伦敦银定盘（单次，不分 AM/PM） | `[2.173,0.904,null]` | 1968-01-02 |
| `platinum_am.json` | 铂金上午定盘 | `[471,289.65,null]` | 1990-04-02 |
| `platinum_pm.json` | 铂金下午定盘 | `[470.5,289.45,null]` | 1990-04-02 |
| `palladium_am.json` | 钯金上午定盘 | `[128,78.7,null]` | 1990-04-02 |
| `palladium_pm.json` | 钯金下午定盘 | `[127.65,78.55,null]` | 1990-04-02 |

**404 实测**：`silver_am.json`、`silver_pm.json`、`lbma_gold_am.json`、`gold_pm_latest.json`、`latest.json`、`lbma_gold.json`、`lbma_gold_am.json` 等猜测均 404。白银不区分 AM/PM。

## 响应格式

内容为**单行 JSON 数组**，元素按日期升序排列，每个元素：

```json
{"is_cms_locked": 0, "d": "1968-01-02", "v": [35.18, 14.64, null]}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `d` | string | 定盘日期，格式 `YYYY-MM-DD` |
| `v` | number[3] | 价格三元组，固定顺序：**[美元, 英镑, 欧元]** |
| `v[2]` | number\|null | 早期欧元未诞生/未启用时为 `null` |
| `is_cms_locked` | 0/1 | 后台内容锁定标记，对使用者无意义 |

**最新定盘价 = 数组最后一个元素的 `v` 值。** 数组按日期升序，末尾即最新。

### 数据体量与截断问题（实测记录）

- `gold_pm.json` 全量 > 100,000 字符（约 57 年 × 250 交易日 ≈ 1.4 万+ 条 × ~65 字节）；
- 本会话的抓取工具单次响应上限 100,000 字符，**只能拿到文件头部，读不到末尾**，`JSON.parse` 会因截断报 `Unterminated string`；
- 尝试过的代理均失败：allorigins/codetabs → 522（被 Cloudflare 拦）、corsproxy.io → 需要 Key、cors.lol → 限流、corsfix → 只允许浏览器、r.jina.ai → 网络失败；
- **结论：这类大文件必须在本地（或自有服务器）完整下载后取最后一条**，示例见下。

## 实测快照（2026-09-05 会话）

- 直接读尾部失败，最新定盘值经 **WGC 官方 API 同源数据**（见 02 号文档）获得：
  - 伦敦金 AM 定盘 2026-09-04：**4466.25 USD**（GBP 3301.90 / EUR 3842.76）
  - 伦敦金 PM 定盘 2026-09-04：**4415.40 USD**（GBP 3269.16 / EUR 3803.43）
- 白银/铂/钯最新定盘：本会话未能从官方文件尾部读取；在本地执行下方命令即可得到。

## 代码示例

### PowerShell（一条命令取最新定盘）

```powershell
# 黄金 PM 最新定盘（返回对象：d 日期, v 三元组）
(Invoke-RestMethod 'https://prices.lbma.org.uk/json/gold_pm.json')[-1]

# 白银 / 铂 / 钯
(Invoke-RestMethod 'https://prices.lbma.org.uk/json/silver.json')[-1]
(Invoke-RestMethod 'https://prices.lbma.org.uk/json/platinum_am.json')[-1]
(Invoke-RestMethod 'https://prices.lbma.org.uk/json/palladium_am.json')[-1]
```

### Python

```python
import requests, json

url = "https://prices.lbma.org.uk/json/gold_pm.json"
data = requests.get(url, timeout=30).json()   # 全量 ~1MB 内存，可接受
latest = data[-1]
print(latest["d"], "USD:", latest["v"][0], "GBP:", latest["v"][1], "EUR:", latest["v"][2])
```

### curl

```bash
curl -s https://prices.lbma.org.uk/json/gold_pm.json | tail -c 200   # 看末尾片段
```

## 注意事项

1. **非实时**：这是每日定盘基准价，不是连续行情；要看实时价用腾讯/东财（03/04 号文档）。
2. **时差**：定盘结果在伦敦定盘结束后才写入文件，中国用户通常当天傍晚/晚上才能拿到当日值。
3. **官方但无 API 文档**：端点长期稳定（文件名多年未变），但属于"约定俗成的公开文件"，LBMA 未承诺 SLA；网页上的正式入口是 [LBMA Precious Metal Prices](https://www.lbma.org.uk/prices-and-data/precious-metal-prices) 页面的图表与下载（XLSX）。
4. **CORS**：文件未带跨域头，浏览器前端直接 fetch 大概率受限，需经后端代理。
5. **同源替代**：FRED（06 号文档）曾镜像 LBMA 序列，但旧序列号已失效；WGC API（02 号文档）当前可提供同源最新定盘；GoldAPI.io 的 `/api/lbma/{metal}/{date}` 端点（08 号文档）也提供 LBMA 定盘。
