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
    description     = db.Column(db.Text)
    tags            = db.Column(db.Text)
    skills          = db.Column(db.Text)
    apply_url       = db.Column(db.String(500))
    posted_at       = db.Column(db.String(50))
    category        = db.Column(db.String(100))
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
    """사용자 프로필 테이블"""
    __tablename__ = "user_profiles"

    id              = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    name            = db.Column(db.String(100), default="기본 사용자")
    skills          = db.Column(db.Text, default="")
    resume          = db.Column(db.Text, default="")

    pref_job_title  = db.Column(db.String(200), default="")
    pref_category   = db.Column(db.String(200), default="")
    pref_salary     = db.Column(db.Float, nullable=True)
    pref_location   = db.Column(db.String(200), default="")

    w_skills        = db.Column(db.Integer, default=3)
    w_title         = db.Column(db.Integer, default=1)
    w_category      = db.Column(db.Integer, default=1)
    w_salary        = db.Column(db.Integer, default=1)
    w_location      = db.Column(db.Integer, default=1)

    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    match_histories = db.relationship("MatchHistory", backref="user", lazy=True, cascade="all, delete-orphan")
    resumes         = db.relationship("UserResume", backref="profile", lazy=True, cascade="all, delete-orphan")
    feedbacks       = db.relationship("ResumeFeedback", backref="profile", lazy=True, cascade="all, delete-orphan")
    
    # 🆕 1:N 관계 - 타인/경쟁자 비교 이력서 보관함 추가
    comp_resumes    = db.relationship("ComparisonResume", backref="profile", lazy=True, cascade="all, delete-orphan")

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
    """매칭 실행 이력 테이블"""
    __tablename__ = "match_histories"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=True)
    run_at           = db.Column(db.DateTime, default=datetime.utcnow)
    avg_fit_score    = db.Column(db.Integer, default=0)
    total_jobs       = db.Column(db.Integer, default=0)
    analyzed_jobs    = db.Column(db.Integer, default=0)
    skills_snapshot  = db.Column(db.Text, default="")
    preferences_snapshot = db.Column(db.Text, default="{}")
    top_matches     = db.Column(db.Text, default="[]")

    def to_dict(self):
        return {
            "id":             self.id,
            "user_id":        self.user_id,
            "run_at":         self.run_at.isoformat() if self.run_at else None,
            "run_at_date":    self.run_at.strftime('%Y-%m-%d') if self.run_at else None,
            "run_at_time":    self.run_at.strftime('%H:%M:%S') if self.run_at else None,
            "avg_fit_score":  self.avg_fit_score,
            "total_jobs":     self.total_jobs,
            "analyzed_jobs":  self.analyzed_jobs,
            "skills_snapshot": self.skills_snapshot.split(",") if self.skills_snapshot else [],
            "preferences_snapshot": json.loads(self.preferences_snapshot or "{}"),
            "top_matches":    json.loads(self.top_matches or "[]"),
        }


class UserResume(db.Model):
    """사용자의 다중 이력서 관리 테이블 (1안)"""
    __tablename__ = "user_resumes"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    title      = db.Column(db.String(150), default="나의 이력서")
    content    = db.Column(db.Text, nullable=False)
    is_main    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "title":      self.title,
            "content":    self.content,
            "is_main":    self.is_main,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ResumeFeedback(db.Model):
    """AI 이력서 피드백 및 첨삭 결과 테이블 (2안)"""
    __tablename__ = "resume_feedbacks"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    resume_hint  = db.Column(db.String(100))
    ai_advice    = db.Column(db.Text, nullable=False)
    strengths    = db.Column(db.Text, default="")
    weaknesses   = db.Column(db.Text, default="")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "resume_hint":  self.resume_hint,
            "ai_advice":    self.ai_advice,
            "strengths":    self.strengths.split(",") if self.strengths else [],
            "weaknesses":   self.weaknesses.split(",") if self.weaknesses else [],
            "created_at":   self.created_at.isoformat() if self.created_at else None
        }


# 🆕 타인/합격자 이력서 보관용 신규 테이블 추가
class ComparisonResume(db.Model):
    """비교용 경쟁자 또는 합격자 이력서 테이블"""
    __tablename__ = "comparison_resumes"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    
    label       = db.Column(db.String(100), nullable=False)  # 예: "네이버 합격자 이력서", "상위 10% 개발자 표본"
    target_name = db.Column(db.String(50), default="익명 구직자")
    content     = db.Column(db.Text, nullable=False)         # 비교 대상의 이력서 본문 줄글
    skills      = db.Column(db.Text, default="")            # 해당 이력서에서 추출한 스킬셋 (콤마 구분)
    
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "user_id":     self.user_id,
            "label":       self.label,
            "target_name": self.target_name,
            "content":     self.content,
            "skills":      self.skills.split(",") if self.skills else [],
            "created_at":  self.created_at.isoformat() if self.created_at else None
        }


class CachedFeedback(db.Model):
    """기술 스택별 AI 피드백 캐시 테이블"""
    __tablename__ = "cached_feedbacks"

    id         = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), unique=True, nullable=False)
    feedback   = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "feedback": self.feedback,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }