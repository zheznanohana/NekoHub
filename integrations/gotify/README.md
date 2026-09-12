# Gotify integration foundation

源码已下载至 `server/`，版本记录见 `upstream.json`，上游许可证保留在源码内。
源码目录为独立 Git checkout，由本目录的 `.gitignore` 排除，避免误提交嵌套仓库。
其他机器复现：从 upstream.json 指定 repository 克隆，再 checkout 指定 revision。

## 配置格式（v3 起）

Gotify 3.x 读取 dotenv 文件 `gotify-server.env`（工作目录下），不再读取 `config.yml`。
也可直接用同名环境变量覆盖；`GOTIFY_CONFIG_FILE` 可指定绝对路径。
完整键名见 `server/gotify-server.env.example`。

**`GOTIFY_DEFAULTUSER_PASS` 只在首次创建数据库时生效。** 改密码要么在 Web 界面改，
要么删除 `data/gotify.db` 重新初始化（会丢失全部消息）。

## 本机运行（当前部署方式，无需 Docker）

官方发行版二进制装在 `%LOCALAPPDATA%\NekoHubMemory\gotify\`（`gotify-windows-amd64.exe`，v3.1.0）。
同目录 `gotify-server.env` 内容：

```
GOTIFY_SERVER_LISTENADDR=127.0.0.1
GOTIFY_SERVER_PORT=18080
GOTIFY_DEFAULTUSER_NAME=admin
GOTIFY_DEFAULTUSER_PASS=<首次初始化时写入>
GOTIFY_REGISTRATION=false
GOTIFY_PASSSTRENGTH=10
```

`Start-NekoHub.ps1` 会在记忆服务之前拉起它并等待 `/health`。手动检查：

```powershell
Invoke-RestMethod http://127.0.0.1:18080/health
```

管理员密码、Client Token、Application Token 由 DPAPI 保存在
`%LOCALAPPDATA%\NekoHubMemory\environment.xml`，只有当前 Windows 用户能解密。读取方法：

```powershell
[System.Net.NetworkCredential]::new('', (Import-Clixml "$env:LOCALAPPDATA\NekoHubMemory\environment.xml")).Password | ConvertFrom-Json
```

- `MEMORY_GOTIFY_TOKEN` 是 **Client Token**，后台 worker 用它拉取消息。
- `GOTIFY_APP_TOKEN` 是 **Application Token**，用于发送通知（PC 设置里的发送 Token）。
- 默认只监听本机；手机接入前另行配置 TLS 和访问控制。

## 备选：Docker Compose

具备 Docker 时可用本目录 `compose.yaml`（镜像固定 3.1.0）：

```powershell
Copy-Item .env.example .env
# 在 .env 填写自己的 GOTIFY_ADMIN_PASSWORD 后执行
docker compose config --quiet
docker compose up -d
```

容器中的后续 NekoHub 服务应使用内部地址 `http://gotify:80`。
两种方式的数据互相独立，不要同时占用 18080。

## 停止与回滚

二进制方式：`Stop-Process -Id (Get-Content "$env:LOCALAPPDATA\NekoHubMemory\gotify.pid")`。
Compose 方式：`docker compose down` 停止服务并保留数据卷；不要附加 `-v`，除非明确要销毁消息。
首次导入前保存 PC 数据库副本；升级前停止 Gotify 并备份 `data/` 或完整数据卷。
若数据库迁移过，回滚使用匹配的旧版本和备份，不直接让旧版本打开新数据库。

完整设计见项目 `docs/daily-memory-design.md`。
