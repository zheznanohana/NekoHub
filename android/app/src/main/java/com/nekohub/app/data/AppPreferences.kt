package com.nekohub.app.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object AppPreferences {
    private const val PREF_NAME = "nekohub_prefs"
    private const val KEY_AI_MODELS = "ai_models"
    private const val KEY_CURRENT_MODEL = "current_model_id"
    private const val KEY_DATA_SOURCES = "data_sources"
    private const val KEY_LIMITS = "limits"
    
    private var prefs: SharedPreferences? = null
    
    fun init(context: Context) {
        if (prefs == null) {
            prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        }
    }
    
    fun getPrefs(): SharedPreferences {
        return prefs ?: throw IllegalStateException("AppPreferences not initialized")
    }
    
    // AI 模型配置
    fun saveAiModels(modelsJson: String) {
        getPrefs().edit().putString(KEY_AI_MODELS, modelsJson).apply()
    }
    
    fun getAiModels(): String? {
        return getPrefs().getString(KEY_AI_MODELS, null)
    }
    
    fun saveCurrentModelId(modelId: Long) {
        getPrefs().edit().putLong(KEY_CURRENT_MODEL, modelId).apply()
    }
    
    fun getCurrentModelId(): Long {
        return getPrefs().getLong(KEY_CURRENT_MODEL, -1)
    }
    
    // 数据源配置
    fun saveDataSources(sources: List<String>) {
        getPrefs().edit().putString(KEY_DATA_SOURCES, sources.joinToString(",")).apply()
    }
    
    fun getDataSources(): List<String> {
        val str = getPrefs().getString(KEY_DATA_SOURCES, "gotify,rss")
        return str?.split(",") ?: listOf("gotify", "rss")
    }
    
    // 条数限制
    fun saveLimits(limits: Map<String, Int>) {
        val str = limits.entries.joinToString(",") { "${it.key}=${it.value}" }
        getPrefs().edit().putString(KEY_LIMITS, str).apply()
    }
    
    fun getLimits(): Map<String, Int> {
        val str = getPrefs().getString(KEY_LIMITS, "gotify=10,rss=5") ?: "gotify=10,rss=5"
        return str.split(",").associate {
            val parts = it.split("=")
            if (parts.size == 2) parts[0] to parts[1].toInt() else "" to 0
        }.filterKeys { it.isNotEmpty() }
    }
}
