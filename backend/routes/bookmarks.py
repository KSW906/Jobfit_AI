"""
bookmarks.py — 관심 채용 공고(북마크) 관리 라우트

엔드포인트 목록:
  GET    /api/bookmarks            — 현재 사용자의 북마크 목록 (공고 상세 포함, 최신순)
  POST   /api/bookmarks            — 공고 북마크 추가 {job_posting_id}
  DELETE /api/bookmarks/<job_id>   — 해당 공고 북마크 해제
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models import Bookmark, JobPosting
from routes.auth import get_current_user_from_request

bookmarks_bp = Blueprint("bookmarks", __name__)


@bookmarks_bp.route("/api/bookmarks", methods=["GET"])
def list_bookmarks():
    """현재 로그인한 사용자의 북마크 목록 조회"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    records = (
        Bookmark.query.filter_by(user_id=user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    return jsonify([b.to_dict() for b in records]), 200


@bookmarks_bp.route("/api/bookmarks", methods=["POST"])
def add_bookmark():
    """공고를 북마크에 추가"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    body = request.get_json() or {}
    job_id = body.get("job_posting_id")
    if not job_id:
        return jsonify({"error": "job_posting_id는 필수입니다."}), 400

    job = JobPosting.query.get(job_id)
    if not job:
        return jsonify({"error": "존재하지 않는 공고입니다."}), 404

    existing = Bookmark.query.filter_by(user_id=user.id, job_posting_id=job_id).first()
    if existing:
        return jsonify({"success": True, "message": "이미 저장된 공고입니다.", "bookmark": existing.to_dict()}), 200

    try:
        bookmark = Bookmark(user_id=user.id, job_posting_id=job_id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({"success": True, "message": "북마크에 저장했습니다.", "bookmark": bookmark.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"북마크 저장 실패: {str(e)}"}), 500


@bookmarks_bp.route("/api/bookmarks/<int:job_posting_id>", methods=["DELETE"])
def remove_bookmark(job_posting_id):
    """공고 북마크 해제 (job_posting_id 기준)"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    record = Bookmark.query.filter_by(user_id=user.id, job_posting_id=job_posting_id).first()
    if not record:
        return jsonify({"error": "저장되지 않은 공고입니다."}), 404

    try:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"success": True, "message": "북마크를 해제했습니다."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"북마크 해제 실패: {str(e)}"}), 500
