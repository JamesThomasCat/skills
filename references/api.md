# Gitee API 参考（本 skill 用到的接口）

Base：`https://gitee.com/api/v5`  
鉴权：`Authorization: Bearer <token>`，或查询参数 `access_token`。永远不要打印 token。读取顺序与落地（环境变量 / `.env` / 会话级）见 [token.md](token.md)。

Open API 文档：https://gitee.com/api/v5/swagger ，机器可读规范：https://gitee.com/api/v5/swagger_doc.json

脚本与接口（只跑左列入口；不要按右列路径自己发 HTTP。`_gitee_http.py` 不是入口）：

| 脚本 | 调用 |
|------|------|
| `list_users.py` | collaborators + contributors（`type=authors`） |
| `list_commits.py` | commits 列表 |
| `commit_detail.py` | commits/{sha} |
| `work_by_person.py` | 上面三类都拉，并按人分组 |
| `daily_report.py` | 企业仓库列表（404 才回退组织）+ 成员/贡献者过滤 + 全部分支 commits（按日、按人） |

## 仓库成员

`GET /repos/{owner}/{repo}/collaborators`

- 分页：`page`、`per_page`（最大 100）
- 返回 `ProjectMember`：`id`、`login`、`name`、`permissions`、`member_role`、`html_url`
- 无权限时常 403。公开仓库无 token 也可能失败。

相关：

- `GET /repos/{owner}/{repo}/collaborators/{username}` — 是否为成员
- `GET /repos/{owner}/{repo}/collaborators/{username}/permission` — 权限

## 贡献者

`GET /repos/{owner}/{repo}/contributors`

- 查询：`type=authors` | `committers`（本 skill 默认 `authors`）
- 返回：`name`、`email`、`contributions`
- 一般无 `login`，靠 email/name 和 commit 作者对齐

## 提交列表

`GET /repos/{owner}/{repo}/commits`

| 参数 | 含义 |
|------|------|
| `sha` | 分支名或起始 SHA，默认仓库默认分支 |
| `path` | 只含该文件的提交 |
| `author` | 作者邮箱或 login |
| `since` / `until` | ISO 8601 |
| `page` / `per_page` | 分页，最大 100 |

列表项里 **message 在 `commit.message`**，不是顶层字符串。另有 `sha`、`author.login`、`commit.author.email` / `name` / `date`。列表接口 **没有** `files` / `patch`。

## 提交详情（代码）

`GET /repos/{owner}/{repo}/commits/{sha}`

- `sha` 可以是完整 SHA 或分支名
- `commit.message`：提交说明
- `files[]`：`filename`、`status`、`additions`、`deletions`、`changes`、`patch`、`truncated`
- `stats`：`additions` / `deletions` / `total`
- 顶层 `truncated`：文件列表被截断

需要该提交时刻的完整文件：

- `GET /repos/{owner}/{repo}/contents/{path}?ref={sha}`（content 多为 Base64）
- `GET /repos/{owner}/{repo}/raw/{path}?ref={sha}`

## 对比（两点之间的 diff，不能替代全量 commit 列表）

`GET /repos/{owner}/{repo}/compare/{base}...{head}`

- `base` / `head`：分支、Tag 或 SHA
- `commits[].commit.message`（最多 100 条 commit）
- `files[].patch`

单条 commit 且已知父 SHA 时，可用 `base=parent`、`head=sha` 作为详情接口的备选。

## 企业仓库（工作日报默认）

`GET /enterprises/{enterprise}/repos`

- 查询：`type=all`（本 skill 日报默认）、`page` / `per_page`
- 仓库路径用 `path` 或 `name`，命名空间是 `owner.login`
- 日报按人过滤时：先用 login / 姓名 / 邮箱对上成员或贡献者，再用这些身份字段（含邮箱）去对当天 commit。Git `author.name` 可以和 Gitee 显示名不同，只要邮箱相同就算同一个人。
- `testdaily` 是企业空间，日报**先走这条**，不要先打组织接口

## 组织仓库

`GET /orgs/{org}/repos`

- 查询：`type=all`、`page` / `per_page`
- 仅当企业仓库接口 **HTTP 404**（该 path 不是企业）时，`daily_report.py` 才回退到这里
- 401/403 等鉴权错误不回退

## 分支

`GET /repos/{owner}/{repo}/branches`

- 分页：`page`、`per_page`
- 返回 `name`

工作日报要对每个分支带 `sha=<branch>` 调提交列表，再按 SHA 去重。

