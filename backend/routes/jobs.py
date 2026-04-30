from flask import Blueprint, request, jsonify
from extensions import db
from models import JobPosting, SkillStat
from services.collector.remotive import normalize as remotive_normalize

# ================================================================
# 현재: 규칙 기반 파서 사용 중
# 업그레이드 방법: 아래 주석 해제 후 위 줄 주석 처리
# ================================================================
from services.parser.rule_based import extract_skills, make_feedback
# from services.parser.claude import extract_skills, make_feedback  # Claude API 버전
# ================================================================
# Claude API 업그레이드 시 추가 작업:
# 1. pip install anthropic
# 2. .env에 ANTHROPIC_API_KEY=your_key_here 추가
# 3. config.py에서 ANTHROPIC_API_KEY 주석 해제
# 4. 위 import 줄만 교체하면 끝
# ================================================================

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/", methods=["GET"])
def home():
    """기존 루트 엔드포인트 유지"""
    return jsonify({"message": "Jobfit AI Backend is running"})


@jobs_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@jobs_bp.route("/api/jobs", methods=["POST"])
def save_jobs():
    """
    n8n에서 채용 공고 저장
    단일 객체 또는 배열 모두 허용

    ================================================================
    다른 소스 추가 시:
    - source 파라미터로 구분
    - services/collector/ 에 새 파일 추가
    ================================================================
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "데이터가 없습니다"}), 400

    if isinstance(data, dict):
        data = [data]

    saved, skipped = 0, 0
    skill_freq = {}

    for raw in data:
        source = raw.get("source", "remotive")

        # ================================================================
        # 소스별 normalizer 선택
        # 사람인 추가 시:
        # elif source == "saramin":
        #     from services.collector.saramin import normalize as saramin_normalize
        #     normalized = saramin_normalize(raw)
        # ================================================================
        if source == "remotive":
            normalized = remotive_normalize(raw)
        else:
            skipped += 1
            continue
        # ================================================================

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

    return jsonify({
        "message": f"{saved}개 저장, {skipped}개 스킵",
        "saved":   saved,
        "skipped": skipped,
    }), 201


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