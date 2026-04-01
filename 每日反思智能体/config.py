import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'reflection.db')
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
AI_MODEL = 'claude-haiku-4-5-20251001'
