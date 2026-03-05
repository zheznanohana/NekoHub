package com.nekohub.app

import androidx.compose.foundation.background
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ForwardScreen() {
    // 全局设置
    var forwardEnabled by remember { mutableStateOf(false) }
    var forwardMode by remember { mutableStateOf(0) } // 0=全部，1=仅原始，2=仅 AI
    
    // 钉钉配置
    var dingtalkWebhook by remember { mutableStateOf("") }
    var dingtalkSecret by remember { mutableStateOf("") }
    
    // Telegram 配置
    var tgToken by remember { mutableStateOf("") }
    var tgChatId by remember { mutableStateOf("") }
    
    // SMTP 配置
    var smtpHost by remember { mutableStateOf("") }
    var smtpUser by remember { mutableStateOf("") }
    var smtpPass by remember { mutableStateOf("") }
    var smtpTo by remember { mutableStateOf("") }
    
    var isSaving by remember { mutableStateOf(false) }
    var showSaveSuccess by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F7FA))
            .verticalScroll(rememberScrollState())
    ) {
        // 全局设置
        SettingsSection(title = "全局设置") {
            // 转发开关
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "开启转发",
                        fontSize = 15.sp,
                        color = Color(0xFF303133)
                    )
                    Text(
                        text = "启用通知转发功能",
                        fontSize = 13.sp,
                        color = Color(0xFF909399)
                    )
                }
                Switch(
                    checked = forwardEnabled,
                    onCheckedChange = { forwardEnabled = it },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        checkedTrackColor = Color(0xFF409EFF)
                    )
                )
            }
            
            Divider(modifier = Modifier.padding(horizontal = 16.dp))
            
            // 转发模式
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Text(
                    text = "转发内容",
                    fontSize = 14.sp,
                    color = Color(0xFF606266),
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                
                ForwardModeSelector(
                    selectedMode = forwardMode,
                    onModeSelected = { forwardMode = it }
                )
            }
        }
        
        // 钉钉机器人
        SettingsSection(title = "钉钉机器人") {
            SettingsInput(
                label = "Webhook URL",
                value = dingtalkWebhook,
                onValueChange = { dingtalkWebhook = it },
                placeholder = "https://oapi.dingtalk.com/robot/send?access_token=...",
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Link,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
            
            SettingsInput(
                label = "加签密钥",
                value = dingtalkSecret,
                onValueChange = { dingtalkSecret = it },
                placeholder = "SEC...",
                isPassword = true,
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Key,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
        }
        
        // Telegram Bot
        SettingsSection(title = "Telegram Bot") {
            SettingsInput(
                label = "Bot Token",
                value = tgToken,
                onValueChange = { tgToken = it },
                placeholder = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.AlternateEmail,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
            
            SettingsInput(
                label = "Chat ID",
                value = tgChatId,
                onValueChange = { tgChatId = it },
                placeholder = "用户 ID 或群组 ID（-100 开头）",
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Person,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
        }
        
        // SMTP 邮件
        SettingsSection(title = "邮件 SMTP") {
            SettingsInput(
                label = "SMTP 服务器",
                value = smtpHost,
                onValueChange = { smtpHost = it },
                placeholder = "smtp.gmail.com",
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Dns,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
            
            SettingsInput(
                label = "发件邮箱",
                value = smtpUser,
                onValueChange = { smtpUser = it },
                placeholder = "your@gmail.com",
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Email,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
            
            SettingsInput(
                label = "授权码",
                value = smtpPass,
                onValueChange = { smtpPass = it },
                placeholder = "应用专用密码",
                isPassword = true,
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Key,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
            
            SettingsInput(
                label = "收件邮箱",
                value = smtpTo,
                onValueChange = { smtpTo = it },
                placeholder = "recipient@example.com",
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.MarkunreadMailbox,
                        contentDescription = null,
                        tint = Color(0xFF409EFF),
                        modifier = Modifier.size(20.dp)
                    )
                }
            )
        }
        
        // 保存和测试按钮
        Spacer(modifier = Modifier.height(24.dp))
        
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Button(
                onClick = {
                    isSaving = true
                    // TODO: 保存设置
                    scope.launch {
                        kotlinx.coroutines.delay(1000)
                        isSaving = false
                        showSaveSuccess = true
                    }
                },
                modifier = Modifier
                    .weight(1f)
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp),
                enabled = !isSaving
            ) {
                if (isSaving) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("保存中...")
                } else {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("保存配置")
                }
            }
            
            OutlinedButton(
                onClick = { /* TODO: 测试转发 */ },
                modifier = Modifier
                    .weight(1f)
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Send,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("测试转发")
            }
        }
        
        if (showSaveSuccess) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "✓ 配置已保存",
                color = Color(0xFF67C23A),
                fontSize = 14.sp,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
        }
        
        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
fun ForwardModeSelector(
    selectedMode: Int,
    onModeSelected: (Int) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        ForwardModeOption(
            mode = 0,
            title = "全部外转 (原始 + AI)",
            selectedMode = selectedMode,
            onModeSelected = onModeSelected
        )
        
        ForwardModeOption(
            mode = 1,
            title = "仅转发原始通知",
            selectedMode = selectedMode,
            onModeSelected = onModeSelected
        )
        
        ForwardModeOption(
            mode = 2,
            title = "仅转发 AI 分析结果",
            selectedMode = selectedMode,
            onModeSelected = onModeSelected
        )
    }
}

@Composable
fun ForwardModeOption(
    mode: Int,
    title: String,
    selectedMode: Int,
    onModeSelected: (Int) -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp),
        color = if (selectedMode == mode) Color(0xFFECF5FF) else Color.White,
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = title,
                fontSize = 14.sp,
                color = if (selectedMode == mode) Color(0xFF409EFF) else Color(0xFF303133)
            )
            
            RadioButton(
                selected = selectedMode == mode,
                onClick = { onModeSelected(mode) },
                colors = RadioButtonDefaults.colors(
                    selectedColor = Color(0xFF409EFF)
                )
            )
        }
    }
}


