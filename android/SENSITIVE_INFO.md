# NekoHub Android - 敏感信息配置

## ⚠️ 重要提示

**此文件包含敏感信息，不应提交到 Git！**

## Gotify 配置

```kotlin
// Gotify 服务器地址
val GOTIFY_URL = "https://YOUR_GOTIFY_SERVER"

// Gotify Client Token (用于读取通知)
val GOTIFY_CLIENT_TOKEN = "YOUR_CLIENT_TOKEN"

// Gotify App Token (用于发送通知)
val GOTIFY_APP_TOKEN = "YOUR_APP_TOKEN"
```

## AI 模型配置

用户可以在应用中添加自己的 AI 模型：
- API Base URL (如：https://api.moonshot.cn/v1)
- API Key (如：sk-xxxxx)
- 模型名称 (如：moonshot-v1-8k)

## 后端 API 配置

```kotlin
// NekoHub 后端服务器地址
val NEKOHUB_API_URL = "http://YOUR_SERVER_IP:5000/api/"
```

## 安全建议

1. **不要硬编码敏感信息**
   - 所有密码、token、API key 都应该由用户在应用中配置
   - 使用 Android Keystore 存储敏感数据

2. **使用环境变量**
   - 在 CI/CD 中使用环境变量注入配置
   - 不要将配置文件提交到 Git

3. **代码审查**
   - 提交前检查是否有敏感信息泄露
   - 使用 `git-secrets` 或类似工具自动检测
