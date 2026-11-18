import os
import json
import requests
from dotenv import load_dotenv
from services.parser.rule_based import (
    extract_skills as rule_based_extract,
    make_feedback as rule_based_feedback,
    get_all_skills
)

# .env 환경 변수 재로드
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def extract_skills_gemini(text: str) -> dict:
    """Gemini API를 사용하여 스킬 추출"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 없습니다.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    prompt = f"""
채용 공고 텍스트를 분석하여 다음을 JSON 형식으로 추출해주세요:
1. "skills": 채용 공고에 언급된 모든 기술 스택 및 프로그래밍 언어의 리스트 (예: Python, React, Git, AWS 등).
2. "required": 필수 요건(필수 조건)에 해당하는 기술 스택 리스트.
3. "preferred": 우대 사항(우대 조건)에 해당하는 기술 스택 리스트.
4. "certifications": 요구되거나 우대되는 자격증 리스트.

반드시 다른 설명 없이 아래 형식에 정확히 부합하는 JSON 객체 하나만 반환해주세요.
반환 형식:
{{
    "skills": ["Python", "AWS", "Git"],
    "required": ["Python"],
    "preferred": ["AWS"],
    "certifications": []
}}

채용공고 본문:
{text}
"""
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    return json.loads(text_content)


def extract_skills_openai(text: str, model: str = "gpt-4o-mini") -> dict:
    """OpenAI API를 사용하여 스킬 추출"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 없습니다.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    prompt = f"""
채용 공고 텍스트를 분석하여 다음을 JSON 형식으로 추출해주세요:
1. "skills": 채용 공고에 언급된 모든 기술 스택 및 프로그래밍 언어의 리스트 (예: Python, React, Git, AWS 등).
2. "required": 필수 요건(필수 조건)에 해당하는 기술 스택 리스트.
3. "preferred": 우대 사항(우대 조건)에 해당하는 기술 스택 리스트.
4. "certifications": 요구되거나 우대되는 자격증 리스트.

반드시 다른 설명 없이 아래 형식에 정확히 부합하는 JSON 객체 하나만 반환해주세요.
반환 형식:
{{
    "skills": ["Python", "AWS", "Git"],
    "required": ["Python"],
    "preferred": ["AWS"],
    "certifications": []
}}

채용공고 본문:
{text}
"""
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that extracts skills from job postings in JSON format."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=12)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["choices"][0]["message"]["content"].strip()
    return json.loads(text_content)


def extract_skills_claude(text: str, model: str = "claude-sonnet-4-6") -> dict:
    """Claude API를 사용하여 스킬 추출"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 없습니다.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = f"""
채용 공고 텍스트를 분석하여 스킬을 추출해주세요.
반드시 마크다운 펜스(```)나 설명 없이 유효한 JSON 형식으로만 답해주세요.

반환 형식:
{{
    "skills": ["전체 스킬 목록"],
    "required": ["필수 스킬 목록"],
    "preferred": ["우대 스킬 목록"],
    "certifications": ["자격증 목록"]
}}

채용공고 본문:
{text}
"""
    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    res_data = res.json()
    text_content = res_data["content"][0]["text"].strip()

    if "```json" in text_content:
        text_content = text_content.split("```json")[1].split("```")[0].strip()
    elif "```" in text_content:
        text_content = text_content.split("```")[1].split("```")[0].strip()

    return json.loads(text_content)


def extract_skills(text: str) -> dict:
    """
    다중 AI 협력 스킬 추출기
    - Gemini-2.5-Flash가 설정되어 있으면 기본으로 사용 (성능 우수 및 초고속)
    - 실패/미설정 시 OpenAI GPT-4o-Mini 사용
    - 실패/미설정 시 Claude-3.5-Haiku 사용
    - 모두 실패 시 규칙 기반(rule_based)으로 자동 폴백
    """
    if GEMINI_API_KEY:
        try:
            return extract_skills_gemini(text)
        except Exception as e:
            print(f"[Warning] Gemini 스킬 추출 실패, OpenAI 사용 시도: {e}")

    if OPENAI_API_KEY:
        try:
            return extract_skills_openai(text, model="gpt-4o-mini")
        except Exception as e:
            print(f"[Warning] OpenAI 스킬 추출 실패, Claude Haiku 사용 시도: {e}")

    if ANTHROPIC_API_KEY:
        try:
            return extract_skills_claude(text, model="claude-haiku-4-5-20251001")
        except Exception as e:
            print(f"[Warning] Claude Haiku 스킬 추출 실패, Claude Sonnet 시도: {e}")
            try:
                return extract_skills_claude(text, model="claude-sonnet-4-6")
            except Exception as se:
                raise RuntimeError(f"Claude API 스킬 추출 실패: {se}") from se

    # 모든 AI 호출 실패 시 기존 rule_based 사용
    return rule_based_extract(text)


def make_feedback_gemini(missing_skills: list, resume_text: str = "") -> list:
    """Gemini API를 사용하여 맞춤 피드백 작성"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 없습니다.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    if resume_text:
        prompt = f"""
IT 채용 커리어 코치로서, 다음의 각 부족 스킬에 대해 사용자의 이력서 내용을 바탕으로 1~2문장의 아주 구체적이고 개인화된 한국어 피드백 및 보완 가이드를 제시해주세요.
사용자의 이력서에 있는 기존 프로젝트 경험이나 역량을 어떻게 활용 혹은 발전시키면 해당 부족한 스킬을 효과적으로 보완할 수 있을지 맞춤 코칭을 제공해야 합니다.

사용자의 이력서:
{resume_text}

부족한 스킬 목록:
{json.dumps(missing_skills)}

반드시 다른 설명 없이 JSON 배열 구조로만 대답해주세요.
예시 형식:
[
  "Docker: 이력서의 'A 프로젝트'를 진행할 때 로컬 개발 환경 통일을 위해 Dockerfile을 작성하여 컨테이너화하고 배포까지 고도화해보는 실습을 권장합니다.",
  ...
]
"""
    else:
        prompt = f"""
IT 채용 커리어 코치로서, 다음의 각 부족 스킬에 대해 1~2문장의 아주 구체적이고 실질적인 한국어 학습 로드맵 및 피드백을 제시해주세요.
반드시 다른 설명 없이 JSON 배열 구조로만 대답해주세요.

부족한 스킬 목록:
{json.dumps(missing_skills)}

예시 형식:
[
  "Docker: 컨테이너 개념을 익힌 후, 본인의 웹 프로젝트를 Dockerfile로 빌드하여 로컬에서 구동해 보는 토이 프로젝트 실습을 권장합니다.",
  ...
]
"""
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    return json.loads(text_content)


def make_feedback_openai(missing_skills: list, model: str = "gpt-4o", resume_text: str = "") -> list:
    """OpenAI API를 사용하여 맞춤 피드백 작성"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 없습니다.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    if resume_text:
        prompt = f"""
IT 채용 커리어 코치로서, 다음의 각 부족 스킬에 대해 사용자의 이력서 내용을 바탕으로 1~2문장의 아주 구체적이고 개인화된 한국어 피드백 및 보완 가이드를 제시해주세요.
사용자의 이력서에 있는 기존 프로젝트 경험이나 역량을 어떻게 활용 혹은 발전시키면 해당 부족한 스킬을 효과적으로 보완할 수 있을지 맞춤 코칭을 제공해야 합니다.

사용자의 이력서:
{resume_text}

부족한 스킬 목록:
{json.dumps(missing_skills)}

반드시 다른 설명 없이 JSON 배열 구조로만 대답해주세요.
예시 형식:
[
  "Docker: 이력서의 'A 프로젝트'를 진행할 때 로컬 개발 환경 통일을 위해 Dockerfile을 작성하여 컨테이너화하고 배포까지 고도화해보는 실습을 권장합니다.",
  ...
]
"""
    else:
        prompt = f"""
IT 채용 커리어 코치로서, 다음의 각 부족 스킬에 대해 1~2문장의 아주 구체적이고 실질적인 한국어 학습 로드맵 및 피드백을 제시해주세요.
반드시 다른 설명 없이 JSON 배열 구조로만 대답해주세요.

부족한 스킬 목록:
{json.dumps(missing_skills)}

예시 형식:
[
  "Docker: 컨테이너 개념을 익힌 후, 본인의 웹 프로젝트를 Dockerfile로 빌드하여 로컬에서 구동해 보는 토이 프로젝트 실습을 권장합니다.",
  ...
]
"""
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a career coach giving short, actionable advice on learning missing skills in JSON array format."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["choices"][0]["message"]["content"].strip()
    
    # Extract JSON if returned as a JSON object containing the array under a key, or clean string representation
    parsed_json = json.loads(text_content)
    if isinstance(parsed_json, dict):
        # Some JSON mode calls wrap it in a dict, let's find the array inside it
        for val in parsed_json.values():
            if isinstance(val, list):
                return val
    return parsed_json


def make_feedback_claude(missing_skills: list, model: str = "claude-sonnet-4-6", resume_text: str = "") -> list:
    """Claude API를 사용하여 맞춤 피드백 작성"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 없습니다.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    if resume_text:
        prompt = f"""
IT 채용 커리어 코치로서, 다음의 각 부족 스킬에 대해 사용자의 이력서 내용을 바탕으로 1~2문장의 아주 구체적이고 개인화된 한국어 피드백 및 보완 가이드를 제시해주세요.
사용자의 이력서에 있는 기존 프로젝트 경험이나 역량을 어떻게 활용 혹은 발전시키면 해당 부족한 스킬을 효과적으로 보완할 수 있을지 맞춤 코칭을 제공해야 합니다.

사용자의 이력서:
{resume_text}

부족한 스킬 목록:
{json.dumps(missing_skills)}

반드시 마크다운 펜스 없이 JSON 배열 구조로만 대답해주세요.
예시 형식:
[
  "Docker: 이력서의 'A 프로젝트'를 진행할 때 로컬 개발 환경 통일을 위해 Dockerfile을 작성하여 컨테이너화하고 배포까지 고도화해보는 실습을 권장합니다.",
  ...
]
"""
    else:
        prompt = f"""
IT 채용 커리어 코치로서, 다음의 각 부족 스킬에 대해 1~2문장의 아주 구체적이고 실질적인 한국어 학습 로드맵 및 피드백을 제시해주세요.
반드시 마크다운 펜스 없이 JSON 배열 구조로만 대답해주세요.

부족한 스킬 목록:
{json.dumps(missing_skills)}

예시 형식:
[
  "Docker: 컨테이너 개념을 익힌 후, 본인의 웹 프로젝트를 Dockerfile로 빌드하여 로컬에서 구동해 보는 토이 프로젝트 실습을 권장합니다.",
  ...
]
"""
    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    res.raise_for_status()
    res_data = res.json()
    text_content = res_data["content"][0]["text"].strip()

    if "```json" in text_content:
        text_content = text_content.split("```json")[1].split("```")[0].strip()
    elif "```" in text_content:
        text_content = text_content.split("```")[1].split("```")[0].strip()

    return json.loads(text_content)


def compare_resumes_claude(user_resume: str, comp_resume: str, comp_label: str, model: str = "claude-sonnet-4-6") -> dict:
    """Claude API로 사용자 이력서와 비교 이력서를 심층 비교 분석"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 없습니다.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = f"""당신은 IT 채용 전문 커리어 코치입니다.
아래 두 이력서를 꼼꼼히 비교 분석하고, 반드시 마크다운 펜스 없이 아래 JSON 형식으로만 응답해주세요.

=== 사용자 이력서 ===
{user_resume}

=== 비교 대상 이력서 (레이블: {comp_label}) ===
{comp_resume}

분석 기준:
1. strengths: 사용자 이력서가 비교 대상보다 뛰어난 점 (구체적으로 3가지)
2. weaknesses: 사용자 이력서가 비교 대상보다 부족한 점 (구체적으로 3가지)
3. skill_gap: 비교 대상에는 있지만 사용자에게 없는 핵심 기술/역량 목록
4. advice: 사용자가 비교 대상 수준으로 발전하기 위한 실질적인 조언 (3가지)
5. overall_assessment: 전반적인 비교 평가 한 문장 요약

반환 형식 (JSON):
{{
  "strengths": ["강점1", "강점2", "강점3"],
  "weaknesses": ["약점1", "약점2", "약점3"],
  "skill_gap": ["기술1", "기술2", "기술3"],
  "advice": ["조언1", "조언2", "조언3"],
  "overall_assessment": "전반적인 평가 한 문장"
}}"""

    payload = {
        "model": model,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=40)
    res.raise_for_status()
    text_content = res.json()["content"][0]["text"].strip()

    if "```json" in text_content:
        text_content = text_content.split("```json")[1].split("```")[0].strip()
    elif "```" in text_content:
        text_content = text_content.split("```")[1].split("```")[0].strip()

    return json.loads(text_content)


def compare_resumes_gemini(user_resume: str, comp_resume: str, comp_label: str) -> dict:
    """Gemini API로 이력서 비교 분석"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 없습니다.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""당신은 IT 채용 전문 커리어 코치입니다.
아래 두 이력서를 꼼꼼히 비교 분석하고 JSON 형식으로만 응답해주세요.

=== 사용자 이력서 ===
{user_resume}

=== 비교 대상 이력서 (레이블: {comp_label}) ===
{comp_resume}

반환 형식:
{{
  "strengths": ["사용자의 강점1", "강점2", "강점3"],
  "weaknesses": ["사용자의 약점1", "약점2", "약점3"],
  "skill_gap": ["부족한 기술1", "기술2", "기술3"],
  "advice": ["개선 조언1", "조언2", "조언3"],
  "overall_assessment": "전반적인 평가 한 문장"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=15)
    res.raise_for_status()
    text_content = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return json.loads(text_content)


def compare_resumes(user_resume: str, comp_resume: str, comp_label: str) -> dict:
    """
    다중 AI 이력서 비교 분석
    - Claude Sonnet 우선 → Gemini 폴백
    """
    if not user_resume or not comp_resume:
        raise ValueError("비교할 이력서 내용이 없습니다.")

    if ANTHROPIC_API_KEY:
        try:
            return compare_resumes_claude(user_resume, comp_resume, comp_label, model="claude-sonnet-4-6")
        except Exception as e:
            print(f"[Warning] Claude 이력서 비교 실패: {e}")

    if GEMINI_API_KEY:
        try:
            return compare_resumes_gemini(user_resume, comp_resume, comp_label)
        except Exception as e:
            print(f"[Warning] Gemini 이력서 비교 실패: {e}")

    raise RuntimeError("이력서 비교 분석에 사용할 수 있는 AI API가 없습니다.")


def make_feedback(missing_skills: list, resume_text: str = "") -> list:
    """
    다중 AI 협력 피드백 생성
    - Claude-3.5-Sonnet이 설정되어 있으면 최우선 사용
    - 실패/미설정 시 OpenAI GPT-4o 사용
    - 실패/미설정 시 Gemini-2.5-Flash 사용
    - 모두 실패 시 규칙 기반 피드백으로 폴백
    """
    if not missing_skills:
        return []

    # 1. Claude-sonnet 우선 적용 (실패 시 Claude-haiku 시도)
    if ANTHROPIC_API_KEY:
        try:
            return make_feedback_claude(missing_skills, model="claude-sonnet-4-6", resume_text=resume_text)
        except Exception as e:
            print(f"[Warning] Claude Sonnet 피드백 생성 실패, Claude Haiku 시도: {e}")
            try:
                return make_feedback_claude(missing_skills, model="claude-haiku-4-5-20251001", resume_text=resume_text)
            except Exception as he:
                print(f"[Warning] Claude API 피드백 생성 전체 실패: {he}")

    # 2. OpenAI GPT-4o 적용
    if OPENAI_API_KEY:
        try:
            return make_feedback_openai(missing_skills, model="gpt-4o", resume_text=resume_text)
        except Exception as e:
            print(f"[Warning] OpenAI 피드백 생성 실패, Gemini 시도: {e}")

    # 3. Gemini 적용
    if GEMINI_API_KEY:
        try:
            return make_feedback_gemini(missing_skills, resume_text=resume_text)
        except Exception as e:
            print(f"[Warning] Gemini 피드백 생성 실패, 규칙 기반 폴백: {e}")

    # 4. 폴백
    return rule_based_feedback(missing_skills)


def extract_skills_from_resume_gemini(text: str) -> list:
    """Gemini API를 사용하여 이력서에서 기술 스택 추출"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 없습니다.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    prompt = f"""
    이력서 텍스트를 분석하여 구직자가 보유하고 있거나 경험한 프로그래밍 언어, 프레임워크, 라이브러리, 데이터베이스, 클라우드 등의 기술 스택 목록을 추출해주세요.
    반드시 다른 설명 없이 아래 형식에 정확히 부합하는 JSON 객체 하나만 반환해주세요. 키 이름은 반드시 "skills"여야 합니다.
    반환 형식:
    {{
        "skills": ["Java", "Spring Boot", "React", "MySQL"]
    }}

    이력서 본문:
    {text}
    """
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    return json.loads(text_content).get("skills", [])


def extract_skills_from_resume_openai(text: str) -> list:
    """OpenAI API를 사용하여 이력서에서 기술 스택 추출"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 없습니다.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    prompt = f"""
    이력서 텍스트를 분석하여 구직자가 보유하고 있거나 경험한 프로그래밍 언어, 프레임워크, 라이브러리, 데이터베이스, 클라우드 등의 기술 스택 목록을 추출해주세요.
    반드시 다른 설명 없이 아래 형식에 정확히 부합하는 JSON 객체 하나만 반환해주세요. 키 이름은 반드시 "skills"여야 합니다.
    반환 형식:
    {{
        "skills": ["Java", "Spring Boot", "React", "MySQL"]
    }}

    이력서 본문:
    {text}
    """
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a professional recruiter who extracts technical skills from resumes in JSON format."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["choices"][0]["message"]["content"].strip()
    return json.loads(text_content).get("skills", [])


def extract_skills_from_resume_claude(text: str) -> list:
    """Claude API를 사용하여 이력서에서 기술 스택 추출"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 없습니다.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = f"""
    이력서 텍스트를 분석하여 구직자가 보유하고 있거나 경험한 기술 스택 목록을 추출해주세요.
    반드시 마크다운 펜스(```)나 설명 없이 유효한 JSON 형식으로만 답해주세요. 키 이름은 반드시 "skills"여야 합니다.
    반환 형식:
    {{
        "skills": ["Java", "Spring Boot", "React", "MySQL"]
    }}

    이력서 본문:
    {text}
    """
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    res_data = res.json()
    text_content = res_data["content"][0]["text"].strip()

    if "```json" in text_content:
        text_content = text_content.split("```json")[1].split("```")[0].strip()
    elif "```" in text_content:
        text_content = text_content.split("```")[1].split("```")[0].strip()

    return json.loads(text_content).get("skills", [])


def extract_skills_from_resume(text: str) -> list:
    """
    다중 AI 협력 이력서 기술 스택 추출기
    - Gemini -> OpenAI -> Claude 순서로 실행
    """
    if not text:
        return []

    if GEMINI_API_KEY:
        try:
            return extract_skills_from_resume_gemini(text)
        except Exception as e:
            print(f"[Warning] Gemini 이력서 스킬 추출 실패: {e}")

    if OPENAI_API_KEY:
        try:
            return extract_skills_from_resume_openai(text)
        except Exception as e:
            print(f"[Warning] OpenAI 이력서 스킬 추출 실패: {e}")

    if ANTHROPIC_API_KEY:
        try:
            return extract_skills_from_resume_claude(text)
        except Exception as e:
            print(f"[Warning] Claude 이력서 스킬 추출 실패: {e}")

    return []


def normalize_skills_gemini(skills_list: list) -> list:
    """Gemini API를 사용하여 스킬 표준 명칭 정형화"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 없습니다.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    prompt = f"""
    주어진 기술 스택 목록을 IT 업계 표준 명칭으로 정형화(Normalize)해주세요.
    글자가 완전히 동일하지 않더라도, 동의어나 줄임말, 버전 표시가 포함된 명칭인 경우 업계에서 널리 쓰이는 표준 형태로 일대일 매핑해 치환해야 합니다.

    치환 예시:
    - JS, Javascript, js -> JavaScript
    - React.js, reactjs, ReactJS -> React
    - Python3, python -> Python
    - AWS EC2, S3, ec2, aws-s3 -> AWS
    - SQL -> MySQL (RDB 맥락)
    - VueJS, Vue.js, vue -> Vue
    - SpringBoot -> Spring

    반드시 다른 부가적인 설명 없이 결과에 해당하는 JSON 배열 하나만 반환해주세요. 키 이름은 없으며, 순수한 문자열의 JSON 배열 형태여야 합니다.
    반환 예시:
    ["JavaScript", "React", "Python", "AWS"]

    변환할 기술 목록:
    {json.dumps(skills_list)}
    """
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    res = requests.post(url, headers=headers, json=payload, timeout=8)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    return json.loads(text_content)


def normalize_skills_openai(skills_list: list) -> list:
    """OpenAI API를 사용하여 스킬 표준 명칭 정형화"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 없습니다.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    prompt = f"""
    주어진 기술 스택 목록을 IT 업계 표준 명칭으로 정형화(Normalize)해주세요.
    글자가 완전히 동일하지 않더라도, 동의어나 줄임말, 버전 표시가 포함된 명칭인 경우 업계에서 널리 쓰이는 표준 형태로 일대일 매핑해 치환해야 합니다.

    치환 예시:
    - JS, Javascript, js -> JavaScript
    - React.js, reactjs, ReactJS -> React
    - Python3, python -> Python
    - AWS EC2, S3, ec2, aws-s3 -> AWS
    - SQL -> MySQL
    - VueJS, Vue.js, vue -> Vue
    - SpringBoot -> Spring

    반드시 다른 부가적인 설명 없이 결과에 해당하는 JSON 배열 하나만 반환해주세요. 키 이름은 없으며, 순수한 문자열의 JSON 배열 형태여야 합니다.
    반환 예시:
    ["JavaScript", "React", "Python", "AWS"]

    변환할 기술 목록:
    {json.dumps(skills_list)}
    """
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a developer tool that normalizes developer skill names into standard industry names as a JSON array."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=8)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["choices"][0]["message"]["content"].strip()
    parsed = json.loads(text_content)
    if isinstance(parsed, dict):
        for val in parsed.values():
            if isinstance(val, list):
                return val
    return parsed


def normalize_skills_claude(skills_list: list, model: str = "claude-haiku-4-5-20251001") -> list:
    """Claude API를 사용하여 스킬 표준 명칭 정형화"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 없습니다.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    prompt = f"""
    주어진 기술 스택 목록을 IT 업계 표준 명칭으로 정형화(Normalize)해주세요.
    글자가 완전히 동일하지 않더라도, 동의어나 줄임말, 버전 표시가 포함된 명칭인 경우 업계에서 널리 쓰이는 표준 형태로 일대일 매핑해 치환해야 합니다.

    치환 예시:
    - JS, Javascript, js -> JavaScript
    - React.js, reactjs, ReactJS -> React
    - Python3, python -> Python
    - AWS EC2, S3, ec2, aws-s3 -> AWS
    - SQL -> MySQL
    - VueJS, Vue.js, vue -> Vue
    - SpringBoot -> Spring

    반드시 다른 부가적인 설명이나 마크다운 코드 블록 없이 결과에 해당하는 JSON 배열 하나만 반환해주세요. 키 이름은 없으며, 순수한 문자열의 JSON 배열 형태여야 합니다.
    반환 예시:
    ["JavaScript", "React", "Python", "AWS"]

    변환할 기술 목록:
    {json.dumps(skills_list)}
    """
    payload = {
        "model": model,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    res_data = res.json()
    text_content = res_data["content"][0]["text"].strip()

    if "```json" in text_content:
        text_content = text_content.split("```json")[1].split("```")[0].strip()
    elif "```" in text_content:
        text_content = text_content.split("```")[1].split("```")[0].strip()

    return json.loads(text_content)


def normalize_skills(skills_list: list) -> list:
    """
    다중 AI 협력 스킬 명칭 정형화
    - 입력된 스킬셋을 표준 스택 명칭으로 자동 변환해 시맨틱 매칭 성공률을 높임
    """
    if not skills_list:
        return []

    if GEMINI_API_KEY:
        try:
            return normalize_skills_gemini(skills_list)
        except Exception as e:
            print(f"[Warning] Gemini 스킬 정형화 실패: {e}")

    if OPENAI_API_KEY:
        try:
            return normalize_skills_openai(skills_list)
        except Exception as e:
            print(f"[Warning] OpenAI 스킬 정형화 실패: {e}")

    if ANTHROPIC_API_KEY:
        try:
            return normalize_skills_claude(skills_list, model="claude-haiku-4-5-20251001")
        except Exception as e:
            print(f"[Warning] Claude Haiku 스킬 정형화 실패, Claude Sonnet 시도: {e}")
            try:
                return normalize_skills_claude(skills_list, model="claude-sonnet-4-6")
            except Exception as se:
                print(f"[Warning] Claude API 스킬 정형화 전체 실패: {se}")

    return skills_list
