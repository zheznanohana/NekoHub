# 🛠️ NekoHub 开发文档

## 项目结构

```
nekohub-web/
├── app/                          # 后端 Flask
│   ├── __init__.py              # 应用工厂
│   ├── config.py                # 配置
│   ├── routes/                  # API 路由
│   │   ├── api.py               # REST API
│   │   ├── ws.py                # WebSocket
│   │   └── openclaw.py          # OpenClaw 接口
│   ├── models/                  # 数据模型
│   │   ├── message.py           # 消息
│   │   ├── settings.py          # 设置
│   │   └── task.py              # 任务
│   └── services/                # 业务逻辑
│       ├── gotify.py            # Gotify 客户端
│       ├── ai.py                # AI 服务
│       ├── rss.py               # RSS 订阅
│       ├── imap.py              # 邮件
│       └── web3.py              # Web3
├── frontend/                     # Web 端前端 (原始)
├── mobile/                       # 移动端 (新增)
│   ├── frontend/                # 移动端前端
│   │   ├── src/
│   │   │   ├── App.vue          # 主应用 (含启动画面)
│   │   │   ├── main.js          # 入口
│   │   │   ├── components/      # 组件
│   │   │   │   ├── SplashScreen.vue  # 启动画面
│   │   │   │   ├── MainLayout.vue    # 主布局
│   │   │   │   ├── Inbox.vue         # 收件箱
│   │   │   │   ├── AIChat.vue        # AI 助手
│   │   │   │   ├── Tasks.vue         # 任务
│   │   │   │   ├── Forward.vue       # 转发
│   │   │   │   ├── RSS.vue           # RSS
│   │   │   │   ├── Settings.vue      # 设置
│   │   │   │   └── Login.vue         # 登录
│   │   │   ├── router/          # 路由
│   │   │   └── stores/          # Pinia 状态
│   │   ├── public/
│   │   │   ├── manifest.json    # PWA 配置
│   │   │   └── sw.js            # Service Worker
│   │   ├── android/             # Android 原生
│   │   │   ├── app/
│   │   │   │   ├── build.gradle
│   │   │   │   └── capacitor.build.gradle
│   │   │   └── build.gradle
│   │   ├── package.json
│   │   └── vite.config.js
│   └── .github/
│       └── workflows/
│           └── android-build.yml  # CI/CD
└── README.md
```

---

## 🚀 开发环境

### 前置要求

- Node.js 20+
- Java 17+
- Android SDK 34
- Git

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/zheznanohana/NekoHub.git
cd NekoHub

# 2. 安装前端依赖
cd mobile/frontend
npm install

# 3. 同步 Capacitor
npx cap sync android

# 4. 开发模式
npm run dev

# 5. 编译 APK
cd android
./gradlew assembleDebug
```

---

## 📱 移动端开发

### 目录结构

```
mobile/frontend/src/
├── App.vue              # 主应用组件
├── main.js              # 入口文件
├── components/          # 页面组件
│   ├── SplashScreen.vue # 启动画面
│   ├── MainLayout.vue   # 主布局
│   └── ...
├── router/              # 路由配置
└── stores/              # 状态管理
```

### 组件开发规范

#### 启动画面 (SplashScreen.vue)

```vue
<template>
  <div class="splash-screen">
    <!-- 动画内容 -->
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  props: {
    duration: { type: Number, default: 2000 }
  },
  emits: ['ready'],
  setup(props, { emit }) {
    // 实现逻辑
  }
}
</script>

<style scoped>
/* 样式 */
</style>
```

#### 主布局 (MainLayout.vue)

- 响应式设计
- 移动端底部导航
- 桌面端侧边栏
- 深色模式支持

### 样式规范

```css
/* 使用 CSS 变量 */
:root {
  --primary-color: #409eff;
  --bg-primary: #ffffff;
  --text-primary: #333333;
}

/* 深色模式 */
.dark-mode {
  --bg-primary: #1a1a1a;
  --text-primary: #ffffff;
}

/* 移动端优化 */
@media (max-width: 768px) {
  /* 移动端样式 */
}
```

---

## 🔧 构建配置

### Capacitor 配置

```json
{
  "appId": "com.nekohub.app",
  "appName": "NekoHub",
  "webDir": "dist",
  "bundledWebRuntime": false
}
```

### Gradle 配置

**app/build.gradle:**
```gradle
android {
    namespace = "com.nekohub.app"
    compileSdk = 34
    
    defaultConfig {
        applicationId "com.nekohub.app"
        minSdkVersion 26
        targetSdkVersion 34
        versionCode 1
        versionName "1.0.0"
    }
    
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
```

### Java 版本修复

Capacitor 5.x 默认使用 Java 21，需要修改为 Java 17：

```bash
# 修改 3 个文件
sed -i 's/JavaVersion.VERSION_21/JavaVersion.VERSION_17/g' \
  app/capacitor.build.gradle \
  capacitor-cordova-android-plugins/build.gradle \
  node_modules/@capacitor/android/capacitor/build.gradle
```

---

## 📦 发布流程

### 1. 更新版本号

```bash
# mobile/frontend/package.json
{
  "version": "1.0.0"
}

# mobile/frontend/android/app/build.gradle
versionCode 1
versionName "1.0.0"
```

### 2. 编译 Release APK

```bash
cd mobile/frontend/android
./gradlew assembleRelease
```

### 3. 签名 APK

```bash
# 创建密钥
keytool -genkey -v -keystore release-key.jks \
  -alias nekohub -keyalg RSA -keysize 2048 -validity 10000

# 签名
apksigner sign --ks release-key.jks \
  --out NekoHub-release.apk \
  app/build/outputs/apk/release/app-release-unsigned.apk
```

### 4. 创建 GitHub Release

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会自动：
- 编译 Release APK
- 签名
- 创建 Release
- 上传 APK

---

## 🧪 测试

### 单元测试

```bash
cd mobile/frontend
npm run test
```

### E2E 测试

```bash
npm run test:e2e
```

### 手动测试清单

- [ ] 启动画面显示正常
- [ ] 登录功能正常
- [ ] 各页面导航正常
- [ ] 深色模式切换正常
- [ ] 响应式布局正常
- [ ] 触摸反馈正常
- [ ] 通知推送正常
- [ ] 后台运行正常

---

## 🐛 常见问题

### Q: Java 版本错误
```
error: invalid source release: 21
```

**解决：** 修改 build.gradle 使用 Java 17

### Q: Capacitor sync 失败
```
ERROR: Unable to sync
```

**解决：**
```bash
npx cap clean
npx cap sync android
```

### Q: APK 签名失败
```
ERROR: Signing failed
```

**解决：** 检查密钥文件路径和密码

---

## 📚 参考资源

- [Vue 3 文档](https://vuejs.org/)
- [Capacitor 文档](https://capacitorjs.com/)
- [Element Plus 文档](https://element-plus.org/)
- [Android 开发文档](https://developer.android.com/)

---

**最后更新：** 2026-03-05  
**维护者：** 小爪 🐾
