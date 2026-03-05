# NekoHub Android

🐱 NekoHub 的 Android 原生客户端 - 使用 Kotlin + Jetpack Compose 开发

## 功能特性

- 📬 **收件箱** - 查看 Gotify 通知
- 🤖 **AI 对话** - 支持自定义 AI 模型，可读取通知和 RSS 数据
- ✅ **任务** - 自动化任务管理
- 📡 **转发** - 支持钉钉、Telegram、SMTP 转发
- 📰 **RSS** - RSS 订阅管理
- ⚙️ **设置** - Gotify 配置

## 技术栈

- **语言**: Kotlin 1.9
- **UI**: Jetpack Compose + Material Design 3
- **网络**: Retrofit + OkHttp
- **构建**: Gradle 8.2
- **最低版本**: Android 8.0 (API 26)

## 构建说明

### 环境要求

- Android Studio Hedgehog 或更高版本
- JDK 17
- Android SDK 34

### 编译

```bash
# 克隆项目
git clone https://github.com/zheznanohana/NekoHub-Android.git
cd NekoHub-Android

# 编译 Debug 版本
./gradlew assembleDebug

# APK 输出位置
app/build/outputs/apk/debug/app-debug.apk
```

## 配置说明

### 1. Gotify 配置

在设置中配置：
- Gotify 服务器 URL
- Client Token (用于读取通知)
- App Token (用于发送通知)

### 2. AI 模型配置

在 AI 聊天界面点击 ➕ 添加模型：
- 模型名称 (如：Kimi)
- API Base URL (如：https://api.moonshot.cn/v1)
- 模型名称 (如：moonshot-v1-8k)
- API Key

### 3. 后端 API 配置

修改 `RetrofitClient.kt`:
```kotlin
var BASE_URL = "http://YOUR_SERVER_IP:5000/api/"
```

## 安全提示

⚠️ **不要提交敏感信息到 Git！**

- API Keys
- 密码
- Token
- 服务器地址

所有敏感信息应由用户在应用中配置。

## 项目结构

```
app/src/main/java/com/nekohub/app/
├── MainActivity.kt          # 主活动
├── NekoHubApp.kt            # 应用入口
├── InboxScreen.kt           # 收件箱界面
├── AIChatScreen.kt          # AI 聊天界面
├── TasksScreen.kt           # 任务界面
├── ForwardScreen.kt         # 转发界面
├── RSSScreen.kt             # RSS 界面
├── SettingsScreen.kt        # 设置界面
├── CommonComponents.kt      # 通用组件
├── data/
│   ├── AppPreferences.kt    # 偏好设置
│   └── Repository.kt        # 数据仓库
└── network/
    ├── RetrofitClient.kt    # 网络客户端
    └── ApiService.kt        # API 接口
```

## 许可证

MIT License

## 作者

@zheznanohana

## 相关链接

- [NekoHub Web](https://github.com/zheznanohana/NekoHub)
- [Jetpack Compose](https://developer.android.com/jetpack/compose)
- [Material Design 3](https://m3.material.io/)
