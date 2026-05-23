from flask import Blueprint, request, jsonify
from extensions import db
from models import UserProfile
from routes.auth import get_current_user_from_request

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/api/profile", methods=["GET"])
def get_profile():
    """현재 로그인한 사용자의 프로필 가져오기"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    profile = UserProfile.query.get(user.id)
    if not profile:
        # 프로필 자동 생성
        profile = UserProfile(id=user.id, name=user.username)
        db.session.add(profile)
        db.session.commit()
        
    return jsonify(profile.to_dict())

@profile_bp.route("/api/profile", methods=["POST"])
def save_profile():
    """현재 로그인한 사용자의 프로필 저장 또는 업데이트"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다"}), 400

    profile = UserProfile.query.get(user.id)
    if not profile:
        profile = UserProfile(id=user.id, name=user.username)
        db.session.add(profile)

    # 파라미터 파싱 및 바인딩
    skills = body.get("skills", [])
    if isinstance(skills, list):
        profile.skills = ",".join(skills)
    else:
        profile.skills = str(skills)

    # 이력서 텍스트 필드 업데이트
    profile.resume = body.get("resume", "").strip()

    preferences = body.get("preferences", {})
    profile.pref_job_title = preferences.get("job_title", "").strip()
    profile.pref_category = preferences.get("category", "").strip()
    
    salary_val = preferences.get("salary")
    try:
        profile.pref_salary = float(salary_val) if salary_val else None
    except (ValueError, TypeError):
        profile.pref_salary = None
        
    profile.pref_location = preferences.get("location", "").strip()

    priorities = body.get("priorities", {})
    profile.w_skills = int(priorities.get("skills", 3))
    profile.w_title = int(priorities.get("job_title", 1))
    profile.w_category = int(priorities.get("category", 1))
    profile.w_salary = int(priorities.get("salary", 1))
    profile.w_location = int(priorities.get("location", 1))

    db.session.commit()
    return jsonify({"success": True, "profile": profile.to_dict()})
