"""
insights.py — 데이터 인사이트 대시보드 라우트

엔드포인트 목록:
  GET /api/insights/skill-growth   — 사용자 매칭 이력 기반 적합도/스킬 성장 추이
  GET /api/insights/trends         — 채용 시장 스킬 수요 트렌드 (보유 여부 표시)
  GET /api/insights/salary?skill=X — 공고 연봉 분포 통계 (스킬 필터 선택)
"""

import re
from flask import Blueprint, request, jsonify
from extensions import db
from models import MatchHistory, SkillStat, JobPosting, UserProfile
from routes.auth import get_current_user_from_request

insights_bp = Blueprint("insights", __name__)


def parse_salary_number(sal_str: str):
    """연봉 문자열에서 대표 숫자 추출 (analyze.py 로직과 동일 규칙)"""
    if not sal_str:
        return None
    sal_str_lower = sal_str.lower()
    multiplier = 1
    if "k" in sal_str_lower:
        multiplier = 1000

    # 쉼표(,)는 천 단위 구분기호인 경우가 많으므로 먼저 제거하고 숫자 추출
    sal_str_clean = sal_str_lower.replace(",", "")
    clean_str = re.sub(r"[^\d.]", " ", sal_str_clean)
    numbers = re.findall(r"\d+(?:\.\d+)?", clean_str)
    if not numbers:
        return None

    val = max(float(n) for n in numbers)
    if val < 1000 and multiplier == 1000:
        val *= 1000
    return val


@insights_bp.route("/api/insights/skill-growth", methods=["GET"])
def skill_growth():
    """사용자의 과거 매칭 분석 이력을 시계열로 반환 (적합도/스킬 수 추이)"""
    user = get_current_user_from_request()
    if not user:
        return jsonify({"error": "로그인이 필요한 서비스입니다."}), 401

    histories = (
        MatchHistory.query.filter_by(user_id=user.id)
        .order_by(MatchHistory.run_at.asc())
        .all()
    )

    points = []
    for h in histories:
        skills_count = len([s for s in (h.skills_snapshot or "").split(",") if s.strip()])
        points.append({
            "run_at":        h.run_at.isoformat() if h.run_at else None,
            "date":          h.run_at.strftime("%m/%d") if h.run_at else "",
            "avg_fit_score": h.avg_fit_score or 0,
            "skills_count":  skills_count,
            "analyzed_jobs": h.analyzed_jobs or 0,
        })

    summary = {
        "total_runs":    len(points),
        "first_score":   points[0]["avg_fit_score"] if points else 0,
        "latest_score":  points[-1]["avg_fit_score"] if points else 0,
        "score_delta":   (points[-1]["avg_fit_score"] - points[0]["avg_fit_score"]) if len(points) >= 2 else 0,
        "skills_delta":  (points[-1]["skills_count"] - points[0]["skills_count"]) if len(points) >= 2 else 0,
    }

    return jsonify({"points": points, "summary": summary}), 200


@insights_bp.route("/api/insights/trends", methods=["GET"])
def trends():
    """채용 시장 스킬 수요 트렌드. 사용자가 보유한 스킬은 owned=true 로 표시."""
    limit = request.args.get("limit", 15, type=int)
    stats = SkillStat.query.order_by(SkillStat.count.desc()).limit(limit).all()

    owned_lower = set()
    user = get_current_user_from_request()
    if user:
        prof = UserProfile.query.get(user.id)
        if prof and prof.skills:
            owned_lower = {s.strip().lower() for s in prof.skills.split(",") if s.strip()}

    max_count = max((s.count for s in stats), default=1) or 1
    items = [{
        "skill":   s.skill_name,
        "count":   s.count,
        "ratio":   round(s.count / max_count, 3),
        "owned":   s.skill_name.lower() in owned_lower,
    } for s in stats]

    return jsonify({"trends": items, "max_count": max_count}), 200


@insights_bp.route("/api/insights/salary", methods=["GET"])
def salary():
    """저장된 공고들의 연봉 분포 통계. ?skill= 로 특정 스킬 요구 공고만 필터링."""
    skill = request.args.get("skill", "").strip()

    q = JobPosting.query
    if skill:
        skill_lower = skill.strip().lower()
        q = q.filter(
            (db.func.lower(JobPosting.skills) == skill_lower) |
            db.func.lower(JobPosting.skills).like(f"{skill_lower},%") |
            db.func.lower(JobPosting.skills).like(f"%,{skill_lower}") |
            db.func.lower(JobPosting.skills).like(f"%,{skill_lower},%")
        )
    jobs = q.all()

    values = []
    for j in jobs:
        val = parse_salary_number(j.salary)
        if val is not None and val > 0:
            values.append(val)

    if not values:
        return jsonify({
            "count": 0,
            "skill": skill,
            "message": "연봉 정보를 추출할 수 있는 공고가 없습니다.",
            "stats": None,
            "buckets": [],
        }), 200

    values.sort()
    n = len(values)
    median = values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2
    avg = sum(values) / n

    # 분포 버킷 (최소~최대 구간을 6등분)
    lo, hi = values[0], values[-1]
    bucket_count = 6
    buckets = []
    if hi > lo:
        step = (hi - lo) / bucket_count
        edges = [lo + step * i for i in range(bucket_count + 1)]
        counts = [0] * bucket_count
        for v in values:
            idx = min(int((v - lo) / step), bucket_count - 1)
            counts[idx] += 1
        for i in range(bucket_count):
            buckets.append({
                "range_min": round(edges[i]),
                "range_max": round(edges[i + 1]),
                "count":     counts[i],
            })
    else:
        buckets.append({"range_min": round(lo), "range_max": round(hi), "count": n})

    return jsonify({
        "count": n,
        "skill": skill,
        "stats": {
            "min":    round(lo),
            "max":    round(hi),
            "avg":    round(avg),
            "median": round(median),
        },
        "buckets": buckets,
    }), 200
