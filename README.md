# AgriFinance Platform: Hybrid Graph & Generative AI Agri-Advisory Ecosystem

A modern, robust financial-inclusion and seasonal-planning portal engineered specifically for smallholder farmers and agricultural SACCOs (Savings and Credit Co-operatives) in Kenya. This platform leverages a hybrid database paradigm—coupling traditional relational structures with high-performance graph networking—and supercharges the user experience with contextual, localized Generative AI.

---

## 🎯 Project Objective

Smallholder farmers across Kenya face critical barriers to financial inclusion: lack of structured records, opaque credit risk profiling from traditional financial institutions, and limited access to actionable, hyper-localized agronomic advice. 

The objective of this platform is threefold:
1. **Democratize Strategic Advisory:** Deliver immediate, customized seasonal farming strategies (covering land prep, resource allocation, and market outlooks) specific to a farmer's county, budget, and local peer context.
2. **De-risk Agri-Financing:** Provide credit review pipelines (SACCOs) with clear, AI-driven risk scoring based on target crops, historical land data, and localized yield projections.
3. **Foster a Resilient Community:** Use a high-scale subscription architecture to trigger instant, low-latency notifications across channels like SMS and WhatsApp, keeping regional farming hubs connected to critical market developments.

---

## 🏗️ Architecture & Technology Stack

The platform is meticulously built with scalability, separation of concerns, and low-bandwidth execution in mind:

* **Frontend Ecosystem:** Tailwind CSS for a modern, mobile-responsive user experience tailored for field deployment.
* **Core Application Framework:** Flask 3.x web application environment.
* **Relational Data Store (SQLite/PostgreSQL):** Manages structured transactional attributes, profile metadata (User models, Roles), and historical tabular documents (Farm Plans, Loan Records, Feed Posts).
* **Graph Database Engine (Neo4j):** Manages social subscription pipelines, directional communication topologies (`:SUBSCRIBED_TO`), and multi-hop localized peer cluster lookups natively.
* **Generative AI Engine (Gemini 2.5 Flash Lite):** Synthesizes regional peer data to generate printable strategic advisories and analyzes operational metrics to produce clean JSON credit scores.
* **Notification Gateway Architecture:** Integrated with Twilio API (WhatsApp pipelines) and Africa's Talking (SMS networks) for real-time community engagement alerts.

---

## ⚙️ Key Architectural Features

### 1. Hybrid Peer-Aware AI Advisor
When a farmer requests a seasonal configuration, the system queries the Neo4j Graph database to parse patterns of successful peers in the same regional county cluster cultivating the same crop. This graph metadata is dynamically injected into the **Gemini 2.5 Flash Lite** model context window to generate highly context-aware, hyper-localized advice.

### 2. High-Performance Text Rendering & Offline Delivery
* **Jinja Markdown Compiler:** Raw AI outputs are cleanly compiled on the fly using a custom `render_markdown` filter linked to `markupsafe` and `markdown`.
* **Memory-Buffered PDF Engine:** Uses `xhtml2pdf` to transform formatted guidelines into print-ready documentation via a memory buffer string (`io.BytesIO`), preserving device resources on low-end hardware.

### 3. Native JSON Credit Risk Assessment
The credit assessment module overrides language ambiguities by passing strict schema configurations (`response_mime_type="application/json"`) to the Gemini model engine, producing predictable, structured JSON telemetry data for corporate auditing pipelines.

---

## 📂 Project Directory Structure

```text
agrifinance_platform/
│
├── app/
│   ├── __init__.py          # Application factory configuration layout
│   ├── extensions.py        # Shared instance binds (SQLAlchemy, LoginManager)
│   │
│   ├── community/
│   │   └── routes.py        # Social interactions, video uploads & notify triggers
│   │
│   ├── dashboard/
│   │   └── routes.py        # Core planning routes, PDF builders & filter hooks
│   │
│   ├── models/
│   │   └── sql_models.py    # Structured database declarations (User, Post, Loan)
│   │
│   ├── services/
│   │   ├── ai_service.py    # Gemini LLM implementations & YouTube summarizers
│   │   ├── neo4j_service.py # Graph query adapters & peer mapping hooks
│   │   └── notification_service.py # Twilio WhatsApp & Africa's Talking SMS engines
│   │
│   └── templates/           # Jinja layout views (base.html, loans/advisory.html)
│
├── run.py                   # Platform execution bootstrap script
├── requirements.txt         # Verified python production dependency constraints
└── .gitignore               # Protection mapping rules against security credentials leaks
