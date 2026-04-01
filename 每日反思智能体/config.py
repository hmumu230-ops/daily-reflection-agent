import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'data', 'reflection.db'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
QIANWEN_API_KEY = os.environ.get('QIANWEN_API_KEY', '')
AI_MODEL = 'qwen-plus'           # 可选: qwen-turbo(快/便宜) qwen-plus(均衡) qwen-max(最强)
AI_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
