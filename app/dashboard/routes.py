
import io
import markdown
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from markupsafe import Markup
from xhtml2pdf import pisa

from app.extensions import db
from app.models.sql_models import User, FarmPlan, LoanApplication, Post, FieldVisit, Sacco, FarmLedger, CropYield
from app.services.ai_service import AIService
from app.services.neo4j_service import Neo4jService
from app.services.notification_service import NotificationService
from app.services.weather_service import WeatherService

# Chemical input categories that trigger automatic EU compliance screening
CHEMICAL_INPUT_CATEGORIES = {'Fertilizer', 'Pesticide', 'Herbicide', 'Fungicide', 'Chemical Input'}


dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('home.html')

@dashboard_bp.route('/dashboard')
@login_required
def index():
    if current_user.role == 'officer':
        farmers_in_region = User.query.filter_by(role='farmer', county=current_user.county).all()
        pending_loans = LoanApplication.query.join(User, LoanApplication.user_id == User.id)\
            .filter(User.county == current_user.county)\
            .order_by(LoanApplication.created_at.desc()).limit(10).all()
        
        return render_template('dashboard/officer_index.html', officer=current_user, farmers=farmers_in_region, loans=pending_loans)
        
    loan_widget = LoanApplication.query.filter_by(user_id=current_user.id).order_by(LoanApplication.created_at.desc()).first()
    feed_posts = []
    
    try:
        ns = Neo4jService()
        farmer_crop = current_user.primary_crop or 'Maize'
        similar_peers = ns.get_similar_farmers(current_user.county, farmer_crop, current_user.phone_number)
        ns.close()
        
        if similar_peers:
            peer_names = [peer['name'] for peer in similar_peers]
            feed_posts = Post.query.join(User).filter(
                User.full_name.in_(peer_names) | (User.county == current_user.county)
            ).order_by(Post.created_at.desc()).limit(5).all()
    except Exception as e:
        print(f"Dashboard Neo4j Feed Error: {e}")

    if not feed_posts:
        feed_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    market_snapshot = [
        {"crop": "Beans (Yellow)", "price": "12,500 KES / Bag", "trend": "Up (+4%)"},
        {"crop": "Maize (White)", "price": "3,400 KES / Bag", "trend": "Down (-2%)"},
        {"crop": "Potatoes (Irish)", "price": "4,100 KES / Crate", "trend": "Stable"}
    ]
    
    # Retrieve farm ledger entries
    ledger_entries = FarmLedger.query.filter_by(user_id=current_user.id).order_by(FarmLedger.activity_date.desc(), FarmLedger.created_at.desc()).all()
    total_income = sum(e.amount for e in ledger_entries if e.record_type == 'income')
    total_expense = sum(e.amount for e in ledger_entries if e.record_type == 'expense')
    net_cashflow = total_income - total_expense
    
    # Retrieve localized weather forecast
    weather_info = WeatherService.get_forecast(current_user.county)
    
    return render_template(
        'dashboard/farmer_index.html', 
        farmer=current_user, 
        loan=loan_widget, 
        feed=feed_posts, 
        markets=market_snapshot,
        ledger=ledger_entries,
        total_income=total_income,
        total_expense=total_expense,
        net_cashflow=net_cashflow,
        weather=weather_info
    )


@dashboard_bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan_season():
    if request.method == 'POST':
        submitted_crop = request.form.get('crop_type') or current_user.primary_crop or 'Maize'
        submitted_budget = float(request.form.get('budget') or 0)
        
        ai_payload = {
            "crop_type": submitted_crop,
            "county": current_user.county,
            "sub_county": current_user.sub_county,
            "farm_size": float(request.form.get('farm_size') or getattr(current_user, 'farm_size', 1.0) or 1.0),
            "budget": submitted_budget,
            "irrigation_type": request.form.get('irrigation_type') or getattr(current_user, 'water_source', 'Rain-fed'),
            "expected_loan": float(request.form.get('expected_loan') or 0)
        }
        
        graph_context = None
        regional_alerts = 0
        try:
            ns = Neo4jService()
            graph_context = ns.search_graph_rag_context(current_user.phone_number)
            regional_alerts = ns.get_regional_outbreak_risk(current_user.county, submitted_crop)
            ns.close()
        except Exception as e:
            print(f"Neo4j Context Error in planning: {e}")
            
        ai = AIService()
        recommendation_text = ai.generate_farm_advisory(ai_payload, graph_context, regional_alerts)
        html_advisory = markdown.markdown(recommendation_text, extensions=['extra'])
        safe_html_advisory = Markup(html_advisory)
        
        new_plan = FarmPlan(
            user_id=current_user.id,
            season_name=f"Long Rains Season {datetime.utcnow().year}",
            crop_to_plant=submitted_crop,
            estimated_budget=submitted_budget,
            ai_recommendations=recommendation_text,
            is_export_oriented=request.form.get('is_export_oriented') == 'on',
            target_market=request.form.get('target_market', 'Local')
        )
        db.session.add(new_plan)
        db.session.commit()
        
        # If EU-oriented, register DESTINED_FOR graph edge
        target_market = request.form.get('target_market', 'Local')
        if target_market != 'Local':
            try:
                ns = Neo4jService()
                ns.link_crop_to_market(submitted_crop, target_market)
                ns.close()
            except Exception as e:
                print(f"Neo4j DESTINED_FOR Sync Error: {e}")
        
        flash('Seasonal farming strategy processed successfully.', 'success')
        return render_template('loans/advisory.html', content=safe_html_advisory, plan=new_plan)

    return render_template('loans/apply.html', type='plan')


@dashboard_bp.route('/officer/visit', methods=['POST'])
@login_required
def log_visit():
    """
    Dedicated controller route enabling field staff to enter crop condition audits.
    """
    if current_user.role != 'officer':
        flash('Access denied. Role restricted to official field staff identifiers.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    farmer_id = request.form.get('farmer_id')
    condition = request.form.get('crop_health_status') # 'Healthy', 'Pest Outbreak', etc.
    notes = request.form.get('notes_summary', '')
    action = request.form.get('recommended_action', '')
    gps = request.form.get('gps_coordinates', '')
    
    farmer_user = User.query.get_or_404(farmer_id)
    
    # Save Visit record inside SQL relational tables
    visit = FieldVisit(
        farmer_id=farmer_user.id,
        officer_id=current_user.id,
        gps_coordinates=gps,
        crop_health_status=condition,
        notes_summary=notes,
        recommended_action=action
    )
    db.session.add(visit)
    db.session.commit()
    
    # Sync structural temporal edge transitions into Neo4j
    try:
        ns = Neo4jService()
        ns.log_field_visit(
            officer_phone=current_user.phone_number,
            farmer_phone=farmer_user.phone_number,
            visit_id=visit.id,
            condition=condition,
            notes=notes,
            action=action,
            coordinates=gps
        )
        ns.close()
    except Exception as e:
        print(f"Neo4j Log Field Visit Sync Error: {e}")
        
    flash(f"Field visit metrics recorded successfully for {farmer_user.full_name}.", 'success')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/plan/download/<int:plan_id>')
@login_required
def download_pdf(plan_id):
    plan = FarmPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    parsed_html_advisory = markdown.markdown(plan.ai_recommendations or "No advisory text found.", extensions=['extra'])
    
    pdf_html_layout = f"""
    <html>
    <head><style>@page {{ size: letter; margin: 1in; }} body {{ font-family: Helvetica, sans-serif; color: #333; }}</style></head>
    <body>
        <h2>AgriNexus Seasonal Strategy ({plan.season_name})</h2>
        <p>Mkulima: {current_user.full_name} | Eneo: {current_user.county}</p>
        <hr/>
        <div>{parsed_html_advisory}</div>
    </body>
    </html>
    """
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(pdf_html_layout, dest=pdf_buffer)
    pdf_buffer.seek(0)
    return Response(pdf_buffer.getvalue(), mimetype='application/pdf', headers={"Content-Disposition": f"attachment;filename=Plan_{plan.id}.pdf"})


@dashboard_bp.route('/ledger/add', methods=['POST'])
@login_required
def add_ledger_entry():
    try:
        record_type = request.form.get('record_type') # 'income' or 'expense'
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '')
        
        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
            return redirect(url_for('dashboard.index'))

        # ----- EU Compliance Auto-Screening for Chemical Inputs -----
        compliance_status = 'Unverified'
        if category in CHEMICAL_INPUT_CATEGORIES:
            try:
                ai = AIService()
                # Use description as the text-based compliance signal
                query_text = description or category
                risk_level, flagged_substances, reason = ai.check_text_compliance(
                    query_text, target_crop=current_user.primary_crop or 'General'
                )
                if risk_level == 'High' or flagged_substances:
                    compliance_status = 'Flagged'
                    # Propagate to Neo4j Input graph
                    try:
                        ns = Neo4jService()
                        ns.log_input_purchase(
                            farmer_phone=current_user.phone_number,
                            input_name=query_text[:100],
                            manufacturer='Unknown',
                            batch='SMS-Logged',
                            compliance_status='Flagged'
                        )
                        ns.close()
                    except Exception as e:
                        print(f"Neo4j Input Compliance Sync Error: {e}")
                    # Alert farmer via SMS
                    try:
                        NotificationService.send_sms_via_africastalking(
                            current_user.phone_number,
                            f"AgriNexus EU ALERT: Input '{query_text[:40]}' flagged! {reason[:100]}"
                        )
                    except Exception:
                        pass
                elif risk_level == 'Low':
                    compliance_status = 'Safe'
            except Exception as e:
                print(f"Ledger Compliance Auto-Screen Error: {e}")
        # -----------------------------------------------------------
            
        new_entry = FarmLedger(
            user_id=current_user.id,
            record_type=record_type,
            category=category,
            amount=amount,
            description=description,
            compliance_status=compliance_status
        )
        db.session.add(new_entry)
        db.session.commit()
        
        # Dynamically evaluate the cashflow to adjust the credit score
        entries = FarmLedger.query.filter_by(user_id=current_user.id).all()
        total_income = sum(e.amount for e in entries if e.record_type == 'income')
        total_expense = sum(e.amount for e in entries if e.record_type == 'expense')
        net = total_income - total_expense
        
        new_score = current_user.credit_score
        if net > 50000:
            new_score = min(850, current_user.credit_score + 15)
        elif net < -10000:
            new_score = max(300, current_user.credit_score - 10)
            
        if new_score != current_user.credit_score:
            current_user.credit_score = new_score
            db.session.commit()
            
            # Sync to Neo4j
            try:
                ns = Neo4jService()
                user_payload = {
                    'id': current_user.id,
                    'phone_number': current_user.phone_number,
                    'full_name': current_user.full_name,
                    'role': current_user.role,
                    'age': getattr(current_user, 'age', None),
                    'gender': getattr(current_user, 'gender', None),
                    'credit_score': current_user.credit_score,
                    'farm_size': getattr(current_user, 'farm_size', 0.0),
                    'water_source': getattr(current_user, 'water_source', 'Rain-fed'),
                    'county': current_user.county,
                    'sub_county': current_user.sub_county,
                    'primary_crop': getattr(current_user, 'primary_crop', None),
                    'sacco_name': current_user.sacco.name if getattr(current_user, 'sacco', None) else None,
                    'national_id': getattr(current_user, 'national_id', None),
                    'ward': getattr(current_user, 'ward', None),
                    'soil_type': getattr(current_user, 'soil_type', None),
                    'irrigation_type': getattr(current_user, 'irrigation_type', None),
                    'livestock_count': getattr(current_user, 'livestock_count', 0),
                    'years_farming': getattr(current_user, 'years_farming', 0),
                    'smartphone_owned': getattr(current_user, 'smartphone_owned', True),
                    'literacy_level': getattr(current_user, 'literacy_level', None),
                    'preferred_language': getattr(current_user, 'preferred_language', None)
                }
                ns.sync_user_node(user_payload)
                ns.close()
            except Exception as e:
                print(f"Neo4j Ledger Credit Sync Error: {e}")

        status_note = f" (EU Compliance: {compliance_status})"
        flash(f'Farm ledger transaction recorded successfully!{status_note}', 'success')
    except Exception as e:
        flash(f'Error adding transaction: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard.index'))



@dashboard_bp.route('/ai-advisor/chat', methods=['POST'])
@login_required
def ai_advisor_chat():
    message = request.json.get('message', '').strip() if request.json else request.form.get('message', '').strip()
    if not message:
        return {"error": "Message is empty"}, 400
    
    try:
        # Include ledger summary inside prompt for AI advisor context
        ledger_text = "No recorded transactions."
        entries = FarmLedger.query.filter_by(user_id=current_user.id).all()
        if entries:
            total_income = sum(e.amount for e in entries if e.record_type == 'income')
            total_expense = sum(e.amount for e in entries if e.record_type == 'expense')
            recent = [f"{e.activity_date}: {e.record_type.upper()} of KES {e.amount} ({e.category})" for e in entries[:3]]
            ledger_text = f"Total Income: KES {total_income}, Total Expense: KES {total_expense}, Net Cashflow: KES {total_income - total_expense}. Recent: " + "; ".join(recent)

        prompt = f"""
        You are AgriNexus Co-Pilot, an interactive AI agricultural expert assisting Kenyan smallholder farmers.
        The farmer asking you questions is named {current_user.full_name}, growing {current_user.primary_crop or 'Maize'} in {current_user.county} County.
        Farmer's financial profile from farm ledger: {ledger_text}
        
        Farmer's query: "{message}"
        
        Keep your advice short (max 4 sentences), warm, extremely practical, and tailored to Kenya's climate and crops. Use Swahili/English mixed naturally.
        """
        ai = AIService()
        response = ai.model.generate_content(prompt)
        return {"response": response.text}
    except Exception as e:
        print(f"AI Advisor Chat Error: {e}")
        return {"response": "Habari! Mfumo wa ushauri una hitilafu kidogo kwa sasa. Tafadhali jaribu tena baada ya muda mfupi."}, 500


@dashboard_bp.route('/report-outbreak', methods=['POST'])
@login_required
def report_outbreak():
    if current_user.role != 'farmer':
        flash('Access denied. Only registered farmers can report outbreaks.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    crop_name = request.form.get('crop_name', current_user.primary_crop or 'Maize')
    file = request.files.get('outbreak_image')
    
    if not file or file.filename == '':
        flash('Please upload a valid image of the crop damage.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    try:
        image_bytes = file.read()
        mime_type = file.mimetype
        
        ai = AIService()
        pest_name, severity, recommendations = ai.analyze_pest_image(image_bytes, mime_type)
        
        # Sync to Neo4j Outbreak database
        ns = Neo4jService()
        ns.log_pest_disease_outbreak(
            farmer_phone=current_user.phone_number,
            name=pest_name,
            type="Pest",
            severity=severity
        )
        ns.close()
        
        flash(f"Ushauri wa AI: Aligundua {pest_name} (Kiwango: {severity}). Ushauri: {recommendations}", "success")
    except Exception as e:
        print(f"Outbreak Analytics Error: {e}")
        flash(f"Hitilafu ya uchambuzi wa picha: {str(e)}", "danger")
        
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/scan-input', methods=['POST'])
@login_required
def scan_input_compliance():
    """
    Multimodal EU compliance endpoint. Accepts a fertilizer/pesticide label image.
    Runs AI screening, stamps the result to the ledger entry, and propagates to Neo4j graph.
    """
    if current_user.role != 'farmer':
        flash('Access denied. Only registered farmers can scan inputs.', 'danger')
        return redirect(url_for('dashboard.index'))

    file = request.files.get('input_label_image')
    input_name = request.form.get('input_name', '').strip()
    manufacturer = request.form.get('manufacturer', 'Unknown').strip()
    batch = request.form.get('batch', 'N/A').strip()
    target_crop = request.form.get('target_crop', current_user.primary_crop or 'General')

    if not file or file.filename == '':
        flash('Please upload a label image of the input product.', 'danger')
        return redirect(url_for('dashboard.index'))

    try:
        image_bytes = file.read()
        mime_type = file.mimetype

        ai = AIService()
        risk_level, flagged_substances, reason, product_name = ai.screen_input_compliance(image_bytes, mime_type, target_crop)

        if not input_name:
            input_name = product_name or 'Unknown Input'

        compliance_status = 'Flagged' if (risk_level in ['High', 'Medium'] or flagged_substances) else 'Safe'

        # Save to SQLite FarmLedger
        try:
            new_entry = FarmLedger(
                user_id=current_user.id,
                record_type='expense',
                category='Fertilizer',
                amount=0.0,
                description=f"AI Scan: {input_name}",
                compliance_status=compliance_status
            )
            db.session.add(new_entry)
            db.session.commit()
        except Exception as e:
            print(f"Failed to save scan to FarmLedger: {e}")

        # Sync Input node into Neo4j compliance graph
        try:
            ns = Neo4jService()
            ns.log_input_purchase(
                farmer_phone=current_user.phone_number,
                input_name=input_name,
                manufacturer=manufacturer,
                batch=batch,
                compliance_status=compliance_status
            )
            # If flagged, find and alert exposed peers in the same cluster
            if compliance_status == 'Flagged':
                exposed_peers = ns.get_compliance_exposed_peers(
                    current_user.county, current_user.primary_crop or 'Maize', current_user.phone_number
                )
                for peer in exposed_peers:
                    alert_msg = (
                        f"AgriNexus EU ALERT: Fertilizer/pesticide '{input_name}' in your cluster has been "
                        f"flagged as EU non-compliant. Risk: {risk_level}. Check your inputs before harvest."
                    )
                    try:
                        NotificationService.send_sms_via_africastalking(peer['phone_number'], alert_msg)
                    except Exception:
                        pass
            ns.close()
        except Exception as e:
            print(f"Neo4j Input Scan Sync Error: {e}")

        # Notify farmer via SMS if flagged
        if compliance_status == 'Flagged':
            flagged_list = ", ".join(flagged_substances) if flagged_substances else "substances detected"
            try:
                NotificationService.send_sms_via_africastalking(
                    current_user.phone_number,
                    f"AgriNexus EU SCAN: '{input_name}' FLAGGED! Substances: {flagged_list[:60]}. {reason[:80]}"
                )
            except Exception:
                pass
            flash(
                f"⚠️ EU Compliance FLAGGED for '{input_name}': {reason} Flagged substances: {', '.join(flagged_substances) or 'See details'}.",
                'danger'
            )
        else:
            flash(f"✅ EU Compliance SAFE for '{input_name}': {reason}", 'success')

    except Exception as e:
        print(f"Input Label Scan Error: {e}")
        flash(f'Label scan error: {str(e)}', 'danger')

    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/officer/register_farmer', methods=['POST'])
@login_required
def officer_register_farmer():
    if current_user.role != 'officer':
        flash('Access denied. Officers only.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    phone_number = request.form.get('phone_number')
    county = request.form.get('county')
    sub_county = request.form.get('sub_county')
    ward = request.form.get('ward')
    national_id = request.form.get('national_id')
    primary_crop = request.form.get('primary_crop')
    farm_size = float(request.form.get('farm_size') or 1.0)
    soil_type = request.form.get('soil_type', 'Clay loam')
    irrigation_type = request.form.get('irrigation_type', 'Rain-fed')
    sacco_name = request.form.get('sacco_name')

    # Simple validations
    if User.query.filter_by(username=username).first():
        flash('Username is already taken.', 'danger')
        return redirect(url_for('dashboard.index'))
    if User.query.filter_by(phone_number=phone_number).first():
        flash('Phone number is already associated with an account.', 'danger')
        return redirect(url_for('dashboard.index'))

    sacco_obj = None
    if sacco_name and sacco_name.strip():
        cleaned_sacco_name = sacco_name.strip()
        sacco_obj = Sacco.query.filter_by(name=cleaned_sacco_name).first()
        if not sacco_obj:
            sacco_obj = Sacco(name=cleaned_sacco_name, county=county)
            db.session.add(sacco_obj)
            db.session.commit()

    new_farmer = User(
        username=username,
        email=email,
        role='farmer',
        full_name=full_name,
        phone_number=phone_number,
        county=county,
        sub_county=sub_county,
        ward=ward,
        national_id=national_id,
        primary_crop=primary_crop,
        farm_size=farm_size,
        soil_type=soil_type,
        irrigation_type=irrigation_type,
        credit_score=710,
        sacco_id=sacco_obj.id if sacco_obj else None
    )
    new_farmer.set_password("Password123")
    db.session.add(new_farmer)
    db.session.commit()

    # Sync user to Neo4j
    try:
        ns = Neo4jService()
        user_payload = {
            'id': new_farmer.id,
            'phone_number': new_farmer.phone_number,
            'full_name': new_farmer.full_name,
            'role': new_farmer.role,
            'age': getattr(new_farmer, 'age', None),
            'gender': getattr(new_farmer, 'gender', None),
            'credit_score': new_farmer.credit_score,
            'farm_size': new_farmer.farm_size,
            'water_source': irrigation_type,  # Map fallback field dynamically
            'county': new_farmer.county,
            'sub_county': new_farmer.sub_county,
            'primary_crop': new_farmer.primary_crop,
            'sacco_name': sacco_obj.name if sacco_obj else None,
            'national_id': new_farmer.national_id,
            'ward': new_farmer.ward,
            'soil_type': new_farmer.soil_type,
            'irrigation_type': new_farmer.irrigation_type,
            'smartphone_owned': True,
            'literacy_level': 'Basic',
            'preferred_language': 'English'
        }
        ns.sync_user_node(user_payload)
        ns.close()
    except Exception as e:
        print(f"Neo4j Farmer Registration Sync Failure: {e}")

    flash(f"Farmer {full_name} registered successfully!", "success")
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/officer/upload_yield', methods=['POST'])
@login_required
def officer_upload_yield():
    if current_user.role != 'officer':
        flash('Access denied. Officers only.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    farmer_id = int(request.form.get('farmer_id'))
    crop_name = request.form.get('crop_name')
    season_name = request.form.get('season_name')
    acreage = float(request.form.get('acreage') or 1.0)
    yield_kg = float(request.form.get('yield_kg') or 0.0)
    revenue = float(request.form.get('revenue') or 0.0)

    farmer = User.query.get_or_404(farmer_id)
    
    new_yield = CropYield(
        user_id=farmer.id,
        crop_name=crop_name,
        season_name=season_name,
        acreage=acreage,
        yield_kg=yield_kg,
        revenue=revenue
    )
    db.session.add(new_yield)
    db.session.commit()

    flash(f"Crop yield data uploaded successfully for farmer {farmer.full_name}.", "success")
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/officer/copilot/<int:farmer_id>')
@login_required
def officer_copilot(farmer_id):
    if current_user.role != 'officer':
        return {"error": "Unauthorized"}, 403
        
    farmer = User.query.get_or_404(farmer_id)
    
    # Compile history
    components_visits = FieldVisit.query.filter_by(farmer_id=farmer.id).order_by(FieldVisit.created_at.desc()).limit(3).all()
    visits_text = "; ".join([f"{v.created_at.strftime('%Y-%m-%d')}: {v.crop_health_status} ({v.recommended_action or 'No recommendation'})" for v in components_visits]) or "No visits logged yet."
    
    components_yields = CropYield.query.filter_by(user_id=farmer.id).order_by(CropYield.created_at.desc()).limit(3).all()
    yields_text = "; ".join([f"{y.season_name}: {y.crop_name} harvested {y.yield_kg}kg, revenue KES {y.revenue}" for y in components_yields]) or "No yield records uploaded."

    prompt = f"""
    You are AgriNexus Co-Pilot, an AI field advisor. Compile a pre-visit briefing dossier for a farmer:
    - Name: {farmer.full_name}
    - Location: {farmer.county} County, {farmer.sub_county} Sub-county, Ward: {getattr(farmer, 'ward', 'N/A')}
    - Soil: {getattr(farmer, 'soil_type', 'Clay Loam')} | Irrigation: {getattr(farmer, 'irrigation_type', 'Rain-fed')} | Years Farming: {getattr(farmer, 'years_farming', 0)}
    - Credit Score Baseline: {farmer.credit_score} / 850
    - Farm Visits History: {visits_text}
    - Yield Records: {yields_text}
    
    Provide exactly 3 sentences summarizing:
    1. The farmer's operational history and credit rating tier.
    2. Key findings from recent visits and yields.
    3. The recommended focus area for the upcoming visit (e.g. soil treatment, pest control, or credit extension).
    
    Keep it in clear Swahili/English mixed naturally, practical, and flat text.
    """
    try:
        ai = AIService()
        response = ai.model.generate_content(prompt)
        return {"dossier": response.text.strip()}
    except Exception as e:
        print(f"Officer Copilot Intelligence Generation Error: {e}")
        return {"dossier": f"Hitilafu wakati wa kutoa ripoti: {str(e)}"}, 500
