from flask import Blueprint, request, jsonify
import io
from pypdf import PdfReader
from extensions import db
from models import UserProfile
from routes.auth import get_current_user_from_request
from services.parser.multi_ai import extract_skills_from_resume

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


@profile_bp.route("/api/profile/upload-resume", methods=["POST"])
def upload_resume_pdf():
    """PDF 이력서를 업로드하여 텍스트를 추출하고 사용자의 프로필 이력서 필드에 저장"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    if "file" not in request.files:
        return jsonify({"error": "파일이 전송되지 않았습니다."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "선택된 파일이 없습니다."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "PDF 파일만 업로드할 수 있습니다."}), 400

    try:
        import re
        # PDF 파일 메모리에 로드 및 텍스트 추출
        pdf_stream = io.BytesIO(file.read())
        reader = PdfReader(pdf_stream)
        
        extracted_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"
        
        # [텍스트 전처리 및 정규식 청소]
        # 1. 연속된 여러 줄바꿈(\n)을 단일 줄바꿈(\n)으로 병합하여 불필요한 개행 제거
        extracted_text = re.sub(r"\n+", "\n", extracted_text)
        # 2. 연속된 여러 공백을 단일 공백으로 병합
        extracted_text = re.sub(r" +", " ", extracted_text)
        
        extracted_text = extracted_text.strip()
        if not extracted_text:
            return jsonify({"error": "PDF 파일에서 텍스트를 추출할 수 없습니다. 이미지 스캔 형식이 아닌 텍스트 형식의 PDF인지 확인해 주세요."}), 400

        # 프로필 가져오거나 자동 생성하여 이력서 텍스트 업데이트
        profile = UserProfile.query.get(user.id)
        if not profile:
            profile = UserProfile(id=user.id, name=user.username)
            db.session.add(profile)
            
        profile.resume = extracted_text
        db.session.commit()

        # 이력서 내 기술 스택 추출 수행 (추천용)
        try:
            extracted_skills = extract_skills_from_resume(extracted_text)
        except Exception as e:
            print(f"[Warning] 이력서 기술 스택 추출 실패: {e}")
            extracted_skills = []

        return jsonify({
            "success": True,
            "message": "PDF 이력서가 업로드되고 분석 완료되었습니다.",
            "resume": profile.resume,
            "extracted_skills": extracted_skills
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"PDF 처리 중 오류가 발생했습니다: {str(e)}"}), 500
