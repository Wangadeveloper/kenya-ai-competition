from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse

from app.extensions import db
from app.models.sql_models import User, Sacco
from app.auth.forms import LoginForm, RegistrationForm

# Neo4j Service Instance Integration
from app.services.neo4j_service import Neo4jService

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
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dashboard.index')
            
        return redirect(next_page)
        
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Unified Account Creation Handler.
    Dynamically configures unique profile schemas for traditional farmers or 
    field officers, mapping SACCO cooperatives, and mirroring context telemetry 
    instantly to the Neo4j Graph database for down-stream GraphRAG processing.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        sacco_obj = None
        
        # Step 1: Dynamic SACCO/Cooperative Structural Intercept
        if form.role.data == 'farmer' and form.sacco_name.data:
            sacco_name_cleaned = form.sacco_name.data.strip()
            # Check if this Cooperative entity already exists within our relational tables
            sacco_obj = Sacco.query.filter_by(name=sacco_name_cleaned).first()
            if not sacco_obj:
                # Dynamically instantiate a new cooperative block matching the farmer's location context
                sacco_obj = Sacco(name=sacco_name_cleaned, county=form.county.data)
                db.session.add(sacco_obj)
                db.session.commit()

        # Step 2: Build the baseline shared telemetry user record instance
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            full_name=form.full_name.data,
            phone_number=form.phone_number.data.strip(),
            county=form.county.data,
            sub_county=form.sub_county.data,
            age=form.age.data,
            gender=form.gender.data,
            sacco_id=sacco_obj.id if sacco_obj else None
        )
        new_user.set_password(form.password.data)
        
        # Step 3: Inject role-specific tracking criteria context configurations
        if form.role.data == 'farmer':
            new_user.farm_size = form.farm_size.data or 0.0
            new_user.primary_crop = form.primary_crop.data or 'Maize'
            new_user.livestock_type = form.livestock_type.data or 'None'
            new_user.water_source = form.water_source.data or 'Rain-fed'
            new_user.credit_score = 710  # Initial platform baseline entry default rating
            
        elif form.role.data == 'officer':
            new_user.employee_id = form.employee_id.data
            new_user.organization = form.organization.data or 'Mercy Corps'
            new_user.assigned_region = f"{form.county.data} - {form.sub_county.data or 'All Zones'}"
            
        # Step 4: Commit and execute relational database transactional state write
        db.session.add(new_user)
        db.session.commit()
        
        # Step 5: Dual-Persistence State Serialization Hook into Neo4j Cluster Layer
        try:
            ns = Neo4jService()
            user_payload = {
                'id': new_user.id,
                'phone_number': new_user.phone_number,
                'full_name': new_user.full_name,
                'role': new_user.role,
                'age': new_user.age,
                'gender': new_user.gender,
                'credit_score': getattr(new_user, 'credit_score', 700),
                'farm_size': getattr(new_user, 'farm_size', 0.0),
                'water_source': getattr(new_user, 'water_source', 'Rain-fed'),
                'county': new_user.county,
                'sub_county': new_user.sub_county,
                'primary_crop': getattr(new_user, 'primary_crop', None),
                'sacco_name': sacco_obj.name if sacco_obj else None,
                'national_id': getattr(new_user, 'national_id', None),
                'ward': getattr(new_user, 'ward', None),
                'soil_type': getattr(new_user, 'soil_type', None),
                'irrigation_type': getattr(new_user, 'irrigation_type', None),
                'livestock_count': getattr(new_user, 'livestock_count', 0),
                'years_farming': getattr(new_user, 'years_farming', 0),
                'smartphone_owned': getattr(new_user, 'smartphone_owned', True),
                'literacy_level': getattr(new_user, 'literacy_level', None),
                'preferred_language': getattr(new_user, 'preferred_language', None),
                'organization': getattr(new_user, 'organization', 'Mercy Corps')
            }

            # Execute transactional Cypher MERGE logic safely
            ns.sync_user_node(user_payload)
            ns.close()
        except Exception as graph_err:
            # FAIL-SOFT SAFETY BOUNDARY: Catch cluster exceptions or network timeouts 
            # to prevent authentication thread locking if the graph cluster is offline.
            # Real-time telemetry sync will be reconciled via asynchronous tasks.
            pass
        
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