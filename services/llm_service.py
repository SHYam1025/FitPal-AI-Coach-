import os
from typing import Annotated, Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain and LangGraph imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

# Load env file variables at compile time
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()  # Options: 'gemini' or 'openrouter'

# ==========================================
# LLM PROVIDER SELECTION ENGINE
# ==========================================
if LLM_PROVIDER == "openrouter":
    from langchain_openai import ChatOpenAI
    print("🤖 Initializing Model via OpenRouter Gateway...")
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="google/gemini-2.5-flash"
    )
else:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("♊ Initializing Model via Native Google Gemini API...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is missing from the .env file.")
    
    # ✅ FIXED: Standardized string identifier to gemini-2.5-flash to eliminate client 404 drops
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.2,
        max_output_tokens=4000  # Gives the report analyzer a long runway to finish output
    )

# ==========================================
# 1. DEFINE THE CORE GRAPH STATE
# ==========================================
class AgentState(TypedDict):
    session_id: str
    messages: List[BaseMessage]
    intent: str
    report_content: Optional[str]
    response: str

class IntentClassifier(BaseModel):
    intent: str = Field(
        description="Categorize user intent strictly into: 'log_calories', 'analyze_report', or 'general_chat'"
    )

# ==========================================
# 2. GRAPH NODES (FUNCTION LOGIC)
# ==========================================
def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes only the absolute latest incoming message to dynamically classify current intent.
    """
    latest_message = state["messages"][-1].content
    structured_llm = llm.with_structured_output(IntentClassifier)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Analyze the single user input text and classify its primary target context for a fitness app. "
                   "If they ask for workouts, exercises, or general questions, classify as 'general_chat'. "
                   "If they detail foods, meals, or ask to log eating items, classify as 'log_calories'."),
        ("human", "{input}")
    ])
    
    classification_chain = prompt | structured_llm
    result = classification_chain.invoke({"input": latest_message})
    
    # Force route to analysis ONLY if new report content was explicitly parsed during this specific execution hook
    intent = "analyze_report" if state.get("report_content") else result.intent
    
    print(f"🔮 [LangGraph Router] Classified text intent as: '{intent}'")
    return {"intent": intent}

def rag_chat_node(state: AgentState) -> Dict[str, Any]:
    latest_message = state["messages"][-1].content
    context = ""  # Active FAISS setup
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are 'FitPal', an expert fitness coach. Answer using this context:\n{context}\n\n"
            "CRITICAL STYLING RULES:\n"
            "1. NEVER use markdown asterisks (**) or bold text anywhere in your response.\n"
            "2. Keep the spacing dense. Do not include empty lines or double line-breaks between points.\n"
            "3. For structure, use clean lists with numbering (1., 2.) or bullet dashes (-).\n"
            "4. If you need emphasis, wrap keywords in HTML code tags like <code>Keyword</code> instead of bolding."
        )),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    res = chain.invoke({"input": latest_message, "context": context})
    return {"response": res.content, "intent": "general_chat"}

def calorie_logger_node(state: AgentState) -> Dict[str, Any]:
    latest_message = state["messages"][-1].content
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are FitPal's nutrition parser. Estimate calories, protein, carbs, and fats for the described meal.\n\n"
            "CRITICAL STYLING RULES:\n"
            "1. NEVER use markdown asterisks (**) or bold text anywhere.\n"
            "2. Keep the response compact with zero empty spaces or empty vertical lines.\n"
            "3. Present the macro breakdown cleanly using a compact list format.\n"
            "Example format:\n"
            "Meal Breakdown:\n"
            "- Calories: 350 kcal\n"
            "- Protein: 12g\n"
            "- Carbs: 69g\n"
            "- Fats: 4g"
        )),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    res = chain.invoke({"input": latest_message})
    return {"response": res.content, "intent": "general_chat"}

def report_analyzer_node(state: AgentState) -> Dict[str, Any]:
    latest_message = state["messages"][-1].content
    report_data = state.get("report_content", "No explicit report text found.")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are 'FitPal', an expert fitness coach and medical report analyzer.\n"
            "Analyze the provided medical report findings and answer the user query completely.\n\n"
            "CRITICAL STYLING RULES:\n"
            "1. NEVER use markdown asterisks (**) or hashes (##) anywhere in your response.\n"
            "2. Keep the spacing dense. Do not include excessive empty lines or blank vertical spaces.\n"
            "3. For section titles, use crisp uppercase plain text headers (e.g., DIETARY PLAN:) or HTML italics like <i>DIETARY PLAN</i>.\n"
            "4. For metrics, key biomarkers, or variables requiring visual emphasis, wrap them in HTML code tags like <code>Triglycerides</code>.\n\n"
            "CRITICAL DISCLAIMER:\n"
            "You must introduce the analysis with a clear statement that you are an AI assistant, not a medical professional, doctor, or dietitian, and recommend consulting a qualified healthcare provider for clinical assessments."
        )),
        ("human", "Report Content Data:\n{report}\n\nUser Prompt Question: {input}")
    ])
    
    chain = prompt | llm
    res = chain.invoke({"input": latest_message, "report": report_data})
    return {"response": res.content, "intent": "general_chat"}

# ==========================================
# 3. CONDITIONAL ROUTING LOGIC
# ==========================================
def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "general_chat")
    if intent == "log_calories":
        return "calorie_logger"
    elif intent == "analyze_report":
        return "medical_analyzer"
    return "general_chat"

# ==========================================
# 4. COMPILING THE GRAPH PIPELINE
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("intent_router", intent_router_node)
workflow.add_node("general_chat", rag_chat_node)
workflow.add_node("calorie_logger", calorie_logger_node)
workflow.add_node("medical_analyzer", report_analyzer_node)

workflow.add_edge(START, "intent_router")
workflow.add_conditional_edges(
    "intent_router",
    route_by_intent,
    {
        "general_chat": "general_chat",
        "calorie_logger": "calorie_logger",
        "medical_analyzer": "medical_analyzer"
    }
)

workflow.add_edge("general_chat", END)
workflow.add_edge("calorie_logger", END)
workflow.add_edge("medical_analyzer", END)

app_graph = workflow.compile()

# ==========================================
# 5. UNIVERSAL SERVICE ENTRYPOINT
# ==========================================
def generate_response(session_id: str, message: str, report_content: Optional[str] = None) -> str:
    redis_history = RedisChatMessageHistory(session_id=session_id, url=REDIS_URL)
    past_messages = redis_history.messages
    
    current_user_message = HumanMessage(content=message)
    full_message_set = past_messages + [current_user_message]
    
    # Clear and initialize graph inputs completely fresh per transaction turn
    initial_state: AgentState = {
        "session_id": session_id,
        "messages": full_message_set,
        "intent": "general_chat",          # Force state variable clear reset
        "report_content": report_content,  # Overwrites history context cleanly
        "response": ""
    }
    
    final_output_state = app_graph.invoke(initial_state)
    ai_final_text = final_output_state["response"]
    
    # Save the execution turn out to Redis
    redis_history.add_user_message(message)
    redis_history.add_ai_message(ai_final_text)
    
    return ai_final_text

def setup_rag_pipeline():
    print("Initializing FAISS Vector Store Knowledge Base...")
    pass