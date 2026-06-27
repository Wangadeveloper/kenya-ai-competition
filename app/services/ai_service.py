import google.generativeai as genai
from flask import current_app
import json
import math
from app.extensions import db
from app.models.sql_models import ExtensionGuide, FarmLedger
from app.services.neo4j_service import Neo4jService
from app.services.notification_service import NotificationService

class AIService:
    def __init__(self, user_context=None):
        """
        Initializes the AI Service with optional user context for Agentic Tool execution.
        """
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.user = user_context

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
        """Generates a 768-dimension vector embedding."""
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
        """Computes the cosine similarity between two numeric vectors."""
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
        """Retrieves the most semantically relevant extension guide using SQLite vector matching."""
        try:
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
                    
            if max_sim > 0.4:
                return best_guide
        except Exception as e:
            print("Error during vector retrieval:", e)
        return None

    def generate_farm_advisory(self, data, graph_context, regional_alerts=0, compliance_flags=None):
        """Generates hyper-localized agricultural strategy using deep GraphRAG payloads."""
        peer_context = ""
        if graph_context:
            peer_context = (
                f"Neighboring Farms Condition: {graph_context.get('last_condition', 'Unknown')}. "
                f"Sacco Membership Base: {graph_context.get('sacco_name', 'Independent')}. "
                f"Nearest Transacting Market: {graph_context.get('local_market', 'Regional')} "
                f"where current market price is {graph_context.get('market_price', 'Variable')} KES/KG."
            )
            
        guide_context = ""
        crop = data.get('crop_type', 'Maize')
        county = data.get('county', 'Kakamega')
        guide = self.retrieve_relevant_guide(f"Farming {crop} in {county}")
        if guide:
            guide_context = f"Scientific Agricultural Guideline on {guide.title}: {guide.content}"
            
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
        """Evaluates financial loan risk against traditional credit scores and graph context metrics."""
        ledger_text = "No recorded transactions."
        if hasattr(user_profile, 'ledger_entries') and user_profile.ledger_entries.count() > 0:
            entries = user_profile.ledger_entries.all()
            total_income = sum(e.amount for e in entries if e.record_type == 'income')
            total_expense = sum(e.amount for e in entries if e.record_type == 'expense')
            recent = [f"{e.activity_date}: {e.record_type.upper()} of KES {e.amount} ({e.category} - {e.description or ''}) [Compliance: {e.compliance_status}]" for e in entries[:5]]
            ledger_text = f"Total Income: KES {total_income:,.2f}, Total Expense: KES {total_expense:,.2f}, Net Cashflow: KES {total_income - total_expense:,.2f}. Recent entries: " + "; ".join(recent)

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
        1. 'risk_score': an integer strictly between 1 and 100.
        2. 'status_verdict': A string matching exactly one of these: 'Approved', 'Pending', 'Rejected'.
        3. 'justification': A plain text evaluation, exactly 3 sentences.
        """
        try:
            response = self.model.generate_content(prompt)
            parsed = json.loads(self.clean_json(response.text))
            
            risk_score = int(parsed.get('risk_score', 50))
            status_verdict = parsed.get('status_verdict', 'Pending')
            justification = parsed.get('justification', 'Financing evaluation performed via context-matrix architecture.')
            
            if target_market == 'EU' and flagged_input_count > 0 and status_verdict == 'Approved':
                status_verdict = 'Pending'
                justification += f" [AUTO-DOWNGRADE: {flagged_input_count} EU non-compliant input(s) detected in ledger audit trail.]"
            
            return risk_score, status_verdict, justification
        except Exception:
            fallback_status = 'Approved' if user_profile.credit_score >= 700 and active_outbreaks == 0 else 'Pending'
            if user_profile.credit_score < 600: fallback_status = 'Rejected'
            if target_market == 'EU' and flagged_input_count > 0: fallback_status = 'Pending'
            return 50, fallback_status, f"Automated credit verification fallback route utilized for {loan_data.get('crop')}. Manual field check recommended."

    def summarize_youtube_content(self, video_url):
        """Extracts agricultural takeaways from videos into brief text templates."""
        prompt = f"""
        You are an expert Kenyan agricultural extension advisor. 
        Analyze or make logical inferences about this farming video link: {video_url}.
        Provide a maximum 3-sentence summary in plain, clear text (mix English and simple Swahili naturally). 
        Focus on concrete instructions. Do not use any markdown formatting or bullet points.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return f"Muhtasari wa video haupatikani kwa sasa. Tembelea kiungo hiki kupata maelezo: {video_url}"

    def analyze_pest_image(self, image_bytes, mime_type):
        """Performs multimodal identification of plant pest/disease damage."""
        prompt = """
        You are an expert plant pathologist. Analyze this image of crop damage or pest infestation:
        1. Identify the specific pest or disease name (e.g. 'Fall Armyworm', 'Late Blight').
        2. Evaluate the damage severity: choose exactly one of 'Low', 'Medium', 'High'.
        3. Provide a practical 2-sentence treatment recommendation (in Swahili/English mixed).
        
        Return a strict JSON object containing exactly these three keys:
        {"name": "pest name", "severity": "Low/Medium/High", "recommendations": "treatment recommendations"}
        """
        try:
            image_part = {"mime_type": mime_type, "data": image_bytes}
            response = self.model.generate_content([image_part, prompt])
            parsed = json.loads(self.clean_json(response.text))
            return parsed.get("name", "Unknown Pest/Disease"), parsed.get("severity", "Medium"), parsed.get("recommendations", "Monitor crop closely.")
        except Exception as e:
            print("Error in multimodal analysis:", e)
            return "General Crop Damage", "Medium", "Ugonjwa wa mmea umeripotiwa. Wasiliana na afisa wa nyanjani."

    def check_text_compliance(self, ingredient_text, target_crop='General'):
        """Text-based EU compliance check for USSD/SMS feature-phone users."""
        prompt = f"""
        You are an EU agricultural input compliance auditor.
        Analyze this input name or active ingredients list for use on {target_crop}:
        "{ingredient_text}"
        
        Return a strict JSON object with exactly these three keys:
        {{
          "risk_level": "Low" or "Medium" or "High",
          "flagged_substances": ["list", "of", "flagged", "names"],
          "reason": "Plain language, SMS-safe explanation under 160 characters. Mix Swahili/English naturally."
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            parsed = json.loads(self.clean_json(response.text))
            return parsed.get("risk_level", "Low"), parsed.get("flagged_substances", []), parsed.get("reason", "Hakuna tatizo la EU lililopatikana.")
        except Exception as e:
            print("Error in text compliance check:", e)
            return "Medium", [], "Tathmini ya EU haikufaulu. Wasiliana na afisa wa kilimo."


    # =========================================================================
    # 🤖 NATIVE AGENTIC TOOL DECLARATIONS & EXECUTION ENGINE
    # =========================================================================

    def tool_save_ledger_entry(self, record_type: str, category: str, amount: float, description: str, compliance_status: str) -> str:
        """
        Saves an individual extracted or screened transactional entry directly to the SQL relational FarmLedger table.
        Args:
            record_type: System string value; must match exactly 'income' or 'expense'.
            category: Normalized database class; e.g., 'Fertilizer', 'Pesticide', 'Seeds', 'Labor', 'Equipment', 'Harvest Sale'.
            amount: Precision floating point currency transaction value in KES.
            description: Plain details specifying product brand names, batch metadata, or quantity metrics.
            compliance_status: The calculated EU export regulatory metric; must match exactly 'Safe', 'Flagged', or 'Unverified'.
        """
        if not self.user:
            return "Error: Internal engine runtime lacks user session binding context."
        try:
            new_entry = FarmLedger(
                user_id=self.user.id,
                record_type=record_type,
                category=category,
                amount=float(amount),
                description=description,
                compliance_status=compliance_status
            )
            db.session.add(new_entry)
            db.session.commit()
            return f"Success: Logged KES {amount} {record_type} under category '{category}' with status [{compliance_status}]."
        except Exception as e:
            db.session.rollback()
            return f"Error writing to SQL database ledger footprint: {str(e)}"

    def tool_sync_neo4j_compliance_graph(self, input_name: str, compliance_status: str) -> str:
        """
        Propagates chemical input metadata updates directly into the structural Neo4j compliance knowledge graph.
        Args:
            input_name: The extracted generic or brand chemical product label name string.
            compliance_status: The verified execution safety status value matching exactly 'Safe' or 'Flagged'.
        """
        if not self.user:
            return "Error: Internal engine runtime lacks user structural graph context."
        try:
            ns = Neo4jService()
            ns.log_input_purchase(
                farmer_phone=self.user.phone_number,
                input_name=input_name[:100],
                manufacturer='Extracted by Agent',
                batch='Agent Scan Loop',
                compliance_status=compliance_status
            )
            
            if compliance_status == 'Flagged':
                exposed_peers = ns.get_compliance_exposed_peers(
                    self.user.county, self.user.primary_crop or 'Maize', self.user.phone_number
                )
                for peer in exposed_peers:
                    alert_msg = (
                        f"AgriNexus EU ALERT: Chemical input '{input_name[:30]}' in your region has been "
                        f"flagged as non-compliant. Check your fields before harvesting for export."
                    )
                    try:
                        NotificationService.send_sms_via_africastalking(peer['phone_number'], alert_msg)
                    except Exception:
                        pass
            ns.close()
            return f"Success: Synced tracking node to Neo4j cluster network for '{input_name}'."
        except Exception as e:
            return f"Error writing node edge vectors to Neo4j graph registry: {str(e)}"

    def tool_dispatch_immediate_sms_warning(self, message: str) -> str:
        """
        Broadcasts an immediate, high-priority safety compliance alert SMS message directly to the transacting farmer's phone.
        Args:
            message: Explicit warning notification content string detailing the risk factor and active ingredient breakdown.
        """
        if not self.user:
            return "Error: Missing communication dispatch subscriber telemetry context."
        try:
            NotificationService.send_sms_via_africastalking(self.user.phone_number, message[:160])
            return "Success: Dispatched high-priority warning broadcast SMS to user handset terminal."
        except Exception as e:
            return f"Error invoking external shortcode gateway infrastructure: {str(e)}"

    def execute_multimodal_document_agent(self, image_bytes: bytes, mime_type: str, target_crop: str = 'General'):
        """
        Launches an autonomous agent session using native function calling tools.
        Determines if an image is an input label or a purchase receipt, extracts metrics, 
        evaluates EU compliance (Regulation EC No 396/2005 & EC 2023/915 Cadmium limits),
        and invokes tools to update the system state dynamically.
        """
        # Instantiate agent system topology equipped with local tools
        agent_tools = [
            self.tool_save_ledger_entry,
            self.tool_sync_neo4j_compliance_graph,
            self.tool_dispatch_immediate_sms_warning
        ]
        
        agent_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=agent_tools
        )
        
        agent_instructions = f"""
        You are the senior AgriNexus Autonomous Document Agent serving smallholder agricultural value chains in Kenya.
        The current active session farmer profile grows: {target_crop}.

        Your operational execution blueprint:
        1. Parse the uploaded document image block. Discern if it represents a Financial Purchase Receipt/Invoice or a Chemical Input Product Label.
        
        2. If it is a FINANCIAL PURCHASE RECEIPT / INVOICE:
           - Scan and extract EVERY relevant item entry (Fertilizers, Pesticides, Seeds, Labor, Tools, etc.).
           - Extract the monetary item price value.
           - Check if the item belongs to a chemical input category. Evaluate its EU compliance vector.
           - FOR EVERY ITEM detected, call the `tool_save_ledger_entry` tool with correct arguments.
           - If a chemical input is flagged as EU non-compliant ('Flagged'), also execute `tool_sync_neo4j_compliance_graph` and trigger an immediate warning message to the farmer via `tool_dispatch_immediate_sms_warning`.
        
        3. If it is a CHEMICAL INPUT LABEL:
           - Analyze chemical parameters, active substances, heavy metals (Cadmium), or phosphonates.
           - Identify if the input breaches EU export regulatory tolerances (Regulation EC No 396/2005 or Cadmium thresholds in EC 2023/915).
           - Determine the compliance status string mapping strictly to: 'Safe' or 'Flagged'.
           - Log this analysis into the farmer's records by calling `tool_save_ledger_entry` as a KES 0.0 tracking record with description matching "AI Scan: [Product Name]".
           - Cross-propagate this data footprint into the Neo4j map by calling `tool_sync_neo4j_compliance_graph`.
           - If it is non-compliant, you MUST issue a critical SMS text alert via `tool_dispatch_immediate_sms_warning`.

        Maintain structural parameter typing. Drive completion metrics systematically across all ledger objects found.
        Finally, deliver a concise overview statement text mixing Swahili/English naturally summarizing your automated actions.
        """
        
        image_part = {"mime_type": mime_type, "data": image_bytes}
        chat_session = agent_model.start_chat(enable_automatic_function_calling=True)
        
        try:
            response = chat_session.send_message([image_part, agent_instructions])
            return response.text
        except Exception as e:
            print(f"Critical System Agent Session Failure: {e}")
            return "### Hitilafu ya Mfumo wa Agentic\nMfumo umeshindwa kuchambua hati hiyo kiotomatiki. Tafadhali jaribu tena au wasiliana na usaidizi."