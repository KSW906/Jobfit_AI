from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db
from routes.jobs import jobs_bp
from routes.analyze import analyze_bp


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

    # DB 테이블 생성
    with app.app_context():
        db.create_all()
        print("✅ DB 테이블 생성 완료")

    return app


if __name__ == "__main__":
    app = create_app()
    print("🚀 Flask 서버 시작: http://localhost:5000")
    app.run(debug=True, port=5000)