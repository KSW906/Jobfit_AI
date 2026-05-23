from flask import Blueprint, request, jsonify
from models import JobPosting
from services.parser.rule_based import get_all_skills
from services.parser.multi_ai import extract_skills, make_feedback

# 비교에 사용할 스킬 목록 (소문자 set)
VALID_SKILLS_LOWER = set(s.lower() for s in get_all_skills())

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
    resume_text     = data.get("resume", "").strip()

    if not resume_text:
        from models import UserProfile
        from routes.auth import get_current_user_from_request
        user = get_current_user_from_request()
        if user:
            profile = UserProfile.query.get(user.id)
            if profile and profile.resume:
                resume_text = profile.resume

    if not job_description:
        return jsonify({"error": "채용 공고 내용이 필요합니다."}), 400
    if not user_skills:
        return jsonify({"error": "사용자 기술 목록이 필요합니다."}), 400

    # 스킬 추출 (규칙 기반 or Claude API)
    try:
        parsed        = extract_skills(job_description)
        job_keywords  = parsed["skills"]
    except Exception as e:
        return jsonify({"error": f"스킬 추출 실패 (Claude API): {str(e)}"}), 500

    user_skills_lower = [s.lower() for s in user_skills]

    matched_skills = [s for s in job_keywords if s.lower() in user_skills_lower]
    missing_skills = [s for s in job_keywords if s.lower() not in user_skills_lower]

    fit_score = calculate_fit_score(matched_skills, job_keywords)
    try:
        feedback  = make_feedback(missing_skills, resume_text=resume_text)
    except Exception as e:
        return jsonify({"error": f"피드백 생성 실패 (Claude API): {str(e)}"}), 500

    return jsonify({
        "job_title":       job_title,
        "job_keywords":    job_keywords,
        "user_skills":     user_skills,
        "matched_skills":  matched_skills,
        "missing_skills":  missing_skills,
        "fit_score":       fit_score,
        "feedback":        feedback,
        "resume_used":     bool(resume_text),
    })


import re

def parse_salary_number(sal_str: str) -> float | None:
    if not sal_str:
        return None
    sal_str_lower = sal_str.lower()
    multiplier = 1
    if "k" in sal_str_lower:
        multiplier = 1000
    
    clean_str = re.sub(r"[^\d.]", " ", sal_str_lower)
    numbers = re.findall(r"\d+(?:\.\d+)?", clean_str)
    if not numbers:
        return None
    
    val = max(float(n) for n in numbers)
    if val < 1000 and multiplier == 1000:
        val *= 1000
    return val


@analyze_bp.route("/api/analyze", methods=["POST"])
def analyze_from_db():
    """
    DB에 저장된 공고 전체와 사용자 스킬 및 개인별 가중치 선호도 매칭 분석
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다"}), 400

    my_skills = body.get("my_skills", [])
    if not my_skills:
        return jsonify({"error": "my_skills는 필수입니다"}), 400

    limit = body.get("limit", 10)

    from routes.auth import get_current_user_from_request
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    # 이력서 정보 가져오기
    resume_text = body.get("resume", "").strip()
    if not resume_text:
        from models import UserProfile
        profile = UserProfile.query.get(user.id)
        if profile and profile.resume:
            resume_text = profile.resume

    # 우선순위 선호 조건 및 가중치 추출
    preferences = body.get("preferences", {})
    priorities = body.get("priorities", {})

    pref_title = preferences.get("job_title", "").strip()
    pref_category = preferences.get("category", "").strip()
    pref_salary_val = None
    try:
        if "salary" in preferences and preferences["salary"]:
            pref_salary_val = float(preferences["salary"])
    except (ValueError, TypeError):
        pass
    pref_location = preferences.get("location", "").strip()

    # 가중치 (우선순위 상=3, 중=2, 하=1 등 동적 입력 가능, 기본값 매칭)
    w_skills = int(priorities.get("skills", 3))
    w_title = int(priorities.get("job_title", 1)) if pref_title else 0
    w_category = int(priorities.get("category", 1)) if pref_category else 0
    w_salary = int(priorities.get("salary", 1)) if pref_salary_val is not None else 0
    w_location = int(priorities.get("location", 1)) if pref_location else 0

    # 가중치 범위 제한 (0 ~ 5)
    w_skills = max(0, min(5, w_skills))
    w_title = max(0, min(5, w_title))
    w_category = max(0, min(5, w_category))
    w_salary = max(0, min(5, w_salary))
    w_location = max(0, min(5, w_location))

    all_jobs = JobPosting.query.order_by(JobPosting.fetched_at.desc()).all()
    if not all_jobs:
        return jsonify({"error": "저장된 채용 공고가 없습니다. n8n 워크플로우를 먼저 실행해주세요"}), 404

    my_skills_lower = [s.lower() for s in my_skills]
    results         = []
    all_missing     = []
    skill_demand    = {}

    for job in all_jobs:
        # skills 필드 사용
        job_skills = [s.strip() for s in job.skills.split(",") if s.strip()] if job.skills else []

        seen = set()
        filtered_skills = []
        for s in job_skills:
            key = s.lower()
            if key in VALID_SKILLS_LOWER and key not in seen:
                seen.add(key)
                filtered_skills.append(s)

        if not filtered_skills:
            continue

        matched = [s for s in filtered_skills if s.lower() in my_skills_lower]
        missing = [s for s in filtered_skills if s.lower() not in my_skills_lower]

        # 1. 기술 스택 적합도
        skills_score = calculate_fit_score(matched, filtered_skills)

        # 2. 직무명 매칭도
        title_score = 100
        if pref_title:
            title_words = [w.lower() for w in pref_title.split() if w.strip()]
            if title_words:
                matched_words = [w for w in title_words if w in job.title.lower()]
                title_score = int((len(matched_words) / len(title_words)) * 100)
            else:
                title_score = 0

        # 3. 분야(카테고리) 매칭도
        category_score = 100
        if pref_category:
            job_cat = (job.category or "").lower()
            job_tags = (job.tags or "").lower()
            if pref_category.lower() in job_cat or pref_category.lower() in job_tags:
                category_score = 100
            else:
                category_score = 0

        # 4. 연봉 매칭도
        salary_score = 100
        if pref_salary_val is not None:
            job_sal_val = parse_salary_number(job.salary)
            if job_sal_val is not None:
                if job_sal_val >= pref_salary_val:
                    salary_score = 100
                else:
                    salary_score = int((job_sal_val / pref_salary_val) * 100)
            else:
                # 연봉 기입이 없는 공고는 중립 점수(50) 부여
                salary_score = 50

        # 5. 회사 위치 매칭도
        location_score = 100
        if pref_location:
            job_loc = (job.location or "").lower()
            if pref_location.lower() in job_loc:
                location_score = 100
            else:
                location_score = 0

        # 가중치 종합 점수 산출
        denom = w_skills + w_title + w_category + w_salary + w_location
        if denom > 0:
            fit_score = int((skills_score * w_skills +
                             title_score * w_title +
                             category_score * w_category +
                             salary_score * w_salary +
                             location_score * w_location) / denom)
        else:
            fit_score = skills_score

        try:
            feedback = make_feedback(missing, resume_text=resume_text)
        except Exception as e:
            return jsonify({"error": f"피드백 생성 실패 (Claude API): {str(e)}"}), 500
        all_missing.extend(missing)

        # 스킬 수요 집계
        for skill in filtered_skills:
            skill_demand[skill] = skill_demand.get(skill, 0) + 1

        results.append({
            "job":            job.to_dict(),
            "fit_score":      fit_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "feedback":       feedback,
            "match_details": {
                "skills": skills_score,
                "job_title": title_score,
                "category": category_score,
                "salary": salary_score,
                "location": location_score
            }
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

    # 매칭 이력 DB 저장
    try:
        from extensions import db
        from models import UserProfile, MatchHistory
        import json

        # 현재 사용자 프로필 존재 확인 및 생성
        profile = UserProfile.query.get(user.id)
        if not profile:
            profile = UserProfile(id=user.id, name=user.username)
            db.session.add(profile)
            db.session.flush()

        # 상위 5개 결과 요약 저장
        top_matches_summary = []
        for r in results[:5]:
            top_matches_summary.append({
                "job_title": r["job"]["title"],
                "company": r["job"]["company"],
                "location": r["job"]["location"],
                "salary": r["job"]["salary"],
                "fit_score": r["fit_score"],
                "matched_skills": r["matched_skills"]
            })

        history_record = MatchHistory(
            user_id=user.id,
            avg_fit_score=avg_score,
            total_jobs=len(all_jobs),
            analyzed_jobs=len(results),
            skills_snapshot=",".join(my_skills),
            preferences_snapshot=json.dumps(preferences),
            top_matches=json.dumps(top_matches_summary)
        )
        db.session.add(history_record)
        db.session.commit()
        print(f"[MatchHistory] Saved results to database (ID: {history_record.id})")
    except Exception as db_err:
        print(f"[MatchHistory] Error saving to database: {db_err}")

    return jsonify({
        "results":           results,
        "learning_priority": learning_priority[:10],
        "resume_used":       bool(resume_text),
        "summary": {
            "total_jobs":    len(all_jobs),
            "analyzed_jobs": len(results),
            "avg_fit_score": avg_score,
        }
    })


@analyze_bp.route("/api/analyze/history", methods=["GET"])
def get_analyze_history():
    """현재 로그인한 사용자의 과거 매칭 분석 이력 목록 조회"""
    from routes.auth import get_current_user_from_request
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401
        
    try:
        from models import MatchHistory
        histories = MatchHistory.query.filter_by(user_id=user.id).order_by(MatchHistory.run_at.desc()).limit(20).all()
        return jsonify([h.to_dict() for h in histories])
    except Exception as e:
        return jsonify({"error": str(e)}), 500