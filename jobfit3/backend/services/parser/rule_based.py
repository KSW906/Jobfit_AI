import re

# ================================================================
# 기존 app.py의 IT_SKILLS + FEEDBACK_MAP 유지하면서 확장
# 새 스킬 추가 시 여기에만 추가하면 됨
# ================================================================

IT_SKILLS = {
    "language":  ["Python", "Java", "JavaScript", "TypeScript", "C", "C++",
                  "Go", "Rust", "Kotlin", "Swift", "Ruby", "PHP", "Scala", "R"],
    "frontend":  ["React", "Vue", "Angular", "HTML", "CSS", "Next.js", "Nuxt",
                  "Svelte", "Tailwind", "Bootstrap", "jQuery"],
    "backend":   ["Flask", "Django", "FastAPI", "Spring", "Node.js", "Express",
                  "NestJS", "Laravel", "Rails"],
    "database":  ["MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite",
                  "Elasticsearch", "DynamoDB", "Firebase"],
    "devops":    ["Docker", "Kubernetes", "AWS", "GCP", "Azure", "Linux",
                  "Git", "CI/CD", "Terraform", "Jenkins", "GitHub Actions", "Bash"],
    "ai":        ["TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn",
                  "LangChain", "OpenAI", "LLM", "NLP", "RAG", "MLOps", "Spark"],
    "tools":     ["Figma", "Jira", "Postman", "Agile", "Scrum", "REST", "GraphQL", "gRPC"],
}

FEEDBACK_MAP = {
    # 기존 FEEDBACK_MAP 유지
    "Python":       "Python 기본 문법과 데이터 처리 연습을 추천합니다.",
    "Java":         "Java 객체지향 문법과 Spring 연계를 학습해보세요.",
    "JavaScript":   "JavaScript 기본 문법과 비동기 처리를 학습하세요.",
    "TypeScript":   "TypeScript 타입 시스템과 React 연계를 학습해보세요.",
    "React":        "React 컴포넌트, props, state 구조를 연습하세요.",
    "Flask":        "Flask로 REST API 서버를 직접 구현해보세요.",
    "Spring":       "Spring Boot를 활용한 백엔드 API 개발을 학습하세요.",
    "Docker":       "Docker를 활용해 프로젝트를 컨테이너로 실행해보세요.",
    "Kubernetes":   "Docker 이후 Kubernetes로 컨테이너 오케스트레이션을 학습하세요.",
    "AWS":          "AWS EC2 또는 S3를 이용한 배포 경험을 쌓아보세요.",
    "MySQL":        "SQL 기본 문법과 테이블 설계를 학습하세요.",
    "PostgreSQL":   "PostgreSQL과 ORM(SQLAlchemy 등) 활용법을 학습하세요.",
    "MongoDB":      "NoSQL 개념과 MongoDB CRUD 操作을 학습하세요.",
    "Git":          "Git branch, commit, push, pull 협업 흐름을 익히세요.",
    "Node.js":      "Node.js와 Express로 간단한 REST API를 만들어보세요.",
    "TensorFlow":   "TensorFlow 공식 튜토리얼로 기본 모델 학습을 경험하세요.",
    "PyTorch":      "PyTorch로 간단한 신경망을 직접 구현해보세요.",
}


def get_all_skills() -> list:
    """모든 카테고리의 스킬을 평탄화해서 반환"""
    skills = []
    for category in IT_SKILLS.values():
        skills.extend(category)
    return skills


def extract_skills(text: str) -> dict:
    """
    규칙 기반 스킬 추출기 (기존 extract_skills 로직 유지 + 확장)

    반환 형식:
    {
        "skills":         ["전체 추출 스킬"],
        "required":       [],  # Claude API 업그레이드 시 채워짐
        "preferred":      [],  # Claude API 업그레이드 시 채워짐
        "certifications": []   # Claude API 업그레이드 시 채워짐
    }

    ================================================================
    Claude API로 업그레이드 시:
    - required / preferred / certifications 필드가 실제로 채워짐
    - services/parser/claude.py 파일의 extract_skills()로 교체
    ================================================================
    """
    if not text:
        return {"skills": [], "required": [], "preferred": [], "certifications": []}

    # HTML 태그 제거
    clean_text = re.sub(r"<[^>]+>", " ", text)

    found = []
    for skill in get_all_skills():
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, clean_text, re.IGNORECASE):
            found.append(skill)

    return {
        "skills":         list(set(found)),
        "required":       [],  # Claude API 업그레이드 시 채워짐
        "preferred":      [],  # Claude API 업그레이드 시 채워짐
        "certifications": [],  # Claude API 업그레이드 시 채워짐
    }


def make_feedback(missing_skills: list) -> list:
    """
    기존 make_feedback 로직 유지
    부족 스킬에 대한 학습 피드백 반환
    """
    feedback = []
    for skill in missing_skills:
        feedback.append(
            FEEDBACK_MAP.get(skill, f"{skill} 역량을 보완하면 직무 적합도를 높일 수 있습니다.")
        )
    return feedback