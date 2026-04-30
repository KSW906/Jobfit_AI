from datetime import datetime
from extensions import db


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
    # 확장성: source 필드로 API 출처 구분
    # 현재: "remotive"
    # 추후: "saramin", "wanted" 등 추가 가능
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