"""Explicit projections from plugin caches; never serialize account configs."""
import hashlib
import json
import uuid


CATALOG = [
    ('gotify', '通知', '标题、正文、应用 ID、优先级、时间', '后端游标拉取；PC 不重复导入'),
    ('rss', '订阅文章', '订阅名、标题、链接、作者、发布时间、摘要', '插件已加载条目'),
    ('imap', '邮件（IMAP / POP3）', '账户标签、主题、发件人、日期、正文', '不导入密码或附件'),
    ('web3', '链上交易', '账户标签、交易哈希、时间、转出/转入、金额单位', '插件现有 EVM / BTC 数据'),
    ('github', 'GitHub Issues', '仓库、Issue 编号、标题、正文、更新时间', '后端同步；当前不含 PR、代码、私信'),
    ('manual', '手动日常记录', '正文、时间、版本、证据引用', '聊天确认写入'),
    ('social', '社交聊天入口', 'Telegram / Discord / OneBot 消息命令', '适配器已接；需绑定账户，不全量抓聊天历史'),
]


def document(source, group, fields, title, body):
    fields = {k: v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
              for k, v in fields.items()}
    # Evidence text includes structured context, so extraction can cite it exactly.
    text = json.dumps(fields, ensure_ascii=False, sort_keys=True) + '\n\n' + str(body or '')
    text = text[:100000]
    fingerprint = hashlib.sha256((source+'\n'+group+'\n'+text).encode()).hexdigest()
    return {'schema_version': '1.0', 'kind': 'memory.ingest', 'request_id': uuid.uuid4().hex,
        'source': {'type': source, 'instance_id': 'pc:'+source, 'external_id': fingerprint},
        'occurred_at': None, 'timezone': 'Asia/Tokyo',
        'content': {'title': str(title or '')[:1000], 'text': text, 'fields': fields}, 'provenance': 'external'}


def snapshots(source, cache, limit=100):
    records = []
    for group, items in list(cache.items()):
        for item in list(items):
            if source == 'rss':
                fields = {'feed': group, **{k: str(item.get(k, '')) for k in ('id','title','link','author','published')}}
                title, body = item.get('title',''), item.get('summary','')
            elif source == 'imap':
                # raw_acc includes IMAP/SMTP passwords: deliberately never touched.
                fields = {'account_label': group, **{k:str(item.get(k,'')) for k in ('subject','from','date_full','uid')}}
                title, body = item.get('subject',''), item.get('body','')
            elif source == 'web3':
                fields = {'account_label': group, **{k:item.get(k) for k in ('hash','time','time_str','from','to','val_sym','display')}}
                title, body = item.get('display',''), ''
            else:
                raise ValueError('unsupported PC cache')
            records.append(document(source, str(group), fields, title, body))
            if len(records) >= limit:
                return records
    return records
