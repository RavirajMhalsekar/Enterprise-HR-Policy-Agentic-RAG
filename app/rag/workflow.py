import logging
import os
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from app.core.config import get_settings
from app.rag.state import AgentState, RouteDecision, EvidenceGrade
from app.rag.vectorstore import get_retriever

logger = logging.getLogger(__name__)
settings = get_settings()


_llm = None
_web_search = None


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text", "")))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


# Initialize the Google Generative AI model
llm = ChatGoogleGenerativeAI(
    model=settings.google_model,
    google_api_key=settings.google_api_key or None,
    temperature=0.1,
)


def web_search_tool():
    global _web_search
    if _web_search is None:
        if not settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is missing")
        _web_search = TavilySearch(
            tavily_api_key=settings.tavily_api_key,
            max_results=5,
            topic="general",
            include_answer=True,
            include_raw_content=False,
        )
    return _web_search


def add_trace(state: AgentState, message: str):
    return [*state.get("trace", []), message]


def route_question(state: AgentState):
    router = llm.with_structured_output(RouteDecision, method="json_mode")
    decision = router.invoke(f"""
You route messages for an enterprise HR policy and employee support assistant.
Use kb for questions about company HR policies, leave, holidays, benefits, payroll,
remote work, attendance, onboarding, performance, expenses, travel, conduct, or employee support.
Use direct only for greetings, thanks, or casual chat that needs no company knowledge.
Question: {state['question']}
Return valid JSON like {{"route":"kb"}}.
""")
    return {"source_used": decision.route, "trace": add_trace(state, f"Router → {decision.route.upper()}")}



def route_after_router(state: AgentState) -> Literal["retrieve_kb", "direct_answer"]:
    return "retrieve_kb" if state["source_used"] == "kb" else "direct_answer"



def retrieve_kb(state: AgentState):
    docs = get_retriever().invoke(state["current_query"])
    return {"kb_docs": docs, "trace": add_trace(state, f"Private KB retrieval → {len(docs)} chunks")}


def grade_kb(state: AgentState):
    grader = llm.with_structured_output(EvidenceGrade, method="json_mode")
    context = "\n\n".join(f"Source: {d.metadata.get('source','unknown')}\n{d.page_content}" for d in state["kb_docs"])
    grade = grader.invoke(f"""
You grade evidence for an enterprise HR policy and employee support assistant.
Question: {state['question']}
Private company HR KB evidence:\n{context}
Return good only if the evidence is sufficient to answer confidently and specifically.
Otherwise return weak. JSON: {{"grade":"good"}} or {{"grade":"weak"}}.
""")
    return {"kb_grade": grade.grade, "trace": add_trace(state, f"KB evidence grade → {grade.grade.upper()}")}



def after_kb(state: AgentState) -> Literal["generate_from_kb", "search_web"]:
    return "generate_from_kb" if state["kb_grade"] == "good" else "search_web"



def search_web(state: AgentState):
    result = web_search_tool().invoke({"query": state["current_query"]})
    lines, citations = [], []
    if isinstance(result, dict):
        if result.get("answer"):
            lines.append("Search answer: " + result["answer"])
        for item in result.get("results", []):
            title, url, content = item.get("title", ""), item.get("url", ""), item.get("content", "")
            lines.append(f"Title: {title}\nURL: {url}\nContent: {content}")
            citations.append({"title": title or url, "url": url, "type": "web"})
    else:
        lines.append(str(result))
    return {
        "web_results": "\n\n".join(lines),
        "citations": citations,
        "source_used": "web",
        "trace": add_trace(state, "Web fallback → Tavily search"),
    }



def grade_web(state: AgentState):
    grader = llm.with_structured_output(EvidenceGrade, method="json_mode")
    grade = grader.invoke(f"""
Question: {state['question']}
Web evidence:\n{state['web_results']}
Return good if the evidence is sufficient and directly relevant; otherwise weak.
Return valid JSON like {{"grade":"good"}}.
""")
    return {"web_grade": grade.grade, "trace": add_trace(state, f"Web evidence grade → {grade.grade.upper()}")}



def after_web(state: AgentState) -> Literal["generate_from_web", "rewrite_query", "insufficient"]:
    if state["web_grade"] == "good":
        return "generate_from_web"
    if state["retry_count"] < settings.max_retries:
        return "rewrite_query"
    return "insufficient"




def rewrite_query(state: AgentState):
    resp = llm.invoke(f"""
Rewrite this HR/employee-support question for better private knowledge retrieval and public web search.
Preserve intent, add useful HR/policy keywords, do not answer, return only the query.
Question: {state['question']}
""")
    rewritten = _extract_text(resp.content).strip()
    return {
        "current_query": rewritten,
        "retry_count": state["retry_count"] + 1,
        "trace": add_trace(state, f"Query rewrite → {rewritten}"),
    }



HR_COPILOT_SYSTEM_PROMPT = """You are the NovaRetail HR Policy & Employee Support Copilot, an internal enterprise AI assistant for NovaRetail employees and managers.

Your scope and capabilities include:
1. Company HR policies: Annual leave, sick leave, parental leave, bereavement leave, and public holiday entitlements.
2. Remote work & flexible work schedules and guidelines.
3. Employee benefits: Healthcare, wellness stipends, and retirement plans.
4. Payroll schedules, salary questions, expense reimbursements, and travel allowances.
5. Workplace conduct, anti-harassment policies, performance reviews, and grievance procedures.
6. New hire onboarding requirements and documentation.
7. HR Operations runbooks and standard operating procedures.

Persona & Tone Guidelines:
- Professional, empathetic, structured, and helpful.
- When an employee greets you or asks who you are / what you can help with, introduce yourself as NovaRetail's HR Policy Copilot and outline your HR policy capabilities.
- If an employee asks an out-of-scope non-HR question (such as writing general software code, creative fiction, or general internet browsing), politely clarify that you specialize strictly in NovaRetail HR policy and employee support."""


def generate_from_kb(state: AgentState):
    context = "\n\n".join(f"[Source: {d.metadata.get('source','unknown')}]\n{d.page_content}" for d in state["kb_docs"])
    resp = llm.invoke(f"""{HR_COPILOT_SYSTEM_PROMPT}

Task: Answer the employee's question ONLY using the private company HR KB evidence below.
Be concise, practical, respectful, and policy-grounded. Present steps clearly when applicable.
Do not invent policy details. Mention that the answer is based on the company's private knowledge base.

Question: {state['question']}

Private KB Evidence:
{context}
""")
    answer = _extract_text(resp.content)
    citations = []
    seen = set()
    for d in state["kb_docs"]:
        src = d.metadata.get("source", "Private KB")
        if src not in seen:
            seen.add(src)
            citations.append({"title": src.split("/")[-1], "url": "", "type": "private_kb"})
    return {"answer": answer, "source_used": "private_kb", "citations": citations, "trace": add_trace(state, "Answer generation → PRIVATE KB")}



def generate_from_web(state: AgentState):
    resp = llm.invoke(f"""{HR_COPILOT_SYSTEM_PROMPT}

Task: The private company HR KB was insufficient. Answer the question ONLY from the web evidence below.
Clearly state that this is external public information and may require HR validation before being treated as official company policy or employment guidance.

Question: {state['question']}

Web Evidence:
{state['web_results']}
""")
    answer = _extract_text(resp.content)
    return {"answer": answer, "source_used": "web_search", "trace": add_trace(state, "Answer generation → WEB SEARCH")}



def direct_answer(state: AgentState):
    prompt = f"""{HR_COPILOT_SYSTEM_PROMPT}

Employee Message: {state['question']}

Instruction:
- If the employee asks who you are or what you can help with, introduce yourself as the NovaRetail HR Policy Copilot and clearly summarize the key HR topics you cover (leave, remote work, benefits, payroll, onboarding, workplace conduct).
- If the employee sends a greeting (e.g. "hi", "hello", "good morning"), greet them warmly and ask how you can assist with company HR policies.
- If the message is a polite closing or thank you, respond warmly.
- If the message is completely out-of-scope (e.g. writing software code, general trivia), politely explain that you are dedicated to NovaRetail HR support and guide them to ask HR questions.
Respond concisely and naturally in clear formatting.
"""
    resp = llm.invoke(prompt)
    answer = _extract_text(resp.content)
    return {"answer": answer, "source_used": "direct", "trace": add_trace(state, "Direct response → no retrieval")}






def insufficient(state: AgentState):
    return {
        "answer": "I couldn't find enough reliable evidence in the company HR knowledge base or external search to answer confidently. Please contact the HR team or provide more details.",
        "source_used": "insufficient_evidence",
        "trace": add_trace(state, "Stopped → insufficient reliable evidence"),
    }



def build_graph():
    graph = StateGraph(AgentState)
    for name, fn in {
        "route_question": route_question,
        "retrieve_kb": retrieve_kb,
        "grade_kb": grade_kb,
        "search_web": search_web,
        "grade_web": grade_web,
        "rewrite_query": rewrite_query,
        "generate_from_kb": generate_from_kb,
        "generate_from_web": generate_from_web,
        "direct_answer": direct_answer,
        "insufficient": insufficient,
    }.items():
        graph.add_node(name, fn)
    graph.add_edge(START, "route_question")
    graph.add_conditional_edges("route_question", route_after_router, {
        "retrieve_kb": "retrieve_kb", "direct_answer": "direct_answer"
    })
    graph.add_edge("retrieve_kb", "grade_kb")
    graph.add_conditional_edges("grade_kb", after_kb, {
        "generate_from_kb": "generate_from_kb", "search_web": "search_web"
    })
    graph.add_edge("search_web", "grade_web")
    graph.add_conditional_edges("grade_web", after_web, {
        "generate_from_web": "generate_from_web", "rewrite_query": "rewrite_query", "insufficient": "insufficient"
    })
    graph.add_edge("rewrite_query", "retrieve_kb")
    graph.add_edge("generate_from_kb", END)
    graph.add_edge("generate_from_web", END)
    graph.add_edge("direct_answer", END)
    graph.add_edge("insufficient", END)
    return graph.compile()


agent_graph = build_graph()



def ask(question: str):
    initial: AgentState = {
        "question": question,
        "current_query": question,
        "kb_docs": [],
        "web_results": "",
        "kb_grade": "",
        "web_grade": "",
        "answer": "",
        "source_used": "",
        "retry_count": 0,
        "trace": [],
        "citations": [],
    }
    return agent_graph.invoke(initial)