import secrets
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User, UserProfile

auth_bp = Blueprint("auth", __name__)

def get_current_user_from_request():
    """
    Request의 Authorization 헤더 또는 X-Auth-Token 헤더에서 
    토큰을 읽어 현재 로그인한 User 객체를 반환합니다.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.headers.get("X-Auth-Token")
        
    if not token:
        return None
        
    user = User.query.filter_by(token=token).first()
    return user


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """회원가입 API"""
    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다."}), 400
        
    username = body.get("username", "").strip()
    email = body.get("email", "").strip()
    password = body.get("password", "").strip()
    
    if not username or not email or not password:
        return jsonify({"error": "아이디, 이메일, 비밀번호는 필수 입력 항목입니다."}), 400
        
    # 중복 체크
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "이미 사용 중인 아이디입니다."}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "이미 등록된 이메일입니다."}), 400
        
    try:
        # 비밀번호 해싱 및 사용자 생성
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password
        )
        db.session.add(new_user)
        db.session.flush()  # DB에서 new_user.id 값을 할당받기 위해 flush 실행
        
        # 기본 프로필 연결 생성 (이미 존재하는 경우 재사용)
        existing_profile = UserProfile.query.get(new_user.id)
        if not existing_profile:
            default_profile = UserProfile(
                id=new_user.id,
                name=username
            )
            db.session.add(default_profile)

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "회원가입이 성공적으로 완료되었습니다.",
            "user": new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[Register Error] {traceback.format_exc()}")
        return jsonify({"error": f"회원가입 중 오류가 발생했습니다: {str(e)}"}), 500


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """로그인 API"""
    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다."}), 400
        
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"error": "아이디와 비밀번호를 입력해주세요."}), 400
        
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "아이디 또는 비밀번호가 일치하지 않습니다."}), 401
        
    try:
        # 보안 인증 토큰 발급
        token = secrets.token_hex(16)
        user.token = token
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "로그인에 성공했습니다.",
            "token": token,
            "user": user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"로그인 중 오류가 발생했습니다: {str(e)}"}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """로그아웃 API"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인 상태가 아니거나 유효하지 않은 토큰입니다."}), 401
        
    try:
        # 토큰 파기
        user.token = None
        db.session.commit()
        return jsonify({"success": True, "message": "성공적으로 로그아웃되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"로그아웃 중 오류가 발생했습니다: {str(e)}"}), 500


@auth_bp.route("/api/auth/me", methods=["GET"])
def get_me():
    """현재 로그인한 사용자 정보 반환"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"logged_in": False}), 200
        
    return jsonify({
        "logged_in": True,
        "user": user.to_dict()
    }), 200
