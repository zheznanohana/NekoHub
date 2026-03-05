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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.URL

data class GotifyMessage(
    val id: Int,
    val title: String,
    val message: String,
    val date: String,
    val priority: Int,
    var isRead: Boolean
)

data class GotifyResponse(
    val messages: List<GotifyMessageRaw>
)

data class GotifyMessageRaw(
    val id: Int,
    val title: String?,
    val message: String,
    val date: String,
    val priority: Int
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InboxScreen() {
    var messages by remember { mutableStateOf(listOf<GotifyMessage>()) }
    var isLoading by remember { mutableStateOf(false) }
    var showError by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    
    // 从 Settings 读取配置
    var gotifyUrl by remember { mutableStateOf("") }
    var clientToken by remember { mutableStateOf("") }
    
    // 加载消息
    fun loadMessages() {
        scope.launch {
            isLoading = true
            try {
                val fetchedMessages = fetchGotifyMessages(gotifyUrl, clientToken)
                messages = fetchedMessages.map { msg ->
                    GotifyMessage(
                        id = msg.id,
                        title = msg.title ?: "无标题",
                        message = msg.message,
                        date = parseDate(msg.date),
                        priority = msg.priority,
                        isRead = false
                    )
                }.reversed() // 最新的在前
                showError = false
            } catch (e: Exception) {
                showError = true
                errorMessage = e.message ?: "加载失败"
            } finally {
                isLoading = false
            }
        }
    }
    
    // 初始加载
    LaunchedEffect(Unit) {
        loadMessages()
    }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F7FA))
    ) {
        Column(
            modifier = Modifier.fillMaxSize()
        ) {
            // 顶部操作栏
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
                        Text(
                            text = "收件箱 (${messages.size})",
                            fontSize = 16.sp,
                            fontWeight = androidx.compose.ui.text.font.FontWeight.Medium
                        )
                        
                        if (isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        }
                    }
                    
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        IconButton(
                            onClick = { loadMessages() },
                            modifier = Modifier.size(36.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Refresh,
                                contentDescription = "刷新",
                                tint = Color(0xFF409EFF)
                            )
                        }
                        
                        IconButton(
                            onClick = { messages = messages.map { it.copy(isRead = true) } },
                            modifier = Modifier.size(36.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.DoneAll,
                                contentDescription = "全部已读",
                                tint = Color(0xFF67C23A)
                            )
                        }
                        
                        IconButton(
                            onClick = { messages = emptyList() },
                            modifier = Modifier.size(36.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.DeleteSweep,
                                contentDescription = "清空",
                                tint = Color(0xFFF56C6C)
                            )
                        }
                    }
                }
            }
            
            // 错误提示
            if (showError) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color(0xFFFEF0F0)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "❌ $errorMessage",
                            fontSize = 13.sp,
                            color = Color(0xFFF56C6C)
                        )
                        TextButton(
                            onClick = { loadMessages() }
                        ) {
                            Text("重试", color = Color(0xFF409EFF))
                        }
                    }
                }
            }
            
            // 消息列表
            if (messages.isEmpty() && !isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            imageVector = Icons.Default.Inbox,
                            contentDescription = null,
                            modifier = Modifier.size(64.dp),
                            tint = Color(0xFFC0C4CC)
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("暂无消息", color = Color(0xFF909399))
                        Text("下拉刷新或点击刷新按钮", color = Color(0xFFC0C4CC), fontSize = 12.sp)
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(messages, key = { it.id }) { msg ->
                        MessageCard(
                            message = msg,
                            onToggleRead = {
                                messages = messages.map { m ->
                                    if (m.id == msg.id) m.copy(isRead = !m.isRead) else m
                                }
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun MessageCard(message: GotifyMessage, onToggleRead: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (message.isRead) Color.White else Color(0xFFECF5FF)
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
                .clickable { onToggleRead() }
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = message.title,
                    fontSize = 15.sp,
                    color = if (message.isRead) Color(0xFF606266) else Color(0xFF303133),
                    modifier = Modifier.weight(1f)
                )
                
                if (!message.isRead) {
                    Surface(
                        color = Color(0xFFF56C6C),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text(
                            text = "新",
                            color = Color.White,
                            fontSize = 11.sp,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(6.dp))
            
            Text(
                text = message.message,
                fontSize = 13.sp,
                color = Color(0xFF606266),
                maxLines = 3
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = message.date,
                fontSize = 12.sp,
                color = Color(0xFF909399)
            )
        }
    }
}

// 从 Gotify 获取消息（使用 HttpURLConnection + 简单 JSON 解析）
suspend fun fetchGotifyMessages(baseUrl: String, token: String): List<GotifyMessageRaw> {
    return withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/message?limit=50")
        val connection = url.openConnection() as java.net.HttpURLConnection
        connection.requestMethod = "GET"
        connection.setRequestProperty("X-Gotify-Key", token)
        connection.connectTimeout = 10000
        connection.readTimeout = 10000
        
        val responseCode = connection.responseCode
        if (responseCode == 200) {
            val response = connection.inputStream.bufferedReader().use { it.readText() }
            parseGotifyResponse(response)
        } else {
            throw Exception("Gotify 返回错误：$responseCode")
        }
    }
}

// 简单解析 Gotify JSON 响应
fun parseGotifyResponse(json: String): List<GotifyMessageRaw> {
    val messages = mutableListOf<GotifyMessageRaw>()
    
    // 提取 messages 数组
    val messagesStart = json.indexOf("\"messages\"")
    if (messagesStart == -1) return messages
    
    val arrayStart = json.indexOf("[", messagesStart)
    if (arrayStart == -1) return messages
    
    // 简单解析每个消息对象
    var pos = arrayStart + 1
    var depth = 1
    
    while (pos < json.length && depth > 0) {
        when (json[pos]) {
            '{' -> {
                val objStart = pos
                var objDepth = 1
                pos++
                while (pos < json.length && objDepth > 0) {
                    when (json[pos]) {
                        '{' -> objDepth++
                        '}' -> objDepth--
                    }
                    pos++
                }
                val objStr = json.substring(objStart, pos)
                
                // 解析字段
                val id = extractInt(objStr, "\"id\"") ?: 0
                val title = extractString(objStr, "\"title\"")
                val message = extractString(objStr, "\"message\"") ?: ""
                val date = extractString(objStr, "\"date\"") ?: ""
                val priority = extractInt(objStr, "\"priority\"") ?: 0
                
                if (message.isNotEmpty()) {
                    messages.add(GotifyMessageRaw(id, title, message, date, priority))
                }
            }
            ']' -> depth--
        }
        pos++
    }
    
    return messages
}

fun extractInt(json: String, key: String): Int? {
    val keyPos = json.indexOf(key)
    if (keyPos == -1) return null
    val colonPos = json.indexOf(":", keyPos)
    if (colonPos == -1) return null
    val start = colonPos + 1
    val end = json.indexOfAny(charArrayOf(',', '}'), start)
    if (end == -1) return null
    return json.substring(start, end).trim().toIntOrNull()
}

fun extractString(json: String, key: String): String? {
    val keyPos = json.indexOf(key)
    if (keyPos == -1) return null
    val colonPos = json.indexOf(":", keyPos)
    if (colonPos == -1) return null
    
    var start = colonPos + 1
    while (start < json.length && json[start].isWhitespace()) start++
    
    if (start >= json.length || json[start] != '"') return null
    start++
    
    val end = StringBuilder()
    var i = start
    while (i < json.length) {
        if (json[i] == '\\' && i + 1 < json.length) {
            i += 2
            continue
        }
        if (json[i] == '"') break
        i++
    }
    
    return json.substring(start, i).replace("\\n", "\n").replace("\\\"", "\"")
}

// 测试 Gotify 连接
suspend fun testGotifyConnection(baseUrl: String, token: String): Boolean {
    return withContext(Dispatchers.IO) {
        try {
            val url = URL("$baseUrl/message?limit=1")
            val connection = url.openConnection() as java.net.HttpURLConnection
            connection.requestMethod = "GET"
            connection.setRequestProperty("X-Gotify-Key", token)
            connection.connectTimeout = 5000
            
            val responseCode = connection.responseCode
            responseCode == 200
        } catch (e: Exception) {
            false
        }
    }
}

fun parseDate(dateStr: String): String {
    return try {
        // ISO 8601 格式：2026-03-05T10:00:00.000Z
        val parts = dateStr.split("T")
        if (parts.size >= 2) {
            val timePart = parts[1].split(".")[0]
            "${parts[0]} $timePart"
        } else {
            dateStr
        }
    } catch (e: Exception) {
        dateStr
    }
}
