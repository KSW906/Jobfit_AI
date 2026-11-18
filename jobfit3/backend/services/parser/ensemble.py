"""
ensemble.py — AI 앙상블 분석 엔진
=====================================

프로젝트 내 머신러닝 로직이 집중된 핵심 파일입니다.

[ML 코드 위치 안내]
──────────────────────────────────────────────────────────────
  1. services/parser/rule_based.py
     → IT_SKILLS 딕셔너리 기반 키워드 매칭 (가장 단순한 ML 없는 버전)
     → extract_skills(): 정규식으로 스킬명 추출
     → make_feedback(): FEEDBACK_MAP 딕셔너리 룩업

  2. services/parser/multi_ai.py
     → extract_skills_claude/gemini/openai(): 각 AI API 호출
     → make_feedback(): AI가 생성하는 학습 피드백
     → compare_resumes(): 이력서 비교 분석 (Claude 우선, Gemini 폴백)

  3. routes/analyze.py
     → calculate_fit_score(): 현재 핵심 매칭 점수 계산
       - 가중치 기반 선형 결합: skills·title·category·salary·location
       - 수식: fit = Σ(score_i × weight_i) / Σ(weight_i)
     → get_feedback_with_cache(): CachedFeedback DB 레이어 + AI 폴백

  4. services/parser/ensemble.py  ← 지금 이 파일 (새로 추가)
     → EnsembleAnalyzer: Claude·Gemini·GPT-4o 동시 호출 후 결과 종합
     → ensemble_fit_score(): 3개 점수 가중 평균
     → ensemble_skill_gap(): 과반수 AI가 언급한 스킬만 고신뢰로 분류
     → detect_disagreement(): 점수 편차가 큰 항목 감지
──────────────────────────────────────────────────────────────
"""

import os
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

# 각 AI 모델별 신뢰도 가중치 (합이 반드시 1.0일 필요 없음 — 정규화함)
MODEL_WEIGHTS = {
    "claude":  1.0,
    "gemini":  0.85,
    "openai":  0.9,
}


# ─────────────────────────────────────────────
# 개별 AI 분석 함수
# ─────────────────────────────────────────────

def _analyze_claude(resume: str, job_desc: str, job_title: str) -> dict:
    """Claude Sonnet으로 이력서-공고 적합도 분석"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY 없음")

    prompt = _build_prompt(resume, job_desc, job_title)
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=35,
    )
    res.raise_for_status()
    raw = res.json()["content"][0]["text"].strip()
    return _parse_json_safe(raw, "claude")


def _analyze_gemini(resume: str, job_desc: str, job_title: str) -> dict:
    """Gemini 2.5 Flash로 이력서-공고 적합도 분석"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 없음")

    prompt = _build_prompt(resume, job_desc, job_title)
    res = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=20,
    )
    res.raise_for_status()
    raw = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return _parse_json_safe(raw, "gemini")


def _analyze_openai(resume: str, job_desc: str, job_title: str) -> dict:
    """GPT-4o-mini로 이력서-공고 적합도 분석"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 없음")

    prompt = _build_prompt(resume, job_desc, job_title)
    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        json={
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a career analysis assistant. Respond only in JSON."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=25,
    )
    res.raise_for_status()
    raw = res.json()["choices"][0]["message"]["content"].strip()
    return _parse_json_safe(raw, "openai")


# ─────────────────────────────────────────────
# 프롬프트 빌더
# ─────────────────────────────────────────────

def _build_prompt(resume: str, job_desc: str, job_title: str) -> str:
    return f"""당신은 IT 채용 분야 전문 커리어 분석가입니다.
아래 이력서와 채용 공고를 분석하여 반드시 JSON 형식으로만 응답해주세요. 마크다운 코드펜스(```) 없이 순수 JSON만 반환하세요.

=== 채용 공고 제목 ===
{job_title}

=== 채용 공고 내용 ===
{job_desc[:1500]}

=== 지원자 이력서 ===
{resume[:1500]}

분석 항목:
1. fit_score: 0~100 정수. 이력서가 이 공고에 얼마나 적합한지 종합 점수.
2. matched_skills: 공고 요구사항 중 이력서에서 확인된 스킬 목록 (최대 10개)
3. missing_skills: 공고 요구사항 중 이력서에 없는 핵심 스킬 목록 (최대 8개)
4. strengths: 이 지원자의 강점 2~3가지 (한 줄씩)
5. feedback: 부족한 부분 보완을 위한 구체적 조언 2~3가지 (한 줄씩)
6. confidence: 이 분석의 신뢰도 (0.0~1.0). 이력서/공고 정보가 충분하면 높게.

반환 형식 (이 JSON 구조만 반환):
{{
  "fit_score": 75,
  "matched_skills": ["Python", "Flask"],
  "missing_skills": ["Kubernetes", "Kafka"],
  "strengths": ["백엔드 API 개발 경험 풍부", "Python 숙련도 높음"],
  "feedback": ["Kubernetes 기초 학습 권장", "메시지 큐 경험 추가 필요"],
  "confidence": 0.85
}}"""


def _parse_json_safe(raw: str, model_name: str) -> dict:
    """JSON 파싱 + 펜스 제거 + 필드 검증"""
    text = raw
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{model_name} JSON 파싱 실패: {e}\n원문: {raw[:200]}")

    # 필수 필드 기본값 보정
    data.setdefault("fit_score", 0)
    data.setdefault("matched_skills", [])
    data.setdefault("missing_skills", [])
    data.setdefault("strengths", [])
    data.setdefault("feedback", [])
    data.setdefault("confidence", 0.7)

    # fit_score 범위 보정
    try:
        data["fit_score"] = max(0, min(100, int(data["fit_score"])))
    except (TypeError, ValueError):
        data["fit_score"] = 0

    data["_model"] = model_name
    return data


# ─────────────────────────────────────────────
# 앙상블 집계 (핵심 ML 로직)
# ─────────────────────────────────────────────

def ensemble_fit_score(results: dict) -> dict:
    """
    가중 평균으로 최종 점수 계산 (ML 핵심 집계)

    - 각 모델 신뢰도(confidence)와 사전 가중치(MODEL_WEIGHTS)를 곱해 최종 가중치 결정
    - 실패한 모델은 자동으로 제외되어 남은 모델로 재정규화
    """
    scores = {}
    weights = {}

    for model, data in results.items():
        if data.get("error"):
            continue
        raw_w = MODEL_WEIGHTS.get(model, 0.8)
        conf  = float(data.get("confidence", 0.7))
        w     = raw_w * conf
        scores[model]  = data["fit_score"]
        weights[model] = w

    if not scores:
        return {"ensemble_score": 0, "model_scores": {}, "weight_used": {}}

    total_w = sum(weights.values())
    ensemble = round(sum(scores[m] * weights[m] for m in scores) / total_w)

    # 모델 간 불일치 감지
    score_list = list(scores.values())
    variance   = max(score_list) - min(score_list)
    disagreement = variance >= 20  # 20점 이상 차이나면 불일치로 표시

    return {
        "ensemble_score":  ensemble,
        "model_scores":    scores,
        "weight_used":     {m: round(weights[m], 3) for m in weights},
        "disagreement":    disagreement,
        "score_variance":  variance,
    }


def ensemble_skill_gap(results: dict) -> dict:
    """
    과반수 동의 기반 스킬 분류 (신뢰도별 레이어링)

    - high_confidence: 모든 가용 AI가 동의한 스킬
    - medium_confidence: 과반수(>50%)가 언급한 스킬
    - low_confidence: 한 AI만 언급한 스킬 (참고용)
    """
    valid_results = {m: d for m, d in results.items() if not d.get("error")}
    n = len(valid_results)
    if n == 0:
        return {"high": [], "medium": [], "low": [], "matched": []}

    # 스킬별 언급 횟수 카운트
    missing_count  = {}
    matched_count  = {}

    for data in valid_results.values():
        for s in data.get("missing_skills", []):
            key = s.strip()
            missing_count[key] = missing_count.get(key, 0) + 1
        for s in data.get("matched_skills", []):
            key = s.strip()
            matched_count[key] = matched_count.get(key, 0) + 1

    high   = [s for s, c in missing_count.items() if c == n]
    medium = [s for s, c in missing_count.items() if 0 < c < n and c / n > 0.5]
    low    = [s for s, c in missing_count.items() if c / n <= 0.5]
    matched = [s for s, c in matched_count.items() if c / n >= 0.5]

    return {
        "high":    sorted(high),
        "medium":  sorted(medium),
        "low":     sorted(low),
        "matched": sorted(matched),
    }


def ensemble_strengths_feedback(results: dict) -> dict:
    """
    강점/피드백 텍스트 취합 — 모델별 원문 유지 + 공통 키워드 추출
    """
    valid = {m: d for m, d in results.items() if not d.get("error")}

    all_strengths = {}
    all_feedback  = {}

    for model, data in valid.items():
        all_strengths[model] = data.get("strengths", [])
        all_feedback[model]  = data.get("feedback", [])

    # 공통 키워드 기반 대표 문장 선정 (가장 많은 모델이 언급한 것 우선)
    def pick_representative(per_model: dict) -> list:
        from collections import Counter
        word_map = {}
        for model, sentences in per_model.items():
            for s in sentences:
                words = set(s.lower().split())
                for w in words:
                    if len(w) >= 3:
                        if w not in word_map:
                            word_map[w] = []
                        word_map[w].append(s)
        word_freq = Counter({w: len(sents) for w, sents in word_map.items()})
        seen, rep = set(), []
        for w, _ in word_freq.most_common(30):
            for s in word_map[w]:
                if s not in seen and len(rep) < 4:
                    seen.add(s)
                    rep.append(s)
        return rep

    return {
        "strengths_by_model": all_strengths,
        "feedback_by_model":  all_feedback,
        "representative_strengths": pick_representative(all_strengths),
        "representative_feedback":  pick_representative(all_feedback),
    }


# ─────────────────────────────────────────────
# 메인 앙상블 실행기
# ─────────────────────────────────────────────

class EnsembleAnalyzer:
    """
    Claude + Gemini + GPT-4o를 ThreadPoolExecutor로 병렬 호출하고
    앙상블 결과를 생성하는 클래스
    """

    def __init__(self, timeout: int = 40):
        self.timeout = timeout
        self._analyzers = {
            "claude": _analyze_claude,
            "gemini": _analyze_gemini,
            "openai": _analyze_openai,
        }

    def run(self, resume: str, job_desc: str, job_title: str = "") -> dict:
        """
        3개 AI 병렬 호출 → 앙상블 집계 → 종합 결과 반환

        Returns:
          {
            "ensemble_score":   int,          # 가중 평균 최종 점수
            "score_variance":   int,          # 모델 간 점수 편차
            "disagreement":     bool,         # True면 모델 간 의견 불일치
            "skill_gap": {
              "high":   list,   # 전체 동의 — 반드시 채워야 할 스킬
              "medium": list,   # 과반수 동의
              "low":    list,   # 참고용
              "matched": list,  # 보유 확인된 스킬
            },
            "representative_strengths": list, # 공통 강점
            "representative_feedback":  list, # 공통 개선 조언
            "model_results": {                # 모델별 원본 결과
              "claude": {...},
              "gemini": {...},
              "openai": {...},
            },
            "available_models": list,         # 성공한 모델 목록
            "failed_models":    list,         # 실패한 모델 목록
          }
        """
        raw_results = {}
        start = time.time()

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_model = {
                executor.submit(fn, resume, job_desc, job_title): model
                for model, fn in self._analyzers.items()
            }
            for future in as_completed(future_to_model, timeout=self.timeout):
                model = future_to_model[future]
                try:
                    raw_results[model] = future.result()
                except Exception as e:
                    print(f"[Ensemble] {model} 실패: {e}")
                    raw_results[model] = {"error": str(e), "_model": model}

        elapsed = round(time.time() - start, 2)

        available = [m for m, d in raw_results.items() if not d.get("error")]
        failed    = [m for m, d in raw_results.items() if d.get("error")]

        if not available:
            return {
                "error": "모든 AI 모델 호출이 실패했습니다.",
                "failed_models": failed,
                "elapsed_sec": elapsed,
            }

        # 집계
        score_info     = ensemble_fit_score(raw_results)
        skill_gap      = ensemble_skill_gap(raw_results)
        text_info      = ensemble_strengths_feedback(raw_results)

        return {
            "ensemble_score":            score_info["ensemble_score"],
            "model_scores":              score_info["model_scores"],
            "weight_used":               score_info["weight_used"],
            "disagreement":              score_info.get("disagreement", False),
            "score_variance":            score_info.get("score_variance", 0),
            "skill_gap":                 skill_gap,
            "representative_strengths":  text_info["representative_strengths"],
            "representative_feedback":   text_info["representative_feedback"],
            "strengths_by_model":        text_info["strengths_by_model"],
            "feedback_by_model":         text_info["feedback_by_model"],
            "model_results":             raw_results,
            "available_models":          available,
            "failed_models":             failed,
            "elapsed_sec":               elapsed,
        }
