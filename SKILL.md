---
name: gitee-auto
description: >
  按用户实际要的那一件事拉取 Gitee 数据：仓库成员与贡献者、提交列表、单次 commit
  的 message/diff、按人汇总、或工作日报。用户提到 Gitee/码云、collaborators、
  contributors、commit 列表/详情、按人总结、周报、工作日报、testdaily、今日日报、
  Gitee 私人令牌、GITEE_ACCESS_TOKEN 时使用本 skill。不要默认把几件事一次做完。
  不要用 GitHub API 代替 Gitee。
---

# Gitee 按需采集

不要靠记忆编造提交或文件名。先判断用户要的是下面哪一件，**只跑对应入口脚本**。没有明确要「按人汇总 / 周报 / 谁做了什么」时，不要跑 `work_by_person.py`。用户要「工作日报 / 总结今日工作」时跑 `daily_report.py`，不要跑 `work_by_person.py`。

| 用户要什么 | 脚本 | 不要做 |
|------------|------|--------|
| 成员、贡献者、人员名单 | `scripts/list_users.py` | 不要拉 commits / diff |
| 提交列表、全部 commit | `scripts/list_commits.py` | 不要拉人员，不要逐条 hydrate diff |
| 某个 SHA 的说明和代码改动 | `scripts/commit_detail.py --sha …` | 不要拉全员名单，不要拉仓库历史 |
| 按人汇总、周报、谁改了什么 | `scripts/work_by_person.py` | 这才是唯一会拼人员+提交+详情的入口 |
| 工作日报、总结 xxx 今日工作 | `scripts/daily_report.py` | 不要套按人工作长文；不要先调组织接口再自己改调企业接口；见下方固定样式 |

接口字段见 [references/api.md](references/api.md)。上表「脚本」列才是入口。`scripts/_gitee_http.py` 和 `scripts/test_gitee_http.py` 不是入口，禁止 `import` 或直接运行。表里没有的能力（例如 PR 列表）就停下，说明缺口。

Open API 只给这些入口脚本用。不要你自己 curl / urllib / WebFetch 调 `gitee.com/api/v5`。

## 源文件只读

**使用本 skill ≠ 维护本 skill。** 读说明书、跑现成脚本、把结果交给用户。不要改源文件，也不要在 skill 目录里「顺便」加文件。

源文件指：`SKILL.md`、`scripts/` 下任何 `.py`、`references/`、`.gitignore`。当前工作区即使就是本 skill 仓库，这条仍然成立。

| 可以写 | 不可以写 |
|--------|----------|
| 用户选 1/2 之后，仅通过 `save_token.py` 写 `~/.gitee-auto/env` 或本目录 `.env` | `SKILL.md`、`scripts/*.py`、`references/`、`.gitignore` |
| `--out` 的本次 JSON（不要覆盖上面那些源文件） | 新的 `.py` / `.md`、临时解析脚本、API 摘要、调试笔记 |
| 用户项目目录或系统临时目录里的产出 | 把 skill「补全 / 优化 / 修一下就能跑」 |

入口脚本非 0 退出或抛异常：把命令和错误原文交给用户，**停止**。缺表内入口：同样停止。下列都不算完成任务：

- 改入口脚本、删报错、或「修一下就能跑」
- `import _gitee_http` / 直接跑 `_gitee_http.py`
- 在任意目录（含系统临时目录）写 fetcher 再调 `gitee.com/api/v5`
- WebFetch / curl / urllib 自己拼接口

**例外（必须可观察）：** 用户明确说了「改这个 skill / 修脚本 / 更新说明书」。没这句话就不是例外。

| 借口 | 实际 |
|------|------|
| 脚本报错，改一下就能交差 | 报告错误；改脚本 = 维护 skill |
| 入口挂了，改调 `_gitee_http` | 仍是绕过入口；报告错误并停止 |
| 组织仓库 404，我改调企业 API | 日报脚本已先走企业、仅 404 才回退组织；你只跑入口 |
| 企业仓 owner.login 是个人，我改调 testdaily | 脚本已把企业仓后续 `/repos` 的 owner 写成企业 path；你只跑入口 |
| 先探 testdaily 命名空间类型更稳妥 | 探了就会把 404 说给用户；禁止 |
| Git 作者改名了，我按邮箱重新采集 | 脚本已用成员/贡献者邮箱对齐提交；只跑一次入口 |
| 说明书提到 Open API，我直接请求 | Open API 只给入口脚本；你只跑入口 |
| 临时脚本写在 TEMP，不是改 skill | 仍是凑任务；停下来 |
| 用户只要结果，没有 PR 脚本我就自己拉 | 缺入口 = 缺口；说明没有这项 |
| 当前工作区就是 skill 仓库 | 使用仍只读；工作区位置不是许可 |
| 缺功能，先补个脚本/段落 | 先问用户，未经允许不扩 |
| 写个 `.tmp-*.py` / 摘要方便跑 | 不要落在 skill 目录，也不要用它交差 |
| 我是在优化，不是破坏 | 未经允许的改动就是越权 |

## 开始前

1. 工作日报默认**企业空间** `testdaily`（不是社区组织），不需要单个 `repo`。其他任务向用户确认 `owner` 和 `repo`。可从 `https://gitee.com/{owner}/{repo}` 解析。
2. 按 [Token](#token) 处理鉴权。私有库和**成员列表**缺 token 就停，不要硬跑。公开库只拉 commits 可以无 token。
3. 列表类任务用户没给时间范围时：先问 `since` / `until` / 分支；对方坚持全量再拉，并说明分页上限。
4. 永远不要在命令行或回复里打印 token。不要把 Gitee token 写入 Cursor / Claude / OpenClaw 的 LLM 配置。
5. 按 [源文件只读](#源文件只读) 执行：只跑入口脚本；失败或缺口就停，不要改 skill，不要自己发 HTTP。

鉴权：`Authorization: Bearer <token>`。Base：`https://gitee.com/api/v5`（可用 `GITEE_API_BASE` 覆盖）。读取顺序与落地方式见 [references/token.md](references/token.md)。

在 skill 目录执行脚本。`--out` 指向本次要用的 JSON。不要把 token 写在 `--token` 里；需要时在同一终端设置 `GITEE_ACCESS_TOKEN`。

## Token

脚本自动按顺序读：`--token` → 进程环境变量 `GITEE_ACCESS_TOKEN` → `~/.gitee-auto/env` → 本 skill 的 `.env`。不扫描 `API_KEY` / `ANTHROPIC_AUTH_TOKEN` / `ARK_*`。

缺 token 且当前任务需要它时：**先扫描已有凭据（进程/用户级/系统级环境变量 `GITEE_ACCESS_TOKEN`、`~/.gitee-auto/env`、本 skill 的 `.env`），命中就直接跑脚本（脚本会按上文顺序自动读取），无需询问用户；都没命中再让用户选落地方式、收令牌**。不要自行决定写成环境变量或 `.env`。

申请：https://gitee.com/profile/personal_access_tokens （勾选 `projects`；企业空间日报再勾选 `enterprise`）。

**向用户请求 token 时，必须用下面这段（可微调标点，三项选择不能少、不能改成别的落地点）：**

```
本仓库需要 Gitee 私人令牌才能继续（成员列表 / 私有库几乎必填）。

请先选一种落地方式，再把令牌发给我：

1. 用户级环境变量 GITEE_ACCESS_TOKEN：长期有效；Windows 写入后需重启 Agent 才对所有窗口生效
2. 本 skill 目录 .env：只给 gitee-auto 用，已忽略 git
3. 仅本次会话：当前终端有效，关掉即失效

申请：https://gitee.com/profile/personal_access_tokens （勾选 projects；企业空间日报再勾选 enterprise）

回复示例：「2」然后粘贴令牌；或「先会话级」，再发令牌。
```

收到选择后：

| 用户选 | 你做 |
|--------|------|
| 1 环境变量 | 同一终端设置 `GITEE_ACCESS_TOKEN`（不要回显），再 `python scripts/save_token.py --target env` |
| 2 `.env` | 同样先设环境变量，再 `python scripts/save_token.py --target dotenv` |
| 3 会话级 | 只设当前终端的 `GITEE_ACCESS_TOKEN`，**不要**跑 `save_token.py` |

只发了令牌、没选落地方式：按 **3 会话级** 完成本次请求，并再问要不要改成 1 或 2。`save_token.py` 的 stdout 只有路径和 `token_present`，把路径告诉用户即可。

## 1. 人员名单

```bash
python scripts/list_users.py --owner <owner> --repo <repo> --out users.json
```

两类都要：`collaborators`（login / 姓名 / 权限）和 `contributors`（脚本固定 `type=authors`：姓名 / 邮箱 / contributions）。某接口失败就用已成功的数据，并写明缺口。

输出用简体中文表格，不要套「按人工作」模板。

```markdown
# {owner}/{repo} 仓库人员
## 成员
| login | 姓名 | 角色/权限 |
## 贡献者
| 姓名 | 邮箱 | contributions |
```

## 2. 提交列表

```bash
python scripts/list_commits.py --owner <owner> --repo <repo> --out commits.json
```

常用：`--sha`（分支或起始 SHA）、`--since` / `--until`、`--author`、`--path`、`--max-pages`（每页 100，默认 50）。

列表项的说明在 JSON 的 `message`（来自 API 的 `commit.message`）。**没有** `files` / `patch`。`meta.commits_truncated` 为 true 时加大 `--max-pages` 或收窄时间窗，不要假装覆盖全部历史。

```markdown
# {owner}/{repo} 提交列表
- 范围：分支 / since ~ until / 条数 / 是否截断
| SHA | 作者 | 时间 | message |
```

## 3. 单次（或指定若干次）提交详情

```bash
python scripts/commit_detail.py --owner <owner> --repo <repo> --sha <sha> --out commit.json
```

多个 SHA 就重复 `--sha`。只写这些提交的 message、文件、patch 要点。`files_truncated` / `patch_omitted` 要标明。

```markdown
# 提交 {sha}
- 作者：
- 说明：（原样或扼要）
- 文件：路径 / status / +−
- 改动要点：（根据 patch，不要编）
```

## 4. 按人汇总

只有用户要按人总结时才跑：

```bash
python scripts/work_by_person.py --owner <owner> --repo <repo> --out work.json
```

`--details-limit` 默认 40；`--max-pages` 默认 50。截断时加大参数或收窄窗口。

人员对齐已写在 JSON 的 `people[]`：login → email → name；对不上的单独成组；窗口内零提交的成员在 `zero_commit: true`。总结只用这份 JSON，用简体中文。

```markdown
# {owner}/{repo} 工作总结
## 范围
- 分支 / 时间 / 提交条数 / 已拉详情条数 / 截断或错误
## 按人工作
### {display_name}（@{login} 或邮箱）
- 身份、提交数、主要文件、工作摘要（3–8 句）、代表提交
## 无提交成员
| login | 姓名 | 角色/权限 |
```

多人按提交数降序。没有 diff 的提交只根据 message 写，并注明「未拉取详情」。不要把 merge 机器人或 `Signed-off-by` 当成主要工作。用户如果说的是「工作日报 / 总结」，改走第 5 节，不要用本节长文模板。

## 5. 工作日报

以下说法都走本节，不要走第 4 节：

- 帮我总结 {人} 今日（{YYYY-MM-DD}）的工作日报
- 总结 / 工作日报（且已有该人当天的提交或详情）

含义（必须按此采集，不要只扫一个仓库、不要只扫默认分支）：

1. 企业空间默认 `testdaily`（用户另给空间 path 则用用户的）。`testdaily` 是企业，不是社区组织。
2. 列出该空间下仓库，只保留**贡献者或成员能匹配到该人**的仓库（login / 姓名 / 邮箱）。同邮箱的 Git 作者名（例如贡献者 `meiyanxin`、提交作者 `thoamsmay`）算同一个人。
3. 每个匹配仓库拉取**全部分支**上、该人在该日（Asia/Shanghai `+08:00`）的 commit；同一 SHA 去重。提交过滤要用成员/贡献者上的 login、姓名、**邮箱**，不要只拿用户说的那个名字去对 `commit.author.name`。
4. 用 JSON 里的 `commits` / `commit_details` 归纳事项，禁止编造。

`daily_report.py` 会先请求 `GET /enterprises/{name}/repos`，**仅当该接口 HTTP 404** 时才回退 `GET /orgs/{name}/repos`。不要你先调组织接口、把 404 说给用户、再自己改调企业 API。企业列表里 `owner.login` 常是创建者（例如 `cuizhaoy`），后续 `/repos/{owner}/{repo}` 一律用企业 path（默认 `testdaily`），不要你改成个人 login 或自己重打接口。Git 作者名和查询名不一致时，脚本会用已匹配身份的邮箱对齐，不要你先报「按姓名没匹配上」再按邮箱重跑一遍。

```bash
python scripts/daily_report.py --person <login或姓名> --date YYYY-MM-DD --out daily.json
```

默认 `--concurrency 8`、`--http-timeout 10`（仓库扫描并行，单次 GET 10 秒超时）。`--concurrency 1` 恢复原来的串行循环和 `--sleep` 间隔。

上下文里已经有该人当天的提交详情、用户只说「总结」时：不要重跑全空间扫描，直接按下面样式输出。

**输出必须是这个形状（标题级短语、中文顿号编号）。不要加仓库名、SHA、文件列表、范围说明：**

```
工作日报：
1、AP Student Job Perception
2、AP Student 去答疑前置题目列表
3、保利威加密视频鉴权
```

- 第一行固定为 `工作日报：`
- 同一事项的多条 commit 合并成一条
- 不要把 merge 机器人或纯 `Signed-off-by` 当成条目
- 当天零提交则只写：

```
工作日报：
当天无提交
```

## 不要做的事

- 不要调用 GitHub `api.github.com`。
- 不要用 PR 接口冒充仓库全部 commit。
- 不要把列表接口里的 `commit` 当成字符串；真实字段是 `commit.message`。
- 不要在未分页的情况下声称「全部提交」。
- 不要把「看某个 SHA」做成完整人员报告。
- 不要把「只要名单」顺便拉完全部 commits。
- 不要把「工作日报」做成第 4 节那种按人长文。
- 不要只查默认分支或只查一个仓库来应付 testdaily 日报。
- 不要先请求 `/orgs/testdaily/repos`（或任何 `/orgs/{name}/repos`）再「查命名空间类型」或改调 `/enterprises/{name}/repos`。testdaily 是企业空间；只跑 `daily_report.py`。
- 不要因为 Git 作者名和查询名不同就对用户说「按姓名没匹配上，接下来按邮箱对齐」再重跑采集。只跑一次 `daily_report.py`。
- 不要扫描 `API_KEY` / `ANTHROPIC_AUTH_TOKEN` / 方舟 Key 当 Gitee token。
- 缺 token 时不要自行决定落地方式：先扫描已有环境变量和 `.env`，命中就直接用；都没有才让用户在环境变量、`.env`、会话级里选。
- 不要把 Gitee token 写入 Cursor / Claude / OpenClaw 的语言模型配置。
- 不要修改本 skill 源文件（`SKILL.md`、`scripts/`、`references/`、`.gitignore`）。
- 不要在 skill 目录新增 `.py` / `.md` / 临时脚本或摘要；脚本失败也不许改脚本来绕。
- 不要因为当前工作区是本 skill 仓库，就把「使用」当成「可以改源文件」。
- 用户没说「改这个 skill / 修脚本 / 更新说明书」时，不要扩写、重构或「优化」本 skill。
- 不要自己请求 `gitee.com/api/v5`（含 WebFetch / curl / urllib）；只跑上表入口脚本。
- 不要 `import` 或直接运行 `_gitee_http.py` 来代替入口脚本。
- 入口脚本失败后，不要在临时目录写 fetcher 交差。
- 表里没有的能力（如 PR 列表）不要自己补接口。
