import sys
import os
from app import create_app, socketio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = create_app('development')

if __name__ == '__main__':
    print("=" * 60)
    print("🐱 NekoHub Web Server Starting...")
    print("=" * 60)
    print(f"Backend URL: http://localhost:5000")
    print(f"Frontend URL: http://localhost:5173 (dev) or http://localhost:5000 (prod)")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
