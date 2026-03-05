package com.nekohub.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun NekoHubApp() {
    MainScreen()
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen() {
    var selectedTab by remember { mutableStateOf(0) }
    var rssSelectedFeed by remember { mutableStateOf<Int?>(null) }
    var rssSelectedArticle by remember { mutableStateOf<Int?>(null) }
    
    // 返回逻辑：文章详情→文章列表→订阅源列表→主页
    BackHandler(enabled = rssSelectedArticle != null) {
        rssSelectedArticle = null
    }
    
    BackHandler(enabled = rssSelectedFeed != null && rssSelectedArticle == null) {
        rssSelectedFeed = null
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Text(
                        text = when (selectedTab) {
                            0 -> "NekoHub"
                            1 -> "AI 聊天"
                            2 -> "任务"
                            3 -> "转发"
                            4 -> "RSS"
                            5 -> "设置"
                            else -> "NekoHub"
                        },
                        fontWeight = FontWeight.Medium
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF409EFF),
                    titleContentColor = Color.White
                )
            )
        },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Inbox, contentDescription = null) },
                    label = { Text("收件箱") },
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.SmartToy, contentDescription = null) },
                    label = { Text("AI") },
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.CalendarToday, contentDescription = null) },
                    label = { Text("任务") },
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Forward, contentDescription = null) },
                    label = { Text("转发") },
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.RssFeed, contentDescription = null) },
                    label = { Text("RSS") },
                    selected = selectedTab == 4,
                    onClick = { 
                        selectedTab = 4
                        rssSelectedFeed = null
                        rssSelectedArticle = null
                    }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Settings, contentDescription = null) },
                    label = { Text("设置") },
                    selected = selectedTab == 5,
                    onClick = { selectedTab = 5 }
                )
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues)) {
            when (selectedTab) {
                0 -> InboxScreen()
                1 -> AIChatScreen()
                2 -> TasksScreen()
                3 -> ForwardScreen()
                4 -> RSSScreen(
                    selectedFeedId = rssSelectedFeed,
                    selectedArticleId = rssSelectedArticle,
                    onFeedSelected = { rssSelectedFeed = it },
                    onArticleSelected = { rssSelectedArticle = it }
                )
                5 -> SettingsScreen()
            }
        }
    }
}
