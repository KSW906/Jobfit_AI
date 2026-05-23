from flask import Blueprint, request, jsonify
from extensions import db
from models import JobPosting, SkillStat
from services.collector.remotive import normalize as remotive_normalize

# ================================================================
# 현재: 다중 AI (Gemini + Claude + Fallback) 파서 사용 중
# ================================================================
from services.parser.multi_ai import extract_skills, make_feedback

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/", methods=["GET"])
def home():
    """기존 루트 엔드포인트 유지"""
    return jsonify({"message": "Jobfit AI Backend is running"})


@jobs_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def save_raw_jobs_list(data: list) -> tuple:
    """
    raw 채용 공고 목록을 받아서 각 소스별로 정규화하고 DB에 저장하는 공통 헬퍼 함수
    """
    saved, skipped = 0, 0
    skill_freq = {}

    for raw in data:
        source = raw.get("source", "remotive")

        # 소스별 normalizer 선택
        if source == "remotive":
            normalized = remotive_normalize(raw)
        elif source == "goyo24":
            from services.collector.goyo24 import normalize as goyo24_normalize
            normalized = goyo24_normalize(raw)
        elif source == "adzuna":
            from services.collector.adzuna import normalize as adzuna_normalize
            normalized = adzuna_normalize(raw)
        else:
            skipped += 1
            continue

        if normalized is None:
            skipped += 1
            continue

        # 중복 체크
        if JobPosting.query.filter_by(job_id=normalized["job_id"]).first():
            skipped += 1
            continue

        # 스킬 추출
        parsed   = extract_skills(normalized.get("description", ""))
        skills_str = ",".join(parsed["skills"])

        job = JobPosting(
            job_id          = normalized["job_id"],
            title           = normalized["title"],
            company         = normalized["company"],
            location        = normalized["location"],
            employment_type = normalized["employment_type"],
            salary          = normalized["salary"],
            description     = normalized["description"],
            tags            = normalized["tags"],
            skills          = skills_str,
            apply_url       = normalized["apply_url"],
            posted_at       = normalized["posted_at"],
            category        = normalized["category"],
            source          = normalized["source"],
        )
        db.session.add(job)

        for skill in parsed["skills"]:
            if skill:
                skill_freq[skill] = skill_freq.get(skill, 0) + 1

        saved += 1

    # SkillStat 업데이트
    for skill, cnt in skill_freq.items():
        stat = SkillStat.query.filter_by(skill_name=skill).first()
        if stat:
            stat.count += cnt
        else:
            db.session.add(SkillStat(skill_name=skill, count=cnt))

    db.session.commit()
    return saved, skipped


@jobs_bp.route("/api/jobs", methods=["POST"])
def save_jobs():
    """
    n8n에서 채용 공고 저장
    단일 객체 또는 배열 모두 허용
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "데이터가 없습니다"}), 400

    if isinstance(data, dict):
        data = [data]

    saved, skipped = save_raw_jobs_list(data)

    return jsonify({
        "message": f"{saved}개 저장, {skipped}개 스킵",
        "saved":   saved,
        "skipped": skipped,
    }), 201


@jobs_bp.route("/api/jobs/stats", methods=["GET"])
def get_jobs_stats():
    """DB 내의 채용 공고 소스별 누적 수량 반환"""
    try:
        from sqlalchemy import func
        stats_query = db.session.query(
            JobPosting.source, func.count(JobPosting.id)
        ).group_by(JobPosting.source).all()
        
        counts = {
            "remotive": 0,
            "adzuna": 0
        }
        for source, count in stats_query:
            if source in counts:
                counts[source] = count
        
        total_count = JobPosting.query.count()
        counts["total"] = total_count
        
        return jsonify(counts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/api/jobs/sync", methods=["POST"])
def sync_jobs():
    """모든 채용 공고 소스(Remotive, 고용24, Adzuna)를 직접 동기화(스크래핑)"""
    import os
    from services.collector.remotive import fetch_raw_remotive
    from services.collector.goyo24 import parse_xml
    from services.collector.adzuna import fetch_raw_adzuna
    import requests

    sync_results = {}
    
    # 1. Remotive 수집
    try:
        print("[Sync] Remotive 수집 시작...")
        remotive_raw = fetch_raw_remotive(limit=30)
        remotive_saved, remotive_skipped = save_raw_jobs_list(remotive_raw)
        sync_results["remotive"] = {"saved": remotive_saved, "skipped": remotive_skipped, "status": "success"}
    except Exception as e:
        print(f"[Sync] Remotive 수집 실패: {e}")
        sync_results["remotive"] = {"saved": 0, "skipped": 0, "status": "error", "message": str(e)}



    # 3. Adzuna 수집 (인증키 필요)
    adzuna_id = os.getenv("ADZUNA_APP_ID")
    adzuna_key = os.getenv("ADZUNA_APP_KEY")
    if adzuna_id and adzuna_key:
        try:
            print("[Sync] Adzuna 수집 시작...")
            adzuna_raw = fetch_raw_adzuna(adzuna_id, adzuna_key, limit=30)
            adzuna_saved, adzuna_skipped = save_raw_jobs_list(adzuna_raw)
            sync_results["adzuna"] = {"saved": adzuna_saved, "skipped": adzuna_skipped, "status": "success"}
        except Exception as e:
            print(f"[Sync] Adzuna 수집 실패: {e}")
            sync_results["adzuna"] = {"saved": 0, "skipped": 0, "status": "error", "message": str(e)}
    else:
        sync_results["adzuna"] = {"saved": 0, "skipped": 0, "status": "skipped", "message": "API 키가 구성되지 않았습니다."}

    # 전체 요약 계산
    total_saved = sum(item.get("saved", 0) for item in sync_results.values())
    total_skipped = sum(item.get("skipped", 0) for item in sync_results.values())

    return jsonify({
        "success": True,
        "results": sync_results,
        "summary": {
            "total_saved": total_saved,
            "total_skipped": total_skipped
        }
    })


@jobs_bp.route("/api/jobs", methods=["GET"])
def get_jobs():
    """채용 공고 목록 조회"""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    source   = request.args.get("source")
    skill    = request.args.get("skill")

    q = JobPosting.query
    if source:
        q = q.filter_by(source=source)
    if skill:
        q = q.filter(JobPosting.skills.contains(skill))

    q = q.order_by(JobPosting.fetched_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "jobs":     [j.to_dict() for j in pagination.items],
        "total":    pagination.total,
        "page":     page,
        "per_page": per_page,
        "pages":    pagination.pages,
    })


@jobs_bp.route("/api/skills/stats", methods=["GET"])
def skill_stats():
    """스킬 수요 통계 조회"""
    limit = request.args.get("limit", 20, type=int)
    stats = SkillStat.query.order_by(SkillStat.count.desc()).limit(limit).all()
    return jsonify([s.to_dict() for s in stats])