# Jobfit AI

채용 공고 API 데이터와 사용자 역량 데이터를 비교하여 부족한 기술과 학습 방향을 피드백하는 AI 기반 프로젝트입니다.

## Folder Structure

```
Jobfit-ai/
├── backend/
│   ├── app.py                          # Flask 메인 (기존 구조 유지)
│   ├── config.py                       # 설정
│   ├── extensions.py                   # SQLAlchemy
│   ├── models.py                       # DB 모델
│   ├── requirements.txt
│   ├── routes/
│   │   ├── jobs.py                     # 공고 저장/조회 API
│   │   └── analyze.py                  # 분석 API (/analyze, /api/analyze)
│   └── services/
│       ├── parser/
│       │   ├── rule_based.py           # 규칙 기반 (현재 사용)
│       │   └── claude.py               # Claude API (추후 업그레이드)
│       └── collector/
│           ├── remotive.py             # Remotive 수집기 (구현됨)
│           └── saramin.py              # 사람인 수집기 (추후 구현)
├── frontend/                           # React UI (다음 단계)
├── n8n/
│   └── workflow.json                   # n8n 워크플로우
├── data/
│   └── sample_jobs.json
└── docs/
```

---

## 실행 방법

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
python app.py
```

---

## API 엔드포인트

| 메서드 | URL               | 설명                     |
| ------ | ----------------- | ------------------------ |
| GET    | /                 | 서버 상태 (기존 유지)    |
| GET    | /health           | 헬스 체크                |
| POST   | /analyze          | 단일 JD 분석 (기존 유지) |
| POST   | /api/jobs         | 공고 저장 (n8n → Flask)  |
| GET    | /api/jobs         | 공고 목록 조회           |
| GET    | /api/skills/stats | 스킬 수요 통계           |
| POST   | /api/analyze      | DB 전체 공고 매칭 분석   |

### /analyze 요청 (기존 방식 유지)

```json
{
  "job_title": "백엔드 개발자",
  "job_description": "Python, AWS 경험자...",
  "user_skills": ["Python", "React", "Git"]
}
```

### /api/analyze 요청 (DB 연동 방식)

```json
{
  "my_skills": ["Python", "React", "Git"],
  "limit": 10
}
```

---

## 업그레이드 가이드

### Claude API로 파서 교체

```python
# backend/routes/jobs.py 와 backend/routes/analyze.py 에서
# 현재:
from services.parser.rule_based import extract_skills, make_feedback
# 교체:
from services.parser.claude import extract_skills, make_feedback
```

### 사람인 API 추가

```
1. backend/services/collector/saramin.py 구현
2. backend/routes/jobs.py 의 소스별 normalizer 선택 부분에 saramin 추가
```
