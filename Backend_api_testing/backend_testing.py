
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import boto3
import uuid
import json
import asyncio
import os
import sys
import re
from datetime import datetime, timezone

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Account config
REGION = "us-east-1"
# Agent ARNs
AGENT_ARNS = {
    "sensor": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_sensor_agent-kmDO97sO3z",
    "coordinator": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_coordinator-Kv9FDqiCWN",
    "control": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_control_agent-YWtaMXymSb",
    "task_msg_draft": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_msg_draft-r6ewltpqAA",
    "task_case_send": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_case_send-jUcazbLmg0",
    "task_notification_send": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_notify-EDwN3vZa8b",
    "task_diagnostics": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_diagnostics-FqmcSsmeZU",
    "task_timer": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_timer-2e29jTA7FQ",
    "task_listener": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_listener-3m6bcTYDXV"
}

# CREDENTIAL CHECK — Validates AWS credentials on startup
def check_credentials():
    print("\n" + "=" * 60)
    print("🔐 CHECKING AWS CREDENTIALS")
    print("=" * 60)

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")

    if not access_key or not secret_key or not session_token:
        print("\n❌ AWS CREDENTIALS NOT FOUND!")
        return False
    
    print(f"\n   AWS_ACCESS_KEY_ID:     ✅ Set ({access_key[:8]}...)")
    print(f"   AWS_SECRET_ACCESS_KEY:  ✅ Set (****)")
    print(f"   AWS_SESSION_TOKEN:      ✅ Set ({session_token[:12]}...)")
    print("\n   ⏳ Verifying credentials with AWS STS...")

    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        print(f"\n   ✅ CREDENTIALS VALID!")
        print(f"   Account:  {identity['Account']}")
        print(f"   ARN:      {identity['Arn']}")
        print(f"   UserID:   {identity['UserId']}")
        print("\n" + "=" * 60)
        print("✅ CREDENTIALS OK — Server ready to invoke agents")
        print("=" * 60 + "\n")
        return True
    except Exception as e:
        print(f"\n   ❌ CREDENTIALS EXPIRED OR INVALID: {e}")
        return False
    
# CREDENTIAL REFRESH — Endpoint to update creds without restart    
@app.post("/api/credentials")
async def update_credentials(creds: dict):
    os.environ["AWS_ACCESS_KEY_ID"] = creds.get("aws_access_key_id", "")
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds.get("aws_secret_access_key", "")
    os.environ["AWS_SESSION_TOKEN"] = creds.get("aws_session_token", "")

    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        return {"status": "valid", "account": identity["Account"], "arn": identity["Arn"]}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}
    
# CREDENTIAL STATUS — Check if current creds are still valid    
@app.get("/api/credentials/status")
async def credential_status():
    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        return {"status": "valid", "account": identity["Account"], "arn": identity["Arn"]}
    except Exception as e:
        return {"status": "expired", "error": str(e)}

# HELPER: Invoke agent and stream response chunks    
async def invoke_agent_stream(agent_name: str, message: str, websocket: WebSocket, session_id: str = None):
    """Invoke an agent and stream its response to the frontend via WebSocket.
    Returns (full_response, session_id) so we can reuse sessions for the feedback loop."""

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    if not session_id:
        session_id = str(uuid.uuid4()).replace("-", "") + "0"
    harness_arn = AGENT_ARNS[agent_name]

    # Notify frontend: agent is starting
    await websocket.send_json({
        "type": "agent_start",
        "agent": agent_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=[{"role": "user", "content": [{"text": message}]}]
        )

        full_response = ""
        for event in response.get("stream", []):
            if hasattr(event, "get"):
                if "contentBlockDelta" in event:
                    chunk = event["contentBlockDelta"].get("delta", {}).get("text", "")
                    if chunk:
                        full_response += chunk
                        await websocket.send_json({
                            "type": "agent_chunk",
                            "agent": agent_name,
                            "chunk": chunk,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        await asyncio.sleep(0)
            else:
                text = str(event)
                full_response += text
                await websocket.send_json({
                    "type": "agent_chunk",
                    "agent": agent_name,
                    "chunk": text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Notify frontend: agent is done
        await websocket.send_json({
            "type": "agent_complete",
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return full_response, session_id

    except Exception as e:
        error_msg = str(e)

        if "ExpiredToken" in error_msg or "InvalidIdentityToken" in error_msg:
            await websocket.send_json({
                "type": "credentials_expired",
                "agent": agent_name,
                "error": "AWS credentials have expired. Please refresh from Isengard.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            await websocket.send_json({
                "type": "agent_error",
                "agent": agent_name,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return f"ERROR: {e}", session_id


# HELPER: Parse which task agents the Control Agent assigned
def parse_task_agents_from_control(control_output):
    """
    Read the Control Agent's execution plan and return the list of 
    task agent keys it assigned. The Control Agent decides — not us.
    """
    agent_name_map = {
        "msg_draft": "task_msg_draft",
        "diagnostics": "task_diagnostics",
        "notification_send": "task_notification_send",
        "case_send": "task_case_send",
        "timer": "task_timer",
        "response_listener": "task_listener",
    }

    # Find all "Agent: <name>" in the control output
    agent_matches = re.findall(r'Agent:\s*(\w+)', control_output)

    # Deduplicate while preserving order
    seen = set()
    unique_agents = []
    for agent in agent_matches:
        if agent not in seen:
            seen.add(agent)
            unique_agents.append(agent)

    # Map to our ARN keys
    tasks_to_run = []
    for name in unique_agents:
        arn_key = agent_name_map.get(name)
        if arn_key and arn_key in AGENT_ARNS:
            tasks_to_run.append(arn_key)

    # Fallback if parsing found nothing
    if not tasks_to_run:
        tasks_to_run = ["task_msg_draft", "task_diagnostics", "task_timer"]

    return tasks_to_run


# HELPER: Build task results summary for Control Agent reporting
def build_task_results_summary(task_results):
    """Compile all task agent outputs into a structured input for the Control Agent."""
    summary = "[TASK AGENT RESULTS — FOR CONTROL AGENT REPORTING]\n\n"
    for agent_name, output in task_results.items():
        summary += f"── {agent_name.upper()} RESULT ──\n"
        if output and not output.startswith("ERROR"):
            trimmed = output[:1500] if len(output) > 1500 else output
            summary += f"{trimmed}\n\n"
        else:
            summary += f"FAILED — {output or 'No output received.'}\n\n"
    summary += "── END OF TASK AGENT RESULTS ──\n"
    summary += "\nCompile these results into your CONTEXT SUMMARY REPORT for the Coordinator Agent."
    return summary

def extract_for_control_agent(coordinator_output):
    """
    Extract only the DECISION and HIGH-LEVEL TASK PLAN from the Coordinator's
    full response. The Control Agent doesn't need the assessment or situation analysis.
    """
    # Try ## DECISION (markdown headers)
    decision_match = re.search(r'(## DECISION.*)', coordinator_output, re.DOTALL)
    if decision_match:
        return decision_match.group(1).strip()

    # Try plain text "DECISION" header (no ##)
    decision_match = re.search(r'(^DECISION\s*$.*)', coordinator_output, re.DOTALL | re.MULTILINE)
    if decision_match:
        return decision_match.group(1).strip()

    # Try **Action:** as a fallback
    action_match = re.search(r'(\*?\*?Action\*?\*?:.*)', coordinator_output, re.DOTALL)
    if action_match:
        return action_match.group(1).strip()

    # Try "Action:" without bold
    action_match = re.search(r'(Action:.*)', coordinator_output, re.DOTALL)
    if action_match:
        return action_match.group(1).strip()

    # Last resort: return last 50%
    split_point = len(coordinator_output) // 2
    return coordinator_output[split_point:].strip()
    
# WEBSOCKET: Main orchestration endpoint        
@app.websocket("/ws/orchestrate")
async def orchestrate(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Receive trigger from frontend
            data = await websocket.receive_json()
            trigger_type = data.get("trigger_type")
            payload = data.get("payload", "")

            # Quick credential check before starting
            try:
                sts = boto3.client("sts", region_name=REGION)
                sts.get_caller_identity()
            except Exception:
                await websocket.send_json({
                    "type": "credentials_expired",
                    "agent": "system",
                    "error": "AWS credentials expired. Refresh from Isengard and POST to /api/credentials",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            # Notify frontend: orchestration starting
            await websocket.send_json({
                "type": "orchestration_start",
                "trigger_type": trigger_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # ─── STAGE 1: Sensor Agent ───
            sensor_response, _ = await invoke_agent_stream("sensor", payload, websocket)

            if sensor_response.startswith("ERROR"):
                continue

            # ─── STAGE 2: Coordinator Agent (Initial Decision) ───
            coordinator_response, coordinator_session = await invoke_agent_stream(
                "coordinator", sensor_response, websocket
            )

            if coordinator_response.startswith("ERROR"):
                continue

            # ─── STAGE 3: Control Agent (Planning) ───
            coordinator_response = extract_for_control_agent(coordinator_response)
            control_response, control_session = await invoke_agent_stream(
                "control", coordinator_response, websocket
            )

            if control_response.startswith("ERROR"):
                continue

            # ─── STAGE 4: Task Agents ───
            # The Control Agent decided which agents to use — parse its output
            task_agents_to_run = parse_task_agents_from_control(control_response)

            task_results = {}
            for agent_key in task_agents_to_run:
                result, _ = await invoke_agent_stream(agent_key, control_response, websocket)
                task_results[agent_key] = result

            # ─── STAGE 5: Control Agent (Reporting) ───
            # Feed task results back to Control Agent (same session so it has context)
            task_summary = build_task_results_summary(task_results)
            control_report, _ = await invoke_agent_stream(
                "control", task_summary, websocket, session_id=control_session
            )

            # ─── STAGE 6: Coordinator Agent (Final Assessment) ───
            # Feed Control Agent's report back to Coordinator (same session)
            coordinator_final, _ = await invoke_agent_stream(
                "coordinator", control_report, websocket, session_id=coordinator_session
            )

            # Notify frontend: orchestration complete
            await websocket.send_json({
                "type": "orchestration_complete",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        print("Client disconnected")

# SERVE FRONTEND
@app.get("/")
async def serve_frontend():
    return FileResponse("static/test_frontend.html")

# STARTUP — Check credentials when server starts
@app.on_event("startup")
async def startup_event():
    if not check_credentials():
        print("\n⚠️  Server starting WITHOUT valid credentials.")
        print("   You can update them later via POST /api/credentials")
        print("   or set environment variables and restart.\n")