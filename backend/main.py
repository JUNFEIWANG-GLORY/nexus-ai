import asyncio
import json
import os
from typing import TypedDict, List, Annotated
import operator
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Core Components
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. Initialize Tools ---

# A. Search Tool (Tavily)
try:
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️ Warning: TAVILY_API_KEY not found, search functionality will be unavailable")
    search_tool = TavilySearchResults(max_results=3)
except Exception as e:
    print(f"❌ Tavily Init Error: {e}")
    search_tool = None

# B. LLM Model (Groq) - Fix: Define as None first
llm = None

try:
    if not os.getenv("GROQ_API_KEY"):
        print("🚨 Critical Error: GROQ_API_KEY not found, LLM cannot start! Please check .env file")
    else:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.6
        )
        print("✅ LLM (Groq Llama 3.3) initialized successfully")
except Exception as e:
    print(f"❌ LLM Init Error: {e}")


# --- 2. Define State ---
class AgentState(TypedDict):
    topic: str
    logs: Annotated[List[str], operator.add]
    search_data: str
    final_report: str


# --- 3. Define Agent Nodes ---

# 🕵️ Researcher Agent
async def research_node(state: AgentState):
    topic = state["topic"]

    if not search_tool:
        return {
            "logs": ["❌ Error: Search tool not initialized (check TAVILY_API_KEY)"],
            "search_data": "No search data (tool failure)"
        }

    log_start = f"🕵️ Researcher: Searching Tavily for '{topic}'..."

    try:
        print(f"🔍 Searching via Tavily: {topic}")
        # invoke returns list[dict]
        search_results = await asyncio.to_thread(search_tool.invoke, topic)
        search_data = json.dumps(search_results, ensure_ascii=False)

    except Exception as e:
        print(f"⚠️ Search failed: {e}")
        log_start = f"⚠️ Search Error: {str(e)}"
        search_data = f"Search Failed: {str(e)}"

    log_end = f"✅ Researcher: Latest data retrieved."

    return {
        "logs": [log_start, log_end],
        "search_data": search_data
    }


# ✍️ Writer Agent
async def writer_node(state: AgentState):
    # Fix: If LLM is not initialized, return error report immediately, do not crash
    if not llm:
        return {
            "logs": ["❌ Fatal Error: LLM is not running"],
            "final_report": "## System Error\nCannot generate report because LLM initialization failed.\n\nPlease check backend console logs to confirm `GROQ_API_KEY` is set correctly."
        }

    topic = state["topic"]
    search_data = state["search_data"]

    log_start = f"✍️ Writer: Llama 3.3 is drafting the report..."

    prompt = f"""
    You are a senior technical analyst. Please write a briefing on "{topic}" based on the provided online search results.

    【Search Result Data】:
    {search_data}

    【Requirements】:
    1. Use Markdown format.
    2. Cite specific data or sources from the search results.
    3. Clear structure: Title, Executive Summary, Key Findings, Conclusion.
    4. Professional and objective tone.
    """

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        report_content = response.content
    except Exception as e:
        report_content = f"❌ LLM Call Failed: {str(e)}"

    log_end = f"✅ Writer: Report generated."

    return {
        "logs": [log_start, log_end],
        "final_report": report_content
    }


# --- 4. Build Workflow ---
workflow = StateGraph(AgentState)
workflow.add_node("researcher", research_node)
workflow.add_node("writer", writer_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

app_graph = workflow.compile()

# --- 5. API Interface (Must be at the bottom, no indentation!) ---
@app.get("/api/run-research")
async def run_research(topic: str):
    async def event_generator():
        # Must initialize inputs here, ensuring all State fields are included
        inputs = {"topic": topic, "logs": [], "search_data": "", "final_report": ""}

        try:
            # Run graph
            async for output in app_graph.astream(inputs):
                for key, value in output.items():
                    # Handle log stream
                    if "logs" in value:
                        for log in value["logs"]:
                            yield f"data: {json.dumps({'type': 'log', 'content': log})}\n\n"
                            # Pause briefly to prevent frontend rendering lag
                            await asyncio.sleep(0.1)

                    # Handle final report
                    if "final_report" in value and value["final_report"]:
                        yield f"data: {json.dumps({'type': 'report', 'content': value['final_report']})}\n\n"

        except Exception as e:
            err_msg = f"System Error: {str(e)}"
            yield f"data: {json.dumps({'type': 'log', 'content': err_msg})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")