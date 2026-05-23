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
