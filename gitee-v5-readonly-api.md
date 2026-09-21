# Gitee API v5 — 只读接口全解（GET 类，无写操作）

> 适用：只查询、不修改数据的场景（自动化巡检、数据采集、汇报、只读集成）。
> 依据：官方 Swagger 规范（https://gitee.com/api/v5/swagger，同源镜像 openEuler/go-gitee api/swagger.yaml）
> 与官方 SDK（go-gitee / imjoey ge / gitee-php）交叉核对；标志 [⚠] 的接口为存在性已确认、个别参数细节待核。
>
> 字段说明口径：
> - 「路径参数」：URL 中 {xxx} 占位，必填；
> - 「查询参数」：?key=value，均备注 必填/可选、类型、取值、含义；
> - 「返回关键字段」：响应主体中的主要字段及含义（完整字段以官方文档为准）。

## 0. 通用约定（所有只读接口通用）

| 字段 | 说明 |
|---|---|
| Base URL | https://gitee.com/api/v5 |
| 认证 | 查询参数 access_token（OAuth2 令牌或私人令牌）；公开资源可匿名调用，私有仓库/组织/私人信息必须带 token |
| 分页 | page：页码，整数，默认 1；per_page：每页条数，默认 20，最大 100（部分接口无分页则忽略） |
| 响应格式 | JSON；成功 2xx；鉴权失败 401/403；资源不存在 404 |
| 时间格式 | ISO 8601，如 2024-01-01T00:00:00+08:00 |
| OAuth2 scope | 读取 user_info 需 user_info；读取私人仓库需 projects；issues 需 issues；PR 需 pull_requests；通知需 notification |
| 私人令牌 | 在 https://gitee.com/profile/personal_access_tokens 生成 |

---

## 1. 用户（User）

### 1.1 GET /v5/user
- 功能：获取当前授权登录用户的完整资料（开发中最常用的"我是谁"接口）。
- 路径参数：无。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | access_token | 是 | string | 授权用户令牌（scope 需 user_info） |
- 返回关键字段：User 对象 —— id(用户ID)、login(登录名)、name(昵称)、avatar_url(头像)、email(邮箱，需 emails scope)、blog(主页)、weibo(微博)、bio(简介)、public_repos(公开仓库数)、followers(粉丝数)、following(关注数)、organizations_url、repos_url、created_at(创建时间)、updated_at(更新时间)。

### 1.2 GET /v5/users/{username}
- 功能：获取指定用户的公开资料。
- 路径参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | username | 是 | string | 目标用户登录名 |
- 查询参数：access_token（可选，携带后可看该用户好友化信息/提高限额）。
- 返回关键字段：同 User 公开字段（不含 email 等私密信息）。

### 1.3 GET /v5/user/emails
- 功能：获取授权用户的邮箱列表（需 scope emails）。
- 路径参数：无。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | access_token | 是 | string | 授权用户令牌 |
- 返回关键字段：Email 数组 —— email(邮箱地址)、primary(是否主邮箱)、verified(是否已验证) [⚠ 个别字段名以官方为准]。

### 1.4 GET /v5/users/{username}/repos
- 功能：列出指定用户的公开仓库。
- 路径参数：username（必填，目标用户）。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | type | 否 | string | 仓库类型过滤：all(全部)/owner(本人创建)/member(加入的)；默认 all |
  | sort | 否 | string | 排序字段：full_name(全名)/created(创建时间)/updated(更新时间)；默认 full_name |
  | direction | 否 | string | 排序方向：asc(升序)/desc(降序)；默认 desc |
  | page / per_page | 否 | int | 分页，同通用约定 |
- 返回关键字段：Repo 数组（同 2.1 Repo 结构）。

### 1.5 GET /v5/users/{username}/orgs
- 功能：列出指定用户所属的组织。
- 路径参数：username（必填）。
- 查询参数：page / per_page。
- 返回关键字段：Organization 数组 —— id、login(组织登录名)、name(组织名)、avatar_url、description、public_repos、url、html_url。

### 1.6 GET /v5/user/following [⚠]
- 功能：获取授权用户"正在关注"的用户列表。
- 查询参数：access_token（必填）；page / per_page。
- 返回关键字段：User 数组。

### 1.7 GET /v5/users/{username}/followers [⚠]
- 功能：获取指定用户的粉丝（关注者）列表。
- 路径参数：username（必填）。
- 查询参数：page / per_page。
- 返回关键字段：User 数组。

### 1.8 GET /v5/users/{username}/following [⚠]
- 功能：获取指定用户正在关注的人。
- 路径参数：username（必填）。
- 查询参数：page / per_page。
- 返回关键字段：User 数组。

### 1.9 GET /v5/user/starred/{owner}/{repo} [⚠]
- 功能：判断授权用户是否已加星（收藏）指定仓库。
- 路径参数：owner（仓库所有者）、repo（仓库名）。
- 查询参数：access_token（必填）。
- 返回：已收藏/未收藏状态（布尔或状态码，以官方为准）。

---

## 2. 仓库（Repositories）

### 2.1 GET /v5/user/repos
- 功能：列出授权用户的全部仓库（含私有），开发环境最常用的"我的仓库"接口。
- 路径参数：无。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | access_token | 是 | string | 授权用户令牌（scope projects） |
  | type | 否 | string | all(全部，默认)/owner(我创建)/member(我加入的) |
  | sort | 否 | string | full_name(全名，默认)/created(创建时间)/updated(更新时间) |
  | direction | 否 | string | asc/desc，默认 desc |
  | page / per_page | 否 | int | 分页 |
- 返回关键字段：Repo 数组 —— id、name(仓库名)、full_name(owner/name)、human_name(人类可读名)、namespace(命名空间)、path、owner(User)、description、private(是否私有)、public(是否公开)、fork(是否 fork 仓)、forks(被 fork 次数)、watchers(关注者数)、stargazers_count(加星数)、default_branch(默认分支)、homepage、has_issues、has_wiki、can_comment、created_at、updated_at、url、html_url。

### 2.2 GET /v5/repos/{owner}/{repo}
- 功能：获取单个仓库的详细信息。
- 路径参数：owner（仓库所有者登录名）、repo（仓库名）。
- 查询参数：access_token（私有仓库必填）。
- 返回关键字段：Repo 全字段（同 2.1，另含 open_issues_count、pushed_at 等）。

### 2.3 GET /v5/repos/{owner}/{repo}/forks
- 功能：列出该仓库的 fork 列表。
- 路径参数：owner、repo。
- 查询参数：page / per_page；sort（排序字段，如 stargazers_count）、direction [⚠ 以官方为准]。
- 返回关键字段：Repo 数组。

### 2.4 GET /v5/repos/{owner}/{repo}/stargazers
- 功能：列出给该仓库加星的用户。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：User 数组。

### 2.5 GET /v5/repos/{owner}/{repo}/watchers
- 功能：列出关注该仓库的用户。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：User 数组。

### 2.6 GET /v5/repos/{owner}/{repo}/contributors
- 功能：列出该仓库的贡献者。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：User 数组（含统计字段 [⚠]）。

### 2.7 GET /v5/repos/{owner}/{repo}/branches
- 功能：列出仓库的全部分支。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：Branch 数组 —— name(分支名)、commit(分支最新提交，含 sha/commit/author/url)、protected(是否受保护)、protection_url(保护状态 url)。

### 2.8 GET /v5/repos/{owner}/{repo}/branches/{branch}/protection
- 功能：查看单个分支的保护规则（如是否禁止直接 push）。
- 路径参数：owner、repo、branch（分支名）。
- 查询参数：无。
- 返回关键字段：保护配置对象 —— enabled(是否启用)、保护规则（如强制评审、限制推送者）[⚠ 字段以官方为准]。

### 2.9 GET /v5/repos/{owner}/{repo}/tags
- 功能：列出仓库的 Tag（轻量/附注标签）。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：Tag 数组 —— name(标签名)、message(附注信息，轻量标签为空)、commit(指向的提交，含 sha/commit/url)。

### 2.10 GET /v5/repos/{owner}/{repo}/commits
- 功能：获取仓库的提交历史（可按分支/文件/作者/时间过滤）——开发审计与数据采集的核心接口。
- 路径参数：owner、repo。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | sha | 否 | string | 分支名、tag 名或具体 sha；默认默认分支 |
  | path | 否 | string | 仅返回该路径下文件的提交 |
  | author | 否 | string | 按作者邮箱/用户名过滤 |
  | since | 否 | string | 起止时间（ISO 8601），最早提交 |
  | until | 否 | string | 截止时间（ISO 8601），最新提交 |
  | page / per_page | 否 | int | 分页 |
- 返回关键字段：Commit 数组 —— sha、commit(提交对象：author{name,email,date}/committer/message/comment_count)、author(User)、committer(User)、html_url。

### 2.11 GET /v5/repos/{owner}/{repo}/commits/{sha}
- 功能：获取单个提交的完整详情（含变更文件列表）。
- 路径参数：owner、repo、sha（提交 sha）。
- 查询参数：无。
- 返回关键字段：Commit 详情 —— sha、author、committer、commit.message、parents(父提交数组)、files(变更文件：filename/status/additions/deletions/changes/patch/raw_url)。

### 2.12 GET /v5/repos/{owner}/{repo}/commits/{sha}/comments
- 功能：列出某个提交下的评论。
- 路径参数：owner、repo、sha。
- 查询参数：page / per_page。
- 返回关键字段：Note 数组 —— id、body(评论内容)、html_url、user(评论人)、created_at、updated_at。

### 2.13 GET /v5/repos/{owner}/{repo}/compare/{base}...{head}
- 功能：比较两个分支/tag/提交之间的差异（评审前查看改动范围）。
- 路径参数：owner、repo、base（基线，如 master）、head（对比端，如 feature-branch）。
- 查询参数：无（分页由返回的空数组自身决定 [⚠]）。
- 返回关键字段：Compare 对象 —— commits(提交数组)、files(文件差异数组，同 2.11 files)、ahead_by(领先提交数)、behind_by(落后提交数)、status(比较状态)。

### 2.14 GET /v5/repos/{owner}/{repo}/contents/{path}
- 功能：读取仓库中的文件内容或目录结构（写操作的读前置）。
- 路径参数：owner、repo、path（文件或目录路径；空路径=根目录）。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | ref | 否 | string | 分支名/tag/sha；默认默认分支 |
  | access_token | 否 | string | 私有仓库必填 |
- 返回关键字段：
  - 文件：type=file、content(base64 编码)、encoding、sha、size、name、path、url、html_url、download_url、_links(自链接)
  - 目录：type=dir 的条目数组，含 name、path、sha、url、html_url
  - 注意：文件内容为 base64，需解码后使用。

### 2.15 GET /v5/repos/{owner}/{repo}/releases
- 功能：列出仓库的发布（Release）记录。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：Release 数组 —— id、tag_name(关联标签)、name(标题)、body(说明)、author、html_url、created_at、updated_at、prerelease(是否预发布)。

### 2.16 GET /v5/repos/{owner}/{repo}/releases/{tag}
- 功能：获取单个发布详情。
- 路径参数：owner、repo、tag（发布对应的 tag 名）。
- 查询参数：无。
- 返回关键字段：Release 详情（同 2.15，含附件列表 [⚠]）。

### 2.17 GET /v5/repos/{owner}/{repo}/collaborators
- 功能：列出仓库协作者及其权限。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：ProjectMember 数组 —— id、login、name、avatar_url、html_url、permission(权限：developer/report/observer/tester 等)、role(角色)。

### 2.18 GET /v5/repos/{owner}/{repo}/collaborators/{username}
- 功能：获取单个协作者及其权限。
- 路径参数：owner、repo、username。
- 查询参数：无。
- 返回关键字段：ProjectMember（同 2.17）。

### 2.19 GET /v5/repos/{owner}/{repo}/keys
- 功能：列出仓库部署公钥（CI/只读部署场景）。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：ProjectKey 数组 —— id、title(标题)、public_key(公钥内容)、created_at。

### 2.20 GET /v5/repos/{owner}/{repo}/hooks
- 功能：列出仓库配置的 Webhook（审计集成配置）。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：ProjectHook 数组 —— id、url(回调地址)、push_events(推送事件)、tag_push_events(标签推送)、issues_events(Issue 事件)、note_events(评论事件)、merge_requests_events(合并请求事件)、created_at、updated_at、password(是否加密)。

### 2.21 GET /v5/repos/{owner}/{repo}/hooks/{id}
- 功能：获取单个 Webhook 详情。
- 路径参数：owner、repo、id（Webhook id）。
- 查询参数：无。
- 返回关键字段：ProjectHook（同 2.20）。

---

## 3. Git 数据（GitData，底层对象）

### 3.1 GET /v5/repos/{owner}/{repo}/git/blobs/{sha}
- 功能：按对象 sha 获取 Blob 内容（原始文件二进制）。
- 路径参数：owner、repo、sha。
- 查询参数：无。
- 返回关键字段：Blob —— sha、size、content(base64 编码)、encoding。

### 3.2 GET /v5/repos/{owner}/{repo}/git/trees/{sha}
- 功能：按对象 sha 获取目录树。
- 路径参数：owner、repo、sha。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | recursive | 否 | int | 0(否)/1(递归展开全部子目录)；默认 0 |
- 返回关键字段：Tree —— sha、tree 数组(每项：path 路径、mode 权限模式、type 类型(blob/tree/commit)、sha、size)、truncated(是否截断)。

### 3.3 GET /v5/repos/{owner}/{repo}/git/commits/{sha}
- 功能：按 sha 获取 Commit 对象（与 2.11 相比是更底层的对象视图）。
- 路径参数：owner、repo、sha。
- 查询参数：无。
- 返回关键字段：Commit —— sha、url、author、committer、message、tree(指向的树 sha)、parents(父提交 sha 数组)。

### 3.4 GET /v5/repos/{owner}/{repo}/git/refs
- 功能：获取仓库引用（分支/标签）列表。
- 路径参数：owner、repo。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | ref | 否 | string | 引用路径过滤，如 refs/heads/master |
- 返回关键字段：Ref 数组 —— ref(引用全名)、object{sha、type(commit/tag)、url}。

### 3.5 GET /v5/repos/{owner}/{repo}/git/refs/{ref} [⚠]
- 功能：获取单个引用。
- 路径参数：owner、repo、ref（如 refs/heads/master）。
- 查询参数：无。
- 返回关键字段：Ref（同 3.4）。

---

## 4. Pull Request（代码评审）

### 4.1 GET /v5/repos/{owner}/{repo}/pulls
- 功能：获取仓库 PR 列表（按状态/分支/里程碑/标签过滤）。
- 路径参数：owner、repo。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | state | 否 | string | open(默认)/closed/merged/all |
  | head | 否 | string | 源分支，格式 user:branch |
  | base | 否 | string | 目标分支 |
  | milestone | 否 | int | 里程碑编号过滤 |
  | labels | 否 | string | 标签过滤，逗号分隔 |
  | sort | 否 | string | 排序字段(created/updated 等 [⚠]) |
  | direction | 否 | string | asc/desc |
  | page / per_page | 否 | int | 分页 |
- 返回关键字段：PullRequest 数组 —— id、number(PR 号)、title、body、state、status(评审状态)、user(发起人)、head{label/ref/sha}、base{label/ref/sha}、assignee(负责人)、milestone、labels、comments(评论数)、commits(提交数)、additions/deletions/changed_files(增删改行数/文件数)、html_url、created_at、updated_at、merged_at、closed_at。

### 4.2 GET /v5/repos/{owner}/{repo}/pulls/{number}
- 功能：获取单个 PR 完整详情。
- 路径参数：owner、repo、number（PR 编号）。
- 查询参数：无。
- 返回关键字段：PullRequest 全字段（同 4.1），另含 diff_url、mergeable 等 [⚠]。

### 4.3 GET /v5/repos/{owner}/{repo}/pulls/{number}/comments
- 功能：列出 PR 下的评论（含行内评审意见）。
- 路径参数：owner、repo、number。
- 查询参数：page / per_page；sort/direction [⚠]。
- 返回关键字段：PullRequestComment 数组 —— id、body(内容)、user、created_at、updated_at、path(评论所在文件)、line(行号)、position(位置)、diff_hunk(差异片段)。

### 4.4 GET /v5/repos/{owner}/{repo}/pulls/{number}/commits
- 功能：列出 PR 包含的提交。
- 路径参数：owner、repo、number。
- 查询参数：page / per_page。
- 返回关键字段：Commit 数组（同 2.10）。

### 4.5 GET /v5/repos/{owner}/{repo}/pulls/{number}/files
- 功能：列出 PR 变更的文件及差异。
- 路径参数：owner、repo、number。
- 查询参数：无 [⚠ 分页以官方为准]。
- 返回关键字段：File 数组 —— sha、filename(文件路径)、status(状态：modified/added/deleted/renamed)、additions、deletions、changes、patch(差异内容)。

---

## 5. Issue / 里程碑 / 标签（团队协作）

### 5.1 GET /v5/repos/{owner}/{repo}/issues
- 功能：获取仓库 Issue 列表（项目任务/缺陷的只读视图）。
- 路径参数：owner、repo。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | state | 否 | string | open(默认)/progressing(进行中)/closed(已关闭)/rejected(已拒绝) [⚠ rejected 以官方枚举为准] |
  | labels | 否 | string | 标签过滤，逗号分隔 |
  | assignee | 否 | string | 按负责人过滤 |
  | creator | 否 | string | 按创建人过滤 |
  | milestone | 否 | int | 按里程碑编号过滤 |
  | sort | 否 | string | 排序字段：created/updated [⚠] |
  | direction | 否 | string | asc/desc |
  | since | 否 | string | ISO 8601，只返回该时间后的更新 |
  | page / per_page | 否 | int | 分页 |
- 返回关键字段：Issue 数组 —— id、number(编号)、title、body、state、html_url、user(创建人)、assignee(负责人)、labels[{name,color}]、milestone、comments(评论数)、created_at、updated_at、closed_at、pull_request(关联 PR 信息)。

### 5.2 GET /v5/repos/{owner}/{repo}/issues/{number}
- 功能：获取单个 Issue 详情。
- 路径参数：owner、repo、number（Issue 编号）。
- 查询参数：无。
- 返回关键字段：Issue 全字段（同 5.1）。

### 5.3 GET /v5/repos/{owner}/{repo}/issues/{number}/comments
- 功能：列出 Issue 下的讨论/回复。
- 路径参数：owner、repo、number。
- 查询参数：page / per_page。
- 返回关键字段：Note 数组 —— id、body、html_url、user、created_at、updated_at。

### 5.4 GET /v5/repos/{owner}/{repo}/issues/{number}/operate [⚠]
- 功能：获取 Issue 的审批/转让操作信息（如"同意转让"记录）。
- 路径参数：owner、repo、number。
- 查询参数：无。
- 返回关键字段：审批/操作记录对象（字段以官方为准）。

### 5.5 GET /v5/repos/{owner}/{repo}/comments
- 功能：获取仓库"发布（类似动态）"列表。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：Note 数组 —— id、body(内容)、html_url、user、created_at、updated_at。

### 5.6 GET /v5/repos/{owner}/{repo}/labels
- 功能：获取仓库的全部标签。
- 路径参数：owner、repo。
- 查询参数：page / per_page [⚠]。
- 返回关键字段：Label 数组 —— id、name(名称)、color(颜色值)。

### 5.7 GET /v5/repos/{owner}/{repo}/milestones
- 功能：获取仓库里程碑列表。
- 路径参数：owner、repo。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | state | 否 | string | open(默认)/closed |
  | sort | 否 | string | 排序字段 [⚠] |
  | direction | 否 | string | asc/desc |
  | page / per_page | 否 | int | 分页 |
- 返回关键字段：Milestone 数组 —— id、number、title、description、state、open_issues(打开数)、closed_issues(关闭数)、due_on(截止日期)、created_at、updated_at。

### 5.8 GET /v5/repos/{owner}/{repo}/milestones/{number}
- 功能：获取单个里程碑。
- 路径参数：owner、repo、number。
- 查询参数：无。
- 返回关键字段：Milestone（同 5.7）。

---

## 6. 搜索（Search）

### 6.1 GET /v5/search/repositories
- 功能：全站搜索仓库。
- 路径参数：无。
- 查询参数：
  | 字段 | 必填 | 类型 | 说明 |
  |---|---|---|---|
  | q | 是 | string | 搜索关键字（如 go、gitee sdk） |
  | sort | 否 | string | 排序字段（如 stars/forks）[⚠] |
  | order | 否 | string | asc/desc [⚠] |
  | page / per_page | 否 | int | 分页 |
- 返回关键字段：Repo 数组（同 2.1）。

### 6.2 GET /v5/search/issues
- 功能：全站搜索 Issue。
- 路径参数：无。
- 查询参数：q（必填）、page / per_page [⚠ 其余过滤参数以官方为准]。
- 返回关键字段：Issue 数组（同 5.1）。

### 6.3 GET /v5/search/users
- 功能：全站搜索用户。
- 路径参数：无。
- 查询参数：q（必填）、page / per_page [⚠]。
- 返回关键字段：User 数组。

---

## 7. 组织（Organizations，团队视角）

### 7.1 GET /v5/orgs/{org}
- 功能：获取组织信息。
- 路径参数：org（组织登录名）。
- 查询参数：access_token（私有组织必填）。
- 返回关键字段：Organization —— id、login、name、avatar_url、html_url、description、public_repos、members(成员数)、url、events_url。

### 7.2 GET /v5/orgs/{org}/repos
- 功能：列出组织下的仓库。
- 路径参数：org。
- 查询参数：type(可选 all/public/private [⚠])、sort、direction、page / per_page。
- 返回关键字段：Repo 数组（同 2.1，owner 为组织）。

### 7.3 GET /v5/orgs/{org}/members
- 功能：列出组织成员。
- 路径参数：org。
- 查询参数：page / per_page。
- 返回关键字段：User 数组。

### 7.4 GET /v5/orgs/{org}/memberships/{username}
- 功能：获取组织成员的权限信息。
- 路径参数：org、username。
- 查询参数：无。
- 返回关键字段：OrganizationMembership —— org、user、permission(成员权限：admin/master/developer/reporter/observer/tester)。

---

## 8. 通知 / 动态（辅助信息，[⚠] 标注）

### 8.1 GET /v5/notifications/threads [⚠]
- 功能：获取通知（消息）列表。
- 查询参数：unread(可选，仅未读)、participating(可选，仅我参与的)、since(ISO 8601 起始)、page / per_page；access_token（必填，scope notification）。
- 返回关键字段：通知对象数组 —— id、title、content、html_url、read(已读？)、created_at。

### 8.2 GET /v5/notifications/count [⚠]
- 功能：获取未读通知数量。
- 查询参数：access_token（必填）；unread(可选 bool，是否仅统计未读)。
- 返回关键字段：数量对象 —— count? [字段名以官方为准]。

### 8.3 GET /v5/events [⚠]
- 功能：获取授权用户的动态流。
- 查询参数：access_token（必填）、page / per_page。
- 返回关键字段：Event 数组 —— id、type(事件类型)、actor(User)、repo、payload(事件负载)、created_at。

### 8.4 GET /v5/repos/{owner}/{repo}/events
- 功能：获取仓库动态（push/issue/PR 等事件的流）。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：Event 数组（同 8.3）。

### 8.5 GET /v5/users/{username}/events
- 功能：获取指定用户产生的动态。
- 路径参数：username。
- 查询参数：page / per_page。
- 返回关键字段：Event 数组。

### 8.6 GET /v5/users/{username}/received_events
- 功能：获取指定用户收到的（相关）动态。
- 路径参数：username。
- 查询参数：page / per_page。
- 返回关键字段：Event 数组。

### 8.7 GET /v5/orgs/{org}/events [⚠]
- 功能：获取组织动态。
- 路径参数：org。
- 查询参数：page / per_page。
- 返回关键字段：Event 数组。

### 8.8 GET /v5/networks/{owner}/{repo}/events [⚠]
- 功能：获取 fork 网络动态。
- 路径参数：owner、repo。
- 查询参数：page / per_page。
- 返回关键字段：Event 数组。

---

## 9. 使用建议

1. 只读采集优先用 2.1/2.10/2.14/4.1/5.1（仓库/提交/文件/PR/Issue）。
2. 私有数据一律带 access_token；公开数据尽量匿名以省额度。
3. 大列表务必使用 page + per_page 循环取完（per_page 最大 100）。
4. contents 返回的文件内容为 base64，用前先解码。
5. 文件类接口（contents）直接返回实体内容，抓取单文件比 git clone 更轻。

> 注：[⚠] 项的来源为官方 SDK/文档镜像交叉佐证；正式开发前建议对 ⚠ 项用 Swagger UI 或一次实测响应核对字段名。
