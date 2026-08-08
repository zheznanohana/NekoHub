

# NekoHub - Centro de Gestión de Notificaciones Multiplataforma

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Web%20%7C%20Android-blue)](https://github.com/zheznanohana/NekoHub)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🐱 **NekoHub** es un centro de gestión de notificaciones multiplataforma que soporta notificaciones de Gotify, suscripciones RSS, análisis inteligente con IA, automatización de tareas y más.

---

## 📱 Compatibilidad con Plataformas

| Plataforma | Stack Tecnológico | Estado | Ruta |
|------------|-------------------|--------|------|
| **PC (Windows)** | Python + PyQt5 | ✅ Estable | `/pc` |
| **Web** | Vue 3 + Flask | ✅ Estable | `/web` |
| **Android** | Kotlin + Jetpack Compose | ✅ Estable | `/android` |

---

## 🚀 Inicio Rápido

### Cliente PC (Windows)

```bash
cd pc

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python ui_app.py

# O empaquetar como exe
pyinstaller NekoHub.spec
```

**Funciones:**
- ✅ Gestión de notificaciones de Gotify
- ✅ Suscripciones RSS
- ✅ Análisis inteligente con IA
- ✅ Reenvío de notificaciones (DingTalk/Telegram/SMTP)
- ✅ Automatización de tareas
- ✅ Radar Web3
- ✅ Correo IMAP

---

### Cliente Web

```bash
cd web

# Instalar dependencias del backend
pip install -r requirements.txt

# Iniciar backend
python run.py

# Instalar dependencias del frontend
cd frontend
npm install
npm run dev
```

**Acceso:** http://localhost:5173

**Funciones:**
- ✅ Interfaz web responsiva
- ✅ Acceso multiplataforma
- ✅ Mismas funcionalidades que la versión PC

---

### Cliente Android

```bash
cd android

# Construir con Gradle
./gradlew assembleDebug

# Ubicación del APK generado
# app/build/outputs/apk/debug/app-debug.apk
```

**Funciones:**
- ✅ Aplicación nativa de Android
- ✅ Material Design 3
- ✅ Soporte sin conexión
- ✅ Envío de notificaciones push

---

## 📋 Funciones Principales

### 1. 📬 Buzón de Notificaciones
- Conexión al servidor Gotify
- Sincronización de notificaciones en tiempo real
- Gestión de leídos/no leídos
- Filtrado por palabras clave

### 2. 🤖 Análisis Inteligente con IA
- Soporte para modelos de IA personalizados
- Resumen inteligente del contenido de notificaciones
- Configuración de fuentes de datos (Gotify/RSS)
- Límites de análisis configurables

### 3. 📰 Suscripciones RSS
- Soporta RSS 2.0 / Atom 1.0
- Gestión de múltiples fuentes
- Navegación de lista de artículos y detalles

### 4. ⚡ Automatización de Tareas
- Activación por conteo
- Activación programada
- Activación por intervalo

### 5. 🔗 Reenvío de Notificaciones
- Bot de DingTalk
- Bot de Telegram
- Correo SMTP

---

## 📁 Estructura del Proyecto

```
NekoHub/
├── pc/                 # Cliente PC (Python + PyQt5)
│   ├── ui_*.py         # Interfaz UI
│   ├── plugin_*.py     # Sistema de plugins
│   ├── gotify_*.py     # Cliente Gotify
│   └── requirements.txt
├── web/                # Cliente Web (Vue 3 + Flask)
│   ├── frontend/       # Frontend Vue
│   ├── app/            # Backend Flask
│   └── requirements.txt
├── android/            # Cliente Android (Kotlin + Compose)
│   ├── app/            # Código fuente de la aplicación
│   ├── build.gradle.kts
│   └── README.md
├── docs/               # Documentación
└── README.md           # Este archivo
```

---

## ⚙️ Guía de Configuración

### Configuración de Gotify
- **URL del Servidor:** La URL de tu servidor Gotify
- **Client Token:** Token para leer mensajes
- **App Token:** Token para enviar mensajes

### Configuración de IA
- **URL Base de la API:** Dirección del proveedor de IA
- **API Key:** Tu clave API
- **Nombre del Modelo:** Identificador del modelo personalizado

### Configuración de RSS
- **URL de Suscripción:** Dirección del feed RSS/Atom
- **Intervalo de Actualización:** Frecuencia de refresco automático

---

## 🔒 Avisos de Seguridad

⚠️ **Los siguientes archivos contienen información sensible, no los subas a repositorios públicos:**

- `settings.json` - Configuración del usuario
- `neko_messages.db` - Base de datos local
- `.env` - Variables de entorno
- `*.jks` - Claves de firma de Android
- `local.properties` - Configuración local

---

## 📄 Licencia

Licencia MIT - Ver [LICENSE](LICENSE)

---

## 👤 Autor

**@zheznanohana**

- GitHub: https://github.com/zheznanohana
- Telegram: @tadokoro114810

---

## 🎯 Plan de Desarrollo

- [ ] Cliente iOS (SwiftUI)
- [ ] Extensión de navegador
- [ ] Soporte para más fuentes de notificación
- [ ] Sincronización en la nube

---

**🐾 Hecho con ❤️ por el Equipo de NekoHub**
