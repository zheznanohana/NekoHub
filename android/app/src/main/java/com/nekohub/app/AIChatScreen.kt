package com.nekohub.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.text.BasicTextField
import com.nekohub.app.data.AppPreferences
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

data class ChatMessage(
    val id: Int,
    val content: String,
    val isFromUser: Boolean,
    val time: String
)

data class AIModel(
    val id: Long,
    val name: String,
    val baseUrl: String,
    val model: String,
    var apiKey: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AIChatScreen() {
    val context = LocalContext.current
    var messages by remember { mutableStateOf(listOf<ChatMessage>()) }
    var inputText by remember { mutableStateOf("") }
    var showConfigDialog by remember { mutableStateOf(false) }
    var isSending by remember { mutableStateOf(false) }
    
    var modelConfigs by remember { mutableStateOf(listOf<AIModel>()) }
    var currentModelId by remember { mutableStateOf<Long?>(null) }
    var selectedDataSources by remember { mutableStateOf(listOf("gotify", "rss")) }
    var limits by remember { mutableStateOf(mapOf("gotify" to 10, "rss" to 5)) }
    
    val scope = rememberCoroutineScope()
    var nextId by remember { mutableStateOf(1L) }
    
    LaunchedEffect(Unit) {
        AppPreferences.init(context)
        
        val savedModels = AppPreferences.getAiModels()
        val savedCurrentId = AppPreferences.getCurrentModelId()
        val savedSources = AppPreferences.getDataSources()
        val savedLimits = AppPreferences.getLimits()
        
        if (savedModels != null && savedModels.isNotEmpty()) {
            modelConfigs = parseModelsFromJson(savedModels)
            if (savedCurrentId > 0) {
                currentModelId = savedCurrentId
            }
        }
        
        selectedDataSources = savedSources
        limits = savedLimits
        
        messages = listOf(
            ChatMessage(1, "你好！我是 NekoHub AI 助手\n\n💡 点击右上角 ➕ 添加模型后即可使用", false, "刚刚")
        )
    }
    
    fun saveConfig() {
        val modelsJson = modelsToJson(modelConfigs)
        AppPreferences.saveAiModels(modelsJson)
        currentModelId?.let { AppPreferences.saveCurrentModelId(it) }
        AppPreferences.saveDataSources(selectedDataSources)
        AppPreferences.saveLimits(limits)
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F7FA))
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = Color.White,
            shadowElevation = 2.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.SmartToy,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                    Text(
                        text = if (currentModelId != null) {
                            modelConfigs.find { it.id == currentModelId }?.name ?: "AI 模型"
                        } else {
                            "未配置模型"
                        },
                        fontSize = 15.sp,
                        fontWeight = if (currentModelId != null) 
                            androidx.compose.ui.text.font.FontWeight.Medium 
                        else 
                            androidx.compose.ui.text.font.FontWeight.Normal,
                        color = if (currentModelId != null) Color(0xFF303133) else Color(0xFFF56C6C)
                    )
                }
                
                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    IconButton(
                        onClick = { showConfigDialog = true },
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Add,
                            contentDescription = "添加模型",
                            tint = Color(0xFF67C23A),
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    
                    IconButton(
                        onClick = { showConfigDialog = true },
                        modifier = Modifier.size(40.dp),
                        enabled = modelConfigs.isNotEmpty()
                    ) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = "AI 配置",
                            tint = if (modelConfigs.isNotEmpty()) Color(0xFF606266) else Color(0xFFC0C4CC),
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }
        
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(messages, key = { it.id }) { msg ->
                ChatBubble(message = msg)
            }
            
            if (isSending) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Start
                    ) {
                        Surface(
                            color = Color(0xFFE8F5E9),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    strokeWidth = 2.dp
                                )
                                Text("思考中...", color = Color(0xFF606266), fontSize = 14.sp)
                            }
                        }
                    }
                }
            }
        }
        
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = Color.White,
            shadowElevation = 4.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                Surface(
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(max = 120.dp),
                    color = Color(0xFFF5F7FA),
                    shape = RoundedCornerShape(20.dp)
                ) {
                    BasicTextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        textStyle = TextStyle(fontSize = 14.sp, color = Color(0xFF303133))
                    )
                }
                
                Button(
                    onClick = {
                        if (inputText.isNotBlank() && !isSending) {
                            val userMessage = ChatMessage(
                                messages.size + 1,
                                inputText,
                                true,
                                "刚刚"
                            )
                            messages = messages + userMessage
                            val currentInput = inputText
                            inputText = ""
                            
                            isSending = true
                            
                            scope.launch {
                                val model = currentModelId?.let { id -> modelConfigs.find { it.id == id } }
                                
                                if (model == null) {
                                    val aiResponse = ChatMessage(
                                        messages.size + 1,
                                        "⚠️ 请先添加模型",
                                        false,
                                        "刚刚"
                                    )
                                    messages = messages + aiResponse
                                    isSending = false
                                } else if (model.apiKey.isNullOrEmpty()) {
                                    val aiResponse = ChatMessage(
                                        messages.size + 1,
                                        "⚠️ 请先配置 API Key",
                                        false,
                                        "刚刚"
                                    )
                                    messages = messages + aiResponse
                                    isSending = false
                                } else {
                                    try {
                                        val contextData = buildContextData(selectedDataSources, limits)
                                        val fullMessage = if (contextData.isNotEmpty()) {
                                            "$currentInput\n\n[相关数据]\n$contextData"
                                        } else {
                                            currentInput
                                        }
                                        
                                        val response = callAIApiReal(
                                            baseUrl = model.baseUrl,
                                            apiKey = model.apiKey,
                                            model = model.model,
                                            message = fullMessage
                                        )
                                        val aiResponse = ChatMessage(
                                            messages.size + 1,
                                            response,
                                            false,
                                            "刚刚"
                                        )
                                        messages = messages + aiResponse
                                    } catch (e: Exception) {
                                        val aiResponse = ChatMessage(
                                            messages.size + 1,
                                            "❌ ${e.message}",
                                            false,
                                            "刚刚"
                                        )
                                        messages = messages + aiResponse
                                    } finally {
                                        isSending = false
                                    }
                                }
                            }
                        }
                    },
                    modifier = Modifier
                        .height(48.dp)
                        .width(48.dp),
                    shape = RoundedCornerShape(24.dp),
                    enabled = inputText.isNotBlank() && !isSending
                ) {
                    Icon(
                        imageVector = Icons.Default.Send,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
        
        if (showConfigDialog) {
            AIConfigDialog(
                models = modelConfigs,
                currentModelId = currentModelId,
                selectedDataSources = selectedDataSources,
                limits = limits,
                onDismiss = { 
                    saveConfig()
                    showConfigDialog = false 
                },
                onModelSelected = { 
                    currentModelId = it
                    saveConfig()
                },
                onAddModel = { name, baseUrl, model, apiKey ->
                    val newModel = AIModel(nextId, name, baseUrl, model, apiKey)
                    modelConfigs = modelConfigs + newModel
                    if (currentModelId == null) {
                        currentModelId = nextId
                    }
                    nextId++
                    saveConfig()
                },
                onDeleteModel = { modelId ->
                    modelConfigs = modelConfigs.filter { it.id != modelId }
                    if (currentModelId == modelId) {
                        currentModelId = modelConfigs.firstOrNull()?.id
                    }
                    saveConfig()
                },
                onApiKeyUpdated = { modelId, apiKey ->
                    modelConfigs = modelConfigs.map { m ->
                        if (m.id == modelId) m.copy(apiKey = apiKey) else m
                    }
                    saveConfig()
                },
                onBaseUrlUpdated = { modelId, baseUrl ->
                    modelConfigs = modelConfigs.map { m ->
                        if (m.id == modelId) m.copy(baseUrl = baseUrl) else m
                    }
                    saveConfig()
                },
                onDataSourceToggled = { dataSource ->
                    selectedDataSources = if (dataSource in selectedDataSources) {
                        selectedDataSources - dataSource
                    } else {
                        selectedDataSources + dataSource
                    }
                    saveConfig()
                },
                onLimitChanged = { source, limit ->
                    limits = limits + (source to limit)
                    saveConfig()
                }
            )
        }
    }
}

@Composable
fun ChatBubble(message: ChatMessage) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (message.isFromUser) Arrangement.End else Arrangement.Start
    ) {
        Surface(
            color = if (message.isFromUser) Color(0xFF409EFF) else Color(0xFFE8F5E9),
            shape = RoundedCornerShape(
                topStart = 16.dp,
                topEnd = 16.dp,
                bottomStart = if (message.isFromUser) 16.dp else 4.dp,
                bottomEnd = if (message.isFromUser) 4.dp else 16.dp
            )
        ) {
            Column(
                modifier = Modifier.padding(12.dp)
            ) {
                Text(
                    text = message.content,
                    color = if (message.isFromUser) Color.White else Color(0xFF303133),
                    fontSize = 14.sp,
                    lineHeight = 20.sp
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = message.time,
                    color = if (message.isFromUser) Color(0xFFE0E0E0) else Color(0xFF909399),
                    fontSize = 11.sp,
                    textAlign = TextAlign.End,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

@Composable
fun AIConfigDialog(
    models: List<AIModel>,
    currentModelId: Long?,
    selectedDataSources: List<String>,
    limits: Map<String, Int>,
    onDismiss: () -> Unit,
    onModelSelected: (Long) -> Unit,
    onAddModel: (String, String, String, String) -> Unit,
    onDeleteModel: (Long) -> Unit,
    onApiKeyUpdated: (Long, String) -> Unit,
    onBaseUrlUpdated: (Long, String) -> Unit,
    onDataSourceToggled: (String) -> Unit,
    onLimitChanged: (String, Int) -> Unit
) {
    var showAddDialog by remember { mutableStateOf(false) }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("AI 模型配置") },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("我的模型", fontSize = 14.sp, color = Color(0xFF606266))
                        IconButton(
                            onClick = { showAddDialog = true },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Add,
                                contentDescription = "添加模型",
                                tint = Color(0xFF67C23A),
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    if (models.isEmpty()) {
                        Text(
                            text = "暂无模型，点击右上角 ➕ 添加",
                            fontSize = 13.sp,
                            color = Color(0xFF909399),
                            fontStyle = androidx.compose.ui.text.font.FontStyle.Italic
                        )
                    } else {
                        models.forEach { model ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onModelSelected(model.id) }
                                    .padding(8.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Row(
                                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = model.name,
                                            fontSize = 15.sp,
                                            color = if (model.id == currentModelId) Color(0xFF409EFF) else Color(0xFF303133)
                                        )
                                        if (model.id == currentModelId) {
                                            Surface(
                                                color = Color(0xFF67C23A),
                                                shape = RoundedCornerShape(4.dp)
                                            ) {
                                                Text(
                                                    text = "使用中",
                                                    color = Color.White,
                                                    fontSize = 10.sp,
                                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                                )
                                            }
                                        }
                                    }
                                    Text(
                                        text = model.model,
                                        fontSize = 11.sp,
                                        color = Color(0xFF909399)
                                    )
                                }
                                
                                Row {
                                    IconButton(
                                        onClick = { onDeleteModel(model.id) },
                                        modifier = Modifier.size(32.dp)
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Delete,
                                            contentDescription = "删除",
                                            tint = Color(0xFFF56C6C),
                                            modifier = Modifier.size(16.dp)
                                        )
                                    }
                                    RadioButton(
                                        selected = model.id == currentModelId,
                                        onClick = { onModelSelected(model.id) }
                                    )
                                }
                            }
                        }
                    }
                }
                
                Divider()
                
                Column {
                    Text("数据源", fontSize = 14.sp, color = Color(0xFF606266))
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("📢 通知", fontSize = 14.sp)
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            OutlinedTextField(
                                value = (limits["gotify"] ?: 10).toString(),
                                onValueChange = { 
                                    val num = it.toIntOrNull() ?: 10
                                    onLimitChanged("gotify", num.coerceIn(1, 100))
                                },
                                modifier = Modifier.width(60.dp),
                                singleLine = true,
                                textStyle = TextStyle(fontSize = 13.sp),
                                placeholder = { Text("10", fontSize = 13.sp) }
                            )
                            Checkbox(
                                checked = "gotify" in selectedDataSources,
                                onCheckedChange = { onDataSourceToggled("gotify") }
                            )
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(4.dp))
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("📰 RSS", fontSize = 14.sp)
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            OutlinedTextField(
                                value = (limits["rss"] ?: 5).toString(),
                                onValueChange = { 
                                    val num = it.toIntOrNull() ?: 5
                                    onLimitChanged("rss", num.coerceIn(1, 50))
                                },
                                modifier = Modifier.width(60.dp),
                                singleLine = true,
                                textStyle = TextStyle(fontSize = 13.sp),
                                placeholder = { Text("5", fontSize = 13.sp) }
                            )
                            Checkbox(
                                checked = "rss" in selectedDataSources,
                                onCheckedChange = { onDataSourceToggled("rss") }
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "💡 AI 可以读取选中的数据源进行分析",
                    fontSize = 12.sp,
                    color = Color(0xFF909399)
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("完成")
            }
        }
    )
    
    if (showAddDialog) {
        AddModelDialog(
            onDismiss = { showAddDialog = false },
            onConfirm = { name, baseUrl, model, apiKey ->
                onAddModel(name, baseUrl, model, apiKey)
                showAddDialog = false
            }
        )
    }
}

@Composable
fun AddModelDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String, String, String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var baseUrl by remember { mutableStateOf("https://api.moonshot.cn/v1") }
    var model by remember { mutableStateOf("moonshot-v1-8k") }
    var apiKey by remember { mutableStateOf("") }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("添加 AI 模型") },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("模型名称 *") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("Kimi") }
                )
                
                OutlinedTextField(
                    value = baseUrl,
                    onValueChange = { baseUrl = it },
                    label = { Text("API Base URL *") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("https://api.moonshot.cn/v1") }
                )
                
                OutlinedTextField(
                    value = model,
                    onValueChange = { model = it },
                    label = { Text("模型名称 *") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("moonshot-v1-8k") }
                )
                
                OutlinedTextField(
                    value = apiKey,
                    onValueChange = { apiKey = it },
                    label = { Text("API Key *") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("sk-xxxxxxxx") }
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onConfirm(name, baseUrl, model, apiKey) },
                enabled = name.isNotBlank() && baseUrl.isNotBlank() && model.isNotBlank()
            ) {
                Text("添加")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("取消")
            }
        }
    )
}

fun modelsToJson(models: List<AIModel>): String {
    return models.joinToString("|||") { "${it.id}|${it.name}|${it.baseUrl}|${it.model}|${it.apiKey}" }
}

fun parseModelsFromJson(json: String): List<AIModel> {
    return json.split("|||").mapNotNull { line ->
        val parts = line.split("|")
        if (parts.size == 5) {
            AIModel(
                id = parts[0].toLongOrNull() ?: 0,
                name = parts[1],
                baseUrl = parts[2],
                model = parts[3],
                apiKey = parts[4]
            )
        } else null
    }
}

// 使用 JSONObject 构建 JSON - 和 Python 的 json.dumps 一样安全
suspend fun callAIApiReal(baseUrl: String, apiKey: String, model: String, message: String): String {
    return withContext(Dispatchers.IO) {
        var connection: HttpURLConnection? = null
        try {
            // 清理 URL
            val cleanBase = baseUrl.trim().trimEnd('/')
            val apiUrl = "$cleanBase/chat/completions"
            
            val url = URL(apiUrl)
            connection = url.openConnection() as HttpURLConnection
            
            // 请求配置
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Authorization", "Bearer $apiKey")
            connection.setRequestProperty("Accept", "application/json")
            connection.connectTimeout = 30000
            connection.readTimeout = 60000
            connection.doInput = true
            connection.doOutput = true
            connection.useCaches = false
            
            // 使用 JSONObject 构建 JSON - 自动转义特殊字符
            val payload = JSONObject()
            payload.put("model", model)
            
            val messages = org.json.JSONArray()
            
            val systemMsg = JSONObject()
            systemMsg.put("role", "system")
            systemMsg.put("content", "你是专业的信息处理助手。")
            messages.put(systemMsg)
            
            val userMsg = JSONObject()
            userMsg.put("role", "user")
            userMsg.put("content", message)  // JSONObject 会自动转义特殊字符
            messages.put(userMsg)
            
            payload.put("messages", messages)
            payload.put("temperature", 0.7)
            
            val jsonBody = payload.toString()
            
            // 发送
            val writer = OutputStreamWriter(connection.outputStream, "UTF-8")
            writer.write(jsonBody)
            writer.flush()
            writer.close()
            
            // 响应
            val code = connection.responseCode
            
            if (code == 200) {
                val response = connection.inputStream.bufferedReader().use { it.readText() }
                parseAIResponse(response)
            } else {
                val errorBody = try {
                    connection.errorStream?.bufferedReader()?.use { it.readText() } ?: "无错误信息"
                } catch (e: Exception) {
                    "无法读取"
                }
                throw Exception("API 错误 $code: $errorBody")
            }
        } catch (e: Exception) {
            throw Exception("API 调用失败：${e.message}")
        } finally {
            connection?.disconnect()
        }
    }
}

fun parseAIResponse(json: String): String {
    return try {
        val jsonObj = JSONObject(json)
        val choices = jsonObj.getJSONArray("choices")
        if (choices.length() == 0) return "无响应"
        
        val firstChoice = choices.getJSONObject(0)
        val message = firstChoice.getJSONObject("message")
        message.getString("content")
    } catch (e: Exception) {
        "解析失败：${e.message}"
    }
}

suspend fun buildContextData(dataSources: List<String>, limits: Map<String, Int>): String {
    val context = StringBuilder()
    
    if ("gotify" in dataSources) {
        val limit = limits["gotify"] ?: 10
        try {
            // TODO: 用户需要在设置中配置 Gotify URL 和 Token
            val messages = fetchGotifyMessages("https://YOUR_GOTIFY_SERVER", "YOUR_CLIENT_TOKEN")
            val recent = messages.take(limit)
            if (recent.isNotEmpty()) {
                context.append("📢 最近通知 ($limit 条):\n")
                recent.forEachIndexed { i, msg ->
                    context.append("${i + 1}. 【${msg.title}】${msg.message}\n")
                }
                context.append("\n")
            }
        } catch (e: Exception) {
            context.append("📢 通知：无法获取\n\n")
        }
    }
    
    if ("rss" in dataSources) {
        val limit = limits["rss"] ?: 5
        try {
            val articles = fetchRSSFeedReal("https://sspai.com/feed")
            val recent = articles.take(limit)
            if (recent.isNotEmpty()) {
                context.append("📰 最新文章 ($limit 条):\n")
                recent.forEachIndexed { i, article ->
                    context.append("${i + 1}. ${article["title"]}\n")
                }
                context.append("\n")
            }
        } catch (e: Exception) {
            context.append("📰 RSS：无法获取\n\n")
        }
    }
    
    return context.toString()
}

suspend fun fetchRSSFeedReal(url: String): List<Map<String, String>> {
    return withContext(Dispatchers.IO) {
        try {
            val connection = URL(url).openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 15000
            connection.readTimeout = 15000
            connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            connection.setRequestProperty("Accept", "application/rss+xml, application/xml, */*")
            
            val responseCode = connection.responseCode
            if (responseCode == 200) {
                val response = connection.inputStream.bufferedReader().use { it.readText() }
                parseRSSXmlSimple(response)
            } else {
                throw Exception("HTTP $responseCode")
            }
        } catch (e: Exception) {
            throw e
        }
    }
}

fun parseRSSXmlSimple(xml: String): List<Map<String, String>> {
    val articles = mutableListOf<Map<String, String>>()
    try {
        val factory = javax.xml.parsers.DocumentBuilderFactory.newInstance()
        factory.isNamespaceAware = false
        val builder = factory.newDocumentBuilder()
        val doc = builder.parse(org.xml.sax.InputSource(java.io.StringReader(xml)))
        
        val items = doc.getElementsByTagName("item")
        for (i in 0 until items.length) {
            val item = items.item(i)
            val title = getTextContent(item, "title")
            val link = getTextContent(item, "link")
            val desc = getTextContent(item, "description")
            
            if (title.isNotEmpty()) {
                articles.add(mapOf("title" to title, "link" to link, "description" to desc))
            }
        }
    } catch (e: Exception) {
        e.printStackTrace()
    }
    return articles
}

fun getTextContent(element: org.w3c.dom.Node, tagName: String): String {
    return try {
        val nodes = (element as org.w3c.dom.Element).getElementsByTagName(tagName)
        if (nodes.length > 0) nodes.item(0).textContent ?: "" else ""
    } catch (e: Exception) {
        ""
    }
}
