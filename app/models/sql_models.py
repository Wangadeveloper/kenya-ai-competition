from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


from app.extensions import login_manager  # or wherever your LoginManager instance lives

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Core Persona Routing System
    # Values: 'farmer' or 'officer'
    role = db.Column(db.String(20), nullable=False, default='farmer')
    
    # Shared Personal Telemetry
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    county = db.Column(db.String(50), nullable=False, default='Kakamega')
    sub_county = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    
    # Farmer-Specific Attributes
    farm_size = db.Column(db.Float, nullable=True, default=0.0)
    primary_crop = db.Column(db.String(50), nullable=True, default='Maize')
    livestock_type = db.Column(db.String(50), nullable=True, default='None')
    water_source = db.Column(db.String(50), nullable=True, default='Rain-fed')
    credit_score = db.Column(db.Integer, nullable=False, default=700) # Out of 850
    
    # Field Officer Specific Attributes
    employee_id = db.Column(db.String(50), unique=True, nullable=True)
    assigned_region = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    plans = db.relationship('FarmPlan', backref='farmer', lazy='dynamic')
    loans = db.relationship('LoanApplication', backref='applicant', lazy='dynamic')
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ... Keep your existing User model code completely as it is here ...

class FarmPlan(db.Model):
    __tablename__ = 'farm_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    season_name = db.Column(db.String(100), nullable=False)
    crop_to_plant = db.Column(db.String(50), nullable=False)
    estimated_budget = db.Column(db.Float, default=0.0)
    ai_recommendations = db.Column(db.Text, nullable=True) # Stores Markdown generated advice
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FarmPlan {self.season_name} - {self.crop_to_plant}>"


class LoanApplication(db.Model):
    __tablename__ = 'loan_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)
    # Status values: 'Pending', 'Approved', 'Rejected'
    status = db.Column(db.String(20), nullable=False, default='Pending') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LoanApplication KES {self.amount} - {self.status}>"


class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Post {self.title}>"