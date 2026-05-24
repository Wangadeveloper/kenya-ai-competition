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
        loan_data = {
            'requested_amount': float(request.form.get('amount')),
            'crop': request.form.get('crop'),
            'purpose': request.form.get('purpose'),
            'expected_harvest': float(request.form.get('harvest')),
            'repayment_period': int(request.form.get('period'))
        }
        
        # AI evaluation logic integration run
        ai = AIService()
        risk_score, summary_report = ai.evaluate_loan_risk(loan_data, current_user)
        
        new_loan = LoanApplication(
            user_id=current_user.id,
            requested_amount=loan_data['requested_amount'],
            crop=loan_data['crop'],
            purpose=loan_data['purpose'],
            expected_harvest=loan_data['expected_harvest'],
            repayment_period=loan_data['repayment_period'],
            ai_risk_score=risk_score,
            ai_report=summary_report,
            status='Risk_Reviewed'
        )
        db.session.add(new_loan)
        db.session.commit()
        
        # Send transactional out-of-band updates using low-bandwidth architecture networks
        sms_msg = f"Habari {current_user.full_name}, Loan report for KES {new_loan.requested_amount} processed. AI Risk Score: {risk_score}/100. Verification summary sent to SACCO official."
        NotificationService.send_sms_via_africastalking(current_user.phone_number, sms_msg)
        
        flash('Financing assessment completed via credit intelligence matrix.', 'success')
        return redirect(url_for('dashboard.index'))
        
    return render_template('loans/apply.html', type='loan')