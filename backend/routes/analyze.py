from flask import Blueprint, request, jsonify
from models import JobPosting
from services.parser.rule_based import extract_skills, make_feedback

# ================================================================
# 현재: 규칙 기반 파서 사용 중
# 업그레이드 방법: 아래 주석 해제 후 위 줄 주석 처리
# ================================================================
# from services.parser.claude import extract_skills, make_feedback  # Claude API 버전
# ================================================================

analyze_bp = Blueprint("analyze", __name__)


def calculate_fit_score(matched: list, required: list) -> int:
    """기존 calculate_fit_score 로직 유지"""
    if len(required) == 0:
        return 0
    return round((len(matched) / len(required)) * 100)


@analyze_bp.route("/analyze", methods=["POST"])
def analyze_single():
    """
    기존 /analyze 엔드포인트 유지
    단일 채용공고 + 사용자 스킬 분석

    요청 형식 (기존과 동일):
    {
        "job_title":       "백엔드 개발자",
        "job_description": "Python, AWS, Docker 경험자 우대...",
        "user_skills":     ["Python", "React", "Git"]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON 데이터가 필요합니다."}), 400

    job_title       = data.get("job_title", "")
    job_description = data.get("job_description", "")
    user_skills     = data.get("user_skills", [])

    if not job_description:
        return jsonify({"error": "채용 공고 내용이 필요합니다."}), 400
    if not user_skills:
        return jsonify({"error": "사용자 기술 목록이 필요합니다."}), 400

    # 스킬 추출 (규칙 기반 or Claude API)
    parsed        = extract_skills(job_description)
    job_keywords  = parsed["skills"]

    user_skills_lower = [s.lower() for s in user_skills]

    matched_skills = [s for s in job_keywords if s.lower() in user_skills_lower]
    missing_skills = [s for s in job_keywords if s.lower() not in user_skills_lower]

    fit_score = calculate_fit_score(matched_skills, job_keywords)
    feedback  = make_feedback(missing_skills)

    return jsonify({
        "job_title":       job_title,
        "job_keywords":    job_keywords,
        "user_skills":     user_skills,
        "matched_skills":  matched_skills,
        "missing_skills":  missing_skills,
        "fit_score":       fit_score,
        "feedback":        feedback,
    })


@analyze_bp.route("/api/analyze", methods=["POST"])
def analyze_from_db():
    """
    DB에 저장된 공고 전체와 사용자 스킬 매칭 분석

    요청 형식:
    {
        "my_skills": ["Python", "React", "Git"],
        "limit":     10
    }

    응답 형식:
    {
        "results": [
            {
                "job":             {...},
                "fit_score":       72,
                "matched_skills":  [...],
                "missing_skills":  [...],
                "feedback":        [...]
            }
        ],
        "learning_priority": [
            {"skill": "AWS", "demand_count": 45},
            ...
        ],
        "summary": {
            "total_jobs":    100,
            "avg_fit_score": 58
        }
    }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다"}), 400

    my_skills = body.get("my_skills", [])
    if not my_skills:
        return jsonify({"error": "my_skills는 필수입니다"}), 400

    limit = body.get("limit", 10)

    all_jobs = JobPosting.query.order_by(JobPosting.fetched_at.desc()).all()
    if not all_jobs:
        return jsonify({"error": "저장된 채용 공고가 없습니다. n8n 워크플로우를 먼저 실행해주세요"}), 404

    my_skills_lower = [s.lower() for s in my_skills]
    results         = []
    all_missing     = []
    skill_demand    = {}

    for job in all_jobs:
        # skills + tags 합쳐서 비교
        job_skills = [s.strip() for s in job.skills.split(",") if s.strip()] if job.skills else []
        job_tags   = [t.strip() for t in job.tags.split(",")   if t.strip()] if job.tags   else []
        combined   = list(set(job_skills + job_tags))

        if not combined:
            continue

        matched = [s for s in combined if s.lower() in my_skills_lower]
        missing = [s for s in combined if s.lower() not in my_skills_lower]

        fit_score = calculate_fit_score(matched, combined)
        feedback  = make_feedback(missing)

        all_missing.extend(missing)

        # 스킬 수요 집계
        for skill in combined:
            skill_demand[skill] = skill_demand.get(skill, 0) + 1

        results.append({
            "job":            job.to_dict(),
            "fit_score":      fit_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "feedback":       feedback,
        })

    # fit_score 높은 순 정렬
    results.sort(key=lambda x: x["fit_score"], reverse=True)
    results = results[:limit]

    # 학습 우선순위: 부족 스킬 중 수요 높은 순
    missing_set = set(all_missing)
    learning_priority = sorted(
        [{"skill": s, "demand_count": c} for s, c in skill_demand.items() if s in missing_set],
        key=lambda x: x["demand_count"],
        reverse=True
    )

    avg_score = round(sum(r["fit_score"] for r in results) / len(results)) if results else 0

    return jsonify({
        "results":           results,
        "learning_priority": learning_priority[:10],
        "summary": {
            "total_jobs":    len(all_jobs),
            "analyzed_jobs": len(results),
            "avg_fit_score": avg_score,
        }
    })