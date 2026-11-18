import re
import json
import concurrent.futures
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models import JobPosting, UserProfile, MatchHistory, CachedFeedback
from services.parser.rule_based import get_all_skills
from services.parser.multi_ai import extract_skills, make_feedback, normalize_skills
from services.parser.resources_map import get_resources_for_skill
from routes.auth import get_current_user_from_request

# 비교에 사용할 스킬 목록 (소문자 set)
VALID_SKILLS_LOWER = set(s.lower() for s in get_all_skills())

analyze_bp = Blueprint("analyze", __name__)


def calculate_fit_score(matched: list, required: list) -> int:
    """기존 calculate_fit_score 로직 유지"""
    if len(required) == 0:
        return 0
    return round((len(matched) / len(required)) * 100)


def parse_salary_number(sal_str: str) -> float | None:
    """기존 연봉 파싱 로직 유지"""
    if not sal_str:
        return None
    sal_str_lower = sal_str.lower()
    multiplier = 1
    if "k" in sal_str_lower:
        multiplier = 1000
    
    # 쉼표(,)는 천 단위 구분기호인 경우가 많으므로 먼저 제거하고 숫자 추출
    sal_str_clean = sal_str_lower.replace(",", "")
    clean_str = re.sub(r"[^\d.]", " ", sal_str_clean)
    numbers = re.findall(r"\d+(?:\.\d+)?", clean_str)
    if not numbers:
        return None
    
    val = max(float(n) for n in numbers)
    if val < 1000 and multiplier == 1000:
        val *= 1000
    return val


def get_feedback_with_cache(missing_skills: list, resume_text: str = "", mode: str = "hybrid") -> list:
    if not missing_skills:
        return []

    from datetime import datetime

    if mode not in ["fresh", "hybrid", "cached"]:
        mode = "hybrid"

    result_feedback = []
    uncached_skills = []
    cached_map = {}

    if mode in ["hybrid", "cached"]:
        # Fetch existing cached skill feedbacks
        missing_skills_lower = [s.lower() for s in missing_skills]
        cached_records = CachedFeedback.query.all()
        cached_map = {r.skill_name.lower(): r.feedback for r in cached_records if r.skill_name.lower() in missing_skills_lower}

        for skill in missing_skills:
            key = skill.lower()
            if key in cached_map:
                result_feedback.append(f"{skill}: {cached_map[key]}")
            else:
                uncached_skills.append(skill)
    else:
        uncached_skills = list(missing_skills)

    if uncached_skills and mode in ["fresh", "hybrid"]:
        try:
            ai_feedbacks = make_feedback(uncached_skills, resume_text=resume_text)
            for fb in ai_feedbacks:
                result_feedback.append(fb)
                if ":" in fb:
                    parts = fb.split(":", 1)
                    s_name = parts[0].strip()
                    fb_text = parts[1].strip()
                    # 이력서(resume_text)가 제공된 경우 맞춤형 피드백이므로 공용 캐시에 저장하지 않음 (오염 방지)
                    if not resume_text:
                        # Check if exists and update, else create new
                        record = CachedFeedback.query.filter(db.func.lower(CachedFeedback.skill_name) == db.func.lower(s_name)).first()
                        if record:
                            record.feedback = fb_text
                            record.updated_at = datetime.utcnow()
                        else:
                            new_record = CachedFeedback(skill_name=s_name, feedback=fb_text)
                            db.session.add(new_record)
            # 캐시 업데이트가 있었을 때만 commit
            if not resume_text:
                db.session.commit()
        except Exception as e:
            print(f"[Warning] Failed to generate AI feedback for {uncached_skills}: {e}")
            for skill in uncached_skills:
                result_feedback.append(f"{skill}: 해당 스택에 대한 학습 가이드를 준비 중입니다.")
    
    if uncached_skills and mode == "cached":
        for skill in uncached_skills:
            result_feedback.append(f"{skill}: 공식 튜토리얼을 학습하여 기초 역량을 강화해 보세요.")

    ordered_feedback = []
    feedback_dict = {}
    for fb in result_feedback:
        if ":" in fb:
            parts = fb.split(":", 1)
            feedback_dict[parts[0].strip().lower()] = fb
    
    for skill in missing_skills:
        key = skill.lower()
        if key in feedback_dict:
            ordered_feedback.append(feedback_dict[key])
        else:
            ordered_feedback.append(f"{skill}: 해당 스택의 개념과 실습을 익혀보세요.")

    return ordered_feedback


@analyze_bp.route("/analyze", methods=["POST"])
def analyze_single():
    """단일 채용공고 + 사용자 스킬 분석 엔드포인트"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON 데이터가 필요합니다."}), 400

    job_title       = data.get("job_title", "")
    job_description = data.get("job_description", "")
    user_skills     = data.get("user_skills") or data.get("skills") or data.get("my_skills", [])
    user_skills     = normalize_skills(user_skills)
    resume_text     = data.get("resume", "").strip()

    if not resume_text:
        user = get_current_user_from_request()
        if user:
            prof = UserProfile.query.get(user.id)
            if prof and prof.resume:
                resume_text = prof.resume

    if not job_description:
        return jsonify({"error": "채용 공고 내용이 필요합니다."}), 400
    if not user_skills:
        return jsonify({"error": "사용자 기술 목록이 필요합니다."}), 400

    try:
        parsed        = extract_skills(job_description)
        job_keywords  = parsed["skills"]
    except Exception as e:
        return jsonify({"error": f"스킬 추출 실패 (Claude API): {str(e)}"}), 500

    user_skills_lower = [s.lower() for s in user_skills]

    matched_skills = [s for s in job_keywords if s.lower() in user_skills_lower]
    missing_skills = [s for s in job_keywords if s.lower() not in user_skills_lower]

    fit_score = calculate_fit_score(matched_skills, job_keywords)
    feedback_mode = data.get("feedback_mode", "hybrid")
    try:
        feedback  = get_feedback_with_cache(missing_skills, resume_text=resume_text, mode=feedback_mode)
    except Exception as e:
        return jsonify({"error": f"피드백 생성 실패: {str(e)}"}), 500

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


@analyze_bp.route("/api/analyze", methods=["POST"])
def analyze_from_db():
    """
    [아키텍처 최적화 완료]
    DB에 저장된 공고 전체와 사용자 스킬 및 개인별 가중치 선호도 매칭 분석 후 이력 보관
    """
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    body = request.get_json()
    if not body:
        return jsonify({"error": "요청 데이터가 없습니다"}), 400

    # 파라미터 네이밍 통일 (user_skills를 우선으로 하고, my_skills는 하위 호환성 유지)
    my_skills = body.get("user_skills") or body.get("my_skills", [])
    if not my_skills:
        return jsonify({"error": "user_skills는 필수입니다"}), 400
    my_skills = normalize_skills(my_skills)

    limit = body.get("limit", 10)

    # 이력서 정보 가져오기
    resume_text = body.get("resume", "").strip()
    if not resume_text:
        prof = UserProfile.query.get(user.id)
        if prof and prof.resume:
            resume_text = prof.resume

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

    # 가중치 계산
    w_skills = int(priorities.get("skills", 3))
    w_title = int(priorities.get("job_title", 1)) if pref_title else 0
    w_category = int(priorities.get("category", 1)) if pref_category else 0
    w_salary = int(priorities.get("salary", 1)) if pref_salary_val is not None else 0
    w_location = int(priorities.get("location", 1)) if pref_location else 0

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
    seen_jobs       = set()

    # 1단계: 전체 공고 고속 매칭 점수 연산
    for job in all_jobs:
        # 회사명, 공고 제목, 근무 지역(Location) 기준 중복 공고 건너뛰기 가드
        job_key = (
            job.title.strip().lower(),
            (job.company or "").strip().lower(),
            (job.location or "").strip().lower()
        )
        if job_key in seen_jobs:
            continue
        seen_jobs.add(job_key)

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

        skills_score = calculate_fit_score(matched, filtered_skills)

        title_score = 100
        if pref_title:
            title_words = [w.lower() for w in pref_title.split() if w.strip()]
            if title_words:
                matched_words = [w for w in title_words if w in job.title.lower()]
                title_score = int((len(matched_words) / len(title_words)) * 100)
            else:
                title_score = 0

        category_score = 100
        if pref_category:
            job_cat = (job.category or "").lower()
            job_tags = (job.tags or "").lower()
            if pref_category.lower() in job_cat or pref_category.lower() in job_tags:
                category_score = 100
            else:
                category_score = 0

        salary_score = 100
        if pref_salary_val is not None:
            if pref_salary_val <= 0:
                salary_score = 100
            else:
                job_sal_val = parse_salary_number(job.salary)
                if job_sal_val is not None:
                    if job_sal_val >= pref_salary_val:
                        salary_score = 100
                    else:
                        salary_score = int((job_sal_val / pref_salary_val) * 100)
                else:
                    salary_score = 50

        location_score = 100
        if pref_location:
            job_loc = (job.location or "").lower()
            if pref_location.lower() in job_loc:
                location_score = 100
            else:
                location_score = 0

        denom = w_skills + w_title + w_category + w_salary + w_location
        if denom > 0:
            fit_score = int((skills_score * w_skills +
                             title_score * w_title +
                             category_score * w_category +
                             salary_score * w_salary +
                             location_score * w_location) / denom)
        else:
            fit_score = skills_score

        all_missing.extend(missing)

        for skill in filtered_skills:
            skill_demand[skill] = skill_demand.get(skill, 0) + 1

        match_details = {"skills": skills_score}
        if pref_title:
            match_details["job_title"] = title_score
        if pref_category:
            match_details["category"] = category_score
        if pref_salary_val is not None:
            match_details["salary"] = salary_score
        if pref_location:
            match_details["location"] = location_score

        results.append({
            "job":            job.to_dict(),
            "fit_score":      fit_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "feedback":       "",
            "match_details":  match_details
        })

    # 2단계: 최상위 공고 정렬 및 컷팅
    results.sort(key=lambda x: x["fit_score"], reverse=True)
    results = results[:limit]

    feedback_mode = body.get("feedback_mode", "hybrid")

    # 3단계: 핀포인트 AI 피드백 생성 (ThreadPoolExecutor를 통한 병렬 처리)
    app = current_app._get_current_object()

    def fetch_feedback(r):
        with app.app_context():
            try:
                r["feedback"] = get_feedback_with_cache(r["missing_skills"], resume_text=resume_text, mode=feedback_mode)
            except Exception as e:
                print(f"[Warning] 피드백 건너뜀: {e}")
                r["feedback"] = ["맞춤형 AI 피드백을 실시간으로 로드하지 못했습니다."]

    # concurrent.futures를 활용해 각 공고별 AI 피드백 API 호출을 병렬 수행 (대기 시간 대폭 감소)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(results))) as executor:
        list(executor.map(fetch_feedback, results))

    missing_set = set(all_missing)
    learning_priority = sorted(
        [{"skill": s, "demand_count": c} for s, c in skill_demand.items() if s in missing_set],
        key=lambda x: x["demand_count"],
        reverse=True
    )
    learning_priority = learning_priority[:10]
    for item in learning_priority:
        item["resources"] = get_resources_for_skill(item["skill"])

    avg_score = round(sum(r["fit_score"] for r in results) / len(results)) if results else 0

    # 💾 안전한 사용자별 매칭 이력 스냅샷 DB 보관 로직
    try:
        # UserProfile 자동 방어 생성
        prof = UserProfile.query.get(user.id)
        if not prof:
            prof = UserProfile(id=user.id, name=user.username)
            db.session.add(prof)
            db.session.flush()

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

        # 통째로 복원할 수 있도록 전체 결과 세트(JSON)까지 보관 구조 확장
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
        print(f"[MatchHistory] 유저 {user.username}의 분석 결과 저장 완료 (ID: {history_record.id})")
    except Exception as db_err:
        print(f"[MatchHistory] DB 저장 에러: {db_err}")

    return jsonify({
        "results":           results,
        "learning_priority": learning_priority,
        "resume_used":       bool(resume_text),
        "summary": {
            "total_jobs":    len(all_jobs),
            "analyzed_jobs": len(results),
            "avg_fit_score": avg_score,
        }
    })


# =======================================================================
# 🔄 ✨ [신규 기능 추가] 과거 저장된 이력 리스트 및 상세 내용 조회 API
# =======================================================================

@analyze_bp.route("/api/analyze/history", methods=["GET"])
def get_analyze_history():
    """현재 로그인한 사용자의 과거 매칭 분석 이력 목록 전체 조회 (최신순 20개)"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401
        
    try:
        histories = MatchHistory.query.filter_by(user_id=user.id).order_by(MatchHistory.run_at.desc()).limit(20).all()
        return jsonify([h.to_dict() for h in histories]), 200
    except Exception as e:
        return jsonify({"error": f"이력 조회 실패: {str(e)}"}), 500


@analyze_bp.route("/api/analyze/history/<int:history_id>", methods=["GET"])
def get_analyze_history_detail(history_id):
    """특정 과거 기록을 클릭했을 때 해당 스냅샷 데이터를 온전하게 화면에 복원해주는 상세 보기 API"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401
        
    try:
        record = MatchHistory.query.filter_by(id=history_id, user_id=user.id).first()
        if not record:
            return jsonify({"error": "존재하지 않거나 접근 권한이 없는 분석 기록입니다."}), 404
            
        return jsonify({
            "id": record.id,
            "run_at": record.run_at.isoformat() if record.run_at else None,
            "avg_fit_score": record.avg_fit_score,
            "total_jobs": record.total_jobs,
            "analyzed_jobs": record.analyzed_jobs,
            "skills_snapshot": [s.strip() for s in record.skills_snapshot.split(",") if s.strip()] if record.skills_snapshot else [],
            "preferences_snapshot": json.loads(record.preferences_snapshot) if record.preferences_snapshot else {},
            "top_matches": json.loads(record.top_matches) if record.top_matches else []
        }), 200
    except Exception as e:
        return jsonify({"error": f"상세 기록 로드 실패: {str(e)}"}), 500