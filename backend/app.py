from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db
from routes.jobs import jobs_bp
from routes.analyze import analyze_bp
from routes.profile import profile_bp
from routes.auth import auth_bp
from routes.comparison import comparison_bp
from routes.chatbot import chatbot_bp
from routes.bookmarks import bookmarks_bp
from routes.insights import insights_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS (React 개발 서버 허용)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # DB 초기화
    db.init_app(app)

    # 라우트 등록
    app.register_blueprint(jobs_bp)
    app.register_blueprint(analyze_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(comparison_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(insights_bp)

    # DB 테이블 생성
    with app.app_context():
        db.create_all()
        print("[DB] Table creation completed")
        try:
            db.session.execute(db.text("ALTER TABLE interview_practice_sessions ADD COLUMN interview_mode VARCHAR(50) DEFAULT 'diagnostic'"))
            db.session.commit()
            print("[DB] Migrated: Added interview_mode column to interview_practice_sessions")
        except Exception:
            # Column already exists or error executing
            pass

    return app


# Force reload to pick up new Anthropic API key
if __name__ == "__main__":
    app = create_app()
    print("[Server] Flask server starting: http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)