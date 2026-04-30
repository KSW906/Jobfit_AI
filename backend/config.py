import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'jobs.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================================================================
    # Claude API 업그레이드 시 아래 주석 해제
    # .env 파일에 ANTHROPIC_API_KEY=your_key_here 추가 필요
    # ================================================================
    # ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    # ================================================================