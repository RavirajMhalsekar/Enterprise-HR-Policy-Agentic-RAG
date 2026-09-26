# Enterprise HR Policy & Employee Support Agentic RAG Copilot

An end-to-end **Forward Deployed Engineer (FDE)** project that transforms an Agentic RAG workflow into a deployable internal HR product.

The system combines **LangGraph, FastAPI, Google Gemini, Pinecone, Tavily, SQLite, Docker, and a lightweight HTML/CSS/JavaScript frontend** to provide grounded HR policy answers while keeping private company knowledge separate from public web information.

> 📖 **Full System & Workflow Documentation:**  
> See [`docs/PROJECT_DOCUMENTATION.md`](docs/PROJECT_DOCUMENTATION.md) for detailed architecture, state-machine diagrams, API contracts, ingestion flow, security design, and technology inventory.

---

## 🚀 Live Demo

**Live Application:**  
https://enterprise-hr-policy-agentic-rag-2bbz.onrender.com/

**GitHub Repository:**  
https://github.com/RavirajMhalsekar/Enterprise-HR-Policy-Agentic-RAG

> The application uses fictional company data for demonstration purposes. No real employee or company information is used.

---

# 1. Business Problem

## Customer

**NovaRetail** is a fictional 3,000-employee retail company.

## Problem

The HR team maintains many internal documents covering:

- Leave policies
- Remote-work rules
- Payroll guidance
- Benefits
- Employee onboarding
- Conduct policies
- HR operations
- Workplace procedures

Employees frequently ask HR repetitive questions because:

- They do not know where the correct policy is located.
- Traditional keyword search returns too many documents.
- Generic chatbots can hallucinate policy details.
- Internal documents may not contain current public information.
- Some questions require fresh external information.
- HR teams need visibility into how an AI system reached an answer.

## Example

An employee asks:

> "How many annual leave days do employees receive?"

The answer exists in the private company HR knowledge base.

The system should therefore:

```text
Employee Question
       ↓
Private HR Knowledge Base
       ↓
Evidence Evaluation
       ↓
Grounded Answer
```

It should **not unnecessarily search the public internet**.

Another employee asks:

> "What are the latest public holiday rules in India?"

If the internal HR knowledge base does not contain sufficient information, the system can use external search, evaluate the retrieved evidence, and clearly identify the response as external information requiring HR validation.

---

# 2. Business Goal

Build a secure HR Policy Copilot that:

1. Searches trusted private HR knowledge first.
2. Evaluates whether retrieved evidence is sufficient.
3. Uses web search only when private knowledge is insufficient.
4. Rewrites weak queries and retries retrieval.
5. Generates grounded responses.
6. Shows the Agentic RAG decision path.
7. Provides source/citation information.
8. Allows authorized HR administrators to ingest new documents.
9. Protects API endpoints using authentication and role-based access.
10. Records agent decisions for auditing and debugging.

---

# 3. Why This Is an FDE Project

This project is designed to demonstrate the complete lifecycle of deploying an AI solution for a business customer.

A Forward Deployed Engineer does more than build an LLM prototype.

The workflow is:

```text
Customer Problem
       ↓
Discovery & Requirements
       ↓
Solution Architecture
       ↓
Data / Knowledge Integration
       ↓
Agentic RAG Development
       ↓
API Development
       ↓
User Interface
       ↓
Authentication & Authorization
       ↓
Security + Rate Limiting
       ↓
Audit + Testing
       ↓
Dockerization
       ↓
Deployment
       ↓
Observe + Improve
```

The goal is to demonstrate how an AI prototype can be converted into a usable internal enterprise application.

---

# 4. Solution Architecture

```text
                    Employee / HR User
                           │
                           ▼
                HTML / CSS / JavaScript
                           │
                           ▼
                     FastAPI API
                           │
                  Authentication
                     + RBAC
                           │
                           ▼
              LangGraph Agent Controller
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
      Private HR KB                Tavily Search
        Pinecone                   External Web
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
                    Google Gemini
                           │
                           ▼
                 Grounded Response
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
        Source/Citations            Agent Trace
                                         │
                                         ▼
                                    SQLite Audit
```

### Core design principle

**Private company knowledge is preferred over external web information.**

The web is treated as a fallback rather than the primary source for company policy questions.

---

# 5. Agentic RAG Workflow

The system uses LangGraph to coordinate retrieval, evaluation, fallback, query rewriting, and answer generation.

```text
                         Question
                            │
                            ▼
                    [1] Route Question
                            │
              ┌─────────────┴─────────────┐
              │                           │
        Greeting / Chat              HR / Policy
              │                           │
              ▼                           ▼
        Direct Answer             [2] Retrieve
                                  Private KB
                                      │
                                      ▼
                              [3] Grade Evidence
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                       GOOD                      WEAK
                         │                         │
                         ▼                         ▼
                  Generate KB Answer        [4] Web Search
                                                   │
                                                   ▼
                                           [5] Grade Web
                                              Evidence
                                                   │
                                      ┌────────────┴────────────┐
                                      │                         │
                                    GOOD                      WEAK
                                      │                         │
                                      ▼                         ▼
                               Generate Web            [6] Rewrite Query
                                                            │
                                                            ▼
                                                    Retry Private KB
                                                            │
                                                            ▼
                                                     Max Retry?
                                                       │
                                                       ▼
                                             Insufficient Evidence
```

This prevents the application from simply retrieving documents and asking an LLM to generate an answer.

Instead, the agent evaluates whether its evidence is sufficient before generating the final response.

---

# 6. Agent State

The LangGraph workflow maintains state across the execution.

Key state fields include:

```text
question
current_query
kb_docs
web_results
kb_grade
web_grade
answer
source_used
retry_count
trace
citations
```

This allows the application to expose how the agent reached its final answer.

---

# 7. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent workflow | LangGraph | Stateful routing and conditional decisions |
| LLM | Google Gemini | Routing, grading, rewriting, and answer generation |
| Embeddings | Gemini Embeddings | Vector representation of HR documents |
| Vector DB | Pinecone | Private enterprise HR knowledge base |
| External search | Tavily | Fallback when private evidence is insufficient |
| API | FastAPI | Backend and REST API |
| Authentication | JWT | Secure user authentication |
| Authorization | RBAC | Employee vs HR Admin permissions |
| Audit | SQLite | Query and agent decision logging |
| Frontend | HTML/CSS/JavaScript | Employee-facing interface |
| Markdown rendering | marked.js | Rendering formatted responses |
| Sanitization | DOMPurify | Safe HTML rendering |
| Testing | Pytest | Automated backend tests |
| Packaging | Docker | Reproducible deployment |
| Deployment | Render | Cloud deployment |

---

# 8. Security & Access Control

The project goes beyond a simple RAG prototype by implementing application-level security.

## Authentication

Users authenticate using JWT-based authentication.

The token is stored using an:

```text
HttpOnly
SameSite=Lax
Path=/
```

cookie configuration.

## Roles

The application supports two roles:

```text
Employee
   │
   └── Can use the HR Copilot

HR Admin
   │
   ├── Can use the HR Copilot
   └── Can upload HR knowledge documents
```

## Protected endpoints

Examples:

```text
/api/me
    ↓
Authenticated users

/api/chat
    ↓
Authenticated users

/api/ingest
    ↓
HR Admin only
```

The frontend also adapts its interface based on authentication state and user role.

---

# 9. Rate Limiting

The application includes an in-memory sliding-window rate limiter.

Default limits:

```text
Normal users
    → 20 chat requests / hour

HR Admin
    → Admin chat requests exempt from normal chat limit

HR document ingestion
    → 5 requests / minute
```

This helps prevent accidental or excessive API usage.

---

# 10. Audit Logging

Each chat execution can be recorded in a SQLite audit database.

The audit information includes:

```text
Timestamp
Question
Source used
Agent trace
```

The trace allows developers or administrators to understand the workflow path taken by the agent.

For example:

```text
Router
  ↓
Private KB
  ↓
KB Grade = WEAK
  ↓
Tavily Search
  ↓
Web Grade = GOOD
  ↓
Web Answer
```

This is particularly useful for debugging Agentic RAG behavior.

---

# 11. Knowledge Base & Ingestion

The system supports ingesting HR documents into the private knowledge base.

Supported document formats include:

```text
PDF
DOCX
Markdown
TXT
```

The ingestion pipeline performs:

```text
Document
   ↓
Text Extraction
   ↓
Chunking
   ↓
Embedding Generation
   ↓
Pinecone
```

Documents are stored in the configured Pinecone namespace:

```text
company-hr-kb
```

The project also includes sample HR documents for demonstration.

---

# 12. Project Structure

```text
Enterprise-HR-Policy-Agentic-RAG/
│
├── app/
│   ├── api/
│   │   └── routes.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   │
│   ├── rag/
│   │   ├── state.py
│   │   ├── vectorstore.py
│   │   └── workflow.py
│   │
│   ├── services/
│   │   ├── audit.py
│   │   └── ingestion.py
│   │
│   └── main.py
│
├── data/
│   └── sample_kb/
│       ├── company_hr_handbook.md
│       └── hr_operations_runbook.md
│
├── docs/
│   ├── PROJECT_DOCUMENTATION.md
│   └── architecture.png
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── templates/
│   └── index.html
│
├── tests/
│
├── uploads/
│
├── Dockerfile
├── .dockerignore
├── .env.example
├── ingest_sample_kb.py
├── requirements.txt
├── run.py
├── pyproject.toml
└── README.md
```

---

# 13. Local Setup

## Step 1 — Clone the repository

```bash
git clone https://github.com/RavirajMhalsekar/Enterprise-HR-Policy-Agentic-RAG.git

cd Enterprise-HR-Policy-Agentic-RAG
```

## Step 2 — Create a virtual environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

# 14. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Then configure the required services.

Example:

```env
GOOGLE_API_KEY=your_google_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
PINECONE_API_KEY=your_pinecone_api_key

PINECONE_INDEX_NAME=company-hr-kb
PINECONE_NAMESPACE=company-hr-kb

GOOGLE_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=gemini-embedding-2

JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

DEMO_USER_USERNAME=employee
DEMO_USER_PASSWORD=change-this-password

DEMO_ADMIN_USERNAME=hr_admin
DEMO_ADMIN_PASSWORD=change-this-password

APP_ENV=development
```

> Never commit `.env` or real API keys to GitHub.

---

# 15. Load Sample HR Knowledge

Run:

```bash
python ingest_sample_kb.py
```

This loads the sample HR documents into Pinecone.

---

# 16. Run the Application

```bash
python run.py
```

Open:

```text
http://127.0.0.1:8080
```

FastAPI documentation:

```text
http://127.0.0.1:8080/docs
```

---

# 17. Docker

The application can also be run using Docker.

## Build

```bash
docker build -t hr-policy-copilot .
```

## Run

```bash
docker run --env-file .env -p 8080:8080 hr-policy-copilot
```

The container runs the application using Uvicorn and exposes port `8080`.

The Docker image also runs the application as a non-root user.

---

# 18. Demo Scenarios

## Demo A — Private KB Success

Ask:

> **How many annual leave days do employees receive?**

Expected path:

```text
Router
   ↓
Private KB Retrieval
   ↓
KB Grade → GOOD
   ↓
Generate from Private KB
```

The system should answer using internal HR documentation without unnecessary web search.

---

## Demo B — Company Policy Question

Ask:

> **How many days per week can I work remotely?**

Expected behavior:

```text
Router
   ↓
Private HR KB
   ↓
Evidence Grade → GOOD
   ↓
Grounded Answer
```

---

## Demo C — External / Current Information

Ask:

> **What are the latest public holiday rules in India?**

If the private HR knowledge base does not contain sufficient evidence:

```text
Router
   ↓
Private KB Retrieval
   ↓
KB Grade → WEAK
   ↓
Tavily Search
   ↓
Web Grade → GOOD
   ↓
External Web Answer
```

The response should make it clear that the information comes from external sources and should be validated by HR where appropriate.

---

## Demo D — Weak Query / Insufficient Evidence

Ask an ambiguous question such as:

> **What happens if mine is wrong?**

If the available evidence is insufficient:

```text
Private KB
   ↓
Weak Evidence
   ↓
Web Search
   ↓
Weak Evidence
   ↓
Query Rewrite
   ↓
Retry
   ↓
Insufficient Evidence
```

Instead of inventing an answer, the agent can stop when it cannot establish sufficient evidence.

---

## Demo E — Authentication

When an unauthenticated user attempts to ask a question:

```text
Chat Request
     ↓
Authentication Check
     ↓
Login Required
     ↓
Login Modal
     ↓
Original Question Preserved
     ↓
Authenticated Request
```

The chatbot interface remains visible, while protected actions require authentication.

---

## Demo F — HR Admin Document Upload

An HR Admin can access the document ingestion functionality.

```text
HR Admin
   ↓
Upload HR Document
   ↓
Document Processing
   ↓
Chunking
   ↓
Embedding
   ↓
Pinecone
   ↓
Available to RAG Agent
```

Normal employees do not receive access to the ingestion endpoint.

---

# 19. Testing

The project includes automated tests using Pytest.

Run:

```bash
pytest
```

The test suite covers important application behavior including:

- Authentication
- Authorization
- Protected endpoints
- Chat endpoint behavior
- Admin-only ingestion
- Rate limiting
- Health endpoint
- Core API behavior

The current implementation has been verified with:

```text
18 tests passed
```

---

# 20. FDE Implementation Lifecycle

This project intentionally demonstrates more than the RAG algorithm itself.

### 1. Discovery

Identify the HR team's actual business problem.

### 2. Requirements

Define:

- Private knowledge requirements
- External knowledge requirements
- User roles
- Security requirements
- Audit requirements
- Document ingestion requirements

### 3. Architecture

Design the complete application around:

```text
FastAPI
+
LangGraph
+
Pinecone
+
Gemini
+
Tavily
+
SQLite
```

### 4. Knowledge Integration

Connect enterprise HR documents to the retrieval system.

### 5. Agent Development

Implement:

- Routing
- Retrieval
- Evidence grading
- Web fallback
- Query rewriting
- Retry logic
- Grounded generation

### 6. Product Development

Build:

- Authentication
- RBAC
- Chat interface
- Admin upload
- Agent trace
- Source display

### 7. Security

Add:

- JWT authentication
- HttpOnly cookies
- Role-based authorization
- Rate limiting
- Secret-based configuration

### 8. Testing

Validate:

- API behavior
- Authentication
- Authorization
- Rate limits
- Agent behavior

### 9. Deployment

Package the application with Docker and deploy it to Render.

### 10. Iteration

The architecture is designed to support future improvements such as:

- Better retrieval evaluation
- More granular permissions
- Persistent rate limiting
- Observability
- Human feedback loops
- Production identity providers
- More advanced document lifecycle management

---

# 21. Production Considerations

This project is designed as a portfolio/FDE simulation rather than a production HR system.

For a real enterprise deployment, additional controls would be appropriate.

Examples include:

- Enterprise SSO / OAuth / OIDC
- Persistent distributed rate limiting
- Secrets management
- Managed database instead of local SQLite
- Centralized logging
- Application monitoring
- Structured observability
- Document versioning
- Document-level access control
- Backup and disaster recovery
- Human approval workflows
- Formal security review
- Compliance and privacy assessment

The current project intentionally keeps the architecture understandable while demonstrating the major engineering concerns involved in deploying an Agentic RAG application.

---

# 22. Key Engineering Decisions

### Private KB First

Company policy questions should primarily use trusted internal documentation.

### Evidence Grading

Retrieval does not automatically mean the evidence is sufficient.

The system evaluates retrieved context before generating an answer.

### Web Search as Fallback

External search is used only when private knowledge is insufficient.

### Query Rewriting

Weak queries can be reformulated before another retrieval attempt.

### Explicit Failure

When sufficient evidence cannot be established, the system can return an insufficient-evidence response instead of fabricating policy information.

### Agent Trace

The decision path is exposed for transparency and debugging.

### Authentication + RBAC

The project treats the RAG application as an actual internal product rather than an unauthenticated demo.

### Dockerized Deployment

The application can be packaged and deployed consistently across environments.

---

# 23. What Changed From the IT Support Reference

This project is based on an Agentic RAG architecture originally designed around an IT support use case.

The underlying engineering pattern was adapted to an HR domain.

The following concepts were retained:

- LangGraph workflow
- Conditional graph routing
- Retrieval pipeline
- Evidence grading
- External search fallback
- Query rewriting
- API architecture
- Document ingestion
- Audit logging
- Docker deployment
- Frontend interaction model

The domain-specific components were changed to represent an enterprise HR environment:

- HR prompts
- HR policies
- HR configuration
- HR terminology
- Employee workflows
- HR administrator role
- HR knowledge documents
- HR UI wording
- HR demo scenarios

---

# 24. Project Outcome

The final system demonstrates how an AI engineer can take an Agentic RAG concept and turn it into a deployable business application.

It combines:

```text
Business Problem
       +
Agentic AI
       +
Enterprise Data
       +
Backend Engineering
       +
Frontend Development
       +
Authentication
       +
Authorization
       +
Security
       +
Testing
       +
Docker
       +
Cloud Deployment
```

The result is a complete FDE-style AI product rather than a standalone LLM or RAG prototype.

---

## 📚 Documentation

For the detailed technical implementation, see:

[`docs/PROJECT_DOCUMENTATION.md`](docs/PROJECT_DOCUMENTATION.md)

The documentation covers:

- System architecture
- LangGraph state machine
- Agent nodes
- Retrieval flow
- Ingestion pipeline
- API contracts
- Authentication
- RBAC
- Rate limiting
- Audit logging
- Environment configuration
- Testing
- Deployment

---

## ⚠️ Disclaimer

NovaRetail is a fictional company created for this project.

All HR policies, employee information, and business data used in the demonstration are fictional.

This project is intended for educational, portfolio, and engineering demonstration purposes and is **not legal or HR advice**.

---

## 👨‍💻 Author

**Raviraj Mhalsekar**

Generative AI Engineer | Full-Stack Engineer

GitHub:  
https://github.com/RavirajMhalsekar
