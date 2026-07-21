"""
Project Tensei — Gateway Layer (FastAPI).

This is the bridge between the customer-facing frontend (tensei-prototype/) and
the deployed AgentCore agents (agent_testing/). The frontend calls these HTTP
endpoints; the gateway forwards the message to the Coordinator harness and
returns the agent's reply.

The frontend is a static page and currently runs a scripted simulation. This
gateway does NOT change the frontend — it exposes endpoints the frontend team
can call from app.js (see FRONTEND_INSTRUCTIONS.txt for the exact snippet).

Endpoints
  GET  /health                 — liveness + whether AWS creds/harness are reachable
  POST /session                — create a new investigation session, returns sessionId
  POST /chat                   — send a customer message, get the agent's reply
  GET  /                       — tiny built-in test page to prove the round trip

Run:
    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import agent_client
import config

app = FastAPI(title="Project Tensei — Gateway", version="1.0.0")

# The frontend runs in a browser on a different origin than this gateway, so we
# must enable CORS or the browser will block the fetch() calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models — FastAPI validates these automatically.
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str            # the customer's message text
    sessionId: str | None = None  # optional — omit to start a new session


class ChatResponse(BaseModel):
    reply: str              # the agent's text reply
    sessionId: str          # the session id (new or echoed back) for continuity


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Report gateway liveness and whether the backend agents are reachable.

    Handy for the frontend team to confirm setup before wiring anything up.
    """
    status = {"gateway": "ok", "region": config.REGION, "harness": config.HARNESS_NAME}
    try:
        identity = agent_client.check_credentials()
        status["aws_account"] = identity.get("Account")
        status["credentials"] = "valid"
    except Exception as exc:  # noqa: BLE001 — surface the reason to the caller
        status["credentials"] = f"invalid: {exc}"
    return status


@app.post("/session")
async def create_session():
    """Mint a new investigation session id.

    The frontend calls this once when the workspace opens, then passes the
    returned sessionId on every /chat call so the agent keeps context.
    """
    return {"sessionId": agent_client.new_session_id()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Forward a customer message to the Coordinator agent and return its reply."""
    # Reuse the caller's session, or start a fresh one if none was supplied.
    session_id = request.sessionId or agent_client.new_session_id()

    try:
        reply = agent_client.invoke_agent(request.message, session_id)
    except Exception as exc:  # noqa: BLE001
        # Turn AWS/agent errors into a clean HTTP 502 so the frontend can show
        # a friendly message instead of the connection just hanging.
        raise HTTPException(status_code=502, detail=f"Agent invocation failed: {exc}")

    return ChatResponse(reply=reply, sessionId=session_id)


@app.get("/")
async def index():
    """Serve the tiny built-in test page (static/index.html)."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
