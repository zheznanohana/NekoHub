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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.StringReader
import javax.xml.parsers.DocumentBuilderFactory
import org.xml.sax.InputSource

data class RSSFeed(
    val id: Int,
    val name: String,
    val url: String,
    val lastUpdate: String,
    val unreadCount: Int
)

data class RSSArticle(
    val id: Int,
    val feedId: Int,
    val title: String,
    val link: String,
    val published: String,
    val description: String,
    val source: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RSSScreen(
    selectedFeedId: Int?,
    selectedArticleId: Int?,
    onFeedSelected: (Int?) -> Unit,
    onArticleSelected: (Int?) -> Unit
) {
    var feeds by remember { mutableStateOf(listOf<RSSFeed>()) }
    var articles by remember { mutableStateOf(listOf<RSSArticle>()) }
    var isLoading by remember { mutableStateOf(false) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var showAddDialog by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    
    LaunchedEffect(Unit) {
        feeds = listOf(
            RSSFeed(1, "少数派", "https://sspai.com/feed", "刚刚", 5),
            RSSFeed(2, "Hacker News", "https://news.ycombinator.com/rss", "刚刚", 12),
            RSSFeed(3, "Github Blog", "https://github.blog/feed", "刚刚", 3),
        )
    }
    
    val selectedFeed = feeds.find { it.id == selectedFeedId }
    val selectedArticle = articles.find { it.id == selectedArticleId }
    
    fun loadArticles(feed: RSSFeed) {
        scope.launch {
            isLoading = true
            loadError = null
            try {
                val xml = fetchUrl(feed.url)
                val items = parseRssFeed(xml)
                
                if (items.isEmpty()) {
                    loadError = "未解析到文章"
                    articles = emptyList()
                } else {
                    articles = items.mapIndexed { index, item ->
                        RSSArticle(
                            id = index + 1,
                            feedId = feed.id,
                            title = item["title"] ?: "",
                            link = item["link"] ?: "",
                            published = formatDate(item["pubDate"] ?: ""),
                            description = cleanHtml(item["description"] ?: "").take(200),
                            source = feed.name
                        )
                    }
                    loadError = null
                }
            } catch (e: Exception) {
                loadError = "加载失败：${e.message}"
                articles = emptyList()
            } finally {
                isLoading = false
            }
        }
    }
    
    LaunchedEffect(selectedFeedId) {
        if (selectedFeedId != null) {
            val feed = feeds.find { it.id == selectedFeedId }
            if (feed != null) {
                loadArticles(feed)
            }
        }
    }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF5F7FA))
    ) {
        if (selectedArticle != null) {
            ArticleDetailView(
                article = selectedArticle,
                onBack = { onArticleSelected(null) }
            )
        } else if (selectedFeed != null) {
            ArticleListView(
                feed = selectedFeed,
                articles = articles,
                isLoading = isLoading,
                loadError = loadError,
                onBack = { 
                    onFeedSelected(null)
                    articles = emptyList()
                    loadError = null
                },
                onRefresh = { loadArticles(selectedFeed) },
                onLoadSample = {
                    articles = (1..20).map { i ->
                        RSSArticle(
                            i, selectedFeed.id, "示例文章 $i",
                            "https://example.com/$i", "$i 分钟前",
                            "这是示例文章$i 的摘要内容...", selectedFeed.name
                        )
                    }
                },
                onArticleClick = { onArticleSelected(it.id) }
            )
        } else {
            FeedListView(
                feeds = feeds,
                onFeedClick = { onFeedSelected(it.id) },
                onAddClick = { showAddDialog = true },
                onDelete = { feed -> feeds = feeds.filter { it.id != feed.id } }
            )
        }
        
        if (showAddDialog) {
            AddFeedDialog(
                onDismiss = { showAddDialog = false },
                onConfirm = { name, url ->
                    feeds = feeds + RSSFeed(feeds.size + 1, name, url, "刚刚", 0)
                    showAddDialog = false
                }
            )
        }
    }
}

@Composable
fun FeedListView(
    feeds: List<RSSFeed>,
    onFeedClick: (RSSFeed) -> Unit,
    onAddClick: () -> Unit,
    onDelete: (RSSFeed) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize()
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
                Text(
                    text = "订阅源 (${feeds.size})",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium
                )
                
                IconButton(onClick = onAddClick, modifier = Modifier.size(40.dp)) {
                    Icon(Icons.Default.Add, contentDescription = "添加", tint = Color(0xFF409EFF))
                }
            }
        }
        
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp, 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(feeds, key = { it.id }) { feed ->
                FeedCard(
                    feed = feed,
                    onClick = { onFeedClick(feed) },
                    onDelete = { onDelete(feed) }
                )
            }
        }
    }
}

@Composable
fun FeedCard(feed: RSSFeed, onClick: () -> Unit, onDelete: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .clickable { onClick() }
            ) {
                Text(feed.name, fontSize = 16.sp, color = Color(0xFF303133))
                Spacer(modifier = Modifier.height(4.dp))
                Text(feed.url, fontSize = 12.sp, color = Color(0xFF909399), maxLines = 1)
                Spacer(modifier = Modifier.height(4.dp))
                Text("更新于 ${feed.lastUpdate}", fontSize = 12.sp, color = Color(0xFFC0C4CC))
            }
            
            IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Delete, contentDescription = "删除", tint = Color(0xFFF56C6C))
            }
        }
    }
}

@Composable
fun ArticleListView(
    feed: RSSFeed,
    articles: List<RSSArticle>,
    isLoading: Boolean,
    loadError: String?,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onLoadSample: () -> Unit,
    onArticleClick: (RSSArticle) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize()
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
                    IconButton(onClick = onBack, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                    Text(feed.name, fontSize = 16.sp, fontWeight = FontWeight.Medium)
                }
                
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                } else {
                    IconButton(onClick = onRefresh, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新", tint = Color(0xFF409EFF))
                    }
                }
            }
        }
        
        if (loadError != null) {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color(0xFFFEF0F0)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Text("❌ $loadError", fontSize = 13.sp, color = Color(0xFFF56C6C))
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = onRefresh) { Text("重试") }
                        Button(onClick = onLoadSample) { Text("使用示例数据") }
                    }
                }
            }
        } else if (articles.isEmpty() && !isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.RssFeed, contentDescription = null, modifier = Modifier.size(64.dp), tint = Color(0xFFC0C4CC))
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("暂无文章", color = Color(0xFF909399))
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp, 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(articles, key = { it.id }) { article ->
                    ArticleCard(article = article, onClick = { onArticleClick(article) })
                }
            }
        }
    }
}

@Composable
fun ArticleCard(article: RSSArticle, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
                .clickable { onClick() }
        ) {
            Text(article.title, fontSize = 15.sp, color = Color(0xFF303133), maxLines = 2)
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(article.source, fontSize = 12.sp, color = Color(0xFF409EFF))
                Text(article.published, fontSize = 12.sp, color = Color(0xFF909399))
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(article.description, fontSize = 13.sp, color = Color(0xFF606266), maxLines = 2)
        }
    }
}

@Composable
fun ArticleDetailView(article: RSSArticle, onBack: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize()
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
                    IconButton(onClick = onBack, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                    Text("文章详情", fontSize = 16.sp, fontWeight = FontWeight.Medium)
                }
            }
        }
        
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text(article.title, fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFF303133))
            }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(article.source, fontSize = 13.sp, color = Color(0xFF409EFF))
                    Text(article.published, fontSize = 13.sp, color = Color(0xFF909399))
                }
            }
            item { Divider() }
            item {
                Text(article.description, fontSize = 15.sp, color = Color(0xFF303133), lineHeight = 24.sp)
            }
            item { Spacer(modifier = Modifier.height(32.dp)) }
        }
    }
}

@Composable
fun AddFeedDialog(onDismiss: () -> Unit, onConfirm: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("新增 RSS 订阅") },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("名称") },
                    placeholder = { Text("少数派") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("URL") },
                    placeholder = { Text("https://sspai.com/feed") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onConfirm(name, url) },
                enabled = name.isNotBlank() && url.isNotBlank()
            ) { Text("添加") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("取消") }
        }
    )
}

// 获取 URL 内容
suspend fun fetchUrl(url: String): String {
    return withContext(Dispatchers.IO) {
        val connection = java.net.URL(url).openConnection() as java.net.HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 15000
        connection.readTimeout = 15000
        connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        connection.setRequestProperty("Accept", "application/rss+xml, application/xml, */*")
        connection.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9")
        
        val code = connection.responseCode
        if (code == 200) {
            connection.inputStream.bufferedReader().use { it.readText() }
        } else {
            throw Exception("HTTP $code")
        }
    }
}

// 解析 RSS Feed
fun parseRssFeed(xml: String): List<Map<String, String>> {
    val result = mutableListOf<Map<String, String>>()
    
    try {
        val factory = DocumentBuilderFactory.newInstance()
        factory.isNamespaceAware = false
        factory.isValidating = false
        
        val builder = factory.newDocumentBuilder()
        val doc = builder.parse(InputSource(StringReader(xml)))
        doc.documentElement.normalize()
        
        val items = doc.getElementsByTagName("item")
        
        for (i in 0 until items.length) {
            val item = items.item(i)
            val title = getText(item, "title")
            val link = getText(item, "link")
            val desc = getText(item, "description")
            val date = getText(item, "pubDate")
            
            if (title.isNotEmpty()) {
                result.add(mapOf(
                    "title" to title,
                    "link" to link,
                    "description" to desc,
                    "pubDate" to date
                ))
            }
        }
    } catch (e: Exception) {
        e.printStackTrace()
    }
    
    return result
}

fun getText(element: org.w3c.dom.Node, tag: String): String {
    return try {
        val nodes = (element as org.w3c.dom.Element).getElementsByTagName(tag)
        if (nodes.length > 0) nodes.item(0).textContent ?: "" else ""
    } catch (e: Exception) {
        ""
    }
}

fun cleanHtml(text: String): String {
    return text
        .replace(Regex("<[^>]*>"), "")
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .trim()
}

fun formatDate(date: String): String {
    return try {
        if (date.isEmpty()) return "未知时间"
        if (date.contains(",")) {
            val parts = date.split(",")
            if (parts.size >= 2) {
                val dt = parts[1].trim().split(" ")
                if (dt.size >= 3) "${dt[0]} ${dt[1]} ${dt[2]}" else date.take(19)
            } else date.take(19)
        } else if (date.contains("T")) {
            val parts = date.split("T")
            if (parts.size >= 2) {
                val time = parts[1].split(".")[0].split("Z")[0]
                "${parts[0]} $time"
            } else date.take(19)
        } else {
            date.take(19)
        }
    } catch (e: Exception) {
        date.take(19)
    }
}
