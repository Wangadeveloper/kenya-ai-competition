import io
import markdown
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from markupsafe import Markup
from xhtml2pdf import pisa

from app.extensions import db
from app.models.sql_models import User, FarmPlan, LoanApplication, Post

# Required Graph Network and AI Intelligence Services
from app.services.ai_service import AIService
from app.services.neo4j_service import Neo4jService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('home.html')

@dashboard_bp.route('/dashboard')
@login_required
def index():
    """
    Role-Based Dashboard Switchboard Router leveraging Neo4j Graph Context.
    """
    # CASE A: Render Field Officer Core Portal
    if current_user.role == 'officer':
        # Retrieve regional telemetry matching the officer's regional assignments
        farmers_in_region = User.query.filter_by(role='farmer', county=current_user.county).all()
        
        # Pull latest loans across the officer's assigned county using your specific database relationship structure
        pending_loans = LoanApplication.query.join(User, LoanApplication.user_id == User.id)\
            .filter(User.county == current_user.county)\
            .order_by(LoanApplication.created_at.desc())\
            .limit(10).all()
        
        return render_template(
            'dashboard/officer_index.html',
            officer=current_user,
            farmers=farmers_in_region,
            loans=pending_loans
        )
        
    # CASE B: Render Traditional Farmer Personal Hub with Graph-Enriched Feed
    # Aligned with your backref 'applicant' or strict lookup structure
    loan_widget = LoanApplication.query.filter_by(user_id=current_user.id).order_by(LoanApplication.created_at.desc()).first()
    
    # ADVANCED GRAPH INTEGRATION: Extract contextual personalized feeds via Neo4j Graph
    feed_posts = []
    try:
        ns = Neo4jService()
        # Fall back cleanly to 'Maize' if current_user.primary_crop isn't specified
        farmer_crop = current_user.primary_crop or 'Maize'
        similar_peers = ns.get_similar_farmers(current_user.county, farmer_crop, current_user.phone_number)
        ns.close()
        
        if similar_peers:
            # Query relational posts whose authors match peer profiles in the localized network area
            peer_names = [peer['name'] for peer in similar_peers]
            feed_posts = Post.query.join(User).filter(
                User.full_name.in_(peer_names) | (User.county == current_user.county)
            ).order_by(Post.created_at.desc()).limit(5).all()
    except Exception:
        # Fail-soft fallback boundary to safeguard network uptime
        pass

    if not feed_posts:
        feed_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    market_snapshot = [
        {"crop": "Beans (Yellow Bean)", "price": "12,500 KES / Bag", "trend": "Up (+4%)"},
        {"crop": "Maize (White)", "price": "3,400 KES / Bag", "trend": "Down (-2%)"},
        {"crop": "Potatoes (Irish)", "price": "4,100 KES / Crate", "trend": "Stable"}
    ]
    
    return render_template(
        'dashboard/farmer_index.html', 
        farmer=current_user, 
        loan=loan_widget, 
        feed=feed_posts, 
        markets=market_snapshot
    )


# ... inside app/dashboard/routes.py ...

@dashboard_bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan_season():
    if request.method == 'POST':
        submitted_crop = request.form.get('crop_type') or current_user.primary_crop or 'Maize'
        submitted_budget = float(request.form.get('budget') or 0)
        
        ai_payload = {
            "crop_type": submitted_crop,
            "county": current_user.county,
            "farm_size": float(request.form.get('farm_size') or current_user.farm_size or 1.0),
            "budget": submitted_budget,
            "irrigation_type": request.form.get('irrigation_type') or current_user.water_source or 'Rain-fed',
            "expected_loan": float(request.form.get('expected_loan') or 0)
        }
        
        try:
            ns = Neo4jService()
            similar_peers = ns.get_similar_farmers(ai_payload['county'], ai_payload['crop_type'], current_user.phone_number)
            ns.close()
        except Exception:
            similar_peers = []
            
        ai = AIService()
        recommendation_text = ai.generate_farm_advisory(ai_payload, similar_peers)
        
        # 1. FIXED: Convert the raw Markdown string to clean, safe HTML strings here
        html_advisory = markdown.markdown(recommendation_text, extensions=['extra'])
        safe_html_advisory = Markup(html_advisory)
        
        current_year = datetime.utcnow().year
        new_plan = FarmPlan(
            user_id=current_user.id,
            season_name=f"Long Rains Season {current_year}",
            crop_to_plant=submitted_crop,
            estimated_budget=submitted_budget,
            ai_recommendations=recommendation_text  # Keep raw markdown stored in the database
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        flash('Seasonal farming strategy processed successfully.', 'success')
        
        # 2. FIXED: Pass the clean 'safe_html_advisory' down to your template variable context
        return render_template('loans/advisory.html', content=safe_html_advisory, plan=new_plan)

    return render_template('loans/apply.html', type='plan')

@dashboard_bp.route('/plan/download/<int:plan_id>')
@login_required
def download_pdf(plan_id):
    # 1. Fetch requested farming plan safely matching the authenticated login identifier
    plan = FarmPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    
    # 2. Parse raw Gemini Markdown advisory text using your model's exact 'ai_recommendations' field
    parsed_html_advisory = markdown.markdown(plan.ai_recommendations or "No advisory text found.", extensions=['extra'])
    
    # 3. Create a clean, structural layout template ready for print streaming
    pdf_html_layout = f"""
    <html>
    <head>
        <style>
            @page {{ size: letter; margin: 1in; }}
            body {{ font-family: Helvetica, Arial, sans-serif; color: #333333; line-height: 1.5; }}
            .header {{ border-bottom: 2px solid #059669; padding-bottom: 10px; margin-bottom: 20px; }}
            .title {{ font-size: 24px; font-weight: bold; color: #065f46; }}
            .meta {{ font-size: 12px; color: #666666; margin-bottom: 5px; }}
            h2 {{ font-size: 18px; color: #0f766e; margin-top: 15px; }}
            h3 {{ font-size: 14px; color: #111827; margin-top: 10px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 4px; }}
            strong {{ color: #065f46; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">AgriFinance Seasonal Farm Strategy ({plan.season_name})</div>
            <div class="meta">Mkulima: {current_user.full_name} | Simu: {current_user.phone_number}</div>
            <div class="meta">Eneo: {current_user.county} County | Ukubwa wa Shamba: {current_user.farm_size} Acres</div>
            <div class="meta">Zao Kuu: {plan.crop_to_plant} | Bajeti Imepangiwa: KES {plan.estimated_budget:,.2f}</div>
        </div>
        <div>
            {parsed_html_advisory}
        </div>
    </body>
    </html>
    """
    
    # 4. Stream compiled binary PDF back to user agent browser channels
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(pdf_html_layout, dest=pdf_buffer)
    
    if pisa_status.err:
        return "Mchakato wa PDF umeshindwa, tafadhali jaribu tena baada ya muda mfupi.", 500
        
    pdf_buffer.seek(0)
    
    return Response(
        pdf_buffer.getvalue(),
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment;filename=Mkakati_{plan.crop_to_plant}_{plan.id}.pdf"}
    )