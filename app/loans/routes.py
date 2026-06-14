from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sql_models import LoanApplication
from app.services.ai_service import AIService
from app.services.neo4j_service import Neo4jService
from app.services.notification_service import NotificationService

loans_bp = Blueprint('loans', __name__)

@loans_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            crop = request.form.get('crop', current_user.primary_crop or 'Maize')
            purpose = request.form.get('purpose', 'Farm Inputs Acquisition')
            term_months = int(request.form.get('period', 6))
            
            if amount <= 0:
                flash('Please enter a valid financing request amount.', 'danger')
                return redirect(url_for('loans.apply_loan'))
                
        except ValueError:
            flash('Invalid numerical data submitted for evaluation fields.', 'danger')
            return redirect(url_for('loans.apply_loan'))
        
        loan_payload = {'requested_amount': amount, 'crop': crop, 'purpose': purpose, 'repayment_period': term_months}
        
        # Pull active outbreaks in county
        regional_alerts = 0
        try:
            ns = Neo4jService()
            regional_alerts = ns.get_regional_outbreak_risk(current_user.county, crop)
            ns.close()
        except Exception:
            pass

        # Trigger dynamic credit risk assessment logic via Gemini
        ai = AIService()
        risk_score, assigned_status, justification = ai.evaluate_loan_risk(loan_payload, current_user, regional_alerts)
        
        # Persist into SQL Layer
        new_loan = LoanApplication(
            user_id=current_user.id,
            amount=amount,
            purpose=f"[{crop}] {purpose} | AI note: {justification} (Risk: {risk_score}/100)",
            status=assigned_status,
            repayment_term_months=term_months
        )
        db.session.add(new_loan)
        db.session.commit()
        
        # Mirror inside Neo4j Graph
        try:
            ns = Neo4jService()
            ns.track_loan_issuance(current_user.phone_number, f"L-{new_loan.id}", amount, purpose, assigned_status)
            ns.close()
        except Exception:
            pass
            
        # Dispatch SMS
        sms_payload = f"Habari {current_user.full_name}, loan request KES {amount:,.2f} is {assigned_status}. Risk index: {risk_score}/100."
        try:
            NotificationService.send_sms_via_africastalking(current_user.phone_number, sms_payload)
        except Exception:
            pass
            
        flash(f"Financing request processed with status verdict: {assigned_status}.", 'success' if assigned_status == 'Approved' else 'info')
        return redirect(url_for('dashboard.index'))
        
    return render_template('loans/apply.html', type='loan')