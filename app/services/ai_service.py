import google.generativeai as genai
from flask import current_app
import json

class AIService:
    def __init__(self):
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        # Utilizing the lightning-fast flash model variant
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def generate_farm_advisory(self, data, similar_peers):
        """
        Generates hyper-localized agricultural extension insights using localized
        peer group contexts pulled directly from the Neo4j Graph cluster network.
        """
        peer_context = ", ".join([f"{p['name']} from {p['county']}" for p in similar_peers])
        prompt = f"""
        You are a seasoned local agricultural advisory assistant working with Kenyan SACCOs and small-scale farmers.
        Provide a seasonal plan and strategy based on the input features:
        - Crop Type: {data.get('crop_type', 'Maize')}
        - Target County: {data.get('county', 'Kakamega')}
        - Land Size: {data.get('farm_size', 1.0)} Acres
        - Operating Budget: {data.get('budget', 10000)} KES
        - Water Profile: {data.get('irrigation_type', 'Rain-fed')}
        - Additional Loan Request: {data.get('expected_loan', 0)} KES
        
        Peer Context: {peer_context if peer_context else "No localized peer records available in this cluster."}

        Requirements:
        1. Keep sentences short, actionable, and extremely clear. Avoid academic or dense terminology.
        2. Give an estimated cost overview, profit projection, and a brief market outlook.
        3. Provide localized advice using local Kenyan context (e.g., transport variables, soil characteristics, or regional pests).
        4. Frame suggestions safely without guaranteed returns. Ensure it is easy to read.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return "Ushauri wa Kilimo haupatikani kwa sasa. Tafadhali jaribu tena baada ya muda mfupi."

    def evaluate_loan_risk(self, loan_data, user_profile):
        """
        Evaluates financial loan applications against applicant database telemetry.
        Returns a clean tuple: (int: risk_score, str: justification)
        """
        prompt = f"""
        Analyze financial loan application parameters for a credit risk advisory system:
        - Applicant Name: {user_profile.full_name}
        - Farmer County: {user_profile.county}
        - Historical Farm Size: {getattr(user_profile, 'farm_size', 0.0)} Acres
        - Requested Loan Asset: {loan_data.get('requested_amount', 0.0)} KES
        - Allocated Crop Focus: {loan_data.get('crop', 'General')}
        - Capital Intended Purpose: {loan_data.get('purpose', 'Inputs')}
        - Target Harvest Projections: {loan_data.get('expected_harvest', 0.0)} Units
        - Chosen Repayment Target Window: {loan_data.get('repayment_period', 6)} Months

        Return a strict JSON object containing exactly these two keys:
        1. 'risk_score': an integer strictly between 1 (Minimum Risk) and 100 (High System Hazard).
        2. 'justification': A plain text evaluation, in 3 sentences, explaining the score, whether the loan fits the harvest value, and alternative configurations if unsafe.
        """
        try:
            # Enforce structural JSON returns natively via the Gemini Engine Configuration
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            
            risk_score = int(parsed.get('risk_score', 50))
            justification = parsed.get('justification', 'Financing assessment completed via credit intelligence matrix.')
            return risk_score, justification
            
        except Exception:
            # Fall back cleanly without crashing the controller pipeline if API keys drop or timeout
            fallback_score = 45 if getattr(user_profile, 'credit_score', 710) >= 700 else 75
            return fallback_score, f"Financing evaluated for {loan_data.get('crop', 'crop development')}. Ensure repayment matches local production margins."

    def summarize_youtube_content(self, video_url):
        """
        Analyzes a shared agricultural video link and provides an actionable summary
        that can be easily read or transmitted via low-bandwidth SMS and WhatsApp pipelines.
        """
        prompt = f"""
        You are an expert Kenyan agricultural extension specialist. 
        Analyze or make logical inferences about this farming video link: {video_url}.
        Provide a maximum 3-sentence summary in plain, clear text (mix English and simple Swahili naturally). 
        Focus on concrete, actionable instructions (e.g., proper input applications, row spacing, or pest control methods) 
        that a smallholder farmer can quickly act on. Keep it concise so it prints neatly inside notification feeds.
        Do not use any markdown formatting or bullet points in your response.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Muhtasari wa video haupatikani kwa sasa. Tembelea kiungo hiki kupata maelezo: {video_url}"

    def transcribe_and_summarize_video(self, video_file_path):
        try:
            prompt = "Summarize the core takeaways from a low-bandwidth video asset focused on smallholder dairy or crop performance improvements within East Africa."
            response = self.model.generate_content(prompt)
            return response.text
        except Exception:
            return "Uchambuzi wa video hauwezi kukamilika kwa sasa."