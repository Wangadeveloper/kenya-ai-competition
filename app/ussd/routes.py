from flask import request, Response
from app.extensions import db
from app.models.sql_models import User, Sacco, MarketInsight, LoanApplication, FieldVisit
from app.services.ai_service import AIService
from app.services.neo4j_service import Neo4jService
from app.services.notification_service import NotificationService
from app.ussd import ussd_bp

@ussd_bp.route('/', methods=['POST'])
def ussd_gateway():
    """
    Main USSD gateway endpoint mimicking Africa's Talking protocol.
    Expects POST fields: sessionId, serviceCode, phoneNumber, text
    """
    session_id = request.form.get("sessionId")
    service_code = request.form.get("serviceCode")
    phone_number = request.form.get("phoneNumber", "").strip()
    text = request.form.get("text", "").strip()

    # Look up user by phone number
    user = User.query.filter_by(phone_number=phone_number).first()
    
    response = ""
    
    if not user:
        # ---------------- REGISTRATION FLOW ----------------
        parts = text.split('*') if text else []
        
        if not text:
            response = "CON Welcome to AgriNexus AI.\nYour phone is not registered.\n1. Register as Farmer"
        elif len(parts) == 1 and parts[0] == "1":
            response = "CON Enter your Full Name:"
        elif len(parts) == 2 and parts[0] == "1":
            response = "CON Enter your County:"
        elif len(parts) == 3 and parts[0] == "1":
            response = "CON Enter your Primary Crop (e.g. Maize, Beans, Coffee):"
        elif len(parts) == 4 and parts[0] == "1":
            name = parts[1].strip()
            county = parts[2].strip()
            crop = parts[3].strip()
            
            # Create farmer account
            sacco = Sacco.query.filter(Sacco.county.ilike(f"%{county}%")).first()
            new_user = User(
                username=f"user_{phone_number.replace('+', '')}",
                email=f"{phone_number.replace('+', '')}@agrinexus.co.ke",
                role="farmer",
                full_name=name,
                phone_number=phone_number,
                county=county,
                primary_crop=crop,
                sacco_id=sacco.id if sacco else None,
                credit_score=710
            )
            new_user.set_password("Password123")
            db.session.add(new_user)
            db.session.commit()
            
            # Sync user to Neo4j graph
            try:
                ns = Neo4jService()
                user_payload = {
                    'id': new_user.id,
                    'phone_number': new_user.phone_number,
                    'full_name': new_user.full_name,
                    'role': new_user.role,
                    'age': new_user.age,
                    'gender': new_user.gender,
                    'credit_score': new_user.credit_score,
                    'farm_size': new_user.farm_size,
                    'water_source': new_user.water_source,
                    'county': new_user.county,
                    'sub_county': new_user.sub_county,
                    'primary_crop': new_user.primary_crop,
                    'sacco_name': sacco.name if sacco else None
                }
                ns.sync_user_node(user_payload)
                ns.close()
            except Exception:
                pass
                
            response = "END Registration successful! Please redial USSD code to access services."
        else:
            response = "END Invalid selection. Try again."
            
    else:
        # ---------------- MAIN MENU FLOW ----------------
        parts = text.split('*') if text else []
        
        if not text:
            if user.role == 'officer':
                response = f"CON Welcome, Officer {user.full_name}\n1. Profile Details\n2. Check Credit\n3. Market Prices\n4. Apply Loan\n5. Log Visit"
            else:
                response = f"CON Welcome, Farmer {user.full_name}\n1. Profile Details\n2. Check Credit\n3. Market Prices\n4. Apply Loan"
                
        else:
            choice = parts[0]
            
            if choice == "1":
                # Option 1: Profile Details
                response = f"END Profile Details:\nName: {user.full_name}\nCounty: {user.county}\nRole: {user.role.upper()}\nCrop: {user.primary_crop or 'None'}"
                
            elif choice == "2":
                # Option 2: Check Credit
                response = f"END Credit Profile:\nScore: {user.credit_score}/850\nTier: {'Excellent' if user.credit_score >= 700 else 'Fair' if user.credit_score >= 600 else 'Poor'}"
                
            elif choice == "3":
                # Option 3: Market Prices
                insights = MarketInsight.query.all()
                price_list = []
                for ins in insights:
                    price_list.append(f"{ins.crop_name}: {ins.current_price_per_kg:,.0f} KES ({ins.price_trend})")
                response = "END Market Price Index:\n" + "\n".join(price_list)
                
            elif choice == "4":
                # Option 4: Apply Loan
                if len(parts) == 1:
                    response = "CON Enter loan amount in KES:"
                elif len(parts) == 2:
                    response = "CON Enter detailed loan purpose:"
                elif len(parts) >= 3:
                    try:
                        amount = float(parts[1])
                        purpose = parts[2]
                        if amount <= 0:
                            response = "END Amount must be greater than zero."
                        else:
                            # Evaluate risk dynamically using Gemini
                            ai = AIService()
                            ns = Neo4jService()
                            outbreaks = ns.get_regional_outbreak_risk(user.county, user.primary_crop or "Maize")
                            loan_data = {'requested_amount': amount, 'crop': user.primary_crop or 'Maize', 'purpose': purpose, 'repayment_period': 6}
                            risk_score, status, justification = ai.evaluate_loan_risk(loan_data, user, outbreaks)
                            
                            new_loan = LoanApplication(
                                user_id=user.id,
                                amount=amount,
                                purpose=f"[USSD] {purpose} | AI note: {justification[:100]}",
                                status=status,
                                repayment_term_months=6
                            )
                            db.session.add(new_loan)
                            db.session.commit()
                            
                            ns.track_loan_issuance(user.phone_number, f"L-{new_loan.id}", amount, purpose, status)
                            ns.close()
                            
                            # SMS notification
                            sms_payload = f"USSD ALERT: Loan KES {amount:,.2f} request status: {status}. Risk index: {risk_score}/100."
                            NotificationService.send_sms_via_africastalking(user.phone_number, sms_payload)
                            
                            response = f"END Loan submitted! Status: {status}.\nNote: {justification[:60]}..."
                    except ValueError:
                        response = "END Invalid numeric value for amount."
                    except Exception as e:
                        response = f"END System error: {str(e)[:50]}"
                        
            elif choice == "5" and user.role == 'officer':
                # Option 5: Log Visit (Officer Only)
                if len(parts) == 1:
                    response = "CON Enter farmer's phone number:"
                elif len(parts) == 2:
                    farmer_phone = parts[1].strip()
                    farmer = User.query.filter_by(phone_number=farmer_phone, role='farmer').first()
                    if not farmer:
                        response = "END Farmer with that phone number not found."
                    else:
                        response = "CON Crop Condition:\n1. Healthy\n2. Pest Outbreak\n3. Nutrient Deficient"
                elif len(parts) == 3:
                    response = "CON Enter recommended action:"
                elif len(parts) >= 4:
                    farmer_phone = parts[1].strip()
                    condition_choice = parts[2].strip()
                    action = parts[3].strip()
                    
                    conditions_map = {"1": "Healthy", "2": "Pest Outbreak", "3": "Nutrient Deficient"}
                    condition = conditions_map.get(condition_choice, "Healthy")
                    
                    farmer = User.query.filter_by(phone_number=farmer_phone, role='farmer').first()
                    visit = FieldVisit(
                        farmer_id=farmer.id,
                        officer_id=user.id,
                        crop_health_status=condition,
                        notes_summary=f"USSD Visit Log: Condition {condition}",
                        recommended_action=action
                    )
                    db.session.add(visit)
                    db.session.commit()
                    
                    try:
                        ns = Neo4jService()
                        ns.log_field_visit(user.phone_number, farmer.phone_number, visit.id, condition, "", action, "")
                        ns.close()
                    except Exception:
                        pass
                        
                    response = f"END Field visit recorded for {farmer.full_name}."
            else:
                response = "END Option not supported or restricted."

    return Response(response, mimetype='text/plain')


@ussd_bp.route('/sms', methods=['POST'])
def inbound_sms_gateway():
    """
    Inbound SMS gateway endpoint.
    Parses incoming messages with keywords: ADVISE, PRICE, REPORT
    """
    from_phone = request.form.get("from", "").strip()
    msg_text = request.form.get("text", "").strip()

    if not from_phone or not msg_text:
        return Response("Missing from or text", status=400)

    user = User.query.filter_by(phone_number=from_phone).first()
    if not user:
        # Fail-soft reply to unregistered number
        NotificationService.send_sms_via_africastalking(from_phone, "AgriNexus: Phone number not registered. Please dial our USSD code to sign up.")
        return Response("OK", status=200)

    parts = msg_text.split(maxsplit=1)
    keyword = parts[0].upper() if parts else ""
    argument = parts[1].strip() if len(parts) > 1 else ""

    reply = ""

    if keyword == "ADVISE":
        crop = argument or user.primary_crop or "Maize"
        try:
            ai = AIService()
            ns = Neo4jService()
            alerts = ns.get_regional_outbreak_risk(user.county, crop)
            # Fetch peer graph context
            graph_context = ns.search_graph_rag_context(user.phone_number)
            ns.close()
            
            # Generate strategic advise summary for SMS
            prompt = f"Write a brief 1-sentence farming advice in Swahili/English mixed for growing {crop} in {user.county} county. Keep it flat under 120 chars."
            advisory = ai.model.generate_content(prompt).text.strip()
            reply = f"AgriNexus ADVISE [{crop}]: {advisory}"
        except Exception as e:
            reply = f"AgriNexus ADVISE: Ushauri wa kilimo haupatikani sasa. Jaribu tena."

    elif keyword == "PRICE":
        crop = argument
        if not crop:
            reply = "AgriNexus PRICE: Tafadhali weka jina la zao (e.g. PRICE Maize)."
        else:
            ins = MarketInsight.query.filter(MarketInsight.crop_name.ilike(f"%{crop}%")).first()
            if ins:
                reply = f"AgriNexus PRICE Alert: {ins.crop_name} is KES {ins.current_price_per_kg:,.0f}/kg in {ins.market_location} ({ins.price_trend})."
            else:
                reply = f"AgriNexus PRICE Alert: Presha ya soko haipatikani kwa zao la {crop}."

    elif keyword == "REPORT":
        pest = argument
        if not pest:
            reply = "AgriNexus REPORT: Weka wadudu au ugonjwa uliogundua (e.g. REPORT Armyworm)."
        else:
            try:
                ns = Neo4jService()
                ns.log_pest_disease_outbreak(user.phone_number, pest, "Pest", "Reported by Inbound SMS")
                ns.close()
                reply = f"AgriNexus REPORT: Outbreak of {pest} registered for {user.county} county. Mitigation instructions sent to neighboring farmers."
            except Exception:
                reply = f"AgriNexus REPORT: Ripoti yako ya {pest} imepokelewa na kusajiliwa kwenye mfumo yetu."

    else:
        reply = "AgriNexus Help:\nUse keywords:\n- ADVISE <crop>\n- PRICE <crop>\n- REPORT <pest>"

    NotificationService.send_sms_via_africastalking(from_phone, reply)
    return Response("OK", status=200)
