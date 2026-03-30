import asyncio
import uuid
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command

from src.config import config
from src.agent.graph import graph

app = FastAPI(title="Twenty CRM Agent")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    thread_id = body.get("thread_id") or str(uuid.uuid4())
    graph_config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=graph_config,
        )
    except Exception as e:
        return JSONResponse(
            {"thread_id": thread_id, "type": "error", "content": str(e)},
            status_code=500,
        )

    # Check for HITL interrupt
    state = graph.get_state(graph_config)
    if state.next:
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                for intr in task.interrupts:
                    payload = intr.value
                    if isinstance(payload, dict) and payload.get("type") == "mutation_approval":
                        return JSONResponse({
                            "thread_id": thread_id,
                            "type": "approval_required",
                            "description": payload["description"],
                            "tool_calls": payload.get("tool_calls", []),
                        })

    # Extract response text
    messages = result.get("messages", [])
    response_text = ""
    if messages:
        last = messages[-1]
        response_text = last.content if hasattr(last, "content") else str(last)

    return JSONResponse({
        "thread_id": thread_id,
        "type": "response",
        "content": response_text,
    })


@app.post("/api/approve")
async def approve(request: Request):
    body = await request.json()
    thread_id = body.get("thread_id", "")
    approved = body.get("approved", False)
    graph_config = {"configurable": {"thread_id": thread_id}}

    resume_value = "approved" if approved else "rejected"
    try:
        result = await graph.ainvoke(
            Command(resume=resume_value),
            config=graph_config,
        )
    except Exception as e:
        return JSONResponse(
            {"thread_id": thread_id, "type": "error", "content": str(e)},
            status_code=500,
        )

    # Check if there are more interrupts
    state = graph.get_state(graph_config)
    if state.next:
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                for intr in task.interrupts:
                    payload = intr.value
                    if isinstance(payload, dict) and payload.get("type") == "mutation_approval":
                        return JSONResponse({
                            "thread_id": thread_id,
                            "type": "approval_required",
                            "description": payload["description"],
                        })

    messages = result.get("messages", [])
    response_text = ""
    if messages:
        last = messages[-1]
        response_text = last.content if hasattr(last, "content") else str(last)

    return JSONResponse({
        "thread_id": thread_id,
        "type": "response",
        "content": response_text,
    })


# Mount static files after routes so routes take priority
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main() -> None:
    import uvicorn

    config.validate()
    uvicorn.run(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
