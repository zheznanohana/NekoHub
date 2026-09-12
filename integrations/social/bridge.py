"""NoneBot transports -> versioned memory chat API. No confirmation capability."""
import asyncio
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from backend.memory_v1.blocks import VALIDATOR


class Bridge:
    def __init__(self, config, *, transport=None):
        self.config = config
        self.transport = transport
        self.url = os.getenv('MEMORY_SERVICE_URL', 'http://127.0.0.1:18081').rstrip('/')
        parsed = urlsplit(self.url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password:
            raise ValueError('Bridge requires the loopback memory service')
        self.last = {}
        self.busy = set()

    def allowed(self, adapter, bot_id, user_id, session_id):
        identity = dict(adapter=adapter, bot_id=str(bot_id), user_id=str(user_id), session_id=str(session_id))
        return identity in self.config.get('allowed_sessions', [])

    async def handle(self, adapter, bot_id, user_id, session_id, text):
        if not self.allowed(adapter, bot_id, user_id, session_id):
            return None
        if not text.startswith('/neko '):
            return None
        message = text[6:].strip()
        if not message or len(message) > 10000:
            return '请输入 1–10000 字的记忆命令。'
        key = (adapter, str(bot_id), str(user_id), str(session_id))
        now = time.monotonic()
        if key in self.busy or now - self.last.get(key, -1e9) < max(1, self.config.get('cooldown_seconds', 3)):
            return '上一条请求正在处理，请稍后再试。'
        self.last[key] = now
        self.busy.add(key)
        try:
            # URL and method are code-owned: social input never chooses an endpoint.
            async with httpx.AsyncClient(transport=self.transport, timeout=180, follow_redirects=False, trust_env=False) as client:
                response = await client.post(self.url + '/api/memory/v1/chat',
                    headers={'Authorization': 'Bearer ' + os.environ['MEMORY_SERVICE_TOKEN']},
                    json={'schema_version': '1.0', 'message': message})
                response.raise_for_status()
                if len(response.content) > 2_000_000:
                    raise ValueError('response budget exceeded')
                data = response.json()
                VALIDATOR.validate(data)
                return render(data)
        except (httpx.HTTPError, ValueError, KeyError):
            return '记忆服务暂未就绪；请在本地查看服务状态。'
        finally:
            self.busy.discard(key)


def render(data):
    """Transport text projection; canonical JSON remains unchanged in backend/UI."""
    parts = []
    for block in data['blocks']:
        kind = block['type']
        if kind == 'text':
            parts.append(block['text'])
        elif kind == 'memory.cards':
            parts.extend(f"[{x['id']}] {x['text']}" for x in block['items'][:10])
        elif kind == 'memory.summaries':
            parts.extend(f"[{x['level']} {x['period']}] {x['summary']}" for x in block['items'][:10])
        elif kind == 'memory.action':
            parts.append('待确认提议：' + block['command']['command'] + '\n' + block.get('preview', '') +
                         '\n请在 NekoHub 本地聊天框重新提交该操作并核对确认；社交入口仅提议，不执行。')
        elif kind == 'memory.table':
            parts.extend(f"[{x['level']}] {x['subject']}: {x['content']}" for x in block['rows'][:10])
            parts.append('完整横向/纵向表及 JSON 导出请打开 NekoHub 记忆页。')
        elif kind == 'memory.graph':
            parts.append(f"关系图：{len(block['data']['nodes'])} 个节点，{len(block['data']['facts'])} 条事实。请在 NekoHub 记忆页查看。")
        elif kind == 'memory.network':
            parts.append(f"分层记忆网络：{len(block['nodes'])} 个节点，{len(block['edges'])} 条连接。请在 NekoHub 记忆页缩放、点选和下钻。")
        elif kind == 'memory.receipt':
            parts.append(json.dumps(block['data'], ensure_ascii=False))
    return ('\n\n'.join(parts) or '没有匹配记录。')[:1600]


def main():
    import nonebot
    from nonebot.adapters import Bot, Event
    from nonebot.adapters.telegram import Adapter as Telegram
    from nonebot.adapters.discord import Adapter as Discord
    from nonebot.adapters.onebot.v11 import Adapter as OneBot
    path = Path(os.getenv('NEKOHUB_SOCIAL_CONFIG', Path(__file__).with_name('config.example.json')))
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    bridge = Bridge(config)
    onebot = config.get('onebot_enabled', False)
    if onebot and len(config.get('onebot_v11_access_token', '')) < 24:
        raise ValueError('OneBot requires an access token of at least 24 characters')
    nonebot.init(driver='~fastapi+~httpx+~websockets', host='127.0.0.1', port=18082,
        log_level='WARNING', telegram_bots=config.get('telegram_bots', []),
        discord_bots=config.get('discord_bots', []),
        onebot_v11_access_token=config.get('onebot_v11_access_token'),
        onebot_v11_ws_urls=config.get('onebot_v11_ws_urls', []))
    driver = nonebot.get_driver()
    driver.register_adapter(Telegram)
    driver.register_adapter(Discord)
    if onebot:
        driver.register_adapter(OneBot)
    matcher = nonebot.on_message(priority=20, block=False)

    @matcher.handle()
    async def message(bot: Bot, event: Event):
        try:
            reply = await bridge.handle(bot.adapter.get_name(), bot.self_id,
                event.get_user_id(), event.get_session_id(), event.get_plaintext())
        except (NotImplementedError, ValueError):
            return
        if reply:
            # A text segment, not adapter markup: no CQ code/mention injection.
            message_type = type(event.get_message())
            await bot.send(event, message_type(message_type.get_segment_class().text(reply)))

    @driver.on_startup
    async def startup():
        print(json.dumps({'social': 'ready', 'telegram_accounts': len(config.get('telegram_bots', [])),
            'discord_accounts': len(config.get('discord_bots', [])), 'onebot_enabled': onebot,
            'allowed_sessions': len(config.get('allowed_sessions', []))}), flush=True)

    nonebot.run()


if __name__ == '__main__':
    main()
