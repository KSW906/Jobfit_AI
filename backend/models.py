from datetime import datetime
import json
from extensions import db


class User(db.Model):
    """사용자 계정 테이블"""
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(100), unique=True, nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)
    token         = db.Column(db.String(100), unique=True, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # 1-to-1 관계 설정 (UserProfile)
    profile       = db.relationship("UserProfile", backref="user", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class JobPosting(db.Model):
    """채용 공고 테이블"""
    __tablename__ = "job_postings"

    id              = db.Column(db.Integer, primary_key=True)
    job_id          = db.Column(db.String(200), unique=True, nullable=False)
    title           = db.Column(db.String(300), nullable=False)
    company         = db.Column(db.String(200))
    location        = db.Column(db.String(200))
    employment_type = db.Column(db.String(50))
    salary          = db.Column(db.String(100))
    description     = db.Column(db.Text)         # 원본 HTML JD
    tags            = db.Column(db.Text)          # Remotive tags (콤마 구분)
    skills          = db.Column(db.Text)          # 추출된 스킬 (콤마 구분)
    apply_url       = db.Column(db.String(500))
    posted_at       = db.Column(db.String(50))
    category        = db.Column(db.String(100))

    # ================================================================
    # source 필드: API 출처 구분 (remotive / goyo24 / adzuna 등)
    # ================================================================
    source          = db.Column(db.String(50), default="remotive")

    fetched_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":              self.id,
            "job_id":          self.job_id,
            "title":           self.title,
            "company":         self.company,
            "location":        self.location,
            "employment_type": self.employment_type,
            "salary":          self.salary,
            "description":     self.description,
            "tags":            self.tags.split(",") if self.tags else [],
            "skills":          self.skills.split(",") if self.skills else [],
            "apply_url":       self.apply_url,
            "posted_at":       self.posted_at,
            "category":        self.category,
            "source":          self.source,
            "fetched_at":      self.fetched_at.isoformat() if self.fetched_at else None,
        }


class SkillStat(db.Model):
    """스킬 수요 통계 테이블"""
    __tablename__ = "skill_stats"

    id           = db.Column(db.Integer, primary_key=True)
    skill_name   = db.Column(db.String(100), unique=True, nullable=False)
    count        = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "skill_name":   self.skill_name,
            "count":        self.count,
            "last_updated": self.last_updated.isoformat(),
        }


class UserProfile(db.Model):
    """
    사용자 프로필 테이블
    - 보유 스킬, 선호 조건, 가중치를 영구 저장
    - 단일 사용자 기준 (id=1) 기본 지원
    """
    __tablename__ = "user_profiles"

    id              = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    name            = db.Column(db.String(100), default="기본 사용자")

    # 보유 스킬 (콤마 구분 문자열)
    skills          = db.Column(db.Text, default="")

    # 이력서 (텍스트)
    resume          = db.Column(db.Text, default="")

    # 선호 조건
    pref_job_title  = db.Column(db.String(200), default="")
    pref_category   = db.Column(db.String(200), default="")
    pref_salary     = db.Column(db.Float, nullable=True)
    pref_location   = db.Column(db.String(200), default="")

    # 가중치 (0 ~ 5)
    w_skills        = db.Column(db.Integer, default=3)
    w_title         = db.Column(db.Integer, default=1)
    w_category      = db.Column(db.Integer, default=1)
    w_salary        = db.Column(db.Integer, default=1)
    w_location      = db.Column(db.Integer, default=1)

    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 매칭 이력과 1:N 관계
    match_histories = db.relationship("MatchHistory", backref="user", lazy=True,
                                      cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":             self.id,
            "name":           self.name,
            "skills":         self.skills.split(",") if self.skills else [],
            "resume":         self.resume,
            "preferences": {
                "job_title":  self.pref_job_title,
                "category":   self.pref_category,
                "salary":     self.pref_salary,
                "location":   self.pref_location,
            },
            "priorities": {
                "skills":     self.w_skills,
                "job_title":  self.w_title,
                "category":   self.w_category,
                "salary":     self.w_salary,
                "location":   self.w_location,
            },
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MatchHistory(db.Model):
    """
    매칭 실행 이력 테이블
    - 분석 실행마다 결과 요약 저장
    - UserProfile 과 FK 연결
    """
    __tablename__ = "match_histories"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=True)

    run_at          = db.Column(db.DateTime, default=datetime.utcnow)
    avg_fit_score   = db.Column(db.Integer, default=0)
    total_jobs      = db.Column(db.Integer, default=0)
    analyzed_jobs   = db.Column(db.Integer, default=0)

    # 사용된 스킬 스냅샷
    skills_snapshot = db.Column(db.Text, default="")

    # 선호 조건 스냅샷 (JSON)
    preferences_snapshot = db.Column(db.Text, default="{}")

    # 상위 N개 결과 요약 (JSON 배열)
    top_matches     = db.Column(db.Text, default="[]")

    def to_dict(self):
        return {
            "id":             self.id,
            "user_id":        self.user_id,
            "run_at":         self.run_at.isoformat() if self.run_at else None,
            "avg_fit_score":  self.avg_fit_score,
            "total_jobs":     self.total_jobs,
            "analyzed_jobs":  self.analyzed_jobs,
            "skills_snapshot": self.skills_snapshot.split(",") if self.skills_snapshot else [],
            "preferences_snapshot": json.loads(self.preferences_snapshot or "{}"),
            "top_matches":    json.loads(self.top_matches or "[]"),
        }