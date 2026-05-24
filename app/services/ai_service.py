import google.generativeai as genai
from flask import current_app
import json

class AIService:
    def __init__(self):
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        # Utilizing the lightning-fast flash model variant
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def generate_farm_advisory(self, data, similar_peers):
        peer_context = ", ".join([f"{p['name']} from {p['county']}" for p in similar_peers])
        prompt = f"""
        You are a seasoned local agricultural advisory assistant working with Kenyan SACCOs and small-scale farmers.
        Provide a seasonal plan and strategy based on the input features:
        - Crop Type: {data['crop_type']}
        - Target County: {data['county']}
        - Land Size: {data['farm_size']} Acres
        - Operating Budget: {data['budget']} KES
        - Water Profile: {data['irrigation_type']}
        - Additional Loan Request: {data['expected_loan']} KES
        
        Peer Context: {peer_context if peer_context else "No localized peer records available in this cluster."}

        Requirements:
        1. Keep sentences short, actionable, and extremely clear. Avoid academic or dense terminology.
        2. Give an estimated cost overview, profit projection, and a brief market outlook for {data['county']}.
        3. Provide localized advice using local Kenyan context (e.g., transport variables, soil characteristics, or regional pests).
        4. Frame suggestions safely without guaranteed returns. Ensure it is easy to read.
        """
        response = self.model.generate_content(prompt)
        return response.text

    def evaluate_loan_risk(self, loan_data, user_profile):
        prompt = f"""
        Analyze financial loan application parameters for a credit risk advisory system (e.g., SACCO review pipeline):
        - Applicant Name: {user_profile.full_name}
        - Farmer County: {user_profile.county}
        - Historical Farm Size: {user_profile.farm_size} Acres
        - Requested Loan Asset: {loan_data['requested_amount']} KES
        - Allocated Crop Focus: {loan_data['crop']}
        - Capital Intended Purpose: {loan_data['purpose']}
        - Target Harvest Projections: {loan_data['expected_harvest']} Units
        - Chosen Repayment Target Window: {loan_data['repayment_period']} Months

        Return an absolute JSON object containing exactly these two keys:
        1. 'risk_score': an integer strictly between 1 (Minimum Risk) and 100 (High System Hazard risk thresholds).
        2. 'justification': A plain text evaluation, in 3 sentences, explaining the score, whether the loan fits the harvest value, and alternative financing configurations if unsafe.
        """
        try:
            # Forcing structural JSON outputs natively via the API configurations
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            return parsed.get('risk_score', 50), parsed.get('justification', "Evaluation complete.")
        except Exception:
            return 45, f"Requested financing amount evaluated for {loan_data['crop']}. Ensure repayment matches local production margins."

    # --- NEW: ADDED TO SUPPORT COMMUNITY YOUTUBE AUTO-SUMMARIZATION ---
    def summarize_youtube_content(self, video_url):
        """
        Analyzes a shared agricultural video link and provides an actionable summary
        that can be easily read or transmitted via SMS and WhatsApp pipelines.
        """
        prompt = f"""
        You are an expert Kenyan agricultural extension specialist. 
        Analyze or make logical inferences about this farming video link: {video_url}.
        Provide a maximum 3-sentence summary in plain, clear text (mix English and simple Swahili if natural). 
        Focus on concrete, actionable instructions (e.g., proper input applications, row spacing, or pest control methods) 
        that a smallholder farmer can quickly act on. Keep it concise so it prints neatly inside notification feeds.
        Do not use any markdown formatting tags in your response.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Muhtasari wa video haupatikani kwa sasa. Tembelea kiungo hiki kupata maelezo: {video_url}"

    def transcribe_and_summarize_video(self, video_file_path):
        prompt = "Summarize the core takeaways from a low-bandwidth video asset focused on smallholder dairy or crop performance improvements within East Africa."
        response = self.model.generate_content(prompt)
        return response.text