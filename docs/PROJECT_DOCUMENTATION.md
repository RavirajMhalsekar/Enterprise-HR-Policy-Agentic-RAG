# Enterprise HR Policy & Employee Support Agentic RAG Copilot
## Comprehensive System Architecture & Workflow Documentation

---

## 1. Executive Summary & Business Context

### 1.1 Business Problem Statement
In modern mid-to-large enterprises (such as the reference enterprise **NovaRetail**, with ~3,000 employees), human resources teams manage voluminous, fragmented internal policy documentation:
- Employee handbooks (leave entitlement, benefits, workplace conduct)
- Standard Operating Procedures & HR Operations Runbooks
- Remote work, attendance, and expense reimbursement guidelines
- Performance review and grievance redressal mechanisms

#### Core Challenges:
1. **Information Fragmentation**: Employees struggle to navigate multiple documents and portals, generating high volumes of repetitive inquiries for HR teams.
2. **Hallucination Risk**: Off-the-shelf generative AI chatbots often fabricate policy rules, vacation day allowances, or compliance steps when answers are absent or vague.
3. **Dynamic vs. Private Boundaries**: Questions often blend private company policies (e.g., "How many sick days do I have?") with external regulatory or jurisdiction-specific information (e.g., "What are the statutory public holidays in Bangladesh or India?").
4. **Lack of Transparency & Auditability**: Enterprise HR operations require strict verification of how and why an AI agent arrived at a specific policy recommendation.

### 1.2 The Forward Deployed Engineer (FDE) Solution
This project implements an end-to-end, production-grade **Agentic Retrieval-Augmented Generation (Agentic RAG) Copilot**. Unlike static RAG pipelines, this system operates as an autonomous state machine that:
- **Routes** incoming user intent to avoid unnecessary vector search overhead for conversational greetings.
- **Prioritizes Private Enterprise Knowledge**: Queries internal HR vectors first via **Pinecone**.
- **Self-Reflects & Evaluates (Grading)**: Uses LLM-as-a-Judge grading to assess evidence sufficiency and specificity.
- **Falls Back to Public Web Search**: Triggers **Tavily Search** only when private knowledge is insufficient or missing, attaching clear verification disclaimers.
- **Self-Corrects with Query Rewriting**: Iteratively reformulates ambiguous or underspecified queries before re-querying the knowledge base.
- **Provides Transparent Audit Trails**: Logs every decision step, retrieval score, and execution trace to an **SQLite** audit store and exposes it directly in an interactive UI Trace Drawer.

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
                               ┌─────────────────────────────────────────┐
                               │           Employee / HR Admin           │
                               └────────────────────┬────────────────────┘
                                                    │
                                      HTTP / JSON   │ (POST /api/chat, POST /api/ingest)
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │       FastAPI Application Server        │
                               │  - Request Validation (Pydantic)       │
                               │  - Security & Authentication            │
                               │  - Static & Jinja2 Template Serving     │
                               └─────────┬─────────────────────┬─────────┘
                                         │                     │
                    ┌────────────────────┘                     └────────────────────┐
                    ▼                                                               ▼
  ┌──────────────────────────────────┐                            ┌───────────────────────────────────┐
  │   LangGraph Agentic Controller   │                            │      Document Ingestion Pipeline  │
  │   (StateGraph Workflow Engine)   │                            │  - Multi-format parser (PDF,DOCX) │
  └─────────┬──────────────┬─────────┘                            │  - Recursive Character Splitter   │
            │              │                                      └─────────────────┬─────────────────┘
            │              │                                                        │
   Embeddings / LLM   Web Fallback                                             Embeddings
            │              │                                                        │
            ▼              ▼                                                        ▼
  ┌──────────────────┐  ┌──────────────────┐                      ┌───────────────────────────────────┐
  │  Google Gemini   │  │  Tavily Search   │                      │        Pinecone Vector DB         │
  │  - gemini-2.5-   │  │  (Public Web     │                      │  - Serverless Index (AWS us-east) │
  │    flash (LLM)   │  │   Search API)    │                      │  - Namespace: company-hr-kb       │
  │  - gemini-       │  └──────────────────┘                      │  - Dimension: 3072 (Cosine)       │
  │    embedding-2   │                                            └─────────────────┬─────────────────┘
  └──────────────────┘                                                              │
            │                                                                       │
            └────────────────────── Vector Retrieval (top_k=4) ─────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │       SQLite Audit Database             │
                               │  - Table: query_audit                   │
                               │  - Full trace JSON + Timestamps         │
                               └─────────────────────────────────────────┘
```

---

## 3. Technology Stack & Component Inventory

| Component / Layer | Technology | Version / Specific Model | Function & Role |
| :--- | :--- | :--- | :--- |
| **Agentic Framework** | `LangGraph` | `1.1.10` | Implements stateful, cyclical graph execution, routing, conditional transitions, and retry loops. |
| **Core LLM Orchestration** | `LangChain Core` / `Community` | `1.6.1` / `0.4.2` | Structured LLM output schemas, document loaders, vector store interfaces, and prompts. |
| **Generative LLM** | Google Gemini (`langchain-google-genai`) | `gemini-2.5-flash` | Decision routing, evidence grading, query rewriting, and grounded response synthesis. |
| **Embedding Engine** | Google Generative AI Embeddings | `gemini-embedding-2` | 3,072-dimensional vector embedding model for high-precision semantic search. |
| **Vector Database** | `Pinecone` / `langchain-pinecone` | Serverless `7.3.0` (`0.2.13`) | Managed cloud vector database for private enterprise HR knowledge with namespace isolation. |
| **External Search API** | `Tavily Search` / `langchain-tavily` | `0.2.18` | Search engine optimized for LLMs to retrieve real-time external public information. |
| **Backend REST API** | `FastAPI` + `Uvicorn` | `0.116.1` / `0.35.0` | High-performance asynchronous backend server exposing `/api/chat`, `/api/ingest`, and `/api/health`. |
| **Configuration & Models** | `Pydantic` & `pydantic-settings` | `2.10.1` | Strictly typed environment parsing (`.env`), validation aliases, and API schemas. |
| **Document Parsers** | `PyPDF`, `python-docx`, `TextLoader` | `6.16.2` / `1.2.0` | Ingestion pipeline supporting `.pdf`, `.docx`, `.md`, and `.txt` documents. |
| **Text Chunking** | `RecursiveCharacterTextSplitter` | `1.1.2` | Splits documents into 1,000-character chunks with 200-character overlap and start index tracking. |
| **Audit Logging** | `SQLite3` | Built-in Python standard library | Local embedded database recording query history, source attributions, and serialized execution traces. |
| **Frontend UI** | HTML5, Modern CSS, Vanilla JS | ES6+ Standard | Clean corporate UI with live chat, dynamic sidebar document listing, and trace drawer. |
| **Client-Side Rendering** | `marked.js` + `DOMPurify` | CDN Releases | Secure Markdown parsing and HTML sanitization for LLM responses. |


---

## 4. Agentic RAG Workflow & LangGraph State Machine

### 4.1 State Schema (`AgentState`)
The agent maintains and mutates a structured state dictionary across graph nodes:

```python
class AgentState(TypedDict):
    question: str               # Original user input question
    current_query: str          # Current query (original or rewritten)
    kb_docs: List[Document]     # Retrieved chunks from Pinecone
    web_results: str            # Raw formatted results from Tavily
    kb_grade: str               # "good" | "weak"
    web_grade: str              # "good" | "weak"
    answer: str                 # Final synthesized answer
    source_used: str            # "private_kb" | "web" | "direct" | "insufficient_evidence"
    retry_count: int            # Integer count of query rewrites (max: 2)
    trace: List[str]            # Step-by-step audit breadcrumbs
    citations: List[dict]       # Source citation objects ({title, url, type})
```

### 4.2 Graph Topology & Decision Flow

```
                                 [ START ]
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ route_question  │
                            └────────┬────────┘
                                     │
                    ┌────────────────┴────────────────┐
          (route == "direct")               (route == "kb")
                    │                                 │
                    ▼                                 ▼
          ┌──────────────────┐              ┌──────────────────┐
          │  direct_answer   │              │   retrieve_kb    │
          └─────────┬────────┘              └─────────┬────────┘
                    │                                 │
                    │                                 ▼
                    │                       ┌──────────────────┐
                    │                       │     grade_kb     │
                    │                       └─────────┬────────┘
                    │                                 │
                    │                   ┌─────────────┴─────────────┐
                    │          (kb_grade == "good")        (kb_grade == "weak")
                    │                   │                           │
                    │                   ▼                           ▼
                    │         ┌──────────────────┐        ┌──────────────────┐
                    │         │ generate_from_kb │        │    search_web    │
                    │         └─────────┬────────┘        └─────────┬────────┘
                    │                   │                           │
                    │                   │                           ▼
                    │                   │                 ┌──────────────────┐
                    │                   │                 │    grade_web     │
                    │                   │                 └─────────┬────────┘
                    │                   │                           │
                    │                   │        ┌──────────────────┼──────────────────┐
                    │                   │  (grade == "good")  (weak & retry < max) (weak & retry >= max)
                    │                   │        │                  │                  │
                    │                   │        ▼                  ▼                  ▼
                    │                   │ ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
                    │                   │ │generate_from_│   │ rewrite_query │   │ insufficient │
                    │                   │ │     web      │   └───────┬───────┘   └──────┬───────┘
                    │                   │ └──────┬───────┘           │                  │
                    │                   │        │            (retry_count + 1)         │
                    │                   │        │                   │                  │
                    │                   │        │        [Loop back to retrieve_kb]    │
                    │                   │        │                   │                  │
                    ▼                   ▼        ▼                   └──────────────────┤
                 [ END ]             [ END ]  [ END ]                                [ END ]
```


### 4.3 Detailed Node Execution Logic

#### 1. `route_question`
- **Purpose**: Discerns whether incoming inquiry demands internal HR knowledge retrieval or is casual conversational text.
- **Implementation**: Uses `llm.with_structured_output(RouteDecision, method="json_mode")`.
- **Decision Criteria**:
  - `kb`: Queries regarding leave policies, benefits, salary/payroll, performance reviews, remote work guidelines, onboarding, conduct, or general HR support.
  - `direct`: Greetings ("hi", "hello"), acknowledgments ("thanks"), or non-policy chit-chat.
- **Next Transition**: Evaluated by `route_after_router`:
  - If `route == "kb"` $\rightarrow$ `retrieve_kb`
  - If `route == "direct"` $\rightarrow$ `direct_answer`

#### 2. `direct_answer`
- **Purpose**: Generates natural, concise conversational replies without accessing the vector database.
- **Metadata**: Sets `source_used = "direct"`.
- **Next Transition**: $\rightarrow$ `END`.

#### 3. `retrieve_kb`
- **Purpose**: Executes similarity search against the Pinecone index using Google `gemini-embedding-2` representations.
- **Parameters**: `top_k = settings.top_k` (default: 4 chunks), filtered by namespace `company-hr-kb`.
- **Next Transition**: $\rightarrow$ `grade_kb`.

#### 4. `grade_kb`
- **Purpose**: Assesses whether the retrieved private chunks contain sufficient, unambiguous facts to answer the specific employee question.
- **Implementation**: Structured output with `EvidenceGrade` schema (`grade: Literal["good", "weak"]`).
- **Prompt Guardrails**: Returns `good` *only* if context is directly relevant and sufficient; otherwise flags `weak`.
- **Next Transition**: Evaluated by `after_kb`:
  - If `kb_grade == "good"` $\rightarrow$ `generate_from_kb`
  - If `kb_grade == "weak"` $\rightarrow$ `search_web`

#### 5. `generate_from_kb`
- **Purpose**: Generates grounded, policy-compliant response strictly synthesized from internal documents.
- **Guardrails**: Explicitly prohibited from fabricating details; extracts document sources for structured citation rendering.
- **Metadata**: Sets `source_used = "private_kb"`.
- **Next Transition**: $\rightarrow$ `END`.

#### 6. `search_web`
- **Purpose**: Fallback mechanism invoking Tavily Search API with `max_results=5` and `topic="general"`.
- **Content Extraction**: Parses textual snippets, search answer, titles, and source URLs.
- **Next Transition**: $\rightarrow$ `grade_web`.

#### 7. `grade_web`
- **Purpose**: Evaluates public search results for direct relevance and adequacy.
- **Implementation**: Structured output with `EvidenceGrade` schema.
- **Next Transition**: Evaluated by `after_web`:
  - If `web_grade == "good"` $\rightarrow$ `generate_from_web`
  - If `web_grade == "weak"` and `retry_count < max_retries` $\rightarrow$ `rewrite_query`
  - If `web_grade == "weak"` and `retry_count >= max_retries` $\rightarrow$ `insufficient`

#### 8. `generate_from_web`
- **Purpose**: Synthesizes response from external search findings.
- **Safety Policy**: Mandates a clear disclaimer stating the information is from public sources and must be validated with HR before treating as official company policy.
- **Metadata**: Sets `source_used = "web_search"`.
- **Next Transition**: $\rightarrow$ `END`.

#### 9. `rewrite_query`
- **Purpose**: Reformulates ambiguous, incomplete, or underspecified queries to improve semantic retrieval.
- **Implementation**: Prompts LLM to preserve intent while injecting standard enterprise HR terminology.
- **State Mutation**: Increments `retry_count` by 1; updates `current_query`.
- **Loopback**: Re-routes back to `retrieve_kb` to retry the full retrieval-grading cycle.

#### 10. `insufficient`
- **Purpose**: Graceful fallback when neither private documents nor web search provide verified facts.
- **Safety Output**: Standardized safe notice advising the employee to consult an HR representative directly.
- **Metadata**: Sets `source_used = "insufficient_evidence"`.
- **Next Transition**: $\rightarrow$ `END`.


---

## 5. Knowledge Base & Document Ingestion Pipeline

### 5.1 Document Processing Lifecycle

```
[ Uploaded Document (.pdf, .docx, .md, .txt) ]
                      │
                      ▼
[ Document Loader (PyPDFLoader / TextLoader / DocxDocument) ]
                      │
                      ▼
[ RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200) ]
                      │
                      ▼
[ Embedding Generation (Google gemini-embedding-2 / 3072 dims) ]
                      │
                      ▼
[ Pinecone Vector Store (Namespace: company-hr-kb, Metric: Cosine) ]
```

### 5.2 Supported Formats & Loaders
- **Markdown / Plain Text (`.md`, `.txt`)**: Loaded via `langchain_community.document_loaders.TextLoader(encoding="utf-8")`.
- **PDF Documents (`.pdf`)**: Loaded via `langchain_community.document_loaders.PyPDFLoader`.
- **Word Documents (`.docx`)**: Loaded and parsed paragraph-by-paragraph via `python-docx.Document`.

### 5.3 Vector Store & Index Architecture
- **Vector Database**: Pinecone Serverless Index (`aws` / `us-east-1`).
- **Embedding Dimensions**: `3,072` (matching `gemini-embedding-2` embedding matrix).
- **Distance Metric**: `cosine`.
- **Namespace Isolation**: All HR documents reside under `settings.pinecone_namespace` (default: `company-hr-kb`).
- **Auto-Provisioning**: `app/rag/vectorstore.py::ensure_index()` automatically checks index existence on startup and provisions serverless resources if absent.

---

## 6. REST API Specification & Authentication

The backend exposes a fully typed REST API with automatic OpenAPI documentation available at `/docs`.

### 6.1 Endpoints Summary

| Method | Endpoint | Description | Auth & Role Required | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves main Web UI via Jinja2 template (`templates/index.html`). | None (Public) | None |
| `GET` | `/api/health` | Health status and service metadata. | None (Public) | None |
| `POST` | `/login` / `/api/login` | Authenticates user/admin and sets `HttpOnly` JWT cookie. | None (Public) | None |
| `POST` | `/logout` / `/api/logout`| Clears the `HttpOnly` session cookie. | None | None |
| `GET` | `/api/me` | Returns profile of current authenticated user. | Authenticated (`user` or `admin`) | None |
| `POST` | `/api/chat` | Main Agentic RAG chat completion endpoint. | Authenticated (`user` or `admin`) | 20 req/hr (User only; Admin exempt) |
| `POST` | `/api/ingest` | Admin endpoint for uploading & indexing HR policy files. | Authenticated (`admin` role required) | 5 req/min |

### 6.2 Endpoint Details

#### `POST /login` (and `/api/login`)
**Request Body**:
```json
{
  "username": "user@novaretail.com",
  "password": "UserPasswordHere"
}
```

**Response (200 OK)**:
```json
{
  "status": "ok",
  "message": "Login successful",
  "user": {
    "username": "user@novaretail.com",
    "role": "user"
  }
}
```
*Sets `Set-Cookie: access_token=<jwt>; HttpOnly; Path=/; SameSite=Lax`*

#### `POST /logout` (and `/api/logout`)
**Response (200 OK)**:
```json
{
  "status": "ok",
  "message": "Successfully logged out."
}
```
*Clears `access_token` cookie.*

#### `GET /api/me`
**Response (200 OK)**:
```json
{
  "username": "user@novaretail.com",
  "role": "user"
}
```

#### `POST /api/chat`
**Headers**: `Cookie: access_token=<jwt>`  
**Request Body**:
```json
{
  "question": "How many days of annual leave do full-time employees receive?"
}
```

**Response (200 OK)**:
```json
{
  "answer": "Based on the company's private knowledge base, full-time employees are entitled to 20 days of paid annual leave per calendar year...",
  "source_used": "private_kb",
  "trace": [
    "Router → KB",
    "Private KB retrieval → 4 chunks",
    "KB evidence grade → GOOD",
    "Answer generation → PRIVATE KB"
  ],
  "citations": [
    {
      "title": "company_hr_handbook.md",
      "url": "",
      "type": "private_kb"
    }
  ],
  "rewritten_query": "How many days of annual leave do full-time employees receive?"
}
```
*Rate Limit (429 Too Many Requests) triggers on the 21st request/hr for `user` role with `Retry-After` header.*

#### `POST /api/ingest`
**Headers**: `Cookie: access_token=<admin_jwt>`, `Content-Type: multipart/form-data`  
**Request Form Data**:
- `file`: Binary file (`.pdf`, `.docx`, `.md`, or `.txt`)

**Response (200 OK)**:
```json
{
  "message": "Document indexed",
  "file": "remote_work_policy_2026.pdf",
  "chunks": 8,
  "ids_created": 8
}
```
*Requires `admin` role (returns `403 Forbidden` for standard users). Rate limit is 5 req/min.*


---

## 7. Audit & Decision Trace Logging

To ensure enterprise compliance and support observability:

### 7.1 SQLite Audit Schema
Database Path: `data/audit.db`  
Table Name: `query_audit`

```sql
CREATE TABLE IF NOT EXISTS query_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    question TEXT NOT NULL,
    source_used TEXT NOT NULL,
    trace_json TEXT NOT NULL
);
```

### 7.2 Audit Record Fields
- `created_at`: ISO-8601 UTC timestamp (e.g. `2026-09-25T06:58:00.000000+00:00`).
- `question`: Verbatim user input query.
- `source_used`: Source attribution tag (`private_kb`, `web_search`, `direct`, `insufficient_evidence`).
- `trace_json`: Serialized JSON array capturing all LangGraph node transitions and evaluations.

---

## 8. Frontend Architecture & User Interface

The application features a responsive, single-page interface built with modern vanilla web technologies:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 HR Policy Copilot UI                                   │
├──────────────────────┬──────────────────────────────────────────┬──────────────────────┤
│       SIDEBAR        │                CHAT AREA                 │     TRACE DRAWER     │
│                      │                                          │                      │
│ [Brand Logo & Title] │ [Welcome Banner & Sample Question Chips] │ [Execution Steps]    │
│ [+ Upload Documents] │                                          │                      │
│                      │ [Chat History Stream]                    │ 1. Router → KB       │
│ Navigation:          │  - User message balloons                 │ 2. KB retrieval (4)  │
│  - Chat              │  - Copilot markdown answers              │ 3. Grade → GOOD      │
│  - Documents         │  - Source attribution badge              │ 4. Answer generation │
│                      │  - Inline source citations               │                      │
│ Uploaded Documents:  │                                          │ [Source: Private KB] │
│  - handbook.md       │ [Input Box + Submit Action]              │ [Execution Time]     │
│  - runbook.md        │                                          │                      │
└──────────────────────┴──────────────────────────────────────────┴──────────────────────┘
```

### Key UI Features:
1. **Source Badges**: Visually distinguishes whether an answer originates from `Private Knowledge Base`, `Public Web Search`, or `Direct Assistant`.
2. **Interactive Trace Drawer**: Users and administrators can open the right-side drawer to view the exact step-by-step decision sequence produced by LangGraph.
3. **Safe Markdown Rendering**: Uses `marked.js` with `DOMPurify` to render rich markdown formatting (tables, bullet lists, code blocks) safely without XSS vulnerabilities.
4. **Knowledge Base Upload Modal**: Secure, in-browser file uploader with drag-and-drop support, format validation, and admin key entry.


---

## 9. Configuration & Environment Variables

All settings are managed via `app/core/config.py` using Pydantic Settings and loaded from the root `.env` file (no secrets are hardcoded in source code):

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `GOOGLE_API_KEY` | `string` | `""` | Google AI Studio API key for Gemini models and embeddings. |
| `GOOGLE_MODEL` | `string` | `gemini-2.5-flash` | Gemini model name for routing, grading, and synthesis. |
| `EMBEDDING_MODEL` | `string` | `gemini-embedding-2` | Google embedding model (3072 dimensions). |
| `PINECONE_API_KEY` | `string` | `""` | Pinecone API key for serverless vector database. |
| `PINECONE_INDEX_NAME` | `string` | `enterprise-hr-policy-agentic-rag` | Name of the Pinecone serverless vector index. |
| `PINECONE_NAMESPACE` | `string` | `company-hr-kb` | Logical namespace partitioning HR vectors in Pinecone. |
| `TAVILY_API_KEY` | `string` | `""` | Tavily API key for fallback web search. |
| `JWT_SECRET_KEY` | `string` | `""` | Secret signing key for HS256 JWT creation and verification. |
| `JWT_ALGORITHM` | `string` | `HS256` | JWT signature algorithm. |
| `JWT_EXPIRE_MINUTES` | `integer` | `120` | Session lifetime before expiration (minutes). |
| `DEMO_USER_USERNAME` | `string` | `""` | Configured username for Employee demo account. |
| `DEMO_USER_PASSWORD` | `string` | `""` | Configured password for Employee demo account. |
| `DEMO_ADMIN_USERNAME` | `string` | `""` | Configured username for Admin demo account. |
| `DEMO_ADMIN_PASSWORD` | `string` | `""` | Configured password for Admin demo account. |
| `TOP_K` | `integer` | `4` | Number of document chunks retrieved per query. |
| `MAX_RETRIES` | `integer` | `2` | Maximum query rewrite attempts on weak evidence. |
| `APP_ENV` | `string` | `development` | Deployment environment mode (`development` / `production`). |

---

## 10. Operations & Execution Guide

### 10.1 Local Environment Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install project dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your keys, JWT_SECRET_KEY, and demo credentials
```

### 10.2 Knowledge Base Ingestion
```bash
# Ingest default sample HR documents (Handbook and Operations Runbook)
python ingest_sample_kb.py
```

### 10.3 Running Tests
```bash
# Run the automated test suite
pytest -v
```

### 10.4 Starting the Application Server
```bash
# Launch FastAPI server on http://127.0.0.1:8080
python run.py
```

### 10.5 Demo Verification Scenarios

| Scenario | Sample Action / Prompt | Expected Path & Behavior |
| :--- | :--- | :--- |
| **A. Unauthenticated Query** | Submit question without signing in | UI opens Login Modal; API returns `401 Unauthorized`. |
| **B. Employee Login** | Sign in with `user@novaretail.com` | Success; receives `HttpOnly` JWT cookie. "Upload Documents" button is hidden. |
| **C. Internal Policy Match** | *"How many days of annual leave do employees receive?"* | Router $\rightarrow$ `retrieve_kb` $\rightarrow$ `grade_kb` (GOOD) $\rightarrow$ `generate_from_kb`. Answer cites internal handbook. |
| **D. Casual Greeting** | *"Good morning! How can you help me today?"* | Router $\rightarrow$ `direct_answer`. Responds immediately without vector search. |
| **E. External Information Fallback** | *"What are the official public holidays in Bangladesh for 2026?"* | Router $\rightarrow$ `retrieve_kb` $\rightarrow$ `grade_kb` (WEAK) $\rightarrow$ `search_web` $\rightarrow$ `grade_web` (GOOD) $\rightarrow$ `generate_from_web`. Includes public info disclaimer. |
| **F. Rate Limiting** | Send >20 questions/hr as regular user | API triggers HTTP `429 Too Many Requests` with `Retry-After` header. |
| **G. Admin Login & Ingest** | Sign in with `admin@novaretail.com` | "Upload Documents" button appears. Ingestion succeeds; rate limited to 5 req/min. |


