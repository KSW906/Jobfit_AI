"""
comparison.py — 비교용 이력서 관리 및 AI 비교 분석 라우트

엔드포인트 목록:
  GET    /api/comparison-resumes               — 전체 비교 이력서 목록 조회 (모든 사용자)
  POST   /api/admin/comparison-resumes         — 관리자 전용: 비교 이력서 등록
  DELETE /api/admin/comparison-resumes/<id>    — 관리자 전용: 비교 이력서 삭제
  POST   /api/compare-resume                   — 사용자 이력서 vs 선택한 비교 이력서 AI 분석
"""

import os
from flask import Blueprint, request, jsonify
from extensions import db
from models import ComparisonResume, UserProfile
from routes.auth import get_current_user_from_request
from services.parser.multi_ai import compare_resumes

comparison_bp = Blueprint("comparison", __name__)

# .env 에서 관리자 비밀키 읽기 (없으면 기본값 사용)
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "jobfit-admin-2024")


def _require_admin():
    """
    X-Admin-Secret 헤더 또는 요청 body의 admin_secret 필드로 관리자 인증.
    인증 실패 시 None 반환, 성공 시 True 반환.
    """
    header_secret = request.headers.get("X-Admin-Secret", "")
    body = request.get_json(silent=True) or {}
    body_secret = body.get("admin_secret", "")
    if header_secret == ADMIN_SECRET or body_secret == ADMIN_SECRET:
        return True
    return None


# ─────────────────────────────────────────────
# 1. 비교 이력서 목록 조회 (일반 사용자도 접근 가능)
# ─────────────────────────────────────────────

@comparison_bp.route("/api/comparison-resumes", methods=["GET"])
def list_comparison_resumes():
    """등록된 비교 이력서 목록 반환 (내용 본문은 제외, 레이블/스킬만)"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요합니다."}), 401

    rows = ComparisonResume.query.order_by(ComparisonResume.created_at.desc()).all()
    result = []
    for r in rows:
        result.append({
            "id":          r.id,
            "label":       r.label,
            "target_name": r.target_name,
            "skills":      r.skills.split(",") if r.skills else [],
            "created_at":  r.created_at.isoformat() if r.created_at else None,
            # 본문 미리보기 100자만 제공
            "preview":     r.content[:100] + "..." if len(r.content) > 100 else r.content,
        })
    return jsonify(result), 200


# ─────────────────────────────────────────────
# 2. 관리자 전용: 비교 이력서 등록
# ─────────────────────────────────────────────

@comparison_bp.route("/api/admin/comparison-resumes", methods=["POST"])
def add_comparison_resume():
    """
    관리자가 비교용 이력서를 등록합니다.
    
    Request body:
      admin_secret  str   관리자 인증키
      label         str   이력서 레이블 (예: "네이버 합격자", "시니어 백엔드 개발자")
      target_name   str   익명 이름 (선택, 기본값: "익명 구직자")
      content       str   이력서 본문 전체
      skills        list  이 이력서에서 추출된 핵심 스킬 목록 (선택)
    """
    if not _require_admin():
        return jsonify({"error": "관리자 권한이 없습니다."}), 403

    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다."}), 400

    label   = body.get("label", "").strip()
    content = body.get("content", "").strip()
    if not label or not content:
        return jsonify({"error": "label과 content는 필수입니다."}), 400

    target_name = body.get("target_name", "익명 구직자").strip()
    skills_raw  = body.get("skills", [])
    skills_str  = ",".join([s.strip() for s in skills_raw if s.strip()])

    # user_id는 첫 번째 UserProfile(관리자 계정)을 쓰거나, 없으면 1로 처리
    from models import UserProfile
    admin_profile = UserProfile.query.first()
    uid = admin_profile.id if admin_profile else 1

    try:
        new_item = ComparisonResume(
            user_id=uid,
            label=label,
            target_name=target_name,
            content=content,
            skills=skills_str,
        )
        db.session.add(new_item)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"비교 이력서 '{label}' 등록 완료",
            "id": new_item.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"등록 실패: {str(e)}"}), 500


# ─────────────────────────────────────────────
# 3. 관리자 전용: 비교 이력서 삭제
# ─────────────────────────────────────────────

@comparison_bp.route("/api/admin/comparison-resumes/<int:resume_id>", methods=["DELETE"])
def delete_comparison_resume(resume_id):
    """관리자가 비교 이력서를 삭제합니다."""
    if not _require_admin():
        return jsonify({"error": "관리자 권한이 없습니다."}), 403

    item = ComparisonResume.query.get(resume_id)
    if not item:
        return jsonify({"error": "해당 이력서를 찾을 수 없습니다."}), 404

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": f"ID {resume_id} 삭제 완료"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"삭제 실패: {str(e)}"}), 500


# ─────────────────────────────────────────────
# 4. 이력서 비교 분석 실행
# ─────────────────────────────────────────────

@comparison_bp.route("/api/compare-resume", methods=["POST"])
def compare_resume():
    """
    사용자의 이력서와 선택한 비교 이력서를 AI로 분석합니다.
    
    Request body:
      comparison_resume_id  int   비교할 ComparisonResume의 ID
      resume                str   사용자 이력서 본문 (없으면 프로필에서 자동 로드)
    
    Response:
      {
        "comparison_label": "네이버 합격자",
        "strengths":  [...],
        "weaknesses": [...],
        "skill_gap":  [...],
        "advice":     [...],
        "overall_assessment": "..."
      }
    """
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요합니다."}), 401

    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다."}), 400

    comp_id = body.get("comparison_resume_id")
    if not comp_id:
        return jsonify({"error": "comparison_resume_id가 필요합니다."}), 400

    # 비교 이력서 조회
    comp_item = ComparisonResume.query.get(comp_id)
    if not comp_item:
        return jsonify({"error": "비교 이력서를 찾을 수 없습니다."}), 404

    # 사용자 이력서: 요청 body → 프로필 DB 순서로 로드
    user_resume = body.get("resume", "").strip()
    if not user_resume:
        prof = UserProfile.query.get(user.id)
        if prof and prof.resume:
            user_resume = prof.resume

    if not user_resume:
        return jsonify({
            "error": "이력서를 찾을 수 없습니다. 프로필에서 이력서를 먼저 등록해주세요."
        }), 400

    try:
        result = compare_resumes(
            user_resume=user_resume,
            comp_resume=comp_item.content,
            comp_label=comp_item.label,
        )
        result["comparison_label"] = comp_item.label
        result["comparison_target"] = comp_item.target_name
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"AI 비교 분석 실패: {str(e)}"}), 500
