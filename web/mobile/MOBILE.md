# 📱 NekoHub 手机版

## 🎉 新增功能

### 移动端优化
- ✅ 响应式布局（支持手机/平板/桌面）
- ✅ 移动端底部导航栏
- ✅ 触摸优化交互
- ✅ 防止双击缩放
- ✅ iPhone 刘海屏适配

### PWA 支持
- ✅ 可添加到手机桌面
- ✅ 离线缓存
- ✅ 深色模式支持
- ✅ 全屏显示

### Android APK
- ✅ Capacitor 原生封装
- ✅ GitHub Actions 自动编译
- ✅ 每次推送自动构建 APK

## 📥 下载 APK

访问 GitHub Releases 下载最新版本：
https://github.com/zheznanohana/NekoHub/releases

或者从 GitHub Actions 下载最新构建：
https://github.com/zheznanohana/NekoHub/actions

## 🌐 PWA 安装方法

### iOS Safari
1. 打开 NekoHub 网页
2. 点击底部 Safari 分享按钮
3. 选择"添加到主屏幕"
4. 点击"添加"

### Android Chrome
1. 打开 NekoHub 网页
2. 点击右上角菜单（三个点）
3. 选择"安装应用"或"添加到主屏幕"
4. 点击"添加"

## 🏗️ 自动编译

每次推送到 main 分支会自动触发 Android APK 编译：
- 编译时间：约 10-15 分钟
- APK 保留：30 天
- 下载：GitHub Actions → 选择构建 → 下载 artifacts

## 📋 功能列表

| 功能 | 桌面端 | 移动端 | APK |
|------|--------|--------|-----|
| 收件箱 | ✅ | ✅ | ✅ |
| AI 助手 | ✅ | ✅ | ✅ |
| 自动化任务 | ✅ | ✅ | ✅ |
| 通知转发 | ✅ | ✅ | ✅ |
| RSS 订阅 | ✅ | ✅ | ✅ |
| 系统设置 | ✅ | ✅ | ✅ |
| 深色模式 | ✅ | ✅ | ✅ |
| 离线访问 | ❌ | ✅ | ✅ |

## 🔧 本地开发

```bash
# 安装依赖
cd frontend
npm install

# 开发模式
npm run dev

# 构建 Web 版
npm run build

# 编译 Android APK
npx cap sync android
cd android
./gradlew assembleDebug
```

## 📦 技术栈

- **前端：** Vue 3 + Vite + Element Plus
- **移动端：** Capacitor
- **PWA：** Service Worker + Manifest
- **编译：** GitHub Actions

---

**最后更新：** 2026-03-05
**版本：** 1.0.0
