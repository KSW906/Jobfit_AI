# ================================================================
# 사람인 API 수집기 (추후 구현)
#
# 사용 전 준비사항:
#   1. 사람인 API 키 발급 (https://oapi.saramin.co.kr)
#   2. .env에 SARAMIN_API_KEY=your_key_here 추가
#
# 구현 방법:
#   normalize() 함수를 사람인 API 응답에 맞게 구현
#   remotive.py의 normalize()와 동일한 형식으로 반환하면
#   나머지 코드 변경 없이 바로 사용 가능
#
# 현재 상태: 미구현
# ================================================================


def normalize(raw: dict) -> dict | None:
    """
    사람인 API 응답을 DB 저장 형식으로 변환
    반드시 remotive.py의 normalize()와 동일한 키 구조로 반환

    반환 형식:
    {
        "job_id":          str,
        "title":           str,
        "company":         str,
        "location":        str,
        "employment_type": str,
        "salary":          str,
        "description":     str,
        "tags":            str,   # 콤마 구분
        "apply_url":       str,
        "posted_at":       str,
        "category":        str,
        "source":          "saramin",  # 반드시 "saramin"으로 설정
    }
    """
    # TODO: 사람인 API 연동 구현
    raise NotImplementedError(
        "사람인 수집기가 아직 구현되지 않았습니다.\n"
        "API 키 발급 후 이 파일을 구현해주세요."
    )