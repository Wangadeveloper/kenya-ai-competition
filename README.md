# Agriculture4Good Platform: Hybrid Graph & Generative AI Agri-Advisory Ecosystem

A modern, robust financial-inclusion, seasonal-planning, and compliance portal engineered specifically for smallholder farmers and agricultural SACCOs (Savings and Credit Co-operatives) in Kenya. This platform leverages a hybrid database paradigm—coupling traditional relational structures with high-performance graph networking—and supercharges the user experience with contextual, localized Generative AI.

---

## 🎯 Project Objective

Smallholder farmers across Kenya face critical barriers to financial inclusion: lack of structured records, opaque credit risk profiling from traditional financial institutions, and limited access to actionable, hyper-localized agronomic advice. Additionally, compliance with strict international regulations (e.g., EU chemical input and cadmium residue levels) poses a high risk of crop export rejection.

The objective of this platform is threefold:
1. **Democratize Strategic Advisory:** Deliver immediate, customized seasonal farming strategies (covering land prep, resource allocation, and market outlooks) specific to a farmer's county, budget, and local peer context.
2. **De-risk Agri-Financing:** Provide credit review pipelines (SACCOs) with clear, AI-driven risk scoring based on target crops, historical land data, and localized yield projections.
3. **Foster a Resilient Community & Safe Supply Chain:** Connect regional farming hubs through real-time notifications (SMS/WhatsApp) and enforce strict chemical compliance screening to safeguard crops destined for local or export markets.

---

## 🏗️ Architecture & Technology Stack

The platform is built with scalability, separation of concerns, low-bandwidth access, and high-performance agentic workflows in mind:

* **Frontend Ecosystem:** Tailwind CSS for a modern, mobile-responsive user experience tailored for field deployment.
* **Core Application Framework:** Flask 3.x web application environment.
* **Relational Data Store (SQLite/PostgreSQL):** Manages structured transactional attributes, profile metadata (`User` models, roles, SACCO records), and historical tabular documents (`FarmPlan`, `LoanApplication`, `FarmLedger`, `Post`, `Comment`).
* **Graph Database Engine (Neo4j):** Manages social subscription pipelines, directional communication topologies (`:SUBSCRIBED_TO`), and multi-hop localized peer cluster lookups natively to enable GraphRAG.
* **Generative AI Engine (Gemini 2.5 Flash):** Synthesizes regional peer data to generate printable strategic advisories, executes autonomous document agents with tool-calling capabilities, and evaluates credit applications to return structured JSON risk metrics.
* **Notification Gateway Architecture:** Integrated with Twilio API (WhatsApp pipelines) and Africa's Talking API (SMS networks) for real-time community engagement alerts.

---

## ⚙️ Key Architectural Features

### 1. Autonomous Multimodal Document Agent (EU Compliance Check)
Using Gemini's function-calling capabilities, the platform features a multimodal document-processing agent. When a farmer uploads an image (a financial purchase receipt or a chemical input label):
* **Receipt Processing:** Extracted items (seeds, fertilizers, pesticides, labor) are logged as ledger entries. If a chemical input is flagged as EU non-compliant, the agent raises warnings.
* **Label Compliance Check:** The agent screens chemical active ingredients and heavy metal concentrations (e.g., Cadmium levels under regulations **EC No 396/2005** and **EC 2023/915**).
* **Tool Bindings:** The agent automatically runs native functions to update the SQL database (`tool_save_ledger_entry`), write nodes to the Neo4j compliance graph (`tool_sync_neo4j_compliance_graph`), and dispatch warnings directly to the farmer via SMS (`tool_dispatch_immediate_sms_warning`).

### 2. Hybrid Peer-Aware AI Advisor (GraphRAG & SQLite Vector Search)
When a farmer requests a seasonal configuration:
* **Neo4j Graph Lookup:** The system queries neighboring farms within the same county cluster cultivating the same crop to extract regional context.
* **SQLite Vector-based RAG:** Scientific extension guidelines are stored as text with 768-dimension vector embeddings (`models/gemini-embedding-001`). The system performs local cosine-similarity matching in SQLite to find the most relevant guideline for the crop and location.
* **AI Synthesis:** The graph context and semantic guides are combined in the prompt for **Gemini 2.5 Flash**, producing a highly localized, actionable, and compliant farming plan.

### 3. Offline Access Interfaces (USSD & Inbound SMS)
Recognizing that many smallholders rely on basic feature phones, the platform exposes fully interactive SMS and USSD gateways mimicking Africa's Talking protocols:
* **USSD Gateway (`/ussd/`):** A complete menu interface for registration, profile management, checking credit rating tier (Poor/Fair/Excellent), looking up live crop prices, submitting loan applications (scored live by Gemini), logging field visits (for officers), and performing quick text-based input compliance screens.
* **Inbound SMS Gateway (`/ussd/sms`):** Listens for keywords to reply instantly over SMS:
  - `ADVISE <crop>`: Sends a one-sentence agricultural advice from the AI model.
  - `PRICE <crop>`: Returns current crop pricing and trend from the market insights database.
  - `REPORT <outbreak>`: Logs a regional pest/disease outbreak to the Neo4j graph, triggering warning SMS alerts to neighboring farmers.
  - `CHECK <substance>`: Runs a text-based compliance check on fertilizer or pesticide ingredients.

### 4. Multi-Channel Peer Broadcast Graph
The Neo4j graph maps the community. When a farmer publishes a seasonal post/advisory (including YouTube video uploads summarized automatically by Gemini):
* The system checks the graph database for any users linked to the poster via a `[:SUBSCRIBED_TO]` relationship.
* It parses their preferred channel (`SMS` or `WhatsApp`) and immediately broadcasts the advisory or summary to keep the local peer network updated.

### 5. High-Performance Text Rendering & Offline Delivery
* **Jinja Markdown Compiler:** Raw AI outputs are compiled on the fly using a custom `render_markdown` filter linked to `markupsafe` and `markdown`.
* **Memory-Buffered PDF Engine:** Uses `xhtml2pdf` to transform formatted guidelines into print-ready documentation via a memory buffer string (`io.BytesIO`), preserving device resources on low-end hardware.

### 6. Dual-Perspective Portals & Workflows
* **Farmer Portal:** Provides a detailed overview of seasonal plans, credit scores, weather forecasts, market indexes, interactive agricultural feeds, and a compliance-audited farm ledger (income/expense tracker).
* **Field Officer Portal:** Empowered to manage regional farmer registries, review pending loan applications and risk justification scoring, and submit official GPS-tagged `FieldVisit` logs with crop health status reports.

---

## 📂 Project Directory Structure

```text
agriculture4good_platform/
│
├── app/
│   ├── __init__.py          # Application factory, blueprints & template filters
│   ├── config.py            # Environment configurations (SQLite, Neo4j, Gemini, APIs)
│   ├── extensions.py        # Shared instance binds (SQLAlchemy, LoginManager, Migrate)
│   │
│   ├── auth/                # User login, registration, and session management
│   │   ├── forms.py
│   │   └── routes.py
│   │
│   ├── community/           # Social feeds, YouTube summarizers, and subscriptions
│   │   └── routes.py
│   │
│   ├── dashboard/           # Farmer/Officer dashboards, seasonal planning, PDF generation
│   │   └── routes.py
│   │
│   ├── loans/               # Loan application pipeline and credit risk endpoints
│   │   └── routes.py
│   │
│   ├── models/
│   │   └── sql_models.py    # SQL Database models (Users, SACCOs, Ledgers, Plans, Loans, etc.)
│   │
│   ├── services/
│   │   ├── ai_service.py    # Gemini integrations, vector matching, & function-calling agent
│   │   ├── neo4j_service.py # Neo4j adapters (peer lookup, visit logging, broadcast checks)
│   │   ├── notification_service.py # SMS (Africa's Talking) and WhatsApp (Meta Cloud) dispatchers
│   │   └── weather_service.py # Local county-level weather forecasts
│   │
│   ├── static/              # CSS files and styling elements
│   ├── templates/           # Jinja2 layouts (dashboard, auth, loans, community, PDF templates)
│   │
│   └── ussd/                # Africa's Talking compatible USSD & Inbound SMS gateways
│       └── routes.py
│
├── run.py                   # Platform execution, DB initialization, and mockup seed data
├── requirements.txt         # Project dependency constraints
├── Procfile                 # Deployment configurations for platforms like Heroku/Render
└── render.yaml              # Render blueprint declaration file
```

---

## 🚀 Setup & Local Installation

### Prerequisites
* Python 3.9 or higher
* Neo4j Database Instance (Local or AuraDB Cloud instance)

### Installation Steps

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repository_url>
   cd agriculture4good_platform
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory (based on the `.env` template if available) with the following parameters:
   ```env
   SECRET_KEY=your_flask_secret_key_here
   DATABASE_URL=sqlite:///agriculture4good.db
   
   # Neo4j Configurations
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_neo4j_password_here
   NEO4J_DATABASE=neo4j
   
   # Generative AI Key
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Notifications Credentials (Optional for local simulation fallback)
   AFRICASTALKING_USERNAME=sandbox
   AFRICASTALKING_API_KEY=your_africastalking_key_here
   WHATSAPP_TOKEN=your_whatsapp_bearer_token_here
   WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_id_here
   ```

5. **Run the bootstrap script:**
   ```bash
   python run.py
   ```
   *Note: Upon startup, the script will automatically initialize the SQLite tables, seed initial records (default users, SACCOs, market prices), query the Gemini API to pre-generate and store vector embeddings for the scientific extension guides, and attempt to synchronize the seeded profiles directly to your Neo4j instance.*

### Default Seeded Users (for testing)
* **Field Officer Account:**
  - Phone: `+254712345678`
  - Password: `password`
* **Farmer Account (John):**
  - Phone: `+254711111111`
  - Password: `password`
* **Farmer Account (Mary):**
  - Phone: `+254722222222`
  - Password: `password`
