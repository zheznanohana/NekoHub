import hmac
import hashlib
import base64
import time
import urllib.parse
import requests
import smtplib
from email.mime.text import MIMEText
from typing import Optional

class Forwarder:
    """通知转发器 - 支持钉钉、Telegram、邮件"""
    
    @staticmethod
    def dingtalk(webhook: str, secret: Optional[str], title: str, content: str) -> bool:
        """钉钉机器人转发"""
        try:
            url = webhook
            if secret:
                timestamp = str(round(time.time() * 1000))
                string_to_sign = f'{timestamp}\n{secret}'
                hmac_code = hmac.new(
                    secret.encode('utf-8'),
                    string_to_sign.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                url += f"&timestamp={timestamp}&sign={sign}"
            
            payload = {
                "msgtype": "text",
                "text": {"content": f"【{title}】\n{content}"}
            }
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"DingTalk forward error: {e}")
            return False
    
    @staticmethod
    def telegram(bot_token: str, chat_id: str, title: str, content: str) -> bool:
        """Telegram 转发"""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": f"*{title}*\n\n{content}",
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, json=payload, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"Telegram forward error: {e}")
            return False
    
    @staticmethod
    def email(smtp_server: str, smtp_port: int, user: str, password: str, 
              to_email: str, title: str, content: str) -> bool:
        """SMTP 邮件转发"""
        try:
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['Subject'] = f"[NekoHub] {title}"
            msg['From'] = user
            msg['To'] = to_email
            
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
            server.login(user, password)
            server.sendmail(user, [to_email], msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Email forward error: {e}")
            return False
    
    @staticmethod
    def forward_all(settings: dict, title: str, content: str, mode: int = 0) -> dict:
        """
        根据模式转发
        mode: 0=全部，1=仅原始，2=仅 AI 结果
        """
        results = {
            'dingtalk': False,
            'telegram': False,
            'email': False
        }
        
        # 钉钉
        if settings.get('dingtalk_webhook'):
            results['dingtalk'] = Forwarder.dingtalk(
                settings['dingtalk_webhook'],
                settings.get('dingtalk_secret'),
                title, content
            )
        
        # Telegram
        if settings.get('tg_bot_token') and settings.get('tg_chat_id'):
            results['telegram'] = Forwarder.telegram(
                settings['tg_bot_token'],
                settings['tg_chat_id'],
                title, content
            )
        
        # 邮件
        if settings.get('email_smtp') and settings.get('email_user'):
            results['email'] = Forwarder.email(
                settings['email_smtp'],
                settings.get('email_port', 465),
                settings['email_user'],
                settings.get('email_pass'),
                settings['email_to'],
                title, content
            )
        
        return results
