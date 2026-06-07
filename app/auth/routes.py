from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
# REMOVED: from werkzeug.urls import url_parse
from urllib.parse import urlparse  # ADDED: Modern Python native alternative

from app.extensions import db
from app.models.sql_models import User
from app.auth.forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Unified Login Controller for Farmers and Field Officers.
    Authenticates users via Username or Email and safely redirects them
    to their role-based dashboard switchboard or their originally requested URI.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        # Step 1: Look up user by matching either their raw username string or email handle
        user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.username.data)
        ).first()
        
        # Step 2: Fall back safely if the credentials fail hash verification match tests
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password configuration.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Step 3: Establish secure session cookie persistence parameters
        login_user(user, remember=form.remember_me.data)
        flash(f'Welcome back, {user.full_name}! Successfully authenticated.', 'success')
        
        # Step 4: Check if the user was intercepted by @login_required (Next URL handling)
        next_page = request.args.get('next')
        
        # Security validation check: Ensure the next page route path is relative 
        # (UPDATED to use Python's native urlparse)
        if not next_page or urlparse(next_page).netloc != '':
            # Hands off directly to the centralized role switchboard at dashboard_bp
            next_page = url_for('dashboard.index')
            
        return redirect(next_page)
        
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Unified Account Creation Handler.
    Dynamically configures unique profile schemas for traditional farmers or 
    field officers depending on the chosen context identification identity role form field.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        # Step 1: Build the baseline shared telemetry user record instance
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            full_name=form.full_name.data,
            phone_number=form.phone_number.data,
            county=form.county.data,
            sub_county=form.sub_county.data,
            age=form.age.data,
            gender=form.gender.data
        )
        new_user.set_password(form.password.data)
        
        # Step 2: Inject role-specific tracking criteria context configurations
        if form.role.data == 'farmer':
            new_user.farm_size = form.farm_size.data or 0.0
            new_user.primary_crop = form.primary_crop.data
            new_user.livestock_type = form.livestock_type.data or 'None'
            new_user.water_source = form.water_source.data
            new_user.credit_score = 710  # Initial platform baseline entry default rating
            
        elif form.role.data == 'officer':
            new_user.employee_id = form.employee_id.data
            # Set the operational coverage boundaries based on assigned home base entries
            new_user.assigned_region = f"{form.county.data} - {form.sub_county.data or 'All Zones'}"
            
        # Step 3: Commit and execute database tracking state update
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration completed successfully! Please log in to continue.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Platform Session Terminus endpoint.
    Safely purges runtime browser authorization tokens and falls back onto public domain home index.
    """
    logout_user()
    flash('You have logged out of the platform session safely.', 'success')
    return redirect(url_for('dashboard.home'))