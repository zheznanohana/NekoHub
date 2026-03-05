package com.nekohub.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen() {
    var gotifyUrl by remember { mutableStateOf("https://notify.diu.ac.cn") }
    var clientToken by remember { mutableStateOf("CqggBwFdy829eGB") }
    var appToken by remember { mutableStateOf("Akv0hW76C3mgfSe") }
    var filterMode by remember { mutableStateOf("keyword") }
    var keywords by remember { mutableStateOf("已扣费，已支付，支出") }
    
    var isTesting by remember { mutableStateOf(false) }
    var testResult by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    
    fun testConnection() {
        scope.launch {
            isTesting = true
            testResult = null
            try {
                val success = testGotifyConnection(gotifyUrl, clientToken)
                testResult = if (success) "✅ 连接成功！" else "❌ 连接失败，请检查配置"
            } catch (e: Exception) {
                testResult = "❌ 错误：${e.message}"
            } finally {
                isTesting = false
            }
        }
    }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F7FA))
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Gotify 配置
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color.White,
                    shape = MaterialTheme.shapes.medium,
                    shadowElevation = 2.dp
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Gotify 配置",
                            fontSize = 16.sp,
                            fontWeight = androidx.compose.ui.text.font.FontWeight.Medium,
                            color = Color(0xFF303133)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        OutlinedTextField(
                            value = gotifyUrl,
                            onValueChange = { gotifyUrl = it },
                            label = { Text("服务器 URL") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        
                        OutlinedTextField(
                            value = clientToken,
                            onValueChange = { clientToken = it },
                            label = { Text("Client Token (读取)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        
                        OutlinedTextField(
                            value = appToken,
                            onValueChange = { appToken = it },
                            label = { Text("App Token (发送)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        Button(
                            onClick = { testConnection() },
                            modifier = Modifier.fillMaxWidth().height(44.dp),
                            enabled = !isTesting
                        ) {
                            if (isTesting) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    strokeWidth = 2.dp,
                                    color = Color.White
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("测试中...")
                            } else {
                                Icon(Icons.Default.Wifi, contentDescription = null)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("测试连接")
                            }
                        }
                        
                        if (testResult != null) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = testResult ?: "",
                                color = if (testResult?.contains("✅") == true) Color(0xFF67C23A) else Color(0xFFF56C6C),
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }
            
            // 过滤配置
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color.White,
                    shape = MaterialTheme.shapes.medium,
                    shadowElevation = 2.dp
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "过滤配置",
                            fontSize = 16.sp,
                            fontWeight = androidx.compose.ui.text.font.FontWeight.Medium,
                            color = Color(0xFF303133)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        OutlinedTextField(
                            value = filterMode,
                            onValueChange = { filterMode = it },
                            label = { Text("过滤模式") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        
                        OutlinedTextField(
                            value = keywords,
                            onValueChange = { keywords = it },
                            label = { Text("关键字 (逗号分隔)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = false,
                            maxLines = 3
                        )
                    }
                }
            }
            
            // 版本信息
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color.White,
                    shape = MaterialTheme.shapes.medium,
                    shadowElevation = 2.dp
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "关于 NekoHub",
                            fontSize = 16.sp,
                            fontWeight = androidx.compose.ui.text.font.FontWeight.Medium
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("版本：v7.0 Final", color = Color(0xFF606266), fontSize = 13.sp)
                        Text("编译时间：2026-03-05", color = Color(0xFF606266), fontSize = 13.sp)
                        Text("真实 API + 完整功能", color = Color(0xFF606266), fontSize = 13.sp)
                    }
                }
            }
            
            // 版本信息
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color.White,
                    shape = MaterialTheme.shapes.medium,
                    shadowElevation = 2.dp
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "关于 NekoHub",
                            fontSize = 16.sp,
                            fontWeight = androidx.compose.ui.text.font.FontWeight.Medium
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("版本：v6.0 Real API", color = Color(0xFF606266), fontSize = 13.sp)
                        Text("编译时间：2026-03-05", color = Color(0xFF606266), fontSize = 13.sp)
                        Text("真实 API 调用", color = Color(0xFF606266), fontSize = 13.sp)
                    }
                }
            }
        }
    }
}


