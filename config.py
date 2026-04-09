import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

DATABASE_URL = os.environ.get('DATABASE_URL', '')
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'data', 'reflection.db'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
QIANWEN_API_KEY = os.environ.get('QIANWEN_API_KEY', '')
AI_MODEL = 'qwen-plus'
AI_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

# GitHub 笔记同步配置
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO  = os.environ.get('GITHUB_REPO', 'hmumu230-ops/daily-reflection-agent')
NOTES_DIR    = 'notes'   # 仓库内的笔记文件夹名
