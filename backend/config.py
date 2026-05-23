import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'jobs.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================================================================
    # Claude API 및 OpenAI API 업그레이드
    # ================================================================
    # ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")