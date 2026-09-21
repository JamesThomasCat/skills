# Gitee token 读取与落地

变量名只认 `GITEE_ACCESS_TOKEN`。不扫描 `API_KEY`、`api_key`、`apiKey`、`ANTHROPIC_AUTH_TOKEN`、`ARK_*`。永远不要打印明文。

## 读取顺序

1. 命令行 `--token`（尽量不用，会进进程列表）
2. 当前进程环境变量 `GITEE_ACCESS_TOKEN`
3. 用户级文件 `~/.gitee-auto/env`（`--target env` 写入这里；Windows 同时写用户环境变量）
4. 本 skill 目录 `.env`（`--target dotenv`）

JSON 的 `auth` 只有 `token_present` 和 `token_source`（`cli` / `environ` / `user_env` / `dotenv`），没有令牌本身。

## 落地

在 skill 目录执行。令牌从**已设置的环境变量**或 stdin 读入，不要写在 argv 里。

```bash
python scripts/save_token.py --target env
python scripts/save_token.py --target dotenv
```

`--target session` 不写盘，只校验「有 token」。会话级由 Agent 在当前终端设置环境变量即可。

| target | 写入 | 说明 |
|--------|------|------|
| `env` | `~/.gitee-auto/env`；Windows 另写用户环境变量 | Windows 写入后需重启 Agent 才对所有窗口生效 |
| `dotenv` | `<skill>/.env`（gitignore） | 只给本 skill |
| `session` | 无 | 当前终端 |

文件权限在 POSIX 上为 `0600`。不要写入 `~/.claude/settings.json` 或 OpenClaw 的模型 Key。除用户选中的落地文件外，不要改本 skill 源文件（见 `SKILL.md`「源文件只读」）。

仅在扫描不到已有凭据时才向用户要令牌；话术见 `SKILL.md` 的 Token 一节，三项选择必须原样给出。
