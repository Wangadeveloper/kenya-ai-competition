from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Core Persona Routing System ('farmer', 'officer', or 'buyer')
    role = db.Column(db.String(20), nullable=False, default='farmer')
    
    # Shared Personal Telemetry
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    county = db.Column(db.String(50), nullable=False, default='')
    sub_county = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    
    # Shared Personal Telemetry Expansion
    national_id = db.Column(db.String(20), unique=True, nullable=True)
    ward = db.Column(db.String(50), nullable=True)
    
    # Farmer-Specific Attributes
    farm_size = db.Column(db.Float, nullable=True, default=0.0)
    primary_crop = db.Column(db.String(50), nullable=True, default='Maize')
    livestock_type = db.Column(db.String(50), nullable=True, default='None')
    water_source = db.Column(db.String(50), nullable=True, default='Rain-fed')
    credit_score = db.Column(db.Integer, nullable=False, default=700) 
    sacco_id = db.Column(db.Integer, db.ForeignKey('saccos.id'), nullable=True)
    
    # Farmer-Specific Attributes Expansion
    soil_type = db.Column(db.String(50), nullable=True, default='Clay loam')
    irrigation_type = db.Column(db.String(50), nullable=True, default='Rain-fed')
    livestock_count = db.Column(db.Integer, nullable=True, default=0)
    years_farming = db.Column(db.Integer, nullable=True, default=0)
    smartphone_owned = db.Column(db.Boolean, nullable=True, default=True)
    literacy_level = db.Column(db.String(50), nullable=True, default='Basic')
    preferred_language = db.Column(db.String(20), nullable=True, default='English')
    
    # Field Officer Specific Attributes
    employee_id = db.Column(db.String(50), unique=True, nullable=True)
    assigned_region = db.Column(db.String(100), nullable=True)
    organization = db.Column(db.String(100), nullable=True, default='Mercy Corps')
    
    # Buyer Specific Attributes
    buyer_organization = db.Column(db.String(150), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    plans = db.relationship('FarmPlan', backref='farmer', lazy='dynamic')
    loans = db.relationship('LoanApplication', backref='applicant', lazy='dynamic')
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    ledger_entries = db.relationship('FarmLedger', backref='farmer', lazy='dynamic')
    
    # Relationship tracking for Field Visits (Dual-perspective)
    visits_received = db.relationship('FieldVisit', foreign_keys='FieldVisit.farmer_id', backref='farmer', lazy='dynamic')
    visits_conducted = db.relationship('FieldVisit', foreign_keys='FieldVisit.officer_id', backref='officer', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Sacco(db.Model):
    __tablename__ = 'saccos'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    county = db.Column(db.String(50), nullable=False)
    members = db.relationship('User', backref='sacco', lazy='dynamic')


class FarmPlan(db.Model):
    __tablename__ = 'farm_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    season_name = db.Column(db.String(100), nullable=False)
    crop_to_plant = db.Column(db.String(50), nullable=False)
    estimated_budget = db.Column(db.Float, default=0.0)
    expected_yield_kg = db.Column(db.Float, nullable=True, default=0.0)
    ai_recommendations = db.Column(db.Text, nullable=True)
    
    # EU Compliance Export Fields
    is_export_oriented = db.Column(db.Boolean, nullable=False, default=False)
    target_market = db.Column(db.String(50), nullable=True, default='Local')  # e.g. 'EU', 'Local', 'Regional'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LoanApplication(db.Model):
    __tablename__ = 'loan_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending') 
    repayment_term_months = db.Column(db.Integer, default=6)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FieldVisit(db.Model):
    __tablename__ = 'field_visits'
    
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    gps_coordinates = db.Column(db.String(100), nullable=True)
    crop_health_status = db.Column(db.String(50), nullable=False) # e.g., 'Healthy', 'Pest Outbreak', 'Nutrient Deficient'
    notes_summary = db.Column(db.Text, nullable=False)
    recommended_action = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MarketInsight(db.Model):
    __tablename__ = 'market_insights'
    
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(50), nullable=False, index=True)
    market_location = db.Column(db.String(100), nullable=False) # e.g., 'Chwele Market'
    current_price_per_kg = db.Column(db.Float, nullable=False)
    price_trend = db.Column(db.String(20), default='Stable') # 'Rising', 'Falling', 'Stable'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def content(self):
        text = self.body
        if "--- YouTube URL ---" in text:
            text = text.split("--- YouTube URL ---")[0]
        elif "--- AI Video Takeaways ---" in text:
            text = text.split("--- AI Video Takeaways ---")[0]
        return text.strip()

    @property
    def crop_tag(self):
        if self.title and "Advisory regarding #" in self.title:
            tag = self.title.split("Advisory regarding #")[1].strip()
            return tag if tag else None
        return None

    @property
    def county_tag(self):
        return self.author.county if self.author else "Kakamega"

    @property
    def youtube_url(self):
        if "--- YouTube URL ---" in self.body:
            parts = self.body.split("--- YouTube URL ---")
            subparts = parts[1].split("--- AI Video Takeaways ---")
            return subparts[0].strip()
        return None

    @property
    def video_summary(self):
        if "--- AI Video Takeaways ---" in self.body:
            return self.body.split("--- AI Video Takeaways ---")[1].strip()
        return None


class FarmLedger(db.Model):
    __tablename__ = 'farm_ledgers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    record_type = db.Column(db.String(20), nullable=False) # 'income' or 'expense'
    category = db.Column(db.String(50), nullable=False) # e.g. Seeds, Fertilizer, Labor, Harvest Sale
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    
    # EU Compliance Traceability Audit Field
    # Applied automatically when category is a chemical input (Fertilizer, Pesticide, Herbicide)
    # Values: 'Unverified' (default), 'Safe' (AI screened, passed), 'Flagged' (AI screened, failed EU check)
    compliance_status = db.Column(db.String(20), nullable=False, default='Unverified')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    commenter = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    post = db.relationship('Post', backref=db.backref('comments_list', lazy='dynamic'))


class Repayment(db.Model):
    __tablename__ = 'repayments'
    
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    repayment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='Completed') # 'Completed', 'Failed', 'Pending'

    loan = db.relationship('LoanApplication', backref=db.backref('repayments', lazy='dynamic'))


class CropYield(db.Model):
    __tablename__ = 'crop_yields'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    crop_name = db.Column(db.String(50), nullable=False)
    season_name = db.Column(db.String(100), nullable=False)
    acreage = db.Column(db.Float, default=1.0)
    yield_kg = db.Column(db.Float, default=0.0)
    revenue = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farmer = db.relationship('User', backref=db.backref('yields', lazy='dynamic'))


class ExtensionGuide(db.Model):
    __tablename__ = 'extension_guides'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=True) # Will store list of floats (embedding vector)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)