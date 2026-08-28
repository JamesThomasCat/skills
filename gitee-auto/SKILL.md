---
name: gitee-auto
description: >
  拉取 Gitee 仓库成员与贡献者、分页获取全部提交、读取单次提交的 message 与文件 diff，
  并按人汇总工作内容。用户提到 Gitee/码云仓库人员、collaborators、contributors、
  commit 列表/详情、代码改动、按人总结工作、周报素材、谁改了什么时都要使用本 skill，
  即使没有说「gitee-auto」。不要用 GitHub API 代替 Gitee。
---

# Gitee 仓库人员与按人工作总结

先用脚本把 **成员 + 贡献者 + 提交 + 代码详情** 拉成一份 JSON，再只根据这份数据按人写总结。不要靠记忆编造提交或文件名。不要使用 MCP；只用本 skill 附带的脚本和 Open API。

## 开始前

1. 向用户确认 `owner`（空间 path）和 `repo`（仓库 path）。可从 `https://gitee.com/{owner}/{repo}` 解析。
2. 私有库需要 `GITEE_ACCESS_TOKEN`（私人令牌：https://gitee.com/profile/personal_access_tokens）。公开库无令牌也可以拉 commits；**成员列表常要令牌**。
3. 「全部提交」在大仓库上会很长。用户没给时间范围时：先问 `since` / `until` / 分支；对方坚持全量再拉，并说明分页上限。
4. 永远不要在命令行或回复里打印 token。用环境变量 `GITEE_ACCESS_TOKEN`。

鉴权：`Authorization: Bearer <token>`，或查询参数 `access_token`。Base URL：`https://gitee.com/api/v5`（可用 `GITEE_API_BASE` 覆盖）。永远不要打印 token。

## 采集（必须跑脚本）

在 skill 目录执行（把路径换成实际 skill 根目录）：

```bash
python scripts/fetch_gitee_work.py --owner <owner> --repo <repo> --out work.json
```

常用参数：

| 参数 | 作用 |
|------|------|
| `--sha` | 分支名或起始 SHA，默认仓库默认分支 |
| `--since` / `--until` | ISO 8601 时间窗 |
| `--author` | 按邮箱或 login 过滤提交 |
| `--details-limit` | 要拉取 diff 的提交条数，默认 40；需要更多就加大 |
| `--max-pages` | 列表分页上限，每页 100，默认 50 页 |
| `--token` | 仅当环境变量不可用时使用；不要回显 |

脚本会请求：

- `GET /repos/{owner}/{repo}/collaborators`（成员，分页）
- `GET /repos/{owner}/{repo}/contributors?type=authors`（贡献者）
- `GET /repos/{owner}/{repo}/commits`（提交列表，分页；含 `commit.message`）
- `GET /repos/{owner}/{repo}/commits/{sha}`（代码详情：`files[].filename` / `status` / `patch`）

接口字段见 [references/api.md](references/api.md)。

若某步失败（例如 collaborators 403），继续用已成功的数据，并在报告里写明缺口。不要因为成员接口失败就放弃 commits。

`meta.commits_truncated` 或 `details_truncated` 为 true 时：加大 `--max-pages` / `--details-limit` 再拉，或收窄 `since`/`until`。不要假装已经覆盖全部历史。

`files_truncated` 或某文件 `truncated`/`patch_omitted`：总结里标明 diff 不完整。需要全文时再用 `GET /repos/{owner}/{repo}/contents/{path}?ref={sha}`。

## 人员怎么对齐

仓库里有两类「用户」，都要出现在报告里：

- **成员**：`collaborators`（有仓库权限，含 `login`、`name`、`permissions` / `member_role`）
- **贡献者**：`contributors`（`name`、`email`、`contributions`，通常没有 login）

提交作者可能只出现在其中一侧，或只出现在 commit 的 `author_login` / `author_email`。按下面顺序归到同一个人：

1. `author_login` = 成员 `login`
2. `author_email` = 贡献者 `email`
3. `author_name` = 成员/贡献者 `name`（仅在前两步无法匹配时）

匹配不上就单独成组，标题用 login 或邮箱，不要丢弃。成员有账号但窗口内零提交的人，列在「无提交」而不是省略。

## 按人总结（输出必须用这个结构）

用简体中文。只写 JSON 里出现过的提交和文件。工作内容来自 `message` + `files`（路径、增删、patch 要点），不要把 merge 机器人或 `Signed-off-by` 当成主要工作。

```markdown
# {owner}/{repo} 工作总结

## 范围
- 分支/起始 SHA：
- 时间：since ~ until（未限制则写「脚本返回的全部页」）
- 提交条数 / 已拉详情条数
- 成员数 / 贡献者数
- 截断或接口错误（原样引用 `errors` 与 `meta.*_truncated`）

## 仓库人员
### 成员
| login | 姓名 | 角色/权限 |
### 贡献者
| 姓名 | 邮箱 | contributions |
### 仅一侧出现
- 只在成员里 / 只在贡献者里 / 只在提交作者里

## 按人工作
### {显示名}（@{login} 或邮箱）
- 身份：成员 / 贡献者 / 仅提交作者
- 提交数：N
- 主要文件：（按出现次数或改动量，列出路径）
- 工作摘要：（3–8 句，按主题归纳，不要逐条复述全部 message）
- 代表提交：短 SHA + 一句话 + 关键文件
```

多人时按提交数降序。没有 diff 的提交只根据 message 写，并注明「未拉取详情」。

## 不要做的事

- 不要调用 GitHub `api.github.com`。
- 不要用 PR 接口冒充「仓库全部 commit」。
- 不要把列表接口里的 `commit` 当成字符串；真实字段是 `commit.message`。
- 不要在未分页的情况下声称「全部提交」。
- 不要把 `POST /pulls/{n}/comments`（发表评论）当成 git commit 接口。
