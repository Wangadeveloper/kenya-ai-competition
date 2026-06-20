import google.generativeai as genai
from flask import current_app
import json
import math
from app.models.sql_models import ExtensionGuide

class AIService:
    def __init__(self):
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        # Utilizing gemini-1.5-flash for complex GraphRAG token payloads
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def clean_json(self, text):
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def generate_embedding(self, text):
        """
        Generates a 768-dimension vector embedding using models/gemini-embedding-001.
        """
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        emb = result['embedding']
        if isinstance(emb, dict):
            emb = emb.get('values', [])
        return emb

    def cosine_similarity(self, v1, v2):
        """
        Computes the cosine similarity between two numeric lists.
        """
        if isinstance(v1, dict):
            v1 = v1.get('values', [])
        if isinstance(v2, dict):
            v2 = v2.get('values', [])

        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_a = sum(a * a for a in v1)
        norm_b = sum(b * b for b in v2)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def retrieve_relevant_guide(self, query):
        """
        Retrieves the most semantically relevant extension guide using SQLite vector matching.
        """
        try:
            # Generate query embedding
            q_emb = genai.embed_content(
                model="models/gemini-embedding-001",
                content=query,
                task_type="retrieval_query"
            )['embedding']
            
            if isinstance(q_emb, dict):
                q_emb = q_emb.get('values', [])
                
            guides = ExtensionGuide.query.filter(ExtensionGuide.embedding != None).all()
            if not guides:
                return None
                
            best_guide = None
            max_sim = -1.0
            
            for g in guides:
                sim = self.cosine_similarity(q_emb, g.embedding)
                if sim > max_sim:
                    max_sim = sim
                    best_guide = g
                    
            if max_sim > 0.4:  # Similarity threshold
                return best_guide
        except Exception as e:
            print("Error during vector retrieval:", e)
        return None

    def generate_farm_advisory(self, data, graph_context, regional_alerts=0, compliance_flags=None):
        """
        Generates hyper-localized agricultural strategy using deep GraphRAG payloads.
        compliance_flags: optional list of flagged substance names from EU compliance scans.
        """
        peer_context = ""
        if graph_context:
            peer_context = (
                f"Neighboring Farms Condition: {graph_context.get('last_condition', 'Unknown')}. "
                f"Sacco Membership Base: {graph_context.get('sacco_name', 'Independent')}. "
                f"Nearest Transacting Market: {graph_context.get('local_market', 'Regional')} "
                f"where current market price is {graph_context.get('market_price', 'Variable')} KES/KG."
            )
            
        # Hybrid GraphRAG + Vector Search
        guide_context = ""
        crop = data.get('crop_type', 'Maize')
        county = data.get('county', 'Kakamega')
        guide = self.retrieve_relevant_guide(f"Farming {crop} in {county}")
        if guide:
            guide_context = f"Scientific Agricultural Guideline on {guide.title}: {guide.content}"
            
        # EU Compliance Context Injection
        compliance_context = ""
        if compliance_flags:
            flagged_list = ", ".join(compliance_flags)
            compliance_context = (
                f"\n[EU COMPLIANCE ALERT]: The farmer has previously used inputs containing the following "
                f"substances flagged under EU Regulation (EC) No 396/2005 and EC 2023/915 Cadmium limits: "
                f"{flagged_list}. Strongly recommend certified organic or EU-compliant input alternatives "
                f"(e.g. CAN fertilizer with Cd<20mg/kg, approved biopesticides). Flag these urgently."
            )
            
        prompt = f"""
        You are a seasoned local agricultural advisory expert working with Kenyan SACCOs and small-scale smallholder farmers.
        Provide a seasonal plan and timeline based on the input metrics:
        - Crop Type: {crop}
        - Target Location: {county} County, Sub-county: {data.get('sub_county', 'General')}
        - Land Domain: {data.get('farm_size', 1.0)} Acres
        - Operating Capital: {data.get('budget', 10000)} KES
        - Irrigation Profile: {data.get('irrigation_type', 'Rain-fed')}
        - Intended Financing Asset: {data.get('expected_loan', 0)} KES
        - Target Export Market: {data.get('target_market', 'Local')}
        
        [Scientific Extension Reference Guideline Context]: {guide_context}
        [Ecosystem Graph Context]: {peer_context}
        [Nearby Active Pest/Disease Outbreak Alerts (Last 14 Days)]: {regional_alerts}
        {compliance_context}

        Requirements:
        1. Keep sentences short, actionable, and written in clear plain language. Avoid dense academic terms.
        2. Deliver an estimated operational cost breakdown, realistic profit margins, and a precise market timing outlook.
        3. Localize instructions using explicit Kenyan context (e.g., input availability, regional pests, transport logistics).
        4. Structure suggestions safely using markdown. Emphasize climate mitigation variables if nearby outbreak alerts are high.
        5. If EU compliance flags are present, lead with a dedicated "⚠️ EU Compliance Advisory" section recommending safe input alternatives before the seasonal plan.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception:
            return "### Mfumo wa Ushauri wa Kilimo\nUshauri wa Kilimo haupatikani kwa sasa. Tafadhali jaribu tena baada ya muda mfupi."


    def evaluate_loan_risk(self, loan_data, user_profile, active_outbreaks=0, flagged_input_count=0):
        """
        Evaluates financial loan risk against traditional credit scores and graph context metrics.
        flagged_input_count: number of EU-non-compliant inputs logged in the farmer's ledger.
        Returns a strict tuple: (int: risk_score, str: status_verdict, str: justification)
        """
        ledger_text = "No recorded transactions."
        if hasattr(user_profile, 'ledger_entries') and user_profile.ledger_entries.count() > 0:
            entries = user_profile.ledger_entries.all()
            total_income = sum(e.amount for e in entries if e.record_type == 'income')
            total_expense = sum(e.amount for e in entries if e.record_type == 'expense')
            recent = [f"{e.activity_date}: {e.record_type.upper()} of KES {e.amount} ({e.category} - {e.description or ''}) [Compliance: {e.compliance_status}]" for e in entries[:5]]
            ledger_text = f"Total Income: KES {total_income:,.2f}, Total Expense: KES {total_expense:,.2f}, Net Cashflow: KES {total_income - total_expense:,.2f}. Recent entries: " + "; ".join(recent)

        # Determine if this is an export-backed loan targeting the EU market
        target_market = loan_data.get('target_market', 'Local')
        compliance_risk_note = ""
        if target_market == 'EU' and flagged_input_count > 0:
            compliance_risk_note = (
                f"CRITICAL EU EXPORT RISK: The farmer has {flagged_input_count} chemical input ledger entries "
                f"flagged as non-compliant with EU pesticide/cadmium regulations (EC No 396/2005, EC 2023/915). "
                f"A border rejection risk is HIGH if this loan is approved for EU-destined crops. "
                f"The system recommends automatic downgrade to 'Pending' or 'Rejected' regardless of credit score."
            )

        prompt = f"""
        Analyze financial loan parameters for an agricultural credit risk assessment engine:
        - Applicant Name: {user_profile.full_name}
        - Regional Context: {user_profile.county} | Sub-county: {user_profile.sub_county}
        - Profile Credit Rating Score: {user_profile.credit_score} / 850
        - Historical Farm Footprint: {user_profile.farm_size} Acres
        - Water Source Integrity: {user_profile.water_source}
        - Farm Ledger Financial Profile (with Compliance Audit Trail): {ledger_text}
        - Requested Financing Asset: {loan_data.get('requested_amount', 0.0)} KES
        - Targeted Production Crop: {loan_data.get('crop', 'General')}
        - Capital Intended Focus: {loan_data.get('purpose', 'Inputs')}
        - Expected Harvest Repayment Term: {loan_data.get('repayment_period', 6)} Months
        - Intended Export Market: {target_market}
        - Active Regional Outbreak Risks: {active_outbreaks} indicators detected nearby.
        {compliance_risk_note}

        Return a strict JSON object containing exactly these three keys:
        1. 'risk_score': an integer strictly between 1 (Minimum System Risk) and 100 (Extremely High Hazard).
        2. 'status_verdict': A string matching exactly one of these: 'Approved', 'Pending', 'Rejected'.
        3. 'justification': A plain text evaluation, exactly 3 sentences, explaining production capacity, financial ledger health, and climate-risk AND compliance-risk factors.
        """
        try:
            response = self.model.generate_content(
                prompt
            )
            parsed = json.loads(self.clean_json(response.text))
            
            risk_score = int(parsed.get('risk_score', 50))
            status_verdict = parsed.get('status_verdict', 'Pending')
            justification = parsed.get('justification', 'Financing evaluation performed via context-matrix architecture.')
            
            # Hard override: EU loan with flagged inputs always gets downgraded
            if target_market == 'EU' and flagged_input_count > 0 and status_verdict == 'Approved':
                status_verdict = 'Pending'
                justification += f" [AUTO-DOWNGRADE: {flagged_input_count} EU non-compliant input(s) detected in ledger audit trail.]"
            
            return risk_score, status_verdict, justification
            
        except Exception:
            # Safe boundary automated baseline fallbacks
            fallback_status = 'Approved' if user_profile.credit_score >= 700 and active_outbreaks == 0 else 'Pending'
            if user_profile.credit_score < 600: fallback_status = 'Rejected'
            if target_market == 'EU' and flagged_input_count > 0: fallback_status = 'Pending'
            return 50, fallback_status, f"Automated credit verification fallback route utilized for {loan_data.get('crop')}. Manual field check recommended."

    def summarize_youtube_content(self, video_url):
        """
        Extracts agricultural takeaways from videos into brief text templates.
        """
        prompt = f"""
        You are an expert Kenyan agricultural extension advisor. 
        Analyze or make logical inferences about this farming video link: {video_url}.
        Provide a maximum 3-sentence summary in plain, clear text (mix English and simple Swahili naturally). 
        Focus on concrete instructions (e.g., input applications, row spacing, or pest control methods).
        Do not use any markdown formatting or bullet points in your response. Keep it completely flat for SMS constraints.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return f"Muhtasari wa video haupatikani kwa sasa. Tembelea kiungo hiki kupata maelezo: {video_url}"

    def analyze_pest_image(self, image_bytes, mime_type):
        """
        Performs multimodal identification of plant pest/disease damage.
        Returns a strict tuple: (str: pest_name, str: severity, str: recommendations)
        """
        prompt = """
        You are an expert plant pathologist. Analyze this image of crop damage or pest infestation:
        1. Identify the specific pest or disease name (e.g. 'Fall Armyworm', 'Late Blight').
        2. Evaluate the damage severity: choose exactly one of 'Low', 'Medium', 'High'.
        3. Provide a practical 2-sentence treatment recommendation (in Swahili/English mixed).
        
        Return a strict JSON object containing exactly these three keys:
        {
          "name": "pest or disease name",
          "severity": "Low/Medium/High",
          "recommendations": "actionable treatment recommendation"
        }
        """
        try:
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }
            response = self.model.generate_content(
                [image_part, prompt]
            )
            parsed = json.loads(self.clean_json(response.text))
            return parsed.get("name", "Unknown Pest/Disease"), parsed.get("severity", "Medium"), parsed.get("recommendations", "Monitor crop closely and apply appropriate pesticide.")
        except Exception as e:
            print("Error in multimodal analysis:", e)
            return "General Crop Damage", "Medium", "Ugonjwa wa mmea umeripotiwa. Tafadhali spika dawa ya wadudu na uwasiliane na afisa wa nyanjani."


    def screen_input_compliance(self, image_bytes, mime_type, target_crop='General'):
        """
        Multimodal EU compliance scan for fertilizer/pesticide labels.
        Checks for restricted active ingredients, heavy metals (Cadmium), and phosphonates
        against EU Regulation (EC) No 396/2005 and EC 2023/915 Cadmium limits.
        Returns a strict tuple: (str: risk_level, list: flagged_substances, str: reason, str: product_name)
        """
        prompt = f"""
        You are an EU agricultural input compliance auditor with expertise in EC Regulation No 396/2005
        (Maximum Residue Levels) and EC 2023/915 (Cadmium limits in fertilizers for food crops).
        
        Analyze this fertilizer or pesticide label image for use on {target_crop}:
        
        1. Identify the chemical input product/brand name or active substance name (e.g. "DAP Fertilizer", "Roundup").
        2. Identify any ACTIVE INGREDIENTS, heavy metals (especially Cadmium/Cd), or phosphonates listed.
        3. Flag any substances that exceed EU MRL limits or are restricted/banned under EU regulation.
        4. Assess the overall risk for EU export market compliance.
        
        Return a strict JSON object with exactly these four keys:
        {{
          "product_name": "identified brand or product name (e.g. 'Copper-based Fungicide')",
          "risk_level": "Low" or "Medium" or "High",
          "flagged_substances": ["list", "of", "flagged", "substance", "names"],
          "reason": "Plain language explanation (max 3 sentences) suitable for a farmer or SACCO officer."
        }}
        
        If the label is unreadable or not a chemical input label, return product_name 'Unknown Input', risk_level 'Low', empty flagged list,
        and reason explaining what was detected.
        """
        try:
            image_part = {"mime_type": mime_type, "data": image_bytes}
            response = self.model.generate_content(
                [image_part, prompt]
            )
            parsed = json.loads(self.clean_json(response.text))
            product_name = parsed.get("product_name", "Unknown Input")
            risk_level = parsed.get("risk_level", "Low")
            flagged_substances = parsed.get("flagged_substances", [])
            reason = parsed.get("reason", "No compliance issues detected.")
            return risk_level, flagged_substances, reason, product_name
        except Exception as e:
            print("Error in input compliance screen:", e)
            return "Medium", [], "Ukaguzi wa kiwango cha EU haukuweza kukamilika. Tafadhali wasiliana na afisa wa kilimo.", "Unknown Chemical"


    def check_text_compliance(self, ingredient_text, target_crop='General'):
        """
        Text-based EU compliance check for USSD/SMS feature-phone users who cannot upload images.
        Farmer sends ingredient or product name as a text string.
        Returns a strict tuple: (str: risk_level, list: flagged_substances, str: reason)
        """
        prompt = f"""
        You are an EU agricultural input compliance auditor with expertise in EC Regulation No 396/2005
        (Maximum Residue Levels) and EC 2023/915 (Cadmium limits in fertilizers).
        
        A Kenyan smallholder farmer intending to grow {target_crop} for EU export has provided the following
        fertilizer or pesticide product name or active ingredient list via SMS:
        
        "{ingredient_text}"
        
        1. Identify the active ingredients or substances in this product.
        2. Flag any that are restricted/banned under EU regulations or exceed Cadmium MRL limits.
        3. Assess the overall compliance risk level.
        
        Return a strict JSON object with exactly these three keys:
        {{
          "risk_level": "Low" or "Medium" or "High",
          "flagged_substances": ["list", "of", "flagged", "names"],
          "reason": "Plain language, SMS-safe explanation under 160 characters. Mix Swahili/English naturally."
        }}
        """
        try:
            response = self.model.generate_content(
                prompt
            )
            parsed = json.loads(self.clean_json(response.text))
            return parsed.get("risk_level", "Low"), parsed.get("flagged_substances", []), parsed.get("reason", "Hakuna tatizo la EU lililopatikana.")
        except Exception as e:
            print("Error in text compliance check:", e)
            return "Medium", [], "Tathmini ya EU haikufaulu. Wasiliana na afisa wa kilimo kwa ushauri zaidi."