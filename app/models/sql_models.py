from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), default='Farmer') # Farmer, FieldOfficer, Buyer, Institution
    county = db.Column(db.String(100), nullable=False)
    sub_county = db.Column(db.String(100), nullable=True)
    preferred_language = db.Column(db.String(20), default='Swahili')
    farm_size = db.Column(db.Float, nullable=True) # in Acres
    main_crop = db.Column(db.String(100), nullable=True)
    cooperative = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farm_plans = db.relationship('FarmPlan', backref='farmer', lazy=True)
    loans = db.relationship('LoanApplication', backref='farmer', lazy=True)
    posts = db.relationship('Post', backref='author', lazy=True)

class FarmPlan(db.Model):
    __tablename__ = 'farm_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    crop_type = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, nullable=False)
    farm_size = db.Column(db.Float, nullable=False)
    irrigation_type = db.Column(db.String(50), nullable=False)
    expected_loan = db.Column(db.Float, default=0.0)
    ai_recommendation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LoanApplication(db.Model):
    __tablename__ = 'loans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_amount = db.Column(db.Float, nullable=False)
    crop = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    expected_harvest = db.Column(db.Float, nullable=False) # Estimated yield in KG or bags
    repayment_period = db.Column(db.Integer, nullable=False) # in Months
    status = db.Column(db.String(30), default='Pending') # Pending, Approved, Risk_Reviewed, Denied
    ai_risk_score = db.Column(db.Integer, nullable=True) # Scale of 1-100
    ai_report = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    youtube_url = db.Column(db.String(256), nullable=True) # Videos or images URL
    video_summary = db.Column(db.Text, nullable=True) # Transcribed summary if video
    county_tag = db.Column(db.String(100), nullable=True)
    crop_tag = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


