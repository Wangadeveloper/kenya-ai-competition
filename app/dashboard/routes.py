from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sql_models import FarmPlan, LoanApplication, Post
from app.services.ai_service import AIService
from app.services.neo4j_service import Neo4jService

dashboard_bp = Blueprint('dashboard', __name__)
import markdown
from markupsafe import Markup
from app.dashboard.routes import dashboard_bp

@dashboard_bp.app_template_filter('render_markdown')
def render_markdown_filter(text):
    if not text:
        return ""
    html_content = markdown.markdown(text, extensions=['extra'])
    return Markup(html_content)

@dashboard_bp.route('/')
@login_required
def index():
    # Fetch user telemetry attributes
    loan_widget = LoanApplication.query.filter_by(user_id=current_user.id).order_by(LoanApplication.created_at.desc()).first()
    posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    # Simple static sample feed for regional pricing trends lookup
    market_snapshot = [
        {"crop": "Beans (Yellow Bean)", "price": "12,500 KES / Bag", "trend": "Up (+4%)"},
        {"crop": "Maize (White)", "price": "3,400 KES / Bag", "trend": "Down (-2%)"},
        {"crop": "Potatoes (Irish)", "price": "4,100 KES / Crate", "trend": "Stable"}
    ]
    
    return render_template(
        'dashboard/index.html', 
        user=current_user, 
        loan=loan_widget, 
        feed=posts, 
        markets=market_snapshot
    )

@dashboard_bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan_season():
    if request.method == 'POST':
        data = {
            "crop_type": request.form.get('crop_type'),
            "county": current_user.county,
            "farm_size": float(request.form.get('farm_size', current_user.farm_size)),
            "budget": float(request.form.get('budget')),
            "irrigation_type": request.form.get('irrigation_type'),
            "expected_loan": float(request.form.get('expected_loan', 0))
        }
        
        # 1. Fetch data from Neo4j Social Graph network context
        try:
            ns = Neo4jService()
            similar_peers = ns.get_similar_farmers(data['county'], data['crop_type'], current_user.id)
            ns.close()
        except Exception:
            similar_peers = []
            
        # 2. Extract synthesized inference response using Gemini Architecture Engine
        ai = AIService()
        recommendation_text = ai.generate_farm_advisory(data, similar_peers)
        
        # Save structural tracking state
        new_plan = FarmPlan(
            user_id=current_user.id,
            crop_type=data['crop_type'],
            budget=data['budget'],
            farm_size=data['farm_size'],
            irrigation_type=data['irrigation_type'],
            expected_loan=data['expected_loan'],
            ai_recommendation=recommendation_text
        )
        db.session.add(new_plan)
        db.session.commit()
        
        flash('Seasonal farming strategy processed successfully.', 'success')
        return render_template('loans/advisory.html', content=recommendation_text, plan=new_plan)

    return render_template('loans/apply.html', type='plan')

from flask import Response
from xhtml2pdf import pisa
import io
import markdown # Imported to parse markdown structure before making the PDF

# ... keep your existing index() and plan_season() routes exactly as they are ...

@dashboard_bp.route('/plan/download/<int:plan_id>')
@login_required
def download_pdf(plan_id):
    # 1. Fetch the requested farming plan safely
    plan = FarmPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    
    # 2. Parse raw Gemini Markdown recommendation into structured HTML strings
    parsed_html_advisory = markdown.markdown(plan.ai_recommendation, extensions=['extra'])
    
    # 3. Create a clean, structural layout template specifically for printing
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
            <div class="title">AgriFinance Seasonal Farm Strategy</div>
            <div class="meta">Mkulima: {current_user.full_name} | Simu: {current_user.phone_number}</div>
            <div class="meta">Eneo: {current_user.county} County | Ukubwa wa Shamba: {plan.farm_size} Acres</div>
            <div class="meta">Zao Kuu: {plan.crop_type} | Bajeti Imepangiwa: KES {plan.budget:,.2f}</div>
        </div>
        <div>
            {parsed_html_advisory}
        </div>
    </body>
    </html>
    """
    
    # 4. Stream the compiled PDF binary back to the client browser agent
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(pdf_html_layout, dest=pdf_buffer)
    
    if pisa_status.err:
        return "Mchakato wa PDF umeshindwa, tafadhali jaribu tena baada ya muda mfupi.", 500
        
    pdf_buffer.seek(0)
    
    return Response(
        pdf_buffer.getvalue(),
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment;filename=Mkakati_Msimu_Plan_{plan.id}.pdf"}
    )