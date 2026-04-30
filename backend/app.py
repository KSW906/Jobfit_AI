from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

IT_SKILLS = {
    "language": ["Python", "Java", "JavaScript", "TypeScript", "C", "C++"],
    "frontend": ["React", "Vue", "HTML", "CSS", "Next.js"],
    "backend": ["Flask", "Django", "Spring", "Node.js", "Express"],
    "database": ["MySQL", "PostgreSQL", "MongoDB", "Redis"],
    "devops": ["Docker", "Kubernetes", "AWS", "Linux", "Git", "CI/CD"],
    "ai": ["TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn"]
}

FEEDBACK_MAP = {
    "Python": "Python 기본 문법과 데이터 처리 연습을 추천합니다.",
    "Java": "Java 객체지향 문법과 Spring 연계를 학습해보세요.",
    "JavaScript": "JavaScript 기본 문법과 비동기 처리를 학습하세요.",
    "React": "React 컴포넌트, props, state 구조를 연습하세요.",
    "Flask": "Flask로 REST API 서버를 직접 구현해보세요.",
    "Spring": "Spring Boot를 활용한 백엔드 API 개발을 학습하세요.",
    "Docker": "Docker를 활용해 프로젝트를 컨테이너로 실행해보세요.",
    "AWS": "AWS EC2 또는 S3를 이용한 배포 경험을 쌓아보세요.",
    "MySQL": "SQL 기본 문법과 테이블 설계를 학습하세요.",
    "Git": "Git branch, commit, push, pull 협업 흐름을 익히세요."
}

def get_all_skills():
    skills = []
    for category in IT_SKILLS.values():
        skills.extend(category)
    return skills

def extract_skills(text):
    found = []
    all_skills = get_all_skills()

    for skill in all_skills:
        pattern = re.escape(skill)
        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)

    return list(set(found))

def calculate_fit_score(matched, required):
    if len(required) == 0:
        return 0
    return round((len(matched) / len(required)) * 100)

def make_feedback(missing_skills):
    feedback = []

    for skill in missing_skills:
        feedback.append(
            FEEDBACK_MAP.get(skill, f"{skill} 역량을 보완하면 직무 적합도를 높일 수 있습니다.")
        )

    return feedback

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Jobfit AI Backend is running"
    })

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON 데이터가 필요합니다."}), 400

    job_title = data.get("job_title", "")
    job_description = data.get("job_description", "")
    user_skills = data.get("user_skills", [])

    if not job_description:
        return jsonify({"error": "채용 공고 내용이 필요합니다."}), 400

    if not user_skills:
        return jsonify({"error": "사용자 기술 목록이 필요합니다."}), 400

    job_keywords = extract_skills(job_description)

    user_skills_lower = [skill.lower() for skill in user_skills]

    matched_skills = [
        skill for skill in job_keywords
        if skill.lower() in user_skills_lower
    ]

    missing_skills = [
        skill for skill in job_keywords
        if skill.lower() not in user_skills_lower
    ]

    fit_score = calculate_fit_score(matched_skills, job_keywords)
    feedback = make_feedback(missing_skills)

    result = {
        "job_title": job_title,
        "job_keywords": job_keywords,
        "user_skills": user_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "fit_score": fit_score,
        "feedback": feedback
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)