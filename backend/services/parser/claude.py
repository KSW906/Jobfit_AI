# ================================================================
# Claude API 파서 (업그레이드용)
#
# 사용 전 준비사항:
#   1. pip install anthropic
#   2. requirements.txt에 anthropic 추가
#   3. .env에 ANTHROPIC_API_KEY=your_key_here 추가
#   4. config.py에서 ANTHROPIC_API_KEY 주석 해제
#
# 교체 방법 (routes/jobs.py):
#   현재: from services.parser.rule_based import extract_skills, make_feedback
#   교체: from services.parser.claude import extract_skills, make_feedback
#
# 현재 상태: 미구현 (rule_based.py 사용 중)
# ================================================================

# TODO: 아래 주석 해제 후 구현
# import json
# import anthropic
# from config import Config


def extract_skills(text: str) -> dict:
    """
    Claude API 기반 스킬 추출기
    rule_based보다 정확하게 필수/우대/자격증을 구분

    반환 형식:
    {
        "skills":         ["전체 스킬"],
        "required":       ["필수 스킬"],       ← 규칙 기반과 달리 실제로 채워짐
        "preferred":      ["우대 스킬"],       ← 규칙 기반과 달리 실제로 채워짐
        "certifications": ["자격증"]           ← 규칙 기반과 달리 실제로 채워짐
    }
    """
    # TODO: Claude API 연동 구현
    # client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    #
    # response = client.messages.create(
    #     model="claude-sonnet-4-20250514",
    #     max_tokens=1000,
    #     messages=[{
    #         "role": "user",
    #         "content": f"""
    #         아래 채용공고에서 스킬을 추출해줘.
    #         반드시 JSON 형식으로만 답해줘. 다른 텍스트는 절대 포함하지 마.
    #
    #         채용공고:
    #         {text}
    #
    #         반환 형식:
    #         {{
    #             "skills": ["전체 스킬 목록"],
    #             "required": ["필수 스킬"],
    #             "preferred": ["우대 스킬"],
    #             "certifications": ["요구 자격증"]
    #         }}
    #         """
    #     }]
    # )
    # return json.loads(response.content[0].text)

    raise NotImplementedError(
        "Claude API 파서가 아직 구현되지 않았습니다.\n"
        "rule_based.py를 사용하거나 이 파일을 구현해주세요."
    )


def make_feedback(missing_skills: list) -> list:
    """
    Claude API 기반 피드백 생성
    rule_based의 하드코딩된 FEEDBACK_MAP보다 풍부한 피드백 생성
    """
    # TODO: Claude API 연동 구현
    raise NotImplementedError(
        "Claude API 피드백 생성이 아직 구현되지 않았습니다."
    )