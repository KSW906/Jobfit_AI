import re

# ================================================================
# Adzuna 데이터 수집기
# n8n에서 받은 raw 데이터를 DB 저장 형식으로 변환
# ================================================================

# IT 직종 관련 키워드 (제목 및 카테고리 필터링용)
IT_KEYWORDS = [
    "developer", "engineer", "software", "programmer", "data", "ai",
    "machine learning", "backend", "frontend", "fullstack", "devops", "cloud",
    "systems", "qa", "test", "security", "network", "scrum", "agile", "web",
    "python", "java", "javascript", "typescript", "c#", "c++", "golang", "ruby", "rust"
]


def is_it_job(title: str, category: str) -> bool:
    """IT 직종 여부 확인"""
    text = (title + " " + category).lower()
    return any(kw.lower() in text for kw in IT_KEYWORDS)


def normalize(raw: dict) -> dict | None:
    """
    Adzuna API 응답을 DB 저장 형식으로 변환
    IT 카테고리가 아니거나 키워드가 매칭되지 않으면 None 반환

    raw 구조 예시:
    {
      "id": "129698749",
      "title": "Javascript Developer",
      "salary_min": 50000,
      "salary_max": 55000,
      "contract_type": "permanent",
      "created": "2013-11-08T18:07:39Z",
      "description": "JavaScript Developer Corporate...",
      "location": {
        "display_name": "Marlow, Buckinghamshire",
        "area": ["UK", "South East England", "Buckinghamshire", "Marlow"]
      },
      "company": {
        "display_name": "Corporate Project Solutions"
      },
      "category": {
        "tag": "it-jobs",
        "label": "IT Jobs"
      },
      "redirect_url": "..."
    }
    """
    title = raw.get("title", "")
    category_data = raw.get("category", {})
    category_tag = category_data.get("tag", "")
    category_label = category_data.get("label", "")

    # IT 직종 필터링 (카테고리 태그가 'it-jobs'거나 제목에 IT 키워드가 있는 경우)
    if "it-jobs" not in category_tag.lower() and not is_it_job(title, category_label):
        return None

    job_id = raw.get("id")
    if not job_id:
        return None

    # 연봉 정보 조합 (Adzuna는 파운드/달러 등의 숫자를 반환하므로 문자열로 가공)
    sal_min = raw.get("salary_min")
    sal_max = raw.get("salary_max")
    salary = ""
    if sal_min and sal_max:
        salary = f"{sal_min} - {sal_max}"
    elif sal_min:
        salary = f"{sal_min}"
    elif sal_max:
        salary = f"{sal_max}"

    # 지역 정보
    loc_data = raw.get("location", {})
    location = loc_data.get("display_name", "")

    # 고용 형태 (contract_time: full_time/part_time 등, contract_type: permanent/contract 등)
    contract_type = raw.get("contract_type", "")
    contract_time = raw.get("contract_time", "")
    emp_type = f"{contract_type} ({contract_time})".strip(" ()") if contract_time or contract_type else ""

    # 회사 정보
    company = raw.get("company", {}).get("display_name", "")

    # 태그 (카테고리 라벨이나 태그를 콤마로 연계)
    tags = ",".join(filter(None, [category_label, category_tag]))

    return {
        "job_id":          f"adzuna_{job_id}",
        "title":           title,
        "company":         company,
        "location":        location,
        "employment_type": emp_type,
        "salary":          salary,
        "description":     raw.get("description", ""),
        "tags":            tags,
        "apply_url":       raw.get("redirect_url", ""),
        "posted_at":       raw.get("created", ""),
        "category":        category_label,
        "source":          "adzuna",
    }


def fetch_raw_adzuna(app_id: str, app_key: str, limit: int = 50) -> list:
    """
    Adzuna API를 직접 호출하여 IT 카테고리의 raw 채용 공고 목록을 가져옵니다.
    """
    import requests
    if not app_id or not app_key:
        print("[Sync] Adzuna API Credentials (app_id or app_key) are missing.")
        return []

    url = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": limit,
        "what": "developer",
        "content-type": "application/json"
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            raw_data = res.json()
            jobs = raw_data.get("results", [])
            for j in jobs:
                j["source"] = "adzuna"
            return jobs
        else:
            print(f"[Sync] Adzuna API status error: {res.status_code}")
    except Exception as e:
        print(f"[Sync] Adzuna fetch error: {e}")
    return []

