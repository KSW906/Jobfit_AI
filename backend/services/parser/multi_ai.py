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


def extract_skills_claude(text: str, model: str = "claude-3-5-sonnet-20241022") -> dict:
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
            return extract_skills_claude(text, model="claude-3-5-haiku-20241022")
        except Exception as e:
            print(f"[Warning] Claude Haiku 스킬 추출 실패, Claude Sonnet 시도: {e}")
            try:
                return extract_skills_claude(text, model="claude-3-5-sonnet-20241022")
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


def make_feedback_claude(missing_skills: list, model: str = "claude-3-5-sonnet-20241022", resume_text: str = "") -> list:
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
            {"role": "system", "content": "You are a helpful assistant that extracts skills from resumes in JSON format."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=12)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["choices"][0]["message"]["content"].strip()
    return json.loads(text_content).get("skills", [])


def extract_skills_from_resume_claude(text: str, model: str = "claude-3-5-haiku-20241022") -> list:
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
    이력서 텍스트를 분석하여 구직자가 보유하고 있거나 경험한 프로그래밍 언어, 프레임워크, 라이브러리, 데이터베이스, 클라우드 등의 기술 스택 목록을 추출해주세요.
    반드시 마크다운 펜스(```)나 설명 없이 아래 형식에 정확히 부합하는 JSON 객체 하나만 반환해주세요. 키 이름은 반드시 "skills"여야 합니다.
    반환 형식:
    {{
        "skills": ["Java", "Spring Boot", "React", "MySQL"]
    }}

    이력서 본문:
    {text}
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

    return json.loads(text_content).get("skills", [])


def extract_skills_from_resume(text: str) -> list:
    """
    다중 AI 협력 이력서 기술 스택 추출
    - Gemini -> OpenAI -> Claude 순서로 시도
    """
    if not text:
        return []

    if GEMINI_API_KEY:
        try:
            return extract_skills_from_resume_gemini(text)
        except Exception as e:
            print(f"[Warning] Gemini 이력서 기술 스택 추출 실패: {e}")

    if OPENAI_API_KEY:
        try:
            return extract_skills_from_resume_openai(text)
        except Exception as e:
            print(f"[Warning] OpenAI 이력서 기술 스택 추출 실패: {e}")

    if ANTHROPIC_API_KEY:
        try:
            return extract_skills_from_resume_claude(text)
        except Exception as e:
            print(f"[Warning] Claude 이력서 기술 스택 추출 실패: {e}")

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
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
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

    반드시 다른 부가적인 설명이나 마크다운 코드 블록 없이 결과에 해당하는 JSON 배열 하나만 반환해주세요. 키 이름은 없으며, 순수한 문자열의 JSON 배열 형태여야 합니다.
    반환 예시:
    ["JavaScript", "React", "Python", "AWS"]

    변환할 기술 목록:
    {json.dumps(skills_list)}
    """
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that normalizes IT skills into a JSON array."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    res_json = res.json()
    text_content = res_json["choices"][0]["message"]["content"].strip()
    parsed = json.loads(text_content)
    if isinstance(parsed, dict):
        for val in parsed.values():
            if isinstance(val, list):
                return val
    return parsed


def normalize_skills_claude(skills_list: list, model: str = "claude-3-5-haiku-20241022") -> list:
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
            return normalize_skills_claude(skills_list)
        except Exception as e:
            print(f"[Warning] Claude 스킬 정형화 실패: {e}")

    return skills_list


def synthesize_feedback(missing_skills: list, drafts: list, resume_text: str = "") -> list:
    """
    여러 LLM의 초안 피드백을 취합하여 일관되고 정제된 최종 피드백 리스트 생성
    """
    if not drafts:
        return rule_based_feedback(missing_skills)

    if len(drafts) == 1:
        return drafts[0][1]

    prompt = f"""
    당신은 IT 전문 커리어 코치입니다.
    사용자의 부족한 기술 스택 목록에 대하여 여러 AI 모델들이 작성한 초안 피드백들을 입력받아, 중복되거나 어색한 표현을 정제하고, 가장 구체적이고 유용한 학습 가이드 및 보완 팁을 담은 최종 한국어 피드백 리스트를 합성해주세요.
    각 피드백 항목은 1~2문장으로 아주 구체적이고 실질적인 조언이어야 하며, 사용자 이력서 내용이 존재할 경우 이력서의 프로젝트 경험 등을 언급하며 개인화된 가이드를 제공해야 합니다.
    
    부족한 기술 스택 목록:
    {json.dumps(missing_skills)}
    
    사용자 이력서:
    {resume_text}
    
    AI 모델별 초안 목록:
    """
    for model_name, draft in drafts:
        prompt += f"\n[{model_name} 초안]\n{json.dumps(draft, ensure_ascii=False)}\n"
        
    prompt += f"""
    반드시 부족한 기술 스택 목록({json.dumps(missing_skills)})과 1:1 매핑되는 JSON 배열 구조 하나만 다른 텍스트 없이 반환해주세요. 각 원소의 순서는 부족한 기술 스택 목록의 순서와 정확히 일치해야 합니다.
    
    반환 예시 형식:
    [
      "Docker: 이력서의 'A 프로젝트'를 진행할 때 로컬 개발 환경 통일을 위해 Dockerfile을 작성하여 컨테이너화하고 배포까지 고도화해보는 실습을 권장합니다.",
      "TypeScript: React 프로젝트 개발 경험이 있으시니, 기존 컴포넌트들을 TypeScript로 리팩토링하며 정적 타입 시스템을 점진적으로 도입하는 것을 추천합니다."
    ]
    """

    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            res.raise_for_status()
            text_content = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(text_content)
        except Exception as e:
            print(f"[Ensemble Synthesis Gemini Error] {e}")
            
    if OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a professional career coach helper. Synthesize the provided drafts into a JSON array."},
                    {"role": "user", "content": prompt}
                ]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            res.raise_for_status()
            text_content = res.json()["choices"][0]["message"]["content"].strip()
            parsed = json.loads(text_content)
            if isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, list):
                        return val
            return parsed
        except Exception as e:
            print(f"[Ensemble Synthesis OpenAI Error] {e}")
            
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
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            res.raise_for_status()
            text_content = res.json()["content"][0]["text"].strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0].strip()
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0].strip()
            return json.loads(text_content)
        except Exception as e:
            print(f"[Ensemble Synthesis Claude Error] {e}")

    return drafts[0][1]


def make_feedback(missing_skills: list, resume_text: str = "") -> list:
    """
    다중 AI 협업 피드백 생성 (Ensemble Synthesis)
    - Gemini, OpenAI, Claude를 병렬로 호출하여 초안 피드백 수집
    - 수집된 초안들을 취합하여 최종 합성용 LLM을 통해 정교한 피드백으로 정제 후 반환
    - 특정 API 오류 시 정상 반환된 다른 모델들의 조합으로 보완
    """
    if not missing_skills:
        return []

    import concurrent.futures

    def run_gemini():
        if GEMINI_API_KEY:
            try:
                return make_feedback_gemini(missing_skills, resume_text)
            except Exception as e:
                print(f"[Ensemble Gemini Feedback Error] {e}")
        return None

    def run_openai():
        if OPENAI_API_KEY:
            try:
                return make_feedback_openai(missing_skills, model="gpt-4o", resume_text=resume_text)
            except Exception as e:
                print(f"[Ensemble OpenAI Feedback Error] {e}")
        return None

    def run_claude():
        if ANTHROPIC_API_KEY:
            try:
                return make_feedback_claude(missing_skills, model="claude-3-5-sonnet-20241022", resume_text=resume_text)
            except Exception as e:
                print(f"[Ensemble Claude Feedback Error] {e}")
        return None

    # ThreadPoolExecutor를 이용해 병렬 수행
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_gemini = executor.submit(run_gemini)
        future_openai = executor.submit(run_openai)
        future_claude = executor.submit(run_claude)

        res_gemini = future_gemini.result()
        res_openai = future_openai.result()
        res_claude = future_claude.result()

    drafts = []
    if res_gemini and isinstance(res_gemini, list): drafts.append(("Gemini", res_gemini))
    if res_openai and isinstance(res_openai, list): drafts.append(("OpenAI", res_openai))
    if res_claude and isinstance(res_claude, list): drafts.append(("Claude", res_claude))

    if not drafts:
        # 모든 AI 모델 호출이 실패했거나 아무것도 반환되지 않은 경우
        return rule_based_feedback(missing_skills)

    # 수집된 초안 피드백 합성
    try:
        return synthesize_feedback(missing_skills, drafts, resume_text)
    except Exception as e:
        print(f"[Ensemble Synthesis Fallback] 합성 에러 발생: {e}")
        # 합성 중 에러 발생 시 정상 응답 중 첫 번째 피드백 초안을 반환
        return drafts[0][1]


def compare_resumes(user_resume: str, comp_resume: str, comp_label: str) -> dict:
    """
    사용자 이력서와 비교 대상 이력서(합격자 등)를 비교 분석
    - strengths: 사용자 이력서의 상대적 강점 (list)
    - weaknesses: 사용자 이력서의 상대적 약점/보완점 (list)
    - skill_gap: 부족한 기술 스택 및 역량 격차 (list)
    - advice: 합격 수준으로 끌어올리기 위한 조언 (list)
    - overall_assessment: 종합 평가 (str)
    """
    prompt = f"""
    당신은 IT 전문 채용 전문가이자 기술 커리어 코치입니다.
    사용자의 이력서와 비교 대상 이력서({comp_label})를 비교 분석하여 상세 보고서를 작성해주세요.
    
    사용자 이력서:
    {user_resume}
    
    비교 대상 이력서 ({comp_label}):
    {comp_resume}
    
    두 이력서를 비교하여 다음 항목을 JSON 형식으로 작성해주세요:
    1. "strengths": 비교 대상 이력서 대비 사용자가 가진 강점 목록 (3~5개 항목의 문자열 배열)
    2. "weaknesses": 비교 대상 이력서 대비 사용자가 가진 약점/보완점 목록 (3~5개 항목의 문자열 배열)
    3. "skill_gap": 비교 대상 이력서에 명시되어 있으나 사용자에게 부족한 기술 스택 및 역량 격차 목록 (3~5개 항목의 문자열 배열)
    4. "advice": 사용자가 이직 또는 취업에 성공하기 위한 구체적인 학습 및 커리어 조언 목록 (3~5개 항목의 문자열 배열)
    5. "overall_assessment": 두 이력서의 비교 분석 결과를 요약하는 종합 평가 글 (1~2단락의 설명 텍스트)
    
    반드시 마크다운 코드 블록(```)이나 부가 설명 없이 정확히 위의 키들("strengths", "weaknesses", "skill_gap", "advice", "overall_assessment")을 포함하는 유효한 JSON 객체 하나만 반환해주세요.
    """

    result = None

    # 1. Claude로 시도 (비교 분석 품질 우수)
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
            
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0].strip()
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0].strip()
            result = json.loads(text_content)
        except Exception as e:
            print(f"[Warning] Claude 이력서 비교 실패, OpenAI 시도: {e}")

    # 2. OpenAI로 시도
    if not result and OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a senior tech recruiter analyzing and comparing two resumes. Return result in JSON format."},
                    {"role": "user", "content": prompt}
                ]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            res.raise_for_status()
            text_content = res.json()["choices"][0]["message"]["content"].strip()
            result = json.loads(text_content)
        except Exception as e:
            print(f"[Warning] OpenAI 이력서 비교 실패, Gemini 시도: {e}")

    # 3. Gemini로 시도
    if not result and GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            res.raise_for_status()
            text_content = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            result = json.loads(text_content)
        except Exception as e:
            print(f"[Warning] Gemini 이력서 비교 실패: {e}")

    # 4. 모든 AI 실패 시 기본 더미 응답 반환
    if not result:
        result = {
            "strengths": ["비교 대상 대비 강점을 분석할 수 없습니다. API 설정을 확인해주세요."],
            "weaknesses": ["비교 대상 대비 약점을 분석할 수 없습니다."],
            "skill_gap": ["역량 격차 분석을 불러올 수 없습니다."],
            "advice": ["추가적인 커리어 가이드를 제공할 수 없습니다."],
            "overall_assessment": "모든 AI 분석 API 호출에 실패하여 종합 분석 결과를 제공할 수 없습니다."
        }

    # 결과 리스트 데이터 중복 제거 및 클리닝 (De-duplication Guard)
    for field in ["strengths", "weaknesses", "skill_gap", "advice"]:
        if field in result and isinstance(result[field], list):
            seen = set()
            deduped = []
            for item in result[field]:
                val = item.strip()
                if val and val.lower() not in seen:
                    seen.add(val.lower())
                    deduped.append(val)
            result[field] = deduped

    return result

