# plugin_imap.py
import threading, smtplib, poplib, email, json, imaplib, re, time
from email.header import decode_header
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QSplitter
from qfluentwidgets import (PushButton, LineEdit, TextEdit, CommandBar, Action, FluentIcon, 
                            MessageBoxBase, TitleLabel, SubtitleLabel, BodyLabel, InfoBar, 
                            ComboBox, StrongBodyLabel, CardWidget, ScrollArea)
import html

# --- 核心解析逻辑 (原始完整版) ---
def parse_acc(acc_str):
    if not acc_str: return {"remark": "新账号", "in_proto": "IMAP", "in_host": "", "in_port": 993, "in_ssl": True, "in_user": "", "in_pass": "", "out_host": "", "out_port": 465, "out_ssl": True, "out_user": "", "out_pass": ""}
    if isinstance(acc_str, str) and acc_str.strip().startswith("{"): 
        return json.loads(acc_str)
    
    parts = str(acc_str).split('|')
    res = {"remark": "未命名账号", "in_proto": "IMAP", "in_host": "", "in_port": 993, "in_ssl": True, "in_user": "", "in_pass": "", "out_host": "", "out_port": 465, "out_ssl": True, "out_user": "", "out_pass": ""}
    if len(parts) == 4:
        res.update({"remark": parts[0], "in_host": parts[1], "in_user": parts[2], "in_pass": parts[3], "out_user": parts[2], "out_pass": parts[3]})
    elif len(parts) == 5:
        res.update({"in_proto": parts[0], "remark": parts[1], "in_host": parts[2], "in_user": parts[3], "in_pass": parts[4], "out_user": parts[3], "out_pass": parts[4]})
        res["in_port"] = 993 if parts[0] == "IMAP" else 995
    elif len(parts) == 7:
        res.update({"in_proto": parts[0], "remark": parts[1], "in_host": parts[2], "in_port": int(parts[3]), "in_ssl": (parts[4]=="True"), "in_user": parts[5], "in_pass": parts[6], "out_user": parts[5], "out_pass": parts[6]})
    return res

def decode_mail_header(header_text):
    if not header_text: return "未知"
    try:
        headers = decode_header(header_text)
        decoded = []
        for text, charset in headers:
            if isinstance(text, bytes):
                decoded.append(text.decode(charset or 'utf-8', errors='ignore'))
            else:
                decoded.append(str(text))
        return "".join(decoded)
    except: return "解码错误"

def extract_mail_body(msg):
    body = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain':
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                    break
                elif ctype == 'text/html' and not body:
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
        
        if '<' in body and '>' in body:
            body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.IGNORECASE | re.DOTALL)
            body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.IGNORECASE | re.DOTALL)
            body = re.sub(r'<[^>]+>', ' ', body)
            body = html.unescape(body)
            body = re.sub(r'\s+', ' ', body)
    except Exception: body = "正文解析失败"
    return body.strip() or "无内容"

# --- 完整弹窗组件复活 ---
class MailReaderDialog(MessageBoxBase):
    def __init__(self, parent_window, subject, sender, date_full, body, delete_cb=None):
        super().__init__(parent_window)
        self.viewLayout.addWidget(SubtitleLabel(subject))
        self.viewLayout.addWidget(BodyLabel(f"From: {sender} | Time: {date_full}"))
        self.content = TextEdit(); self.content.setPlainText(body)
        self.content.setReadOnly(True); self.content.setFixedHeight(400)
        self.viewLayout.addWidget(self.content)
        if delete_cb:
            self.btn_del = PushButton("🗑️ 从服务器删除此邮件")
            self.btn_del.clicked.connect(lambda: self._on_delete(delete_cb))
            self.viewLayout.addWidget(self.btn_del)
        self.widget.setMinimumWidth(600)

    def _on_delete(self, cb):
        self.btn_del.setText("正在删除..."); self.btn_del.setEnabled(False)
        cb(); self.accept()

class ComposeDialog(MessageBoxBase):
    def __init__(self, parent_window, lang, accs):
        super().__init__(parent_window)
        self.is_en = lang == "English"
        self.viewLayout.addWidget(SubtitleLabel("Compose Mail" if self.is_en else "写邮件"))
        valid_senders = [a for a in accs if a.get("out_host")]
        if not valid_senders:
            self.viewLayout.addWidget(BodyLabel("⚠️ 暂无有效发件配置！"))
        else:
            sender_lay = QHBoxLayout(); sender_lay.addWidget(StrongBodyLabel("发件账号: "))
            self.cb_sender = ComboBox(); self.cb_sender.addItems([a["remark"] for a in valid_senders])
            sender_lay.addWidget(self.cb_sender, 1); self.viewLayout.addLayout(sender_lay)

        self.ed_to = LineEdit(); self.ed_to.setPlaceholderText("收件人地址")
        self.ed_sub = LineEdit(); self.ed_sub.setPlaceholderText("邮件主题")
        self.ed_body = TextEdit(); self.ed_body.setPlaceholderText("内容...")
        for w in [self.ed_to, self.ed_sub, self.ed_body]: self.viewLayout.addWidget(w)
        self.widget.setMinimumWidth(500)

class ImapConfigDialog(MessageBoxBase):
    def __init__(self, parent_window, raw_accs, lang):
        super().__init__(parent_window)
        self.is_en = lang == "English"
        self.accs = [parse_acc(a) for a in raw_accs]
        self.current_idx = -1
        self.viewLayout.addWidget(TitleLabel("Email Settings" if self.is_en else "高级邮箱配置"))
        
        main_h = QHBoxLayout(); left_v = QVBoxLayout(); self.list_widget = QListWidget()
        for a in self.accs: self.list_widget.addItem(a["remark"])
        self.list_widget.currentRowChanged.connect(self._load_detail)
        
        btn_h = QHBoxLayout()
        self.btn_add = PushButton("新建"); self.btn_del = PushButton("删除")
        self.btn_add.clicked.connect(self._add_new); self.btn_del.clicked.connect(self._delete_current)
        btn_h.addWidget(self.btn_add); btn_h.addWidget(self.btn_del)
        left_v.addWidget(self.list_widget); left_v.addLayout(btn_h); main_h.addLayout(left_v, 1)

        self.scroll = ScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setStyleSheet("background:transparent; border:none;")
        self.form_w = QWidget(); self.form_v = QVBoxLayout(self.form_w)
        
        self.form_v.addWidget(StrongBodyLabel("身份 / 备注名"))
        self.ed_rem = LineEdit(); self.ed_rem.textChanged.connect(self._sync_remark); self.form_v.addWidget(self.ed_rem)
        
        in_card = CardWidget(); in_lay = QVBoxLayout(in_card)
        in_lay.addWidget(SubtitleLabel("收件服务器 (Incoming)"))
        r1 = QHBoxLayout(); r1.addWidget(BodyLabel("协议:")); self.cb_in_proto = ComboBox(); self.cb_in_proto.addItems(["IMAP", "POP3"]); r1.addWidget(self.cb_in_proto); r1.addStretch(1); in_lay.addLayout(r1)
        r2 = QHBoxLayout(); r2.addWidget(BodyLabel("地址:")); self.ed_in_host = LineEdit(); r2.addWidget(self.ed_in_host, 3)
        r2.addWidget(BodyLabel("端口:")); self.ed_in_port = LineEdit(); r2.addWidget(self.ed_in_port, 1); in_lay.addLayout(r2)
        r3 = QHBoxLayout(); r3.addWidget(BodyLabel("安全:")); self.cb_in_ssl = ComboBox(); self.cb_in_ssl.addItems(["SSL/TLS", "Plain"]); r3.addWidget(self.cb_in_ssl); r3.addStretch(1); in_lay.addLayout(r3)
        in_lay.addWidget(BodyLabel("用户名:")); self.ed_in_user = LineEdit(); in_lay.addWidget(self.ed_in_user)
        in_lay.addWidget(BodyLabel("密码:")); self.ed_in_pass = LineEdit(); self.ed_in_pass.setEchoMode(LineEdit.Password); in_lay.addWidget(self.ed_in_pass)
        self.form_v.addWidget(in_card)

        out_card = CardWidget(); out_lay = QVBoxLayout(out_card)
        out_lay.addWidget(SubtitleLabel("发件服务器 (Outgoing)"))
        ro1 = QHBoxLayout(); ro1.addWidget(BodyLabel("地址:")); self.ed_out_host = LineEdit(); ro1.addWidget(self.ed_out_host, 3)
        ro1.addWidget(BodyLabel("端口:")); self.ed_out_port = LineEdit(); ro1.addWidget(self.ed_out_port, 1); out_lay.addLayout(ro1)
        ro2 = QHBoxLayout(); ro2.addWidget(BodyLabel("安全:")); self.cb_out_ssl = ComboBox(); self.cb_out_ssl.addItems(["SSL/TLS", "Plain"]); ro2.addWidget(self.cb_out_ssl); ro2.addStretch(1); out_lay.addLayout(ro2)
        out_lay.addWidget(BodyLabel("用户名:")); self.ed_out_user = LineEdit(); out_lay.addWidget(self.ed_out_user)
        out_lay.addWidget(BodyLabel("密码:")); self.ed_out_pass = LineEdit(); self.ed_out_pass.setEchoMode(LineEdit.Password); out_lay.addWidget(self.ed_out_pass)
        self.form_v.addWidget(out_card)

        self.btn_save_item = PushButton("保存当前账号信息"); self.btn_save_item.clicked.connect(self._save_current); self.form_v.addWidget(self.btn_save_item)
        self.scroll.setWidget(self.form_w); main_h.addWidget(self.scroll, 2)
        self.viewLayout.addLayout(main_h); self.widget.setMinimumWidth(900); self.widget.setMinimumHeight(650)
        
        self.cb_in_proto.currentIndexChanged.connect(self._auto_fill_port); self.cb_in_ssl.currentIndexChanged.connect(self._auto_fill_port)
        if self.accs: self.list_widget.setCurrentRow(0)
        else: self.form_w.setEnabled(False)

    def _auto_fill_port(self):
        is_ssl = self.cb_in_ssl.currentIndex() == 0
        if self.cb_in_proto.currentText() == "IMAP": self.ed_in_port.setText("993" if is_ssl else "143")
        else: self.ed_in_port.setText("995" if is_ssl else "110")

    def _sync_remark(self, text):
        if self.current_idx >= 0: self.list_widget.item(self.current_idx).setText(text or "未命名")

    def _load_detail(self, idx):
        if idx < 0: return
        self.form_w.setEnabled(True); self.current_idx = idx; a = self.accs[idx]
        self.ed_rem.setText(a.get("remark", "")); self.cb_in_proto.setCurrentText(a.get("in_proto", "IMAP"))
        self.ed_in_host.setText(a.get("in_host", "")); self.ed_in_port.setText(str(a.get("in_port", 993)))
        self.cb_in_ssl.setCurrentIndex(0 if a.get("in_ssl", True) else 1); self.ed_in_user.setText(a.get("in_user", ""))
        self.ed_in_pass.setText(a.get("in_pass", "")); self.ed_out_host.setText(a.get("out_host", ""))
        self.ed_out_port.setText(str(a.get("out_port", 465))); self.cb_out_ssl.setCurrentIndex(0 if a.get("out_ssl", True) else 1)
        self.ed_out_user.setText(a.get("out_user", "")); self.ed_out_pass.setText(a.get("out_pass", ""))

    def _save_current(self):
        if self.current_idx < 0: return
        a = self.accs[self.current_idx]
        a.update({"remark": self.ed_rem.text(), "in_proto": self.cb_in_proto.currentText(), "in_host": self.ed_in_host.text(),
                  "in_port": int(self.ed_in_port.text() or 993), "in_ssl": self.cb_in_ssl.currentIndex() == 0,
                  "in_user": self.ed_in_user.text(), "in_pass": self.ed_in_pass.text(), "out_host": self.ed_out_host.text(),
                  "out_port": int(self.ed_out_port.text() or 465), "out_ssl": self.cb_out_ssl.currentIndex() == 0,
                  "out_user": self.ed_out_user.text(), "out_pass": self.ed_out_pass.text()})
        InfoBar.success("保存成功", f"账号 '{a['remark']}' 已更新。", parent=self.window())

    def _add_new(self):
        acc = parse_acc("新账号||||"); self.accs.append(acc); self.list_widget.addItem(acc["remark"])
        self.list_widget.setCurrentRow(len(self.accs)-1)

    def _delete_current(self):
        if self.current_idx >= 0:
            self.accs.pop(self.current_idx); self.list_widget.takeItem(self.current_idx)
            if not self.accs: self.form_w.setEnabled(False)

# --- 主页面 (全量逻辑复活版) ---
class ImapPage(QWidget):
    new_item_signal = Signal(str, str, str)
    fetch_done_signal = Signal(bool)

    def __init__(self, get_settings, save_settings, lang="简体中文"):
        super().__init__()
        self.setObjectName("imap_page")
        self.get_settings, self.save_settings, self.lang = get_settings, save_settings, lang
        self.is_en = lang == "English"
        
        # 核心去重与静默初始化状态
        self.seen_uids = set()
        self.initialized_accounts = set()
        self.mail_cache = {}

        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18)
        root.addWidget(TitleLabel("Universal Email Center" if self.is_en else "全协议邮件中心"))
        
        top_bar = QHBoxLayout(); self.cmd_bar = CommandBar(self)
        self.act_refresh = Action(FluentIcon.SYNC, '收信', triggered=self._manual_refresh)
        self.act_compose = Action(FluentIcon.MAIL, '写邮件', triggered=self._open_compose)
        self.act_config = Action(FluentIcon.SETTING, '配置', triggered=self._open_config)
        self.cmd_bar.addActions([self.act_refresh, self.act_compose, self.act_config])
        top_bar.addWidget(self.cmd_bar); top_bar.addStretch(1)
        
        top_bar.addWidget(StrongBodyLabel("单次收取:"))
        self.ed_limit = LineEdit(); self.ed_limit.setFixedWidth(60)
        self.ed_limit.setText(str(getattr(self.get_settings(), "plugin_imap_fetch_limit", 20)))
        self.btn_save_limit = PushButton("确定"); self.btn_save_limit.clicked.connect(self._save_limit_setting)
        top_bar.addWidget(self.ed_limit); top_bar.addWidget(self.btn_save_limit)
        root.addLayout(top_bar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.acc_list = QListWidget(); self.acc_list.itemClicked.connect(self._on_acc_clicked)
        self.mail_list = QListWidget(); self.mail_list.itemClicked.connect(self._on_mail_clicked)
        self.splitter.addWidget(self.acc_list); self.splitter.addWidget(self.mail_list)
        self.splitter.setSizes([250, 600])
        root.addWidget(self.splitter, 1)

        self._load_config()
        self.fetch_done_signal.connect(self._on_fetch_done)
        self.timer = QTimer(self); self.timer.timeout.connect(self._background_fetch)
        self.timer.start(getattr(self.get_settings(), "plugin_imap_poll_mins", 5) * 60000)

    def fetch_data(self, is_bg=True):
        """供 AI 使用的全量数据接口"""
        data = []
        for rem, mails in self.mail_cache.items():
            for m in mails:
                data.append({"source": f"邮件: {rem}", "title": f"[{m['date_list']}] {m['subject']}", 
                             "summary": f"发件人: {m['from']}\n时间: {m['date_full']}\n正文: {m['body'][:500]}"})
        return data

    def _save_limit_setting(self):
        try: val = int(self.ed_limit.text().strip())
        except: val = 20
        s = self.get_settings(); s.plugin_imap_fetch_limit = val; self.save_settings(s)
        InfoBar.success("设置成功", f"上限已设为 {val}", parent=self)

    def _load_config(self):
        self.raw_accs = getattr(self.get_settings(), "plugin_imap_accs", [])
        self.parsed_accs = [parse_acc(a) for a in self.raw_accs]
        self.acc_list.clear()
        for a in self.parsed_accs: self.acc_list.addItem(f"[{a['in_proto']}] {a['remark']}")

    def _open_config(self):
        try:
            w = ImapConfigDialog(self.window(), self.raw_accs, self.lang)
            if w.exec():
                s = self.get_settings()
                s.plugin_imap_accs = [json.dumps(a, ensure_ascii=False) for a in w.accs]
                self.save_settings(s); self._load_config()
                self.initialized_accounts.clear() # 重置初始化，强制下一轮静默同步
        except Exception as e:
            InfoBar.error("无法打开配置", str(e), parent=self)

    def _open_compose(self):
        valid_senders = [a for a in self.parsed_accs if a.get("out_host")]
        w = ComposeDialog(self.window(), self.lang, valid_senders)
        if w.exec() and valid_senders:
            acc = next(a for a in valid_senders if a["remark"] == w.cb_sender.currentText())
            def send_worker():
                try:
                    msg = MIMEText(w.ed_body.toPlainText(), 'plain', 'utf-8')
                    msg['Subject'], msg['From'], msg['To'] = w.ed_sub.text(), acc['out_user'], w.ed_to.text()
                    svr = smtplib.SMTP_SSL(acc['out_host'], acc['out_port']) if acc['out_ssl'] else smtplib.SMTP(acc['out_host'], acc['out_port'])
                    svr.login(acc['out_user'], acc['out_pass']); svr.sendmail(acc['out_user'], [w.ed_to.text()], msg.as_string()); svr.quit()
                except Exception as e: print(f"发送邮件失败: {e}")
            threading.Thread(target=send_worker, daemon=True).start()
            InfoBar.success("投递中", "邮件正在后台发送", parent=self)

    def _manual_refresh(self):
        self.mail_list.clear(); self.mail_list.addItem("同步中...")
        threading.Thread(target=self._fetch_all, args=(False,), daemon=True).start()

    def _background_fetch(self): threading.Thread(target=self._fetch_all, args=(True,), daemon=True).start()

    def _fetch_all(self, is_bg=False):
        fetch_limit = getattr(self.get_settings(), "plugin_imap_fetch_limit", 20)
        for acc in self.parsed_accs:
            proto, rem, host, user, pwd = acc["in_proto"], acc["remark"], acc["in_host"], acc["in_user"], acc["in_pass"]
            if not host or not user: continue
            display_name, acc_key = f"[{proto}] {rem}", f"{user}@{host}"
            should_notify = acc_key in self.initialized_accounts
            temp_mails = []
            try:
                if proto == "IMAP":
                    mail = imaplib.IMAP4_SSL(host, acc["in_port"]) if acc["in_ssl"] else imaplib.IMAP4(host, acc["in_port"])
                    mail.login(user, pwd); mail.select("inbox")
                    _, res = mail.uid('SEARCH', None, 'ALL')
                    if res[0]:
                        uids = res[0].split()
                        for num in reversed(uids[-fetch_limit:]):
                            uid_val = num.decode(); uid_unique = f"{acc_key}_IMAP_{uid_val}"
                            _, data = mail.uid('FETCH', num, '(RFC822)')
                            msg = email.message_from_bytes(data[0][1]); dt = parsedate_to_datetime(msg.get('Date'))
                            m_data = {"subject": decode_mail_header(msg.get('Subject')), "from": decode_mail_header(msg.get('From')),
                                      "body": extract_mail_body(msg), "date_list": dt.strftime('%m-%d'), "date_full": dt.strftime('%Y-%m-%d %H:%M'),
                                      "uid": uid_val, "raw_acc": acc}
                            temp_mails.append(m_data)
                            if uid_unique not in self.seen_uids:
                                self.seen_uids.add(uid_unique)
                                if should_notify and is_bg: self.new_item_signal.emit(f"Mail: {rem}", m_data['subject'], "imap")
                    mail.logout()
                elif proto == "POP3":
                    svr = poplib.POP3_SSL(host, acc["in_port"]) if acc["in_ssl"] else poplib.POP3(host, acc["in_port"])
                    svr.user(user); svr.pass_(pwd); msg_count = len(svr.list()[1])
                    for i in range(msg_count, max(0, msg_count - fetch_limit), -1):
                        _, lines, _ = svr.retr(i); msg = email.message_from_bytes(b'\r\n'.join(lines)); dt = parsedate_to_datetime(msg.get('Date'))
                        fingerprint = f"{msg.get('Subject')}_{msg.get('From')}_{msg.get('Date')}"
                        uid_unique = f"{acc_key}_POP_{fingerprint}"
                        m_data = {"subject": decode_mail_header(msg.get('Subject')), "from": decode_mail_header(msg.get('From')),
                                  "body": extract_mail_body(msg), "date_list": dt.strftime('%m-%d'), "date_full": dt.strftime('%Y-%m-%d %H:%M'),
                                  "uid": i, "raw_acc": acc}
                        temp_mails.append(m_data)
                        if uid_unique not in self.seen_uids:
                            self.seen_uids.add(uid_unique)
                            if should_notify and is_bg: self.new_item_signal.emit(f"Mail: {rem}", m_data['subject'], "imap")
                    svr.quit()
                self.initialized_accounts.add(acc_key); self.mail_cache[display_name] = temp_mails
            except Exception as e: print(f"Fetch Error {rem}: {e}")
        self.fetch_done_signal.emit(is_bg)

    def _on_fetch_done(self, is_bg):
        if not is_bg: self._on_acc_clicked(self.acc_list.currentItem())

    def _on_acc_clicked(self, item):
        if not item: return
        self.mail_list.clear(); mails = self.mail_cache.get(item.text(), [])
        self.mail_list.addItems([f"[{m['date_list']}] {m['subject']}" for m in mails])

    def _on_mail_clicked(self, item):
        acc_name = self.acc_list.currentItem().text()
        m = self.mail_cache[acc_name][self.mail_list.row(item)]
        def do_delete():
            def worker():
                try:
                    acc = m["raw_acc"]
                    if acc["in_proto"] == "IMAP":
                        mail = imaplib.IMAP4_SSL(acc["in_host"], acc["in_port"]) if acc["in_ssl"] else imaplib.IMAP4(acc["in_host"], acc["in_port"])
                        mail.login(acc["in_user"], acc["in_pass"]); mail.select("inbox"); mail.uid('STORE', m["uid"], '+FLAGS', '\\Deleted'); mail.expunge(); mail.logout()
                    else:
                        svr = poplib.POP3_SSL(acc["in_host"], acc["in_port"]) if acc["in_ssl"] else poplib.POP3(acc["in_host"], acc["in_port"])
                        svr.user(acc["in_user"]); svr.pass_(acc["in_pass"]); svr.dele(m["uid"]); svr.quit()
                    QTimer.singleShot(0, self._manual_refresh)
                except Exception as e: print(f"删除失败: {e}")
            threading.Thread(target=worker, daemon=True).start()
        MailReaderDialog(self.window(), m['subject'], m['from'], m['date_full'], m['body'], do_delete).exec()