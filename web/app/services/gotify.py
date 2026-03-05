import requests
from typing import List, Dict, Optional

class GotifyClient:
    """Gotify API 客户端"""
    
    def __init__(self, base_url: str, recv_token: str, send_token: str):
        self.base_url = base_url.rstrip('/')
        self.recv_token = recv_token
        self.send_token = send_token
        self.session = requests.Session()
    
    def fetch_messages(self, limit: int = 50) -> List[Dict]:
        """获取最新通知"""
        try:
            resp = self.session.get(
                f'{self.base_url}/message',
                params={'limit': limit, 'since': 0},
                headers={'X-Gotify-Key': self.recv_token},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('messages', []) if isinstance(data, dict) else data
        except Exception as e:
            print(f"Gotify fetch error: {e}")
            return []
    
    def send_message(self, title: str, message: str, priority: int = 5) -> bool:
        """发送通知到 Gotify"""
        try:
            resp = self.session.post(
                f'{self.base_url}/message',
                json={
                    'title': title,
                    'message': message,
                    'priority': priority
                },
                headers={'X-Gotify-Key': self.send_token},
                timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"Gotify send error: {e}")
            return False
    
    def test_connection(self) -> tuple:
        """测试连接"""
        try:
            resp = self.session.get(
                f'{self.base_url}/health',
                timeout=5
            )
            if resp.status_code == 200:
                return True, "连接成功"
            return False, f"状态码：{resp.status_code}"
        except Exception as e:
            return False, str(e)
