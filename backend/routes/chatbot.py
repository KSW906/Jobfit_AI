import os
import json
import requests
from flask import Blueprint, request, jsonify
from extensions import db
from models import JobPosting, UserProfile, InterviewPracticeSession
from routes.auth import get_current_user_from_request
from dotenv import load_dotenv
from services.parser.answer_learner import (
    make_question_key,
    save_community_answer,
    get_or_update_optimal_answer,
    fetch_optimal_answer,
    get_community_stats,
)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

chatbot_bp = Blueprint("chatbot", __name__)


def call_llm(prompt: str, json_mode: bool = False) -> str:
    """
    Gemini, OpenAI, Claude를 병렬로 호출하여 초안을 수집한 뒤,
    최종 합성 LLM을 통해 최선의 답변으로 종합(Synthesis)하여 반환하는 앙상블 시스템
    """
    import concurrent.futures

    def run_gemini():
        if GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                if json_mode:
                    payload["generationConfig"] = {"responseMimeType": "application/json"}
                res = requests.post(url, headers=headers, json=payload, timeout=15)
                res.raise_for_status()
                res_json = res.json()
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                print(f"[Ensemble Gemini Chatbot Warning] {e}")
        return None

    def run_openai():
        if OPENAI_API_KEY:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}]
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}
                res = requests.post(url, headers=headers, json=payload, timeout=15)
                res.raise_for_status()
                res_json = res.json()
                return res_json["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[Ensemble OpenAI Chatbot Warning] {e}")
        return None

    def run_claude():
        if ANTHROPIC_API_KEY:
            try:
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                }
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                res.raise_for_status()
                text_content = res.json()["content"][0]["text"].strip()
                if json_mode:
                    if "```json" in text_content:
                        text_content = text_content.split("```json")[1].split("```")[0].strip()
                    elif "```" in text_content:
                        text_content = text_content.split("```")[1].split("```")[0].strip()
                return text_content
            except Exception as e:
                print(f"[Ensemble Claude Chatbot Warning] {e}")
        return None

    # ThreadPoolExecutor를 이용해 병렬 수행
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_gemini = executor.submit(run_gemini)
        future_openai = executor.submit(run_openai)
        future_claude = executor.submit(run_claude)

        r_gemini = future_gemini.result()
        r_openai = future_openai.result()
        r_claude = future_claude.result()

    drafts = []
    if r_gemini: drafts.append(("Gemini", r_gemini))
    if r_openai: drafts.append(("OpenAI", r_openai))
    if r_claude: drafts.append(("Claude", r_claude))

    if not drafts:
        raise RuntimeError("챗봇에 사용할 수 있는 활성화된 AI API 키가 없습니다.")

    if len(drafts) == 1:
        # 단 하나의 모델만 성공 시 즉시 반환
        return drafts[0][1]

    # 초안 병합 텍스트 구축
    drafts_text = ""
    for name, text in drafts:
        drafts_text += f"\n--- [{name}의 답변 초안] ---\n{text}\n"

    # 합성 지침 구성
    if json_mode:
        synthesis_prompt = f"""당신은 여러 AI 모델들의 JSON 형식 답변 초안을 분석하고 정합하여 최종 하나의 완벽한 JSON 답변을 도출하는 수석 AI 커리어 코치입니다.
아래 제공된 여러 AI 모델들의 답변 초안을 바탕으로, 정보를 교차 검증 및 종합하여 하나의 최종 완성된 JSON 객체(또는 배열)를 작성해 주세요.

[각 AI 모델들의 답변 초안]
{drafts_text}

[출력 지침]
- 반드시 다른 부가적인 텍스트, 설명, 서론/결론 및 마크다운 백틱(```) 없이 오직 유효한 단 하나의 JSON 객체/배열만을 반환하세요.
- 원래의 질문 포맷이 예상 면접 질문 리스트(["질문1", "질문2", "질문3"])라면, 최종 결과도 동일한 질문 개수와 포맷의 JSON 배열 형태여야 합니다.
- 원래의 질문 포맷이 면접 채점 피드백 객체({{"score": ..., "analysis": ..., "model_answer": ...}})라면, 최종 결과도 해당 필드를 가지는 하나의 JSON 객체여야 합니다. 각 초안의 score를 참고하여 신뢰성 높은 점수(평균값 내외)를 매기고, 강점과 약점이 고루 담기도록 조언(analysis)과 모범 답안(model_answer)을 정교하게 다듬어 한글로 출력하세요.
"""
    else:
        synthesis_prompt = f"""당신은 여러 AI 모델들이 구직자에게 작성한 커리어 조언 및 대답 초안을 비교 정제하여 최종 완성본을 도출하는 수석 AI 커리어 코치입니다.
아래 제공된 답변 초안들을 꼼꼼히 비교 및 분석하여, 중복된 조언은 제거하고, 각 모델의 실질적인 팁들을 조합하여 자연스럽고 전문적인 한국어 조언으로 합성해 주세요.

[구직자의 원래 질문 및 문맥]
{prompt}

[각 AI 모델들의 답변 초안]
{drafts_text}

[출력 지침]
- 구직자에게 친절하고 격려하는 태도의 존댓말로 답변해 주세요.
- 완성도 높은 문장으로 톤앤매너를 일치시켜 조언을 작성하세요.
- 다른 AI 모델의 명칭(예: "Gemini가 말한 바와 같이")은 언급하지 마세요.
"""

    def call_synthesis_model(synth_prompt: str) -> str:
        if ANTHROPIC_API_KEY:
            try:
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": synth_prompt}]
                }
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                res.raise_for_status()
                text_content = res.json()["content"][0]["text"].strip()
                if json_mode:
                    if "```json" in text_content:
                        text_content = text_content.split("```json")[1].split("```")[0].strip()
                    elif "```" in text_content:
                        text_content = text_content.split("```")[1].split("```")[0].strip()
                return text_content
            except Exception as e:
                print(f"[Ensemble Synthesis Claude Error] {e}")

        if OPENAI_API_KEY:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": synth_prompt}]
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[Ensemble Synthesis OpenAI Error] {e}")

        if GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": synth_prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                res = requests.post(url, headers=headers, json=payload, timeout=15)
                res.raise_for_status()
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                print(f"[Ensemble Synthesis Gemini Error] {e}")

        raise RuntimeError("합성 과정 실패")

    try:
        return call_synthesis_model(synthesis_prompt)
    except Exception as e:
        print(f"[Warning] 합성 단계 실패로 인한 첫 번째 초안 즉시 반환: {e}")
        return drafts[0][1]


@chatbot_bp.route("/api/chat/message", methods=["POST"])
def send_chat_message():
    """AI 커리어 코치 1:1 대화 엔드포인트"""
    user = get_current_user_from_request()
    body = request.get_json() or {}
    message = body.get("message", "").strip()
    history = body.get("history", [])

    # history가 비정상적인 타입으로 들어올 경우 안전하게 빈 리스트로 초기화
    if not isinstance(history, list):
        history = []

    if not message:
        return jsonify({"error": "메시지가 필요합니다."}), 400

    # 유저 프로필 컨텍스트 확보
    skills_context = "없음"
    resume_context = "없음"
    if user:
        prof = UserProfile.query.get(user.id)
        if prof:
            if prof.skills:
                skills_context = prof.skills
            if prof.resume:
                resume_context = prof.resume[:1500]  # 토큰 절약

    # 대화 히스토리 구성
    history_prompt = ""
    for h in history[-8:]:  # 최근 8개 대화만 컨텍스트로 전달
        if isinstance(h, dict):
            role = "구직자" if h.get("role") == "user" else "AI 코치"
            history_prompt += f"{role}: {h.get('content', '')}\n"

    prompt = f"""당신은 IT 채용 및 커리어를 전문으로 하는 친근하고 노련한 AI 커리어 코치입니다.
사용자(구직자)의 고민이나 이력서 질문에 조언을 남겨주세요.
항상 존댓말로 친절하게 조언하고, 격려해 주는 태도를 유지하세요.

[구직자 정보]
- 보유 기술: {skills_context}
- 이력서 초안 요약: {resume_context}

[이전 대화 내역]
{history_prompt}
구직자: {message}
AI 코치:"""

    try:
        reply = call_llm(prompt)
        return jsonify({"reply": reply}), 200
    except RuntimeError as re:
        if "API 키가 없습니다" in str(re):
            return jsonify({"error": "AI API 키가 설정되지 않아 챗봇을 사용할 수 없습니다."}), 503
        return jsonify({"error": f"AI 조언 생성 중 실패: {str(re)}"}), 500
    except Exception as e:
        return jsonify({"error": f"AI 조언 생성 중 실패: {str(e)}"}), 500


@chatbot_bp.route("/api/chat/interview/start", methods=["POST"])
def start_interview():
    """특정 채용공고 타겟팅 모의 면접 시작 세션 생성"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요합니다."}), 401

    body = request.get_json() or {}
    job_posting_id = body.get("job_posting_id")
    interview_mode = body.get("interview_mode", "diagnostic")  # "stress", "diagnostic", "friendly"

    if not job_posting_id:
        return jsonify({"error": "직무 공고 ID가 필요합니다."}), 400

    job = JobPosting.query.get(job_posting_id)
    if not job:
        return jsonify({"error": "존재하지 않는 채용 공고입니다."}), 404

    # 유저 프로필 컨텍스트 확보 및 프로필 없을 시 자동 방어 생성 (외래키 위배 방지)
    prof = UserProfile.query.get(user.id)
    if not prof:
        prof = UserProfile(id=user.id, name=user.username)
        db.session.add(prof)
        db.session.flush()

    resume_text = prof.resume if prof.resume else "이력서 정보가 아직 등록되지 않았습니다."
    user_skills = prof.skills if prof.skills else "스킬셋 미등록"

    # 모드에 따른 프롬프트 지침 주입
    if interview_mode == "stress":
        mode_instruction = "압박 기술 면접 모드입니다. 구직자가 답하기 까다롭고 논리적/기술적 검증이 필요한 아주 예리하고 난이도 높은 핵심 면접 질문 3가지를 출제해 주세요."
    elif interview_mode == "friendly":
        mode_instruction = "친절한 모의 훈련 모드입니다. 면접에 미숙하거나 긴장하는 신입 구직자를 위해 긴장을 해소해 주면서 직군에 대한 기본 지식과 경험을 묻는 비교적 친절하고 평이한 질문 3가지를 출제해 주세요."
    elif interview_mode == "timer":
        mode_instruction = "타임어택(시간제한) 면접 모드입니다. 답변자가 60초의 짧은 시간 제한 동안 대답해야 하므로, 장황한 설명보다 핵심 개념, 기술적 판단 기준, 핵심 논리를 간결하고 명확하게 요약해 답해야 하는 대표적인 직무 및 기술 면접 질문 3가지를 출제해 주세요."
    else:  # diagnostic
        mode_instruction = "다각도 기술 진단 모드입니다. 지원자의 인성/협업(HR), 기술 역량(Tech), 비즈니스 해결 능력(CTO)을 고루 진단해 볼 수 있는 균형 잡힌 대표 면접 질문 3가지를 출제해 주세요."

    prompt = f"""당신은 채용 기업의 기술 및 인사 부서 면접관입니다.
{mode_instruction}
아래 채용 공고와 구직자의 이력서 정보를 밀도 있게 대조하여 질문을 구성해 주세요.
반드시 다른 부가 설명이나 서론 없이 정확히 유효한 JSON 배열 문자열 포맷으로만 답변해야 합니다.

[채용 공고]
- 회사명: {job.company or "익명 기업"}
- 직무명: {job.title}
- 기술 요구사항: {job.skills or "공고 내 명시되지 않음"}
- 공고 본문: {job.description[:1000]}

[구직자 이력 정보]
- 보유 기술: {user_skills}
- 이력서 본문: {resume_text[:1200]}

반환 형식(JSON):
["질문1", "질문2", "질문3"]"""

    try:
        res_text = call_llm(prompt, json_mode=True)
        questions = json.loads(res_text)
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("생성된 질문이 배열 형태가 아닙니다.")
    except Exception as re:
        if isinstance(re, RuntimeError) and "API 키가 없습니다" in str(re):
            return jsonify({"error": "AI API 키가 설정되지 않아 모의 면접을 시작할 수 없습니다."}), 503
        print(f"[Interview Questions Error] {re}")
        # 예외 발생 시 표준 질문 폴백 제공
        # 유저 보유 기술 기반 첫 번째 대표 스킬 추출 (1개만 있어도 대표 기술명 정상 출력)
        user_skills_list = [s.strip() for s in user_skills.split(",") if s.strip()]
        fallback_skill = user_skills_list[0] if user_skills_list else "대표 스킬"

        questions = [
            f"공고된 '{job.title}' 직무를 성공적으로 수행하기 위해 본인이 가진 가장 강점인 기술(예: {fallback_skill})은 무엇인지 설명해 주세요.",
            f"이력서 상의 프로젝트 경험 중 가장 기억에 남는 백엔드/프론트엔드 해결 기술 문제와 그 결과를 설명해 주세요.",
            f"새로운 기술 스택이나 협업 도구를 프로젝트에 조기 도입하여 적응했던 경험과 교훈을 말해 주세요."
        ]

    # 세션 디비 저장
    session = InterviewPracticeSession(
        user_id=user.id,
        job_posting_id=job.id,
        job_title=job.title,
        company=job.company or "익명 기업",
        questions=json.dumps(questions),
        answers=json.dumps([]),
        feedbacks=json.dumps([]),
        current_index=0,
        is_completed=False,
        interview_mode=interview_mode
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "session_id": session.id,
        "company": session.company,
        "job_title": session.job_title,
        "interview_mode": session.interview_mode,
        "questions_count": len(questions),
        "current_index": 0,
        "question": questions[0]
    }), 200


@chatbot_bp.route("/api/chat/interview/answer", methods=["POST"])
def submit_interview_answer():
    """모의 면접 특정 질문에 대한 답변 제출 및 실시간 피드백 채점"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요합니다."}), 401

    body = request.get_json() or {}
    session_id = body.get("session_id")
    user_answer = body.get("answer", "").strip()

    if not session_id or not user_answer:
        return jsonify({"error": "세션 ID와 답변이 필요합니다."}), 400

    session = InterviewPracticeSession.query.get(session_id)
    if not session:
        return jsonify({"error": "존재하지 않는 면접 세션입니다."}), 404

    if session.user_id != user.id:
        return jsonify({"error": "본인 세션만 채점할 수 있습니다."}), 403

    if session.is_completed:
        return jsonify({"error": "이미 완료된 면접 세션입니다."}), 400

    questions = json.loads(session.questions)
    answers = json.loads(session.answers)
    feedbacks = json.loads(session.feedbacks)
    
    if session.current_index >= len(questions):
        return jsonify({"error": "이미 모든 면접 질문에 답변을 제출하셨습니다."}), 400
        
    current_q = questions[session.current_index]
    interview_mode = session.interview_mode or "diagnostic"

    # 각 모드에 따른 프롬프트 및 응답 스키마 구성
    if interview_mode == "stress":
        prompt = f"""당신은 매우 엄격하고 예리한 기술 면접관입니다.
구직자가 면접 질문에 답한 내용을 냉정하고 꼼꼼하게 평가하고, 보완이 필요한 기술적 한계나 논리적 허점을 매섭게 짚어내며 날카로운 비판을 제공해 주세요.
그러나 답변이 기술적으로 정확하고 우수한 해결책을 제시했다면 80~100점 사이의 높은 점수를 부여해야 하며, 무조건적으로 점수를 낮게 깎아서는 안 됩니다. 즉, '비판은 날카롭게 하되 점수는 답변의 객관적 완성도에 맞춰 공정하게 채점'하세요.
그리고 구직자의 답변에서 더 검증해야 할 기술적 허점을 물고 늘어지는 '꼬리 질문(follow_up_question)'을 한국어로 1문항 만들어야 합니다.
반드시 아래 정의된 JSON 포맷 하나만 반환해야 하며 다른 텍스트는 금지합니다.

[면접 컨텍스트]
- 회사/직무: {session.company} - {session.job_title}
- 면접 질문: {current_q}
- 구직자 답변: {user_answer}

반환 형식(JSON):
{{
  "score": 85,
  "analysis": "제시한 이벤트 드리븐 아키텍처 도입 및 수치적 개선 성과는 훌륭하지만, 대용량 트래픽이 몰렸을 때 발생할 수 있는 메모리 누수 방안에 대한 언급이 빠져 있어 기술적 디테일 면에서 약간의 보완이 필요해 보입니다.",
  "model_answer": "이전 아키텍처에서는 CPU 병목이 발생하여, 이를 극복하고자 메모리 상에서 비동기로 이벤트를 처리하는 Node.js 이벤트를 채택해 동시성을 40% 올렸습니다.",
  "follow_up_question": "그렇다면 이벤트를 처리할 때 동시 실행이 몰리면서 메모리가 급증하는 병목이 생겼을 텐데, 백프레셔(Backpressure) 조절은 구체적으로 어떻게 하셨나요?"
}}"""
    elif interview_mode == "friendly":
        prompt = f"""당신은 면접이 떨리는 구직자를 따뜻하게 다독여 주고 격려하는 친절한 멘토형 면접관입니다.
구직자가 답한 내용 중 잘한 점을 크게 칭찬해 주고, 부족한 점은 상처받지 않게 부드럽게 설명하며, 부족한 부분에 대한 힌트(hint)와 쉬운 모범 문장을 제시해 주세요.
반드시 아래 정의된 JSON 포맷 하나만 반환해야 하며 다른 텍스트는 금지합니다.

[면접 컨텍스트]
- 회사/직무: {session.company} - {session.job_title}
- 면접 질문: {current_q}
- 구직자 답변: {user_answer}

반환 형식(JSON):
{{
  "score": 88,
  "analysis": "정말 훌륭하고 자신감 있는 답변입니다! 여기에 구체적인 수치(예: 응답시간 몇 % 개선)를 조금만 곁들이면 완벽한 면접관 취향 저격 대답이 될 거예요.",
  "model_answer": "네! 저는 가상 DOM이 필요한 UI 위주로 개발하였고, 그 결과 렌더링 성능을 개선해 사용자 경험을 올릴 수 있었습니다.",
  "hint": "프로젝트에서 겪은 수치적 성과(예: 로딩속도 2초 단축)나, React.memo 등을 활용한 구체적 최적화 경험을 녹여내시면 훨씬 완성도가 높아집니다."
}}"""
    elif interview_mode == "timer":
        prompt = f"""당신은 타임어택 면접관입니다. 구직자가 60초의 시간 제한을 느끼며 답변한 내용을 채점합니다.
만약 구직자가 답변을 작성하지 못해 답변 내용이 "(제한시간 내에 답변을 제출하지 못했습니다.)" 인 경우, 냉정하게 시간 관리(Time Management) 실패를 지적하고 0~10점 수준의 최하점을 부여하며, 해당 질문에 대한 대략적인 핵심 모범 키워드를 조언에 곁들여 주세요.
정상적으로 답변을 제출한 경우, 주어진 시간 내에 군더더기 없이 핵심 키워드와 논리를 얼마나 명확히 간결하게 전달했는지를 중점적으로 판단하여 평가 및 스코어링을 해주세요.
반드시 아래 정의된 JSON 포맷 하나만 반환해야 하며 다른 텍스트는 금지합니다.

[면접 컨텍스트]
- 회사/직무: {session.company} - {session.job_title}
- 면접 질문: {current_q}
- 구직자 답변: {user_answer}

반환 형식(JSON):
{{
  "score": 85,
  "analysis": "제한 시간 내에 핵심 키워드(예: 가상 DOM, 렌더링 성능)를 명확히 짚어 간결하게 훌륭히 답변했습니다.",
  "model_answer": "가상 DOM의 변경 부분만 배치로 업데이트하여 브라우저 리페인팅 성능을 극대화하는 형태로 설명하여 60초 내 핵심 요약 답변이 되도록 구성했습니다."
}}"""
    else:  # diagnostic
        prompt = f"""당신은 구직자의 역량을 인사(HR), 기술 스택(Tech), 비즈니스 해결 능력(CTO) 세 가지 면접관 관점에서 다각도로 평가하는 AI 진단 면접관입니다.
답변 내용을 토대로 3인의 면접관 관점의 점수와 코멘트를 작성해 주세요.
반드시 아래 정의된 JSON 포맷 하나만 반환해야 하며 다른 텍스트는 금지합니다.

[면접 컨텍스트]
- 회사/직무: {session.company} - {session.job_title}
- 면접 질문: {current_q}
- 구직자 답변: {user_answer}

반환 형식(JSON):
{{
  "score": 80,
  "analysis": "전반적으로 균형 잡힌 답변이나, 기술적 상세 스펙이 보강된다면 설득력이 더 높아질 것입니다.",
  "model_answer": "네, 가상 DOM의 비교 연산 횟수를 최소화하기 위해 컴포넌트를 분할하고 재사용성을 도모했습니다.",
  "personas": {{
    "HR 면접관": {{ "score": 85, "comment": "차분하고 논리적인 톤으로 답변하여 호감도가 높습니다." }},
    "기술 면접관": {{ "score": 75, "comment": "개념은 알지만 실무 코드 최적화 경험에 대한 예시가 조금 부족합니다." }},
    "CTO 면접관": {{ "score": 80, "comment": "기술을 비즈니스 문제 해결에 어떻게 연결했는지가 조금 더 부각되어야 합니다." }}
  }}
}}"""

    try:
        res_text = call_llm(prompt, json_mode=True)
        feedback_data = json.loads(res_text)
        score = int(feedback_data.get("score", 70))
        analysis = feedback_data.get("analysis", "답변 작성을 완료했습니다.")
        model_answer = feedback_data.get("model_answer", "피드백을 바탕으로 보완 답변을 구성해 보세요.")
    except Exception as e:
        print(f"[Answer Scoring Error] {e}")
        score = 75
        analysis = "답변 작성을 완료하셨습니다. 기술적 디테일을 조금 더 상세하게 기술해 준다면 훨씬 완성도 높은 면접 대답이 될 것입니다."
        model_answer = "공식 문서 내용과 본인의 주도적인 트러블슈팅 경험을 결합해 재구성해 보세요."
        feedback_data = {}

    current_feedback = {
        "question": current_q,
        "answer": user_answer,
        "score": score,
        "analysis": analysis,
        "model_answer": model_answer
    }

    # 추가 데이터 병합
    if interview_mode == "stress":
        current_feedback["follow_up_question"] = feedback_data.get("follow_up_question")
    elif interview_mode == "friendly":
        current_feedback["hint"] = feedback_data.get("hint")
    elif interview_mode == "timer":
        pass
    else:  # diagnostic
        current_feedback["personas"] = feedback_data.get("personas", {
            "HR 면접관": { "score": score, "comment": "차분하게 조곤조곤 답변하셨습니다." },
            "기술 면접관": { "score": score, "comment": "기술적 핵심을 대략적으로 언급하셨습니다." },
            "CTO 면접관": { "score": score, "comment": "문제 해결 태도가 준수합니다." }
        })

    # ── 집단지성 학습: 답변 저장 + 최적 답변 합성 트리거 ──────────────
    q_key = make_question_key(session.job_title, current_q)

    # 타임아웃 플레이스홀더 답변은 학습 제외
    is_timeout = "(제한시간 내에 답변을 제출하지 못했습니다.)" in user_answer

    if not is_timeout and score >= 30:
        try:
            should_synthesize = save_community_answer(
                db           = db,
                question_key = q_key,
                question     = current_q,
                answer       = user_answer,
                score        = score,
                interview_mode = interview_mode,
            )

            if should_synthesize:
                # Flask app_context를 캡처하여 백그라운드 스레드로 합성 위임 (API 블로킹 대기 지연 방지)
                from flask import current_app
                import threading
                app = current_app._get_current_object()

                def run_async_synthesis(app_instance, q_key_val, current_q_val, job_title_val, model_answer_val):
                    with app_instance.app_context():
                        try:
                            get_or_update_optimal_answer(
                                db              = db,
                                question_key    = q_key_val,
                                question        = current_q_val,
                                job_title       = job_title_val,
                                ai_model_answer = model_answer_val,
                            )
                        except Exception as async_err:
                            print(f"[LearningEngine Async Error] {async_err}")

                t = threading.Thread(
                    target=run_async_synthesis,
                    args=(app, q_key, current_q, session.job_title, model_answer)
                )
                t.daemon = True
                t.start()

        except Exception as le:
            print(f"[LearningEngine] 저장 실패 (무시): {le}")

    # 이미 합성된 최적 답변이 있으면 피드백에 포함
    if "optimal_answer" not in current_feedback:
        existing_optimal = fetch_optimal_answer(q_key)
        if existing_optimal:
            current_feedback["optimal_answer"] = existing_optimal

    # 커뮤니티 통계 첨부 (프론트에서 "X명이 답변함" 표시용)
    current_feedback["community_stats"] = get_community_stats(q_key)
    # ────────────────────────────────────────────────────────────────────

    # 리스트 업데이트
    answers.append(user_answer)
    feedbacks.append(current_feedback)

    session.answers = json.dumps(answers)
    session.feedbacks = json.dumps(feedbacks)
    session.current_index += 1

    # 다음 질문 추출 및 완료 체크
    next_question = None
    
    # 🌶️ 압박 면접 모드: 꼬리 질문 동적 삽입 처리
    if interview_mode == "stress" and current_feedback.get("follow_up_question"):
        # 꼬리 질문 횟수 제한 (세션의 질문 개수가 5개 이내인 동안만 꼬리 질문 추가)
        if len(questions) < 5:
            # 다음 순서(현재 인덱스 + 1 위치)에 꼬리 질문을 동적으로 삽입!
            questions.insert(session.current_index + 1, current_feedback["follow_up_question"])
            session.questions = json.dumps(questions)
            print(f"[Stress Mode] Inserted follow-up question: {current_feedback['follow_up_question']}")

    # 질문 완료 상태 체크
    if session.current_index >= len(questions):
        session.is_completed = True
    else:
        next_question = questions[session.current_index]

    try:
        db.session.commit()
    except Exception as db_err:
        db.session.rollback()
        print(f"[Interview Commit Error] {db_err}")
        return jsonify({"error": "데이터 저장 중 DB 오류가 발생했습니다."}), 500

    return jsonify({
        "session_id": session.id,
        "feedback": current_feedback,
        "next_question": next_question,
        "is_completed": session.is_completed,
        "current_index": session.current_index,
        "interview_mode": interview_mode
    }), 200
