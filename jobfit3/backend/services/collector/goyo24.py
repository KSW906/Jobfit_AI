import re
import xml.etree.ElementTree as ET

# ================================================================
# 고용24 (워크넷) API 수집기
#
# 사용 전 준비사항:
#   1. 고용24 OpenAPI 사이트에서 인증키 발급
#      → https://www.work24.go.kr/cm/e/a/0110/selectOpenApiIntro.do
#   2. .env에 GOYO24_API_KEY=your_key_here 추가
#
# API 특징:
#   - 응답 형식: XML (UTF-8)
#   - 기본 URL: https://www.work24.go.kr/cm/openapi/call/wk/FileDown.do
#   - IT 직종 코드: 직종코드 파라미터로 필터링 가능
#
# 다른 소스 추가 시:
#   동일한 normalize() 인터페이스로 구현하면
#   나머지 코드 변경 없이 바로 사용 가능
# ================================================================

# IT 직종 관련 키워드 (description 필터링용)
IT_KEYWORDS = [
    "개발", "프로그래밍", "소프트웨어", "백엔드", "프론트엔드",
    "풀스택", "데이터", "AI", "머신러닝", "클라우드", "DevOps",
    "Python", "Java", "JavaScript", "React", "Spring", "Django",
    "데이터베이스", "서버", "API", "앱", "모바일", "시스템"
]


def parse_xml(xml_text: str) -> list:
    """
    고용24 API XML 응답을 파싱해서 공고 리스트 반환
    응답 형식:
    <wantedRoot>
      <wanted>
        <wantedAuthNo>...</wantedAuthNo>
        <corp>회사명</corp>
        <wantedTitle>채용제목</wantedTitle>
        <salTpNm>임금형태</salTpNm>
        <sal>급여</sal>
        <minSal>최소임금</minSal>
        <maxSal>최대임금</maxSal>
        <region1Nm>근무지역</region1Nm>
        <empTpNm>고용형태</empTpNm>
        <minEdubgNm>최소학력</minEdubgNm>
        <career>경력</career>
        <regDt>등록일자</regDt>
        <closeDt>마감일자</closeDt>
        <wantedInfoUrl>채용정보URL</wantedInfoUrl>
        <jobsCd>직종코드</jobsCd>
        <jobsNm>직종명</jobsNm>
      </wanted>
    </wantedRoot>
    """
    try:
        root = ET.fromstring(xml_text)
        jobs = []
        for wanted in root.findall(".//wanted"):
            job = {}
            for child in wanted:
                job[child.tag] = child.text or ""
            jobs.append(job)
        return jobs
    except ET.ParseError:
        return []


def is_it_job(title: str, jobs_name: str) -> bool:
    """IT 직종 여부 확인"""
    text = (title + " " + jobs_name).lower()
    return any(kw.lower() in text for kw in IT_KEYWORDS)


def normalize(raw: dict) -> dict | None:
    """
    고용24 API 응답 데이터를 DB 저장 형식으로 변환
    remotive.py의 normalize()와 동일한 형식으로 반환

    raw: XML 파싱된 딕셔너리 (parse_xml() 결과)
    """
    title    = raw.get("wantedTitle", "")
    jobs_nm  = raw.get("jobsNm", "")

    # IT 직종 필터링
    if not is_it_job(title, jobs_nm):
        return None

    job_id = raw.get("wantedAuthNo", "")
    if not job_id:
        return None

    # 급여 정보 조합
    sal_tp = raw.get("salTpNm", "")
    sal    = raw.get("sal", "")
    salary = f"{sal_tp} {sal}".strip() if sal else sal_tp

    # 지역 정보
    region = raw.get("region1Nm", "") or raw.get("region2Nm", "")

    # 고용형태
    emp_tp = raw.get("empTpNm", "")

    # 채용 URL
    apply_url = raw.get("wantedInfoUrl", "")

    # description은 직종명 + 학력 + 경력으로 구성 (상세 API 별도 호출 필요)
    min_edu    = raw.get("minEdubgNm", "")
    career     = raw.get("career", "")
    description = f"{jobs_nm}. 학력: {min_edu}. 경력: {career}".strip()

    return {
        "job_id":          f"goyo24_{job_id}",
        "title":           title,
        "company":         raw.get("corp", ""),
        "location":        region,
        "employment_type": emp_tp,
        "salary":          salary,
        "description":     description,
        "tags":            jobs_nm,    # 직종명을 태그로 활용
        "apply_url":       apply_url,
        "posted_at":       raw.get("regDt", ""),
        "category":        jobs_nm,
        "source":          "goyo24",
    }


def fetch_and_normalize(api_key: str, keyword: str = "개발자", num: int = 100) -> list:
    """
    고용24 API 직접 호출 후 정규화
    n8n 없이 Flask에서 직접 수집할 때 사용

    ================================================================
    사용 예시 (routes/jobs.py에서):
    from services.collector.goyo24 import fetch_and_normalize
    jobs = fetch_and_normalize(api_key="your_key", keyword="백엔드")
    ================================================================
    """
    import requests

    url = "https://www.work24.go.kr/cm/openapi/call/wk/FileDown.do"
    params = {
        "authKey":   api_key,
        "callTp":    "L",       # 목록 조회
        "returnType":"XML",
        "startPage": 1,
        "display":   num,
        "keyword":   keyword,
        "sort":      "DATE",    # 최신순
    }

    try:
        res  = requests.get(url, params=params, timeout=10)
        jobs = parse_xml(res.text)
        result = []
        for raw in jobs:
            normalized = normalize(raw)
            if normalized:
                result.append(normalized)
        return result
    except Exception as e:
        print(f"고용24 API 호출 실패: {e}")
        return []
