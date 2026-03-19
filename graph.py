from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from typing import TypedDict, Annotated
import operator, json, os
from tools.custom_tools import get_nse_data, update_portfolio, calculate_risk_metrics

llm = ChatOpenAI(
    model="grok-4.1-fast",
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
    temperature=0.1
)

tools = [get_nse_data, update_portfolio, calculate_risk_metrics]
llm_with_tools = llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    portfolio: dict
    next: str

def specialist_node(name: str):
    prompt = open(f"agents/{name}_prompt.md").read()
    def node(state):
        response = llm_with_tools.invoke([HumanMessage(content=prompt + "\nCurrent state: " + str(state["messages"][-1]))])
        return {"messages": [f"{name}: {response.content}"]}
    return node

graph = StateGraph(AgentState)
for agent in ["quant", "technical", "sentiment", "risk", "options"]:
    graph.add_node(agent, specialist_node(agent))

def supervisor(state):
    all_inputs = "\n\n".join(state["messages"])
    supervisor_prompt = open("agents/supervisor_prompt.md").read()
    final = llm.invoke([HumanMessage(content=supervisor_prompt + "\nAgent outputs:\n" + all_inputs)])
    return {"messages": [final.content], "next": END}

graph.add_node("supervisor", supervisor)

# Parallel execution
for agent in ["quant", "technical", "sentiment", "risk", "options"]:
    graph.add_edge("supervisor", agent)  # Wait — actually we start from supervisor and branch
# Correct parallel pattern:
graph.set_entry_point("supervisor")
for agent in ["quant", "technical", "sentiment", "risk", "options"]:
    graph.add_conditional_edges("supervisor", lambda x: agent, {agent: agent})
graph.add_edge(["quant", "technical", "sentiment", "risk", "options"], "supervisor")  # Wait, use parallel

# Simpler working version (recommended for stability):
# Use RunnableParallel in main.py instead of complex edges. Graph above is starter — full parallel code in main.py below.

app = graph.compile()