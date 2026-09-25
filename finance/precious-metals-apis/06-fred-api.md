# 06 · FRED API（圣路易斯联邦储备银行）

## 渠道概况

| 项目 | 内容 |
|---|---|
| 机构 | Federal Reserve Bank of St. Louis（圣路易斯联储） |
| 主机 | api.stlouisfed.org（API）/ fred.stlouisfed.org（网站与 CSV） |
| 官方程度 | ★★★★★ 官方经济数据库（FRED） |
| 鉴权 | 需要免费 API Key |
| 更新频率 | 日更 |
| 与贵金属的关系 | 曾镜像 LBMA 定盘序列（旧序列号现已失效，见实测记录） |

## 获取 API Key（免费）

1. 打开 https://fred.stlouisfed.org/docs/api/api_key.html
2. 注册免费账户，在 My Account → API Keys 生成；
3. Key 通过 query 参数 api_key 传递（无请求头）。

## 端点

### 序列观测值（核心端点）

GET https://api.stlouisfed.org/fred/series/observations?series_id={ID}&api_key={KEY}&file_type=json

| 参数 | 必填 | 说明 |
|---|---|---|
| series_id | 是 | FRED 序列号，站内搜索获得 |
| api_key | 是 | 免费 Key |
| file_type | 否 | json（默认）或 xml |
| realtime_start / realtime_end | 否 | 数据版本时间范围 YYYY-MM-DD |
| observation_start / observation_end | 否 | 观测日期范围 |
| limit | 否 | 返回条数上限（默认 100000，最大 100000） |
| offset | 否 | 分页偏移 |
| sort_order | 否 | asc（默认）/ desc |
| units | 否 | 单位换算 lin/chg/ch1/pch/pc1/pca/cch/cca/cabs |
| frequency | 否 | d/w/bw/m/q/sa/a 频率聚合 |
| aggregation_method | 否 | avg/sum/eop |
| output_type | 否 | 1–4 |
| vintage_dates | 否 | 数据快照日期 |

其他端点：/fred/series（元数据）、/fred/series/search?search_text=（搜索序列号用）、/fred/series/categories、/fred/releases、/fred/sources 等。

### 免 Key 的 CSV 端点（网站自用）

GET https://fred.stlouisfed.org/graph/fredgraph.csv?id={ID}&cosd={YYYY-MM-DD}

- 无需 Key；参数 id 序列号、cosd 起始观测日（coed 结束日）；
- 返回 text/csv（本会话工具拒绝解码 CSV，程序内可直接读取）。

## 响应格式（observations）

{
  "realtime_start": "2026-09-04",
  "realtime_end": "2026-09-04",
  "observation_start": "2016-01-01",
  "observation_end": "2026-09-04",
  "units": "U.S. Dollars per Troy Ounce",
  "output_type": 1,
  "file_type": "json",
  "order_by": "observation_date",
  "sort_order": "asc",
  "count": 2778,
  "offset": 0,
  "limit": 100000,
  "observations": [
    {"realtime_start": "2026-09-04", "realtime_end": "2026-09-04", "date": "2016-01-04", "value": "1078.20"},
    {"realtime_start": "2026-09-04", "realtime_end": "2026-09-04", "date": "2026-09-04", "value": "4415.40"}
  ]
}

value 为字符串，缺失时为 "."。

## 实测记录（2026-09-05 会话）

1. 无 Key 请求（验证端点存活）：
   GET https://api.stlouisfed.org/fred/series/observations?series_id=GOLDPMGBD228NLBM&file_type=json
   → HTTP 400：
   {"error_code":400,"error_message":"Bad Request.  Variable api_key is not set.  Read https://fred.stlouisfed.org/docs/api/api_key.html for more information."}
   ✅ 端点本身正常，仅缺 Key。

2. 旧 LBMA 序列号全部 404（fredgraph.csv 实测）：
   GOLDPMGBD228NLBM（伦敦金 PM）、SLVPMGBD228NLBM（伦敦银）、PLTMGBD228NLBM（铂）、PALLPMGBD228NLBM（钯）→ 均返回 404 错误页。
   ❌ 结论：这些社区流传的 LBMA 序列号已停更/失效，不能直接用。

3. 对照序列 DGS10（10 年期美债收益率）→ 返回正常 CSV（application/csv），证明 CSV 端点本身可用、失效的只是 LBMA 序列号。

4. 正确姿势：用 /fred/series/search?search_text=gold+fixing&api_key=KEY 或 FRED 网站搜索现役序列号（搜索词如 "LBMA gold"、"gold fixing price"），再调用。

## 代码示例

```python
import requests

KEY = "你的免费KEY"
# 1) 搜索现役序列号
r = requests.get("https://api.stlouisfed.org/fred/series/search",
                 params={"search_text": "LBMA gold price", "api_key": KEY}).json()
for s in r["seriess"][:5]:
    print(s["id"], "-", s["title"])
# 2) 取观测值
sid = "GOLDPMGBD228NLBM"   # 替换为搜索到的现役 ID
r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                 params={"series_id": sid, "api_key": KEY, "file_type": "json",
                         "sort_order": "desc", "limit": 5}).json()
for o in r["observations"]:
    print(o["date"], o["value"])
```

## 注意事项

1. 旧 LBMA 序列号已失效（实测），必须先搜索现役序列号；
2. 免费 Key 有速率限制（约 120 次/分钟，公开资料口径）；
3. 数据为日频官方统计口径，非实时行情；
4. 人民币金价：FRED 无 SGE 数据，用 WGC（02 号文档）；
5. 若只需 LBMA 最新定盘，直接用 LBMA 官方 JSON（01）或 WGC（02）更简单。
