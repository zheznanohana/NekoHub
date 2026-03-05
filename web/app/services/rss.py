import feedparser
import requests
from datetime import datetime
from typing import List, Dict

class RssService:
    """RSS 订阅服务"""
    
    def __init__(self):
        self.feeds = []
    
    def add_feed(self, name: str, url: str):
        self.feeds.append({'name': name, 'url': url})
    
    def fetch_data(self, limit: int = 30) -> List[Dict]:
        """获取所有订阅的最新内容"""
        all_items = []
        
        for feed in self.feeds:
            try:
                # 使用 requests 下载，带超时
                resp = requests.get(feed['url'], timeout=5)
                if resp.status_code != 200:
                    print(f"RSS HTTP 错误 ({feed['name']}): {resp.status_code}")
                    continue
                    
                parsed = feedparser.parse(resp.content)
                
                if not parsed.entries:
                    print(f"RSS 无文章 ({feed['name']})")
                    continue
                
                count = max(1, limit // len(self.feeds))
                for entry in parsed.entries[:count]:
                    published = entry.get('published', entry.get('updated', ''))
                    if not published:
                        published = datetime.now().isoformat()
                    
                    all_items.append({
                        'source': feed['name'],
                        'title': entry.title or '无标题',
                        'summary': (entry.get('summary') or entry.get('description') or '')[:500],
                        'link': entry.link or '#',
                        'published': published
                    })
                    
            except requests.Timeout:
                print(f"RSS 超时 ({feed['name']}): {feed['url']}")
            except Exception as e:
                print(f"RSS 错误 ({feed['name']}): {type(e).__name__}: {str(e)[:100]}")
        
        # 按时间排序
        if all_items:
            try:
                all_items.sort(key=lambda x: x['published'], reverse=True)
            except:
                pass
        
        return all_items[:limit]
