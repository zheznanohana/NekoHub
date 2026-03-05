# plugin_rss.py
import feedparser, threading, webbrowser, json, time
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QSplitter, QFrame
from qfluentwidgets import (PushButton, LineEdit, TextEdit, CommandBar, Action, FluentIcon, 
                            MessageBoxBase, TitleLabel, SubtitleLabel, BodyLabel, InfoBar, StrongBodyLabel)

class RssReaderDialog(MessageBoxBase):
    def __init__(self, parent_window, title, content, link, lang):
        super().__init__(parent_window)
        is_en = lang == "English"
        self.viewLayout.addWidget(SubtitleLabel(title))
        self.viewLayout.setContentsMargins(24, 24, 24, 24)
        self.content = TextEdit()
        self.content.setMarkdown(content)
        self.content.setReadOnly(True)
        self.content.setFixedHeight(400)
        self.viewLayout.addWidget(self.content)
        self.btn_link = PushButton("打开原文" if not is_en else "Open Link")
        self.btn_link.clicked.connect(lambda: webbrowser.open(link))
        self.viewLayout.addWidget(self.btn_link)
        self.widget.setMinimumWidth(600)

class RssPage(QWidget):
    new_item_signal = Signal(str, str, str)
    fetch_finished = Signal()

    def __init__(self, get_settings, save_settings, lang="简体中文"):
        super().__init__()
        self.setObjectName("rss_page")
        self.get_settings, self.save_settings, self.lang = get_settings, save_settings, lang
        self.is_en = lang == "English"
        self.seen_guids, self.feed_cache = set(), {}
        self.sources = [] # [{name, url}]

        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18)
        root.addWidget(TitleLabel("RSS Feed Center" if self.is_en else "RSS 订阅中心"))
        
        # 1. 顶部工具栏
        self.cmd_bar = CommandBar(self)
        self.act_refresh = Action(FluentIcon.SYNC, '刷新同步' if not self.is_en else 'Sync All', triggered=self._manual_refresh)
        self.act_add = Action(FluentIcon.ADD, '新增订阅' if not self.is_en else 'Add Feed', triggered=self._add_source)
        self.act_del = Action(FluentIcon.DELETE, '删除订阅' if not self.is_en else 'Delete', triggered=self._delete_source)
        self.cmd_bar.addActions([self.act_refresh, self.act_add, self.act_del])
        root.addWidget(self.cmd_bar)

        # 2. 中间列表区
        self.splitter = QSplitter(Qt.Horizontal)
        self.source_list = QListWidget(); self.source_list.itemClicked.connect(self._on_source_clicked)
        self.article_list = QListWidget(); self.article_list.itemClicked.connect(self._on_article_clicked)
        self.splitter.addWidget(self.source_list); self.splitter.addWidget(self.article_list)
        self.splitter.setSizes([200, 600])
        root.addWidget(self.splitter, 2)

        # 3. 底部编辑器 (修复点击空白 & 支持修改)
        self.editor_frame = QFrame(); self.editor_frame.setFrameShape(QFrame.StyledPanel)
        edit_layout = QVBoxLayout(self.editor_frame)
        edit_layout.addWidget(StrongBodyLabel("Feed Config" if self.is_en else "订阅源配置"))
        
        row1 = QHBoxLayout()
        self.ed_name = LineEdit(); self.ed_name.setPlaceholderText("Name (e.g. Tech News)" if self.is_en else "备注名 (如: 科技要闻)")
        self.ed_url = LineEdit(); self.ed_url.setPlaceholderText("RSS URL (https://...)" if self.is_en else "RSS 地址")
        for w in [self.ed_name, self.ed_url]: row1.addWidget(w)
        edit_layout.addLayout(row1)

        btn_save = PushButton(FluentIcon.SAVE, "Save Changes" if self.is_en else "保存修改")
        btn_save.clicked.connect(self._save_source_config)
        edit_layout.addWidget(btn_save, 0, Qt.AlignRight)
        root.addWidget(self.editor_frame, 1)

        # 4. 计时器初始化 (解决 ui_app 调用崩溃)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._background_fetch)
        poll_mins = getattr(self.get_settings(), "plugin_rss_poll_mins", 10)
        self.timer.start(poll_mins * 60000)

        self.fetch_finished.connect(self._update_ui_after_fetch)
        self._load_config()

    # --- AI 核心接口：全量提供数据 ---
    def fetch_data(self, is_bg=True):
        """AI 核心：不再限制 5 条，由主程序根据分析条数开关进行切片"""
        data = []
        for name, entries in self.feed_cache.items():
            for e in entries:
                data.append({
                    "source": f"RSS: {name}",
                    "title": e.get('title', 'No Title'),
                    "summary": e.get('summary', 'No Content')[:500], # 提供稍长一点的摘要供 AI 分析
                    "link": e.get('link', '')
                })
        return data

    def _sync_to_disk(self):
        s = self.get_settings()
        s.plugin_rss_urls = [json.dumps(src) for src in self.sources]
        self.save_settings(s)

    def _load_config(self):
        s = self.get_settings()
        raw_list = getattr(s, "plugin_rss_urls", [])
        self.sources = []
        self.source_list.clear()
        for raw in raw_list:
            try:
                # 兼容旧版本格式
                if "|" in raw and not raw.startswith("{"):
                    parts = raw.split('|')
                    src = {"name": parts[0], "url": parts[1]}
                else:
                    src = json.loads(raw)
                self.sources.append(src)
                self.source_list.addItem(src['name'])
            except: continue
        if self.sources:
            self.source_list.setCurrentRow(0)
            self._on_source_clicked(self.source_list.currentItem())

    def _on_source_clicked(self, item):
        if not item: return
        idx = self.source_list.row(item)
        src = self.sources[idx]
        
        # 填充编辑器 (解决点击空白)
        self.ed_name.setText(src['name'])
        self.ed_url.setText(src['url'])
        
        # 刷新文章列表
        self.article_list.clear()
        entries = self.feed_cache.get(src['name'], [])
        if entries:
            for e in entries:
                # 增加时间标注，美化显示
                date_str = ""
                if 'published_parsed' in e and e.published_parsed:
                    date_str = f"[{time.strftime('%m-%d', e.published_parsed)}] "
                self.article_list.addItem(f"{date_str}{e.title}")
        else:
            self.article_list.addItem("Pending sync..." if self.is_en else "等待同步历史文章...")

    def _save_source_config(self):
        row = self.source_list.currentRow()
        if row < 0: return
        src = self.sources[row]
        src['name'] = self.ed_name.text()
        src['url'] = self.ed_url.text().strip()
        self.source_list.item(row).setText(src['name'])
        self._sync_to_disk()
        InfoBar.success("Success", "RSS config updated." if self.is_en else "RSS 配置已更新", parent=self)

    def _add_source(self):
        new_n = f"New_Feed_{len(self.sources)+1}"
        src = {"name": new_n, "url": ""}
        self.sources.append(src)
        self.source_list.addItem(new_n)
        self.source_list.setCurrentRow(self.source_list.count()-1)
        self._on_source_clicked(self.source_list.currentItem())
        self._sync_to_disk()

    def _delete_source(self):
        row = self.source_list.currentRow()
        if row >= 0:
            name = self.sources[row]['name']
            if name in self.feed_cache: del self.feed_cache[name]
            self.sources.pop(row)
            self.source_list.takeItem(row)
            self._sync_to_disk()

    def _manual_refresh(self):
        self.article_list.clear()
        self.article_list.addItem("Syncing..." if self.is_en else "正在同步订阅内容...")
        threading.Thread(target=self._fetch_all, daemon=True).start()

    def _background_fetch(self): 
        threading.Thread(target=self._fetch_all, args=(True,), daemon=True).start()

    def _fetch_all(self, is_bg=False):
        for src in self.sources:
            try:
                feed = feedparser.parse(src['url'])
                if feed.entries:
                    self.feed_cache[src['name']] = feed.entries
                    # 检查新文章推送
                    for entry in feed.entries[:3]:
                        guid = getattr(entry, 'id', entry.link)
                        if guid not in self.seen_guids:
                            self.seen_guids.add(guid)
                            if is_bg: self.new_item_signal.emit(f"RSS: {src['name']}", entry.title, "rss")
            except: continue
        self.fetch_finished.emit()

    def _update_ui_after_fetch(self):
        self._on_source_clicked(self.source_list.currentItem())

    def _on_article_clicked(self, item):
        src_item = self.source_list.currentItem()
        if not src_item: return
        entries = self.feed_cache.get(src_item.text(), [])
        row = self.article_list.row(item)
        if 0 <= row < len(entries):
            e = entries[row]
            RssReaderDialog(self.window(), e.title, e.get('summary', '无内容'), e.link, self.lang).exec()