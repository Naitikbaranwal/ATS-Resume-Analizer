from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    resumes = db.relationship('Resume', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    analyses = db.relationship('Analysis', backref='resume', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def latest_analysis(self):
        return self.analyses.order_by(Analysis.created_at.desc()).first()

    def __repr__(self):
        return f'<Resume {self.original_filename}>'


class Analysis(db.Model):
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    overall_score = db.Column(db.Integer, nullable=False) # 0 to 100
    skills_score = db.Column(db.Integer, nullable=False)  # 0 to 100
    ats_score = db.Column(db.Integer, nullable=False)     # 0 to 100
    
    matched_skills_json = db.Column(db.Text, nullable=False, default='[]')
    missing_skills_json = db.Column(db.Text, nullable=False, default='[]')
    formatting_feedback_json = db.Column(db.Text, nullable=False, default='[]')
    
    # Gemini AI columns
    ai_suggestions_json = db.Column(db.Text, nullable=True, default='[]')
    cover_letter = db.Column(db.Text, nullable=True)
    job_fit_analysis = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def ai_suggestions(self):
        return json.loads(self.ai_suggestions_json or '[]')

    @ai_suggestions.setter
    def ai_suggestions(self, value):
        self.ai_suggestions_json = json.dumps(value)

    @property
    def matched_skills(self):
        return json.loads(self.matched_skills_json or '[]')

    @matched_skills.setter
    def matched_skills(self, value):
        self.matched_skills_json = json.dumps(value)

    @property
    def missing_skills(self):
        return json.loads(self.missing_skills_json or '[]')

    @missing_skills.setter
    def missing_skills(self, value):
        self.missing_skills_json = json.dumps(value)

    @property
    def formatting_feedback(self):
        return json.loads(self.formatting_feedback_json or '[]')

    @formatting_feedback.setter
    def formatting_feedback(self, value):
        self.formatting_feedback_json = json.dumps(value)

    def __repr__(self):
        return f'<Analysis {self.job_title} Score={self.overall_score}>'
