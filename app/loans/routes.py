from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sql_models import LoanApplication
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService

loans_bp = Blueprint('loans', __name__)

@loans_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            crop = request.form.get('crop', 'Maize')
            purpose = request.form.get('purpose', 'Farm Inputs Acquisition')
            
            if amount <= 0:
                flash('Please enter a valid financing request amount.', 'danger')
                return redirect(url_for('loans.apply_loan'))
                
        except ValueError:
            flash('Invalid numerical data submitted for evaluation fields.', 'danger')
            return redirect(url_for('loans.apply_loan'))
        
        # 1. COMPUTE SYSTEM CREDIT METRICS EVALUATION
        # Standardize baseline credit risk parameters against the user's database telemetry
        baseline_score = getattr(current_user, 'credit_score', 700)
        
        if baseline_score >= 700:
            assigned_status = 'Approved'
            risk_label = "Maboresho Chini (Low Risk Profile)"
        elif baseline_score >= 600:
            assigned_status = 'Pending'
            risk_label = "Maboresho ya Kati (Moderate Risk Review Required)"
        else:
            assigned_status = 'Rejected'
            risk_label = "Maboresho ya Juu (High Operational Risk Deficit)"
        
        # 2. PERSIST APPLICATION INTO SQL DATABASE MODEL
        new_loan = LoanApplication(
            user_id=current_user.id,
            amount=amount,
            purpose=f"[{crop}] {purpose} - Risk Evaluation Verdict: {risk_label}",
            status=assigned_status
        )
        db.session.add(new_loan)
        db.session.commit()
        
        # 3. DISPATCH LOW-BANDWIDTH NOTIFICATION CHANNEL
        sms_msg = (
            f"Habari {current_user.full_name}, Loan request for KES {amount:,.2f} "
            f"has been submitted. Assessment Status: {assigned_status}. "
            f"Profile score: {baseline_score}/850."
        )
        try:
            NotificationService.send_sms_via_africastalking(current_user.phone_number, sms_msg)
        except Exception as notification_err:
            pass # Avoid interrupting the controller flow if an out-of-band gateway logs a timeout
        
        if assigned_status == 'Approved':
            flash(f"Financing verified and approved! KES {amount:,.2f} provisioned successfully.", 'success')
        elif assigned_status == 'Pending':
            flash("Application is currently under verification processing review by SACCO field officers.", 'info')
        else:
            flash("Financing request could not be processed automatically due to system credit rating thresholds.", 'danger')
            
        return redirect(url_for('dashboard.index'))
        
    return render_template('loans/apply.html', type='loan')