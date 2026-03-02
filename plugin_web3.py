# plugin_web3.py
import threading
import requests
import time
import json
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QSplitter, QFrame
from qfluentwidgets import (PushButton, LineEdit, CommandBar, Action, FluentIcon, CheckBox,
                            TitleLabel, SubtitleLabel, BodyLabel, FlowLayout, ComboBox, 
                            StrongBodyLabel, InfoBar, MessageBoxBase)

# --- 2026 混合动力配置 ---
CHAIN_CONFIG_DATA = {
    "ETH": ("EVM_V2", 1, "https://api.etherscan.io/v2/api"),
    "BSC": ("EVM_SPEC", 56, "https://api.bscscan.com/api"), 
    "Base": ("EVM_SPEC", 8453, "https://api.basescan.org/api"), 
    "Polygon": ("EVM_V2", 137, "https://api.etherscan.io/v2/api"),
    "Arbitrum": ("EVM_V2", 42161, "https://api.etherscan.io/v2/api"),
    "OP": ("EVM_SPEC", 10, "https://api-optimistic.etherscan.io/api"),
    "AVAX": ("EVM_SPEC", 43114, "https://api.snowtrace.io/api"),
    "Linea": ("EVM_V2", 59144, "https://api.etherscan.io/v2/api"),
    "Scroll": ("EVM_V2", 534352, "https://api.etherscan.io/v2/api"),
    "Custom": ("EVM_CUSTOM", 0, "") # 新增自定义链占位符
}

class Web3Page(QWidget):
    new_item_signal = Signal(str, str, str)
    fetch_finished = Signal()

    def __init__(self, get_settings, save_settings, lang="简体中文"):
        super().__init__()
        self.setObjectName("web3_page")
        self.get_settings = get_settings
        self.save_settings = save_settings
        self.lang = lang
        self.is_en = lang == "English"
        self.tx_cache = {} # { "AccountName": [txs...] }
        self.accounts = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.addWidget(TitleLabel("Web3 Asset Radar Pro" if self.is_en else "Web3 官方全资产雷达"))
        
        self.cmd_bar = CommandBar(self)
        self.act_refresh = Action(FluentIcon.SYNC, 'Deep Sync' if self.is_en else '深度同步', triggered=self._manual_refresh)
        self.act_add = Action(FluentIcon.ADD, 'Add' if self.is_en else '新增账户', triggered=self._add_account)
        self.act_del = Action(FluentIcon.DELETE, 'Del' if self.is_en else '删除账户', triggered=self._delete_account)
        self.cmd_bar.addActions([self.act_refresh, self.act_add, self.act_del])
        root.addWidget(self.cmd_bar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.addr_list = QListWidget()
        self.addr_list.itemClicked.connect(self._on_addr_clicked)
        self.tx_list = QListWidget()
        self.tx_list.itemClicked.connect(self._on_tx_clicked)
        self.splitter.addWidget(self.addr_list)
        self.splitter.addWidget(self.tx_list)
        self.splitter.setSizes([260, 540])
        root.addWidget(self.splitter, 2)

        self.editor_frame = QFrame()
        self.editor_frame.setFrameShape(QFrame.StyledPanel)
        edit_layout = QVBoxLayout(self.editor_frame)
        
        # 第一行基础配置
        row1 = QHBoxLayout()
        self.cb_type = ComboBox()
        self.cb_type.addItems(["EVM", "BTC", "SOL"])
        self.cb_type.currentTextChanged.connect(lambda t: self.chain_box.setVisible(t == "EVM"))
        self.ed_name = LineEdit()
        self.ed_name.setText("My_Wallet")
        self.ed_addr = LineEdit()
        self.ed_addr.setPlaceholderText("Address (0x...)")
        self.ed_key = LineEdit()
        self.ed_key.setPlaceholderText("API Key")
        for w in [self.cb_type, self.ed_name, self.ed_addr, self.ed_key]:
            row1.addWidget(w)
        edit_layout.addLayout(row1)

        # 新增第二行：自定义 API 接口配置
        row2 = QHBoxLayout()
        self.ed_custom_url = LineEdit()
        self.ed_custom_url.setPlaceholderText("Custom RPC/API URL (e.g. NodeReal / Alchemy) 勾选 Custom 时生效" if not self.is_en else "Custom API URL (Requires checking 'Custom')")
        row2.addWidget(StrongBodyLabel("自定义接口:" if not self.is_en else "Custom API:"))
        row2.addWidget(self.ed_custom_url, 1)
        edit_layout.addLayout(row2)

        # 链选择区域
        self.chain_box = QFrame()
        self.chain_box_lay = QVBoxLayout(self.chain_box)
        self.chain_flow = FlowLayout()
        self.chain_checks = {}
        for cname in CHAIN_CONFIG_DATA.keys():
            cb = CheckBox(cname)
            self.chain_checks[cname] = cb
            self.chain_flow.addWidget(cb)
        self.chain_box_lay.addLayout(self.chain_flow)
        edit_layout.addWidget(self.chain_box)

        btn_save = PushButton(FluentIcon.SAVE, "Save & Apply" if self.is_en else "保存修改")
        btn_save.clicked.connect(self._save_account_config)
        edit_layout.addWidget(btn_save, 0, Qt.AlignRight)
        
        root.addWidget(self.editor_frame, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: threading.Thread(target=self._fetch_all, daemon=True).start())
        self.timer.start(getattr(self.get_settings(), "plugin_web3_poll_mins", 3) * 60000)
        self.fetch_finished.connect(self._update_ui_after_fetch)
        self._load_accounts_from_settings()

    def fetch_data(self, is_bg=True):
        """AI 核心接口：返回全量缓存，由 AI 处理端决定最终切片条数"""
        data = []
        for name, txs in self.tx_cache.items():
            for t in txs:
                data.append({
                    "source": f"Web3 Radar: {name}",
                    "title": t['display'],
                    "summary": f"Time: {t.get('time_str')}\nHash: {t['hash']}\nFrom: {t['from']}\nTo: {t['to']}"
                })
        return data

    def _sync_to_disk(self):
        s = self.get_settings()
        s.plugin_web3_addrs = [json.dumps(a) for a in self.accounts]
        self.save_settings(s)

    def _load_accounts_from_settings(self):
        s = self.get_settings()
        raw_list = getattr(s, "plugin_web3_addrs", [])
        self.accounts = []
        self.addr_list.clear()
        
        for raw in raw_list:
            try:
                if "|" in raw and not raw.startswith("{"): continue 
                acc = json.loads(raw)
                self.accounts.append(acc)
                self.addr_list.addItem(acc['name'])
            except:
                continue
                
        if self.accounts:
            self.addr_list.setCurrentRow(0)
            self._on_addr_clicked(self.addr_list.currentItem())

    def _on_addr_clicked(self, item):
        if not item: return
        acc = self.accounts[self.addr_list.row(item)]
        
        self.cb_type.setCurrentText(acc.get('type', 'EVM'))
        self.ed_name.setText(acc.get('name', ''))
        self.ed_addr.setText(acc.get('addr', ''))
        self.ed_key.setText(acc.get('key', ''))
        self.ed_custom_url.setText(acc.get('custom_url', '')) # 还原自定义URL
        
        for cname, cb in self.chain_checks.items():
            cb.setChecked(cname in acc.get('chains', []))
            
        self.tx_list.clear()
        if acc['name'] in self.tx_cache:
            self.tx_list.addItems([t['display'] for t in self.tx_cache[acc['name']]])

    def _save_account_config(self):
        row = self.addr_list.currentRow()
        if row < 0: return
        acc = self.accounts[row]
        acc.update({
            "name": self.ed_name.text(), 
            "addr": self.ed_addr.text().strip(), 
            "key": self.ed_key.text().strip(), 
            "custom_url": self.ed_custom_url.text().strip(), # 保存自定义URL
            "type": self.cb_type.currentText(), 
            "chains": [n for n, cb in self.chain_checks.items() if cb.isChecked()]
        })
        self.addr_list.item(row).setText(acc['name'])
        self._sync_to_disk()
        InfoBar.success("Saved", "Config synced." if self.is_en else "配置已保存", parent=self)

    def _add_account(self):
        new_n = f"Wallet_{len(self.accounts)+1}"
        acc = {"name": new_n, "addr": "", "key": "", "custom_url": "", "type": "EVM", "chains": ["ETH"]}
        self.accounts.append(acc)
        self.addr_list.addItem(new_n)
        self.addr_list.setCurrentRow(self.addr_list.count()-1)
        self._on_addr_clicked(self.addr_list.currentItem())
        self._sync_to_disk()

    def _delete_account(self):
        row = self.addr_list.currentRow()
        if row >= 0:
            name = self.accounts[row]['name']
            if name in self.tx_cache:
                del self.tx_cache[name]
            self.accounts.pop(row)
            self.addr_list.takeItem(row)
            self._sync_to_disk()

    def _manual_refresh(self):
        self.tx_list.clear()
        self.tx_list.addItem("Syncing Multi-Chain Data..." if self.is_en else "正在全量深度挖掘链上数据...")
        threading.Thread(target=self._fetch_all, daemon=True).start()

    def _fetch_all(self):
        for acc in self.accounts:
            name = acc['name']
            addr = acc['addr'].lower()
            key = acc['key']
            atype = acc['type']
            custom_url = acc.get('custom_url', '')
            
            if not addr: continue
            all_txs = []
            
            if atype == "EVM":
                for cname in acc.get('chains', []):
                    ctype, cid, base_url = CHAIN_CONFIG_DATA.get(cname, ("EVM_V2", 1, ""))
                    
                    # 💡 核心逻辑：拦截自定义请求
                    if ctype == "EVM_CUSTOM":
                        if not custom_url:
                            print(f"[Web3] Custom chain checked but no URL provided for {name}")
                            continue
                        base_url = custom_url
                    
                    for act in ["txlist", "tokentx"]:
                        try:
                            # 拼接参数
                            params = f"&address={addr}&page=1&offset=200&sort=desc&apikey={key}"
                            if ctype == "EVM_V2":
                                params += f"&chainid={cid}"
                                
                            url = f"{base_url}?module=account&action={act}" + params
                            
                            r = requests.get(url, timeout=15).json()
                            if r.get('status') == '1':
                                for tx in r['result']:
                                    fr = tx.get('from', '').lower()
                                    to = tx.get('to', '').lower()
                                    is_in = (to == addr)
                                    ts = int(tx.get('timeStamp', 0))
                                    sym = tx.get('tokenSymbol', "ETH" if cname=="ETH" else "Token" if cname=="Custom" else cname)
                                    dec = int(tx.get('tokenDecimal', 18))
                                    val = float(tx.get('value', 0)) / (10**dec)
                                    time_str = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M')
                                    arrow = "↙️ (IN)" if is_in else "↗️ (OUT)"
                                    fr_s = f"{fr[:6]}...{fr[-4:]}"
                                    to_s = f"{to[:6]}...{to[-4:]}"
                                    
                                    display = f"{arrow} [{cname}] {val:.4f} {sym} | {fr_s} -> {to_s} | {time_str}"
                                    all_txs.append({
                                        "display": display, 
                                        "hash": tx.get('hash'), 
                                        "time": ts, 
                                        "time_str": datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                        "from": fr, 
                                        "to": to, 
                                        "val_sym": f"{val:.4f} {sym}"
                                    })
                            time.sleep(0.2)
                        except Exception as e:
                            print(f"[Web3] Error fetching {cname} for {name}: {e}")
                            continue
                            
            elif atype == "BTC":
                try:
                    r = requests.get(f"https://blockchain.info/rawaddr/{addr}?limit=100", timeout=15).json()
                    for tx in r.get('txs', []):
                        is_in = any(o.get('addr') == addr for o in tx.get('out', []))
                        ts = tx.get('time', 0)
                        arrow = "↙️ (IN)" if is_in else "↗️ (OUT)"
                        display = f"{arrow} [BTC] Transaction | {datetime.fromtimestamp(ts).strftime('%m-%d %H:%M')}"
                        all_txs.append({
                            "display": display, 
                            "hash": tx.get('hash'), 
                            "time": ts, 
                            "time_str": datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                            "from": "BTC", 
                            "to": addr, 
                            "val_sym": "BTC"
                        })
                except:
                    continue
                    
            all_txs.sort(key=lambda x: x['time'], reverse=True)
            self.tx_cache[name] = all_txs
            
        self.fetch_finished.emit()

    def _update_ui_after_fetch(self):
        self._on_addr_clicked(self.addr_list.currentItem())

    def _on_tx_clicked(self, item):
        acc_item = self.addr_list.currentItem()
        if not acc_item: return
        txs = self.tx_cache.get(acc_item.text(), [])
        row = self.tx_list.row(item)
        
        if 0 <= row < len(txs):
            tx = txs[row]
            w = MessageBoxBase(self.window())
            w.viewLayout.addWidget(SubtitleLabel(f"Detail: {tx['val_sym']}"))
            body = f"Time: {tx['time_str']}\n\nFrom: {tx['from']}\nTo: {tx['to']}\n\nHash: {tx['hash']}"
            w.viewLayout.addWidget(BodyLabel(body))
            w.exec()