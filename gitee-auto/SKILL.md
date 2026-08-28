---
name: gitee-auto
description: >
  按用户实际要的那一件事拉取 Gitee 数据：仓库成员与贡献者、提交列表、单次 commit
  的 message/diff、或按人汇总工作。用户提到 Gitee/码云、collaborators、contributors、
  commit 列表/详情、按人总结、周报素材时使用本 skill。不要默认把四件事一次做完。
  不要用 GitHub API 代替 Gitee。
---

# Gitee 按需采集

只用本 skill 附带的脚本和 Open API。不要靠记忆编造提交或文件名。

先判断用户要的是下面哪一件，**只跑对应脚本**。没有明确要「按人汇总 / 周报 / 谁做了什么」时，不要跑 `work_by_person.py`。

| 用户要什么 | 脚本 | 不要做 |
|------------|------|--------|
| 成员、贡献者、人员名单 | `scripts/list_users.py` | 不要拉 commits / diff |
| 提交列表、全部 commit | `scripts/list_commits.py` | 不要拉人员，不要逐条 hydrate diff |
| 某个 SHA 的说明和代码改动 | `scripts/commit_detail.py --sha …` | 不要拉全员名单，不要拉仓库历史 |
| 按人汇总、周报、谁改了什么 | `scripts/work_by_person.py` | 这才是唯一会拼人员+提交+详情的入口 |

接口字段见 [references/api.md](references/api.md)。

## 开始前

1. 向用户确认 `owner` 和 `repo`。可从 `https://gitee.com/{owner}/{repo}` 解析。
2. 私有库需要环境变量 `GITEE_ACCESS_TOKEN`。公开库无令牌也可以拉 commits；**成员列表常要令牌**。
3. 列表类任务用户没给时间范围时：先问 `since` / `until` / 分支；对方坚持全量再拉，并说明分页上限。
4. 永远不要在命令行或回复里打印 token。

鉴权：`Authorization: Bearer <token>`，或查询参数 `access_token`。Base：`https://gitee.com/api/v5`（可用 `GITEE_API_BASE` 覆盖）。

在 skill 目录执行脚本。`--out` 指向本次要用的 JSON。

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

多人按提交数降序。没有 diff 的提交只根据 message 写，并注明「未拉取详情」。不要把 merge 机器人或 `Signed-off-by` 当成主要工作。

## 不要做的事

- 不要调用 GitHub `api.github.com`。
- 不要用 PR 接口冒充仓库全部 commit。
- 不要把列表接口里的 `commit` 当成字符串；真实字段是 `commit.message`。
- 不要在未分页的情况下声称「全部提交」。
- 不要把「看某个 SHA」做成完整人员报告。
- 不要把「只要名单」顺便拉完全部 commits。
