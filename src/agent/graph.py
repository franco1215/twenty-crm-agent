from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, ToolMessage

from src.agent.state import AgentState
from src.agent.tools import ALL_TOOLS, WRITE_TOOLS
from src.agent.prompts import SYSTEM_PROMPT
from src.llm import get_llm


def _build_graph() -> StateGraph:
    llm = get_llm().bind_tools(ALL_TOOLS)
    tool_node = ToolNode(ALL_TOOLS, handle_tool_errors=True)

    async def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        response = await llm.ainvoke(
            [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        )
        return {"messages": [response]}

    def route_after_agent(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return END

        for tc in last_message.tool_calls:
            if tc["name"] in WRITE_TOOLS:
                return "hitl_node"
        return "tool_node"

    async def hitl_node(state: AgentState) -> dict:
        last_message = state["messages"][-1]
        mutation_calls = [
            tc for tc in last_message.tool_calls if tc["name"] in WRITE_TOOLS
        ]

        descriptions = []
        for tc in mutation_calls:
            op = tc["args"].get("operation", "Unknown operation")
            query = tc["args"].get("query", "")
            descriptions.append(f"**{op}**\n```graphql\n{query}\n```")

        approval_text = "\n\n".join(descriptions)
        response = interrupt(
            {
                "type": "mutation_approval",
                "description": approval_text,
                "tool_calls": [
                    {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
                    for tc in mutation_calls
                ],
            }
        )

        if response == "approved":
            # Execute the mutation tools via ToolNode
            result = await tool_node.ainvoke(state)
            return result

        # Rejected — return tool messages indicating cancellation
        rejection_messages = []
        for tc in last_message.tool_calls:
            rejection_messages.append(
                ToolMessage(
                    content="Operation cancelled by user."
                    if tc["name"] in WRITE_TOOLS
                    else "Operation skipped (mutation was rejected).",
                    tool_call_id=tc["id"],
                )
            )
        return {"messages": rejection_messages}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("hitl_node", hitl_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", route_after_agent)
    workflow.add_edge("tool_node", "agent")
    workflow.add_edge("hitl_node", "agent")

    return workflow


memory = MemorySaver()
graph = _build_graph().compile(checkpointer=memory)
