"""
answer_learner.py — 집단지성 기반 최적 면접 답변 합성 엔진
=============================================================

흐름:
  1. 사용자가 답변 제출 → CommunityAnswer DB에 저장
  2. 해당 질문의 답변이 MIN_ANSWERS 이상 쌓이면 합성 트리거
  3. AI 모범답안(call_llm) + 누적 사용자 답변 풀을 동시에 분석
  4. 두 결과를 비교해 서로의 장점만 뽑아낸 OptimalAnswer 생성/갱신
  5. 이후 같은 질문에 답변 제출 시 OptimalAnswer를 피드백에 함께 반환
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

# 합성 트리거 기준 — 이 수 이상의 답변이 쌓이면 OptimalAnswer 갱신
MIN_ANSWERS_FOR_SYNTHESIS = 3
# 합성에 사용할 최대 답변 수 (너무 많으면 토큰 초과)
MAX_ANSWERS_FOR_SYNTHESIS = 15
# 점수 하한선 — 너무 낮은 답변은 합성에서 제외
MIN_SCORE_THRESHOLD = 30


def make_question_key(job_title: str, question: str) -> str:
    """질문 고유 키 생성 — 공고 직무명 + 질문 앞 80자"""
    return f"{job_title.strip()[:80]}||{question.strip()[:200]}"


def _call_ai(prompt: str, json_mode: bool = False) -> str:
    """Claude → GPT-4o → Gemini 순 폴백"""
    def try_claude():
        if not ANTHROPIC_API_KEY:
            raise ValueError("no key")
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-3-5-sonnet-20241022", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
            timeout=35,
        )
        res.raise_for_status()
        text = res.json()["content"][0]["text"].strip()
        if json_mode:
            for fence in ["```json", "```"]:
                if fence in text:
                    text = text.split(fence)[1].split("```")[0].strip()
                    break
        return text

    def try_openai():
        if not OPENAI_API_KEY:
            raise ValueError("no key")
        payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=25,
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()

    def try_gemini():
        if not GEMINI_API_KEY:
            raise ValueError("no key")
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload, timeout=20,
        )
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    for fn in [try_claude, try_openai, try_gemini]:
        try:
            return fn()
        except Exception as e:
            print(f"[answer_learner] AI 호출 실패: {e}")

    raise RuntimeError("모든 AI 호출 실패")


# ─────────────────────────────────────────────
# 핵심 합성 함수
# ─────────────────────────────────────────────

def synthesize_optimal_answer(
    question: str,
    job_title: str,
    community_answers: list[dict],  # [{"answer": str, "score": int}, ...]
    ai_model_answer: str,
) -> dict:
    """
    AI 모범답안 + 커뮤니티 답변 풀을 비교 분석해 최적 답변 합성

    Returns:
      {
        "ai_model_answer":        str,
        "community_synthesized":  str,   # 사용자 풀에서 뽑아낸 공통 강점 합성
        "optimal_answer":         str,   # 최종 최적 답변
        "analysis":               str,   # 비교 분석 설명
        "strengths_from_community": str,
        "weaknesses_from_ai":     str,
        "sample_count":           int,
        "avg_score":              float,
      }
    """
    # 점수 순 정렬 후 상위 MAX개 선택
    filtered = sorted(
        [a for a in community_answers if a.get("score", 0) >= MIN_SCORE_THRESHOLD],
        key=lambda x: x["score"],
        reverse=True,
    )[:MAX_ANSWERS_FOR_SYNTHESIS]

    if not filtered:
        return None

    avg_score = round(sum(a["score"] for a in filtered) / len(filtered), 1)

    # 커뮤니티 답변 텍스트 구성
    community_text = ""
    for i, a in enumerate(filtered, 1):
        community_text += f"\n[답변 {i}] (점수: {a['score']}점)\n{a['answer']}\n"

    # ── Step 1: 커뮤니티 답변에서 공통 강점 합성 ──
    community_synth_prompt = f"""당신은 면접 코칭 전문가입니다.
아래는 '{job_title}' 직무 면접에서 실제 구직자들이 제출한 답변 {len(filtered)}개입니다.
이 답변들을 분석해서 공통적으로 잘된 점, 자주 나오는 핵심 키워드, 효과적인 표현 방식을 종합해
하나의 "커뮤니티 합성 답변"을 작성해주세요.

[면접 질문]
{question}

[실제 구직자 답변 풀]
{community_text}

[출력 지침]
- 특정 답변을 그대로 복사하지 말고, 공통된 강점을 녹여낸 새 문장으로 작성
- 3~5문장 분량의 자연스러운 한국어 답변
- 구체적 수치나 경험이 포함된 표현 우선 채택
- 다른 설명 없이 답변 본문만 반환"""

    try:
        community_synthesized = _call_ai(community_synth_prompt)
    except Exception as e:
        print(f"[answer_learner] 커뮤니티 합성 실패: {e}")
        community_synthesized = filtered[0]["answer"]  # 최고점 답변으로 폴백

    # ── Step 2: AI 모범답안 vs 커뮤니티 합성 비교 → 최적 답변 도출 ──
    final_synthesis_prompt = f"""당신은 면접 답변 최적화 전문 AI입니다.
아래 두 가지 답변을 꼼꼼히 비교 분석하고, 각각의 장점만을 조합해 더 완성도 높은 최종 최적 답변을 도출해주세요.

[면접 질문]
{question}
(직무: {job_title})

[답변 A — AI 모범답안]
{ai_model_answer}

[답변 B — 실제 구직자 풀 합성 답변]
{community_synthesized}

[비교 분석 및 최적 답변 도출 지침]
- AI 모범답안의 강점: 구조적 완성도, 기술적 정확성
- 커뮤니티 합성 답변의 강점: 실제 경험 기반 생동감, 현실적 표현
- 두 답변에서 오류나 부족한 점이 있다면 과감하게 제거
- 최종 답변은 4~6문장의 완성도 높은 한국어

반드시 아래 JSON 형식으로만 반환 (마크다운 펜스 없이):
{{
  "optimal_answer": "최종 최적 답변 본문",
  "analysis": "두 답변 비교 분석 요약 (2~3문장)",
  "strengths_from_community": "커뮤니티 답변에서 채택한 강점",
  "weaknesses_from_ai": "AI 모범답안 대비 커뮤니티 답변의 보완점"
}}"""

    try:
        raw = _call_ai(final_synthesis_prompt, json_mode=True)
        result = json.loads(raw)
    except Exception as e:
        print(f"[answer_learner] 최적답변 합성 실패: {e}")
        result = {
            "optimal_answer": community_synthesized,
            "analysis": "커뮤니티 답변 풀 기반으로 합성되었습니다.",
            "strengths_from_community": "",
            "weaknesses_from_ai": "",
        }

    result["ai_model_answer"]       = ai_model_answer
    result["community_synthesized"] = community_synthesized
    result["sample_count"]          = len(filtered)
    result["avg_score"]             = avg_score

    return result


# ─────────────────────────────────────────────
# DB 저장/조회 헬퍼 (chatbot.py에서 임포트해서 사용)
# ─────────────────────────────────────────────

def save_community_answer(db, question_key: str, question: str,
                          answer: str, score: int, interview_mode: str):
    """사용자 답변을 CommunityAnswer에 저장하고, 합성 조건 충족 시 True 반환"""
    from models import CommunityAnswer
    entry = CommunityAnswer(
        question_key   = question_key,
        question       = question,
        answer         = answer,
        score          = score,
        interview_mode = interview_mode,
    )
    db.session.add(entry)
    db.session.commit()

    # 합성 트리거 조건 체크
    count = CommunityAnswer.query.filter_by(question_key=question_key).count()
    return count >= MIN_ANSWERS_FOR_SYNTHESIS


def get_or_update_optimal_answer(db, question_key: str, question: str,
                                  job_title: str, ai_model_answer: str) -> dict | None:
    """
    OptimalAnswer 조회 or 생성/갱신.
    MIN_ANSWERS 미만이면 None 반환.
    """
    from models import CommunityAnswer, OptimalAnswer

    answers = (
        CommunityAnswer.query
        .filter_by(question_key=question_key)
        .order_by(CommunityAnswer.score.desc())
        .limit(MAX_ANSWERS_FOR_SYNTHESIS)
        .all()
    )
    if len(answers) < MIN_ANSWERS_FOR_SYNTHESIS:
        return None

    community_list = [{"answer": a.answer, "score": a.score} for a in answers]

    # 합성 실행
    synth = synthesize_optimal_answer(
        question          = question,
        job_title         = job_title,
        community_answers = community_list,
        ai_model_answer   = ai_model_answer,
    )
    if not synth:
        return None

    # DB upsert
    existing = OptimalAnswer.query.filter_by(question_key=question_key).first()
    if existing:
        existing.ai_model_answer         = synth["ai_model_answer"]
        existing.community_synthesized   = synth["community_synthesized"]
        existing.optimal_answer          = synth["optimal_answer"]
        existing.analysis                = synth.get("analysis", "")
        existing.strengths_from_community = synth.get("strengths_from_community", "")
        existing.weaknesses_from_ai      = synth.get("weaknesses_from_ai", "")
        existing.sample_count            = synth["sample_count"]
        existing.avg_score               = synth["avg_score"]
    else:
        existing = OptimalAnswer(
            question_key             = question_key,
            question                 = question,
            ai_model_answer          = synth["ai_model_answer"],
            community_synthesized    = synth["community_synthesized"],
            optimal_answer           = synth["optimal_answer"],
            analysis                 = synth.get("analysis", ""),
            strengths_from_community = synth.get("strengths_from_community", ""),
            weaknesses_from_ai       = synth.get("weaknesses_from_ai", ""),
            sample_count             = synth["sample_count"],
            avg_score                = synth["avg_score"],
        )
        db.session.add(existing)

    db.session.commit()
    return existing.to_dict()


def fetch_optimal_answer(question_key: str) -> dict | None:
    """기존 OptimalAnswer 단순 조회 (합성 없이)"""
    from models import OptimalAnswer
    row = OptimalAnswer.query.filter_by(question_key=question_key).first()
    return row.to_dict() if row else None


def get_community_stats(question_key: str) -> dict:
    """해당 질문의 커뮤니티 답변 통계 반환"""
    from models import CommunityAnswer
    answers = CommunityAnswer.query.filter_by(question_key=question_key).all()
    if not answers:
        return {"count": 0, "avg_score": 0, "needed": MIN_ANSWERS_FOR_SYNTHESIS}
    avg = round(sum(a.score for a in answers) / len(answers), 1)
    return {
        "count":    len(answers),
        "avg_score": avg,
        "needed":   max(0, MIN_ANSWERS_FOR_SYNTHESIS - len(answers)),
        "ready":    len(answers) >= MIN_ANSWERS_FOR_SYNTHESIS,
    }
