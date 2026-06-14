import google.generativeai as genai
from flask import current_app
import json
import math
from app.models.sql_models import ExtensionGuide

class AIService:
    def __init__(self):
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        # Utilizing gemini-1.5-flash for complex GraphRAG token payloads
        self.model = genai.GenerativeModel('gemini-1.5-flash')

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

    def generate_farm_advisory(self, data, graph_context, regional_alerts=0):
        """
        Generates hyper-localized agricultural strategy using deep GraphRAG payloads.
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
            
        prompt = f"""
        You are a seasoned local agricultural advisory expert working with Kenyan SACCOs and small-scale smallholder farmers.
        Provide a seasonal plan and timeline based on the input metrics:
        - Crop Type: {crop}
        - Target Location: {county} County, Sub-county: {data.get('sub_county', 'General')}
        - Land Domain: {data.get('farm_size', 1.0)} Acres
        - Operating Capital: {data.get('budget', 10000)} KES
        - Irrigation Profile: {data.get('irrigation_type', 'Rain-fed')}
        - Intended Financing Asset: {data.get('expected_loan', 0)} KES
        
        [Scientific Extension Reference Guideline Context]: {guide_context}
        [Ecosystem Graph Context]: {peer_context}
        [Nearby Active Pest/Disease Outbreak Alerts (Last 14 Days)]: {regional_alerts}

        Requirements:
        1. Keep sentences short, actionable, and written in clear plain language. Avoid dense academic terms.
        2. Deliver an estimated operational cost breakdown, realistic profit margins, and a precise market timing outlook.
        3. Localize instructions using explicit Kenyan context (e.g., input availability, regional pests, transport logistics).
        4. Structure suggestions safely using markdown. Emphasize climate mitigation variables if nearby outbreak alerts are high.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception:
            return "### Mfumo wa Ushauri wa Kilimo\nUshauri wa Kilimo haupatikani kwa sasa. Tafadhali jaribu tena baada ya muda mfupi."


    def evaluate_loan_risk(self, loan_data, user_profile, active_outbreaks=0):
        """
        Evaluates financial loan risk against traditional credit scores and graph context metrics.
        Returns a strict tuple: (int: risk_score, str: status_verdict, str: justification)
        """
        ledger_text = "No recorded transactions."
        if hasattr(user_profile, 'ledger_entries') and user_profile.ledger_entries.count() > 0:
            entries = user_profile.ledger_entries.all()
            total_income = sum(e.amount for e in entries if e.record_type == 'income')
            total_expense = sum(e.amount for e in entries if e.record_type == 'expense')
            recent = [f"{e.activity_date}: {e.record_type.upper()} of KES {e.amount} ({e.category} - {e.description or ''})" for e in entries[:5]]
            ledger_text = f"Total Income: KES {total_income:,.2f}, Total Expense: KES {total_expense:,.2f}, Net Cashflow: KES {total_income - total_expense:,.2f}. Recent entries: " + "; ".join(recent)

        prompt = f"""
        Analyze financial loan parameters for an agricultural credit risk assessment engine:
        - Applicant Name: {user_profile.full_name}
        - Regional Context: {user_profile.county} | Sub-county: {user_profile.sub_county}
        - Profile Credit Rating Score: {user_profile.credit_score} / 850
        - Historical Farm Footprint: {user_profile.farm_size} Acres
        - Water Source Integrity: {user_profile.water_source}
        - Farm Ledger Financial Profile: {ledger_text}
        - Requested Financing Asset: {loan_data.get('requested_amount', 0.0)} KES
        - Targeted Production Crop: {loan_data.get('crop', 'General')}
        - Capital Intended Focus: {loan_data.get('purpose', 'Inputs')}
        - Expected Harvest Repayment Term: {loan_data.get('repayment_period', 6)} Months
        - Active Regional Outbreak Risks: {active_outbreaks} indicators detected nearby.

        Return a strict JSON object containing exactly these three keys:
        1. 'risk_score': an integer strictly between 1 (Minimum System Risk) and 100 (Extremely High Hazard).
        2. 'status_verdict': A string matching exactly one of these: 'Approved', 'Pending', 'Rejected'.
        3. 'justification': A plain text evaluation, exactly 3 sentences, explaining production capacity, financial ledger health, and climate-risk factors.
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            
            risk_score = int(parsed.get('risk_score', 50))
            status_verdict = parsed.get('status_verdict', 'Pending')
            justification = parsed.get('justification', 'Financing evaluation performed via context-matrix architecture.')
            
            return risk_score, status_verdict, justification
            
        except Exception:
            # Safe boundary automated baseline fallbacks
            fallback_status = 'Approved' if user_profile.credit_score >= 700 and active_outbreaks == 0 else 'Pending'
            if user_profile.credit_score < 600: fallback_status = 'Rejected'
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
                [image_part, prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            return parsed.get("name", "Unknown Pest/Disease"), parsed.get("severity", "Medium"), parsed.get("recommendations", "Monitor crop closely and apply appropriate pesticide.")
        except Exception as e:
            print("Error in multimodal analysis:", e)
            return "General Crop Damage", "Medium", "Ugonjwa wa mmea umeripotiwa. Tafadhali spika dawa ya wadudu na uwasiliane na afisa wa nyanjani."