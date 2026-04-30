import re

# ================================================================
# Remotive 데이터 수집기
# n8n에서 받은 raw 데이터를 DB 저장 형식으로 변환
#
# 다른 API 추가 시:
#   services/collector/saramin.py 생성 후
#   동일한 normalize() 인터페이스로 구현하면 됨
# ================================================================

# IT 카테고리만 허용 (비IT 공고 필터링)
ALLOWED_CATEGORIES = [
    "software-dev", "Software Development",
    "data", "Data",
    "devops-sysadmin", "DevOps / Sysadmin",
    "artificial-intelligence", "Artificial Intelligence",
    "qa", "QA",
]


def normalize(raw: dict) -> dict | None:
    """
    Remotive API 응답을 DB 저장 형식으로 변환
    IT 카테고리가 아니면 None 반환 (필터링)
    """
    category = raw.get("category", "")
    if not any(a.lower() in category.lower() for a in ALLOWED_CATEGORIES):
        return None

    tags = raw.get("tags", [])
    tags_str = ",".join(tags) if isinstance(tags, list) else str(tags)

    return {
        "job_id":          str(raw.get("id", "")),
        "title":           raw.get("title", ""),
        "company":         raw.get("company_name", ""),
        "location":        raw.get("candidate_required_location", ""),
        "employment_type": raw.get("job_type", ""),
        "salary":          raw.get("salary", ""),
        "description":     raw.get("description", ""),
        "tags":            tags_str,
        "apply_url":       raw.get("url", ""),
        "posted_at":       raw.get("publication_date", ""),
        "category":        category,
        "source":          "remotive",
    }