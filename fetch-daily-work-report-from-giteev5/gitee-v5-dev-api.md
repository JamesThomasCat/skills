# Gitee API v5 — 开发相关接口清单

> 依据：官方 Swagger 规范（https://gitee.com/api/v5/swagger，与 openEuler/go-gitee `api/swagger.yaml` 同源）
> 及官方 SDK 文档（go-gitee、gitee-php、gitee-python-client、java-gitee）交叉核对。
> 标注 ⚠ 的接口为存在性基本确认、但参数细节以 Swagger 原文为准。

## 0. 通用约定

- **Base URL**：`https://gitee.com/api/v5`（全部接口以 `/v5/` 开头）
- **认证**：`?access_token=xxx` 查询参数（OAuth2 或私人令牌）
- **分页**：`page`（默认 1）、`per_page`（默认 20，最大 100）
- **Content-Type**：`application/json`
- **私人令牌**：https://gitee.com/profile/personal_access_tokens
- **OAuth2**：
  - 授权：`GET https://gitee.com/oauth/authorize?client_id=&redirect_uri=&response_type=code&scope=`
  - 换 token：`POST https://gitee.com/oauth/token`（grant_type=authorization_code | refresh_token | password）
  - 常用 scope：`user_info` `projects` `projects:fork` `pull_requests` `issues` `notes` `emails` `groups` `star` `watch` `enterprise` `notification`

---

## 1. 用户（开发者本人）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/user | 获取授权用户资料 |
| GET | /v5/user/emails | 获取授权用户的邮箱列表（scope: emails） |
| GET | /v5/users/{username} | 获取指定用户的资料 |
| GET | /v5/users/{username}/repos | 列出指定用户的公开仓库 |
| GET | /v5/users/{username}/orgs | 列出用户所属的组织 |
| GET | /v5/user/starred/{owner}/{repo} 状态 | 是否已加星（收藏） |
| PUT | /v5/user/starred/{owner}/{repo} | 加星仓库 |
| DELETE | /v5/user/starred/{owner}/{repo} | 取消加星 |
| PUT | /v5/user/watched/{owner}/{repo} | 关注仓库（watch） |
| DELETE | /v5/user/watched/{owner}/{repo} | 取消关注 |

## 2. 仓库 Repositories

### 2.1 仓库 CRUD
| 方法 | 路径 | 说明 / 关键参数 |
|---|---|---|
| GET | /v5/user/repos | 授权用户的仓库列表（type=all|owner|member|public|private，sort=full_name|created|updated，direction） |
| POST | /v5/user/repos | 创建仓库（name 必填；description、homepage、has_issues、has_wiki、can_comment、path、private、auto_init、gitignore_template、license_template） |
| GET | /v5/repos/{owner}/{repo} | 获取仓库详情 |
| PATCH | /v5/repos/{owner}/{repo} | 更新仓库（name、description、homepage、has_issues、has_wiki、can_comment、default_branch、private） |
| DELETE | /v5/repos/{owner}/{repo} | 删除仓库 |
| POST | /v5/repos/{owner}/{repo}/forks | Fork 仓库（org 参数可 fork 到组织） |
| GET | /v5/repos/{owner}/{repo}/forks | Fork 列表 |
| GET | /v5/repos/{owner}/{repo}/stargazers | 加星用户列表 |
| GET | /v5/repos/{owner}/{repo}/watchers | 关注者列表 |
| GET | /v5/repos/{owner}/{repo}/contributors | 贡献者列表 |

### 2.2 分支与分支保护
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/branches | 仓库全部分支 |
| POST | /v5/repos/{owner}/{repo}/branches | 创建分支（branch_name、refs） |
| DELETE | /v5/repos/{owner}/{repo}/branches/{branch} | 删除分支 |
| GET | /v5/repos/{owner}/{repo}/branches/{branch}/protection | 查看分支保护规则 |
| PUT | /v5/repos/{owner}/{repo}/branches/{branch}/protection | 设置分支保护（BranchProtectionPutParam） |
| DELETE | /v5/repos/{owner}/{repo}/branches/{branch}/protection | 取消分支保护 |

### 2.3 标签（Tags / Releases）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/tags | 仓库 Tag 列表 |
| POST | /v5/repos/{owner}/{repo}/tags ⚠ | 创建 Tag（tag_name、refs、message） |
| GET | /v5/repos/{owner}/{repo}/releases | 发布（Release）列表 |
| POST | /v5/repos/{owner}/{repo}/releases | 创建发布（tag_name、name、body、target_commitish、prerelease） |
| GET | /v5/repos/{owner}/{repo}/releases/{tag} | 单个发布详情 |
| PATCH | /v5/repos/{owner}/{repo}/releases/{tag} | 编辑发布 |
| DELETE | /v5/repos/{owner}/{repo}/releases/{tag} | 删除发布 |

### 2.4 文件内容（代码读写）
| 方法 | 路径 | 说明 / 关键参数 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/contents/{path} | 获取文件/目录内容（ref 分支；文件返回 base64 content） |
| POST | /v5/repos/{owner}/{repo}/contents/{path} | 新建文件（content(base64)、message、branch、author.name、author.email） |
| PUT | /v5/repos/{owner}/{repo}/contents/{path} | 修改文件（sha、content(base64)、message、branch、author） |
| DELETE | /v5/repos/{owner}/{repo}/contents/{path} | 删除文件（sha、message、branch） |

### 2.5 提交与对比
| 方法 | 路径 | 说明 / 关键参数 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/commits | 提交列表（sha、path、author、since、until） |
| GET | /v5/repos/{owner}/{repo}/commits/{sha} | 单个提交详情 |
| GET | /v5/repos/{owner}/{repo}/commits/{sha}/comments | 提交评论列表 |
| POST | /v5/repos/{owner}/{repo}/commits/{sha}/comments | 对提交发表评论（body） |
| GET | /v5/repos/{owner}/{repo}/compare/{base}...{head} | 比较两个分支/提交（base、head） |

### 2.6 协作者与部署公钥
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/collaborators | 协作者列表 |
| GET | /v5/repos/{owner}/{repo}/collaborators/{username} | 单个协作者（含权限） |
| POST | /v5/repos/{owner}/{repo}/collaborators | 添加协作者（username、permission=developer|report|observer|tester） |
| PUT | /v5/repos/{owner}/{repo}/collaborators/{username} | 修改协作者权限 |
| DELETE | /v5/repos/{owner}/{repo}/collaborators/{username} | 移除协作者 |
| GET | /v5/repos/{owner}/{repo}/keys | 部署公钥列表 |
| POST | /v5/repos/{owner}/{repo}/keys | 添加部署公钥（title、key） |
| DELETE | /v5/repos/{owner}/{repo}/keys/{id} | 删除部署公钥 |

## 3. Git 数据（底层对象）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/git/blobs/{sha} | 获取 Blob（base64） |
| GET | /v5/repos/{owner}/{repo}/git/trees/{sha} | 获取 Tree（recursive=1 递归） |
| GET | /v5/repos/{owner}/{repo}/git/commits/{sha} | 获取 Commit 对象 |
| GET | /v5/repos/{owner}/{repo}/git/refs | 获取引用列表（ref 参数可过滤，如 refs/heads/master） |
| GET | /v5/repos/{owner}/{repo}/git/refs/{ref} | 获取单个引用 ⚠ |

## 4. Pull Request（代码评审）

| 方法 | 路径 | 说明 / 关键参数 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/pulls | PR 列表（state=open|closed|merged|all、sort、direction、milestone、labels） |
| POST | /v5/repos/{owner}/{repo}/pulls | 创建 PR（title 必填、head、base、body） |
| GET | /v5/repos/{owner}/{repo}/pulls/{number} | PR 详情 |
| PATCH | /v5/repos/{owner}/{repo}/pulls/{number} | 更新 PR（title、body、state、base） |
| PUT | /v5/repos/{owner}/{repo}/pulls/{number}/merge | 合并 PR（merge_method=merge|squash|rebase） |
| GET | /v5/repos/{owner}/{repo}/pulls/{number}/comments | PR 评论列表 |
| POST | /v5/repos/{owner}/{repo}/pulls/{number}/comments | 提交 PR 评论/审核意见（body 必填） |
| PATCH | /v5/repos/{owner}/{repo}/pulls/{number}/comments/{id} | 修改 PR 评论 |
| DELETE | /v5/repos/{owner}/{repo}/pulls/{number}/comments/{id} | 删除 PR 评论 |
| GET | /v5/repos/{owner}/{repo}/pulls/{number}/commits | PR 的提交列表 |
| GET | /v5/repos/{owner}/{repo}/pulls/{number}/files | PR 的文件改动列表 |
| POST | /v5/repos/{owner}/{repo}/pulls/{number}/testers ⚠ | PR 测试人员配套操作 |
| POST | /v5/repos/{owner}/{repo}/pulls/{number}/reviewers ⚠ | PR 审核人员配套操作 |

## 5. Issue / 里程碑 / 标签（协作）

| 方法 | 路径 | 说明 / 关键参数 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/issues | Issue 列表（state、assignee、creator、labels、sort、direction、page、per_page） |
| POST | /v5/repos/{owner}/{repo}/issues | 创建 Issue（title 必填、body、labels、milestone、assignee） |
| GET | /v5/repos/{owner}/{repo}/issues/{number} | Issue 详情 |
| PATCH | /v5/repos/{owner}/{repo}/issues/{number} | 更新 Issue（title、body、state=open|closed、labels、assignee、milestone） |
| GET | /v5/repos/{owner}/{repo}/issues/{number}/comments | Issue 评论列表 |
| POST | /v5/repos/{owner}/{repo}/issues/{number}/comments | 回复 Issue（body） |
| PATCH | /v5/repos/{owner}/{repo}/issues/{number}/comments/{id} | 修改评论 |
| DELETE | /v5/repos/{owner}/{repo}/issues/{number}/comments/{id} | 删除评论 |
| DELETE | /v5/repos/{owner}/{repo}/issues/{number}/labels/{name} | 移除 Issue 标签 |
| GET | /v5/repos/{owner}/{repo}/issues/{number}/operate ⚠ | 获取审批/转让操作信息 |
| POST | /v5/repos/{owner}/{repo}/issues/{number}/operate ⚠ | 处理 Issue 转让/拒绝/接受 |
| GET | /v5/repos/{owner}/{repo}/comments | 仓库动态（发布）列表 |
| POST | /v5/repos/{owner}/{repo}/comments | 发布动态（body） |
| GET | /v5/repos/{owner}/{repo}/labels | 仓库标签列表 |
| POST | /v5/repos/{owner}/{repo}/labels | 创建标签（name、color） |
| PATCH | /v5/repos/{owner}/{repo}/labels/{name} | 更新标签 |
| DELETE | /v5/repos/{owner}/{repo}/labels/{name} | 删除标签 |
| GET | /v5/repos/{owner}/{repo}/milestones | 里程碑列表 |
| POST | /v5/repos/{owner}/{repo}/milestones | 创建里程碑 |
| GET | /v5/repos/{owner}/{repo}/milestones/{number} | 单个里程碑 |
| PATCH | /v5/repos/{owner}/{repo}/milestones/{number} | 更新里程碑 |
| DELETE | /v5/repos/{owner}/{repo}/milestones/{number} | 删除里程碑 |

## 6. Webhook（CI/自动化集成）

| 方法 | 路径 | 说明 / 关键参数 |
|---|---|---|
| GET | /v5/repos/{owner}/{repo}/hooks | Webhook 列表 |
| POST | /v5/repos/{owner}/{repo}/hooks | 添加 Webhook（url、password、push_events、tag_push_events、issues_events、note_events、merge_requests_events 等） |
| GET | /v5/repos/{owner}/{repo}/hooks/{id} | 单个 Webhook |
| PATCH | /v5/repos/{owner}/{repo}/hooks/{id} | 更新 Webhook |
| DELETE | /v5/repos/{owner}/{repo}/hooks/{id} | 删除 Webhook |
| POST | /v5/repos/{owner}/{repo}/hooks/{id}/tests | 测试 Webhook 推送 |

## 7. 搜索

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/search/repositories | 搜索仓库（q、sort、order） |
| GET | /v5/search/issues | 搜索 Issue |
| GET | /v5/search/users | 搜索用户 |

## 8. 组织（团队协作）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /v5/orgs/{org} | 获取组织信息 |
| PATCH | /v5/orgs/{org} | 更新组织资料（管理组织时） |
| GET | /v5/orgs/{org}/repos | 组织仓库列表 |
| POST | /v5/orgs/{org}/repos | 在组织下创建仓库 |
| GET | /v5/orgs/{org}/members | 组织成员列表 |
| GET | /v5/orgs/{org}/memberships/{username} | 组织成员及其权限 |
| PUT | /v5/orgs/{org}/memberships/{username} | 添加/调整成员权限（admin|master|developer|reporter|observer|tester） |
| DELETE | /v5/orgs/{org}/memberships/{username} | 移除组织成员 |
| DELETE | /v5/user/memberships/orgs/{org} | 退出组织 |

> 企业版（EnterprisesApi，`/v5/enterprises/{enterprise}/...`）接口规模很大但需企业版授权，此处未展开，需要时另行提取。

---

## 调用示例

```bash
# 列出仓库
curl -G "https://gitee.com/api/v5/user/repos" \
  -d access_token=YOUR_TOKEN -d per_page=100

# 读取文件
curl -G "https://gitee.com/api/v5/repos/{owner}/{repo}/contents/README.md" \
  -d access_token=YOUR_TOKEN -d ref=master

# 修改文件（先取 sha）
curl -X PUT "https://gitee.com/api/v5/repos/{owner}/{repo}/contents/README.md" \
  -H "Content-Type: application/json" \
  -d '{"access_token":"YOUR_TOKEN","sha":"...","content":"..."}'

# 创建 PR
curl -X POST "https://gitee.com/api/v5/repos/{owner}/{repo}/pulls" \
  -H "Content-Type: application/json" \
  -d '{"access_token":"YOUR_TOKEN","title":"fix: xxx","head":"feature-branch","base":"master"}'
```
