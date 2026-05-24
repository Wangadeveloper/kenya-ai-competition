from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from app.extensions import db
from app.models.sql_models import User
from app.auth.forms import RegistrationForm
from app.services.neo4j_service import Neo4jService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(phone_number=form.phone_number.data).first()
        if existing:
            flash('Phone number registered under another profile.', 'danger')
            return render_template('auth/register.html', form=form)
        
        hashed = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(
            full_name=form.full_name.data,
            phone_number=form.phone_number.data,
            password_hash=hashed,
            county=form.county.data,
            cooperative=form.cooperative.data,
            farm_size=form.farm_size.data,
            main_crop=form.main_crop.data,
            role='Farmer'
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Hydrate Graph Pipeline Instance Async/Sync
        try:
            ns = Neo4jService()
            ns.create_farmer_node(
                user_id=new_user.id,
                name=new_user.full_name,
                county=new_user.county,
                cooperative=new_user.cooperative,
                main_crop=new_user.main_crop
            )
            ns.close()
        except Exception as e:
            print(f"Graph pipeline out of sync sync error: {e}")

        flash('Account created! Proceed to Login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone_number')
        password = request.form.get('password')
        user = User.query.filter_by(phone_number=phone).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard.index'))
        flash('Invalid credentials. Check connection details and retry.', 'danger')
    return render_template('auth/register.html', form=None) # Shared UI View layout

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))