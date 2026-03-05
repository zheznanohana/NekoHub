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

data class TaskItem(
    val id: Int,
    val name: String,
    val prompt: String,
    val mode: String, // count/time/interval
    val value: String,
    val domains: List<String>,
    val limits: Map<String, Int>,
    val enabled: Boolean,
    val runCount: Int
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TasksScreen() {
    var tasks by remember { mutableStateOf(listOf<TaskItem>()) }
    var showAddDialog by remember { mutableStateOf(false) }
    var editingTask by remember { mutableStateOf<TaskItem?>(null) }
    
    LaunchedEffect(Unit) {
        tasks = listOf(
            TaskItem(1, "每日天气播报", "总结今天的天气情况", "time", "08:00,20:00", listOf("gotify"), mapOf("gotify" to 10), true, 0),
            TaskItem(2, "邮件检查", "检查新邮件并总结", "interval", "60", listOf("imap"), mapOf("imap" to 5), true, 12),
            TaskItem(3, "らでん 监控", "监控 YouTube 更新", "count", "5", listOf("gotify", "rss"), mapOf("gotify" to 5, "rss" to 5), false, 3),
        )
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
                    Text(
                        text = "自动化任务 (${tasks.size})",
                        fontSize = 16.sp,
                        fontWeight = androidx.compose.ui.text.font.FontWeight.Medium
                    )
                    
                    IconButton(
                        onClick = { showAddDialog = true },
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Add,
                            contentDescription = "新建任务",
                            tint = Color(0xFF409EFF),
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
            
            // 使用指南
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color(0xFFECF5FF)
            ) {
                Column(
                    modifier = Modifier.padding(12.dp)
                ) {
                    Text(
                        text = "💡 使用指南",
                        fontSize = 14.sp,
                        fontWeight = androidx.compose.ui.text.font.FontWeight.Medium,
                        color = Color(0xFF409EFF)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "累计计数：每满 N 条通知运行一次",
                        fontSize = 12.sp,
                        color = Color(0xFF606266)
                    )
                    Text(
                        text = "定时触发：每天指定时间准点总结",
                        fontSize = 12.sp,
                        color = Color(0xFF606266)
                    )
                    Text(
                        text = "固定间隔：每隔 N 分钟梳理一次",
                        fontSize = 12.sp,
                        color = Color(0xFF606266)
                    )
                }
            }
            
            // 任务列表
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(tasks, key = { it.id }) { task ->
                    TaskCard(
                        task = task,
                        onEdit = { editingTask = task },
                        onDelete = { tasks = tasks.filter { t -> t.id != task.id } },
                        onToggle = { 
                            tasks = tasks.map { t -> 
                                if (t.id == task.id) t.copy(enabled = !t.enabled) else t 
                            }
                        },
                        onRun = {
                            tasks = tasks.map { t ->
                                if (t.id == task.id) t.copy(runCount = t.runCount + 1) else t
                            }
                        }
                    )
                }
                
                if (tasks.isEmpty()) {
                    item {
                        Box(
                            modifier = Modifier.fillMaxWidth(),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Icon(
                                    imageVector = Icons.Default.EventBusy,
                                    contentDescription = null,
                                    modifier = Modifier.size(64.dp),
                                    tint = Color(0xFFC0C4CC)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text("暂无任务", color = Color(0xFF909399))
                            }
                        }
                    }
                }
            }
        }
        
        // 添加/编辑任务对话框
        if (showAddDialog || editingTask != null) {
            TaskConfigDialog(
                task = editingTask,
                onDismiss = { 
                    showAddDialog = false
                    editingTask = null
                },
                onConfirm = { task ->
                    if (editingTask != null) {
                        tasks = tasks.map { t -> if (t.id == task.id) task else t }
                    } else {
                        tasks = tasks + task
                    }
                    showAddDialog = false
                    editingTask = null
                }
            )
        }
    }
}

@Composable
fun TaskCard(
    task: TaskItem,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onToggle: () -> Unit,
    onRun: () -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = Color.White
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // 标题栏
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Surface(
                        color = if (task.enabled) Color(0xFFF0F9FF) else Color(0xFFF5F7FA),
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            text = if (task.enabled) "已启用" else "已禁用",
                            color = if (task.enabled) Color(0xFF67C23A) else Color(0xFF909399),
                            fontSize = 12.sp,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                    Text(
                        text = task.name,
                        fontSize = 15.sp,
                        color = Color(0xFF303133)
                    )
                }
                
                Row {
                    IconButton(
                        onClick = onRun,
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = "执行",
                            tint = Color(0xFF67C23A),
                            modifier = Modifier.size(18.dp)
                        )
                    }
                    
                    IconButton(
                        onClick = onEdit,
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Edit,
                            contentDescription = "编辑",
                            tint = Color(0xFF409EFF),
                            modifier = Modifier.size(18.dp)
                        )
                    }
                    
                    Box {
                        IconButton(
                            onClick = { expanded = true },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.MoreVert,
                                contentDescription = "更多",
                                tint = Color(0xFF909399),
                                modifier = Modifier.size(18.dp)
                            )
                        }
                        
                        DropdownMenu(
                            expanded = expanded,
                            onDismissRequest = { expanded = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("删除", color = Color(0xFFF56C6C)) },
                                onClick = {
                                    onDelete()
                                    expanded = false
                                },
                                leadingIcon = {
                                    Icon(
                                        Icons.Default.Delete,
                                        contentDescription = null,
                                        tint = Color(0xFFF56C6C),
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                            )
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            // 任务指令
            Text(
                text = task.prompt,
                fontSize = 13.sp,
                color = Color(0xFF606266),
                modifier = Modifier.fillMaxWidth()
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            // 触发模式
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "触发模式",
                        fontSize = 12.sp,
                        color = Color(0xFF909399)
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = getModeName(task.mode),
                        fontSize = 13.sp,
                        color = Color(0xFF303133)
                    )
                }
                
                Column(
                    horizontalAlignment = Alignment.End
                ) {
                    Text(
                        text = "数据源",
                        fontSize = 12.sp,
                        color = Color(0xFF909399)
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        task.domains.forEach { domain ->
                            Surface(
                                color = getColorForDomain(domain),
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = getDomainName(domain),
                                    color = Color.White,
                                    fontSize = 11.sp,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            // 底部信息
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "已运行 ${task.runCount} 次",
                    fontSize = 12.sp,
                    color = Color(0xFF909399)
                )
                
                Switch(
                    checked = task.enabled,
                    onCheckedChange = { onToggle() },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        checkedTrackColor = Color(0xFF409EFF)
                    )
                )
            }
        }
    }
}

fun getModeName(mode: String): String {
    return when (mode) {
        "count" -> "累计计数"
        "time" -> "定时触发"
        "interval" -> "固定间隔"
        else -> mode
    }
}

fun getDomainName(domain: String): String {
    return when (domain) {
        "gotify" -> "通知"
        "rss" -> "订阅"
        else -> domain
    }
}

fun getColorForDomain(domain: String): Color {
    return when (domain) {
        "gotify" -> Color(0xFF409EFF)
        "rss" -> Color(0xFF67C23A)
        else -> Color(0xFF909399)
    }
}

@Composable
fun TaskConfigDialog(
    task: TaskItem?,
    onDismiss: () -> Unit,
    onConfirm: (TaskItem) -> Unit
) {
    var name by remember { mutableStateOf(task?.name ?: "") }
    var prompt by remember { mutableStateOf(task?.prompt ?: "") }
    var mode by remember { mutableStateOf(task?.mode ?: "count") }
    var value by remember { mutableStateOf(task?.value ?: "") }
    var domains by remember { mutableStateOf(task?.domains ?: listOf("gotify")) }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (task == null) "新建任务" else "编辑任务") },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 任务名称
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("任务名称") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                
                // 任务指令
                OutlinedTextField(
                    value = prompt,
                    onValueChange = { prompt = it },
                    label = { Text("任务指令") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2,
                    maxLines = 4
                )
                
                // 触发模式
                Column {
                    Text("触发模式", fontSize = 14.sp, color = Color(0xFF606266))
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = mode == "count",
                            onClick = { mode = "count" },
                            label = { Text("累计计数") }
                        )
                        FilterChip(
                            selected = mode == "time",
                            onClick = { mode = "time" },
                            label = { Text("定时触发") }
                        )
                        FilterChip(
                            selected = mode == "interval",
                            onClick = { mode = "interval" },
                            label = { Text("固定间隔") }
                        )
                    }
                }
                
                // 触发值
                OutlinedTextField(
                    value = value,
                    onValueChange = { value = it },
                    label = { Text(getModePlaceholder(mode)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                
                // 数据源
                Column {
                    Text("数据源", fontSize = 14.sp, color = Color(0xFF606266))
                    Spacer(modifier = Modifier.height(8.dp))
                    mapOf("gotify" to "📢 通知", "rss" to "📰 订阅").forEach { (domain, label) ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(label)
                            Checkbox(
                                checked = domain in domains,
                                onCheckedChange = { 
                                    domains = if (domain in domains) {
                                        domains - domain
                                    } else {
                                        domains + domain
                                    }
                                }
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val newTask = TaskItem(
                        id = task?.id ?: (System.currentTimeMillis() % 10000).toInt(),
                        name = name,
                        prompt = prompt,
                        mode = mode,
                        value = value,
                        domains = domains,
                        limits = domains.associateWith { 5 },
                        enabled = true,
                        runCount = task?.runCount ?: 0
                    )
                    onConfirm(newTask)
                },
                enabled = name.isNotBlank() && prompt.isNotBlank() && value.isNotBlank()
            ) {
                Text("确定")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("取消")
            }
        }
    )
}

fun getModePlaceholder(mode: String): String {
    return when (mode) {
        "count" -> "每满 N 条运行（如：5）"
        "time" -> "每天几点（如：08:00,20:00）"
        "interval" -> "每隔 N 分钟（如：60）"
        else -> ""
    }
}

@Composable
fun FilterChip(
    selected: Boolean,
    onClick: () -> Unit,
    label: @Composable () -> Unit
) {
    AssistChip(
        onClick = onClick,
        label = label,
        colors = AssistChipDefaults.assistChipColors(
            containerColor = if (selected) Color(0xFFECF5FF) else Color.White
        )
    )
}
