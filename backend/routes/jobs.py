import os
import json
import re
from flask import Blueprint, request, jsonify
from extensions import db
from models import JobPosting, SkillStat, UserProfile
from services.collector.remotive import normalize as remotive_normalize
from services.parser.multi_ai import extract_skills, make_feedback
from routes.auth import get_current_user_from_request

# Anthropic(Claude) 공식 라이브러리 안전하게 로드
try:
    from anthropic import Anthropic
except ImportError:
    import sys
    print("🚨 [Warning] 'anthropic' 라이브러리가 없습니다. 터미널에 'pip install anthropic'을 실행하세요.", file=sys.stderr)

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Jobfit AI Backend is running"})


@jobs_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def save_raw_jobs_list(data: list) -> tuple:
    """raw 채용 공고 목록을 받아서 각 소스별로 정규화하고 DB에 저장하는 공통 헬퍼 함수"""
    saved, skipped = 0, 0
    skill_freq = {}

    for raw in data:
        source = raw.get("source", "remotive")

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

        if JobPosting.query.filter_by(job_id=normalized["job_id"]).first():
            skipped += 1
            continue

        # n8n 수집 시 실시간 스킬 추출 (에러 발생 시 전체 중단되지 않도록 try-except 처리)
        try:
            parsed = extract_skills(normalized.get("description", ""))
            skills_str = ",".join(parsed.get("skills", []))
        except Exception as e:
            print(f"[Warning] 스킬 추출 실패 (job_id: {normalized.get('job_id')}): {e}")
            parsed = {"skills": []}
            skills_str = ""

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

    for skill, cnt in skill_freq.items():
        # 대소문자 구분 없이 기존 스킬 데이터 조회하여 이중 등록 방지
        stat = SkillStat.query.filter(db.func.lower(SkillStat.skill_name) == db.func.lower(skill)).first()
        if stat:
            stat.count += cnt
        else:
            db.session.add(SkillStat(skill_name=skill, count=cnt))

    db.session.commit()
    return saved, skipped


@jobs_bp.route("/api/jobs", methods=["POST"])
def save_jobs():
    """n8n에서 채용 공고 저장 연동 포트"""
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
    try:
        from sqlalchemy import func
        stats_query = db.session.query(
            JobPosting.source, func.count(JobPosting.id)
        ).group_by(JobPosting.source).all()
        
        counts = {"remotive": 0, "adzuna": 0}
        for source, count in stats_query:
            if source:
                counts[source] = count
        
        counts["total"] = JobPosting.query.count()
        return jsonify(counts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jobs_bp.route("/api/jobs/sync", methods=["POST"])
def sync_jobs():
    """크롤러 백엔드 다이렉트 동기화 스위치"""
    from services.collector.remotive import fetch_raw_remotive
    from services.collector.adzuna import fetch_raw_adzuna

    sync_results = {}
    
    try:
        remotive_raw = fetch_raw_remotive(limit=30)
        remotive_saved, remotive_skipped = save_raw_jobs_list(remotive_raw)
        sync_results["remotive"] = {"saved": remotive_saved, "skipped": remotive_skipped, "status": "success"}
    except Exception as e:
        sync_results["remotive"] = {"saved": 0, "skipped": 0, "status": "error", "message": str(e)}

    adzuna_id = os.getenv("ADZUNA_APP_ID")
    adzuna_key = os.getenv("ADZUNA_APP_KEY")
    if adzuna_id and adzuna_key:
        try:
            adzuna_raw = fetch_raw_adzuna(adzuna_id, adzuna_key, limit=30)
            adzuna_saved, adzuna_skipped = save_raw_jobs_list(adzuna_raw)
            sync_results["adzuna"] = {"saved": adzuna_saved, "skipped": adzuna_skipped, "status": "success"}
        except Exception as e:
            sync_results["adzuna"] = {"saved": 0, "skipped": 0, "status": "error", "message": str(e)}
    else:
        sync_results["adzuna"] = {"saved": 0, "skipped": 0, "status": "skipped", "message": "API 키 미구성"}

    total_saved = sum(item.get("saved", 0) for item in sync_results.values())
    total_skipped = sum(item.get("skipped", 0) for item in sync_results.values())

    return jsonify({
        "success": True,
        "results": sync_results,
        "summary": {"total_saved": total_saved, "total_skipped": total_skipped}
    })


@jobs_bp.route("/api/jobs", methods=["GET"])
def get_jobs():
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    source   = request.args.get("source")
    skill    = request.args.get("skill")

    q = JobPosting.query
    if source:
        q = q.filter_by(source=source)
    if skill:
        skill_lower = skill.strip().lower()
        q = q.filter(
            (db.func.lower(JobPosting.skills) == skill_lower) |
            db.func.lower(JobPosting.skills).like(f"{skill_lower},%") |
            db.func.lower(JobPosting.skills).like(f"%,{skill_lower}") |
            db.func.lower(JobPosting.skills).like(f"%,{skill_lower},%")
        )

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
    limit = request.args.get("limit", 20, type=int)
    stats = SkillStat.query.order_by(SkillStat.count.desc()).limit(limit).all()
    return jsonify([s.to_dict() for s in stats])


# =======================================================================
# 🔐 [보안 결합 완료] 다중 유저 토큰 기반 AI 가중치 매칭 엔드포인트
# =======================================================================
@jobs_bp.route("/api/jobs/match", methods=["POST"])
def get_ai_weighted_matches():
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    data = request.get_json() or {}
    # 파라미터 네이밍 통일 (user_skills를 우선으로 하고, skills는 하위 호환성 유지)
    user_skills = data.get("user_skills") or data.get("skills", [])
    user_salary = data.get("salary", 0)
    preferred_location = data.get("location", "Worldwide")
    
    # 로그인한 유저의 실제 DB 프로필에서 이력서 추적
    resume_text = ""
    profile = UserProfile.query.get(user.id)
    if profile and profile.resume:
        resume_text = profile.resume

    skill_importance = data.get("skill_importance", "보통")
    salary_importance = data.get("salary_importance", "보통")
    location_importance = data.get("location_importance", "보통")
    
    job_postings = JobPosting.query.order_by(JobPosting.fetched_at.desc()).limit(10).all()
    if not job_postings:
        return jsonify({"status": "success", "results": [], "message": "DB에 분석할 채용 공고가 없습니다."}), 200

    jobs_payload = []
    for j in job_postings:
        jobs_payload.append({
            "db_id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "salary_text": j.salary,
            "extracted_skills": j.skills
        })

    system_prompt = f"""
    당신은 구직자의 정량적 요구사항과 채용 공고간의 적합도를 계산하는 'Multi-Agent 매칭 본부 AI'입니다.
    [구직자 보유 스킬]: {user_skills} (중요도: {skill_importance})
    [희망 연봉]: {user_salary} KRW (중요도: {salary_importance})
    [선호 지역]: {preferred_location} (중요도: {location_importance})

    [💥 이력서 프로젝트 결합 피드백 특수 지침]
    구직자의 저장된 이력서 본문:
    ---
    {resume_text if resume_text else "제공된 이력서 없음"}
    ---
    이력서 본문이 존재하는 경우, 구직자의 실제 프로젝트 경험 이력과 공고의 부족한 기술셋을 매칭하여 
    구체적인 한국어 실무 리팩토링 방안을 2줄 요약 리포트로 출력하세요.
    
    반드시 마크다운 기호 없이 순수한 JSON 배열 형태로만 응답하세요.
    [
      {{"db_id": 공고_id(Integer), "match_rate": 점수(Integer), "ai_feedback": "한국어 2줄"}}
    ]
    """

    raw_output = ""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key and not api_key.startswith("TEMP"):
        try:
            print("[Match Engine] Claude API 호출 시도...")
            model_name = os.getenv("CLAUDE_MODEL_NAME", "claude-3-haiku-20240307")
            anthropic_client = Anthropic(api_key=api_key, timeout=5.0)
            response = anthropic_client.messages.create(
                model=model_name, max_tokens=2000, temperature=0.2, system=system_prompt,
                messages=[{"role": "user", "content": f"공고: {json.dumps(jobs_payload, ensure_ascii=False)}"}]
            )
            raw_output = response.content[0].text.strip()
        except Exception as e:
            print(f"⚠️ Claude 호출 실패, OpenAI 우회 엔진으로 자동 전환: {e}")

    if not raw_output:
        try:
            print("[Match Engine] OpenAI 우회 엔진 가동...")
            import openai
            openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"공고: {json.dumps(jobs_payload, ensure_ascii=False)}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw_output = response.choices[0].message.content.strip()
            if raw_output.startswith("{") and not raw_output.startswith("["):
                temp_json = json.loads(raw_output)
                if "results" in temp_json: raw_output = json.dumps(temp_json["results"])
                elif isinstance(temp_json, dict) and len(temp_json) == 1: raw_output = json.dumps(list(temp_json.values())[0])
                else: raw_output = f"[{raw_output}]"
        except Exception as openai_err:
            return jsonify({"status": "error", "message": f"AI 호출 최종 실패: {openai_err}"}), 500

    try:
        if raw_output.startswith("```"):
            raw_output = raw_output.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_output.startswith("json"): raw_output = raw_output.split("\n", 1)[1].strip()

        scored_list = json.loads(raw_output)
        final_results = []
        job_map = {j.id: j for j in job_postings}
        
        for item in scored_list:
            j_id = item.get("db_id")
            if j_id in job_map:
                job_obj = job_map[j_id]
                final_results.append({
                    "id": job_obj.id, "title": job_obj.title, "company": job_obj.company,
                    "location": job_obj.location, "salary": job_obj.salary, "skills": job_obj.skills,
                    "apply_url": job_obj.apply_url, "source": job_obj.source,
                    "match_rate": item.get("match_rate", 0), "ai_feedback": item.get("ai_feedback", "분석 완료")
                })
        final_results.sort(key=lambda x: x["match_rate"], reverse=True)
        return jsonify({"status": "success", "count": len(final_results), "results": final_results}), 200
    except Exception as parse_err:
        return jsonify({"status": "error", "message": "결과 데이터 정형화 실패"}), 500


# =======================================================================
# ✨ [인증 결합 완성] 신규 기능: 구직자 이력서 실시간 즉시 분석 및 매칭 엔진
# =======================================================================
@jobs_bp.route("/api/jobs/analyze-resume", methods=["POST"])
def analyze_user_resume():
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    data = request.get_json() or {}
    resume_text = data.get("resume_text", "").strip()
    
    skill_importance = data.get("skill_importance", "보통")
    salary_importance = data.get("salary_importance", "보통")
    location_importance = data.get("location_importance", "보통")
    user_salary = data.get("salary", 0)
    preferred_location = data.get("location", "Worldwide")

    if not resume_text:
        return jsonify({"status": "error", "message": "분석할 이력서 내용이 없습니다."}), 400

    print(f"[Resume Engine] 유저 {user.username}의 실시간 이력서 파싱 시작...")

    try:
        import openai
        openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        resume_prompt = """
        당신은 구직자의 이력서를 정밀 분석하는 '인사 전문가 AI'입니다.
        제공된 이력서 텍스트를 읽고 구직자가 보유한 핵심 기술 스택 명사 리스트를 JSON 포맷으로 추출하세요.
        { "extracted_skills": ["Java", "Spring Boot", "MySQL"] }
        """
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": resume_prompt},
                {"role": "user", "content": f"구직자 이력서 내용:\n{resume_text}"}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        resume_analysis = json.loads(response.choices[0].message.content.strip())
        extracted_skills = resume_analysis.get("extracted_skills", [])
    except Exception as e:
        return jsonify({"status": "error", "message": f"이력서 AI 분석 오류: {str(e)}"}), 500

    if not extracted_skills:
        return jsonify({"status": "success", "extracted_skills": [], "results": [], "message": "추출된 기술 스택이 없습니다."}), 200

    job_postings = JobPosting.query.order_by(JobPosting.fetched_at.desc()).limit(10).all()
    if not job_postings:
        return jsonify({"status": "success", "extracted_skills": extracted_skills, "results": []}), 200

    jobs_payload = []
    for j in job_postings:
        jobs_payload.append({
            "db_id": j.id, "title": j.title, "company": j.company,
            "location": j.location, "salary_text": j.salary, "extracted_skills": j.skills
        })

    system_prompt = f"""
    당신은 구직자의 요구사항과 채용 공고간의 적합도를 계산하는 '매칭 본부 AI'입니다.
    - 보유 스킬: {extracted_skills} (중요도: {skill_importance})
    - 희망 연봉: {user_salary} (중요도: {salary_importance})
    - 선호 지역: {preferred_location} (중요도: {location_importance})

    반드시 마크다운 기호 없이 순수한 JSON 배열 형태로만 반환하세요.
    [
      {{"db_id": 공고_id(Integer), "match_rate": 점수(Integer), "ai_feedback": "점수 산정 이유 (한국어 2줄)"}}
    ]
    """

    try:
        match_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"공고: {json.dumps(jobs_payload, ensure_ascii=False)}"}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        raw_output = match_response.choices[0].message.content.strip()

        if raw_output.startswith("{") and not raw_output.startswith("["):
            temp_json = json.loads(raw_output)
            if "results" in temp_json: raw_output = json.dumps(temp_json["results"])
            elif isinstance(temp_json, dict) and len(temp_json) == 1: raw_output = json.dumps(list(temp_json.values())[0])
            else: raw_output = f"[{raw_output}]"

        scored_list = json.loads(raw_output)
        final_results = []
        job_map = {j.id: j for j in job_postings}
        
        for item in scored_list:
            j_id = item.get("db_id")
            if j_id in job_map:
                job_obj = job_map[j_id]
                final_results.append({
                    "id": job_obj.id, "title": job_obj.title, "company": job_obj.company,
                    "location": job_obj.location, "salary": job_obj.salary, "skills": job_obj.skills,
                    "apply_url": job_obj.apply_url, "source": job_obj.source,
                    "match_rate": item.get("match_rate", 0), "ai_feedback": item.get("ai_feedback", "분석 완료")
                })
        final_results.sort(key=lambda x: x["match_rate"], reverse=True)
        return jsonify({"status": "success", "extracted_skills": extracted_skills, "count": len(final_results), "results": final_results}), 200
    except Exception as parse_err:
        return jsonify({"status": "error", "message": "이력서 결과 매칭 데이터 정형화 실패"}), 500