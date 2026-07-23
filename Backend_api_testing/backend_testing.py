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
AGENT_ARNS = {
    "sensor": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_SENSOR_ARN",
    "coordinator": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_COORDINATOR_ARN",
    "control": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_CONTROL_ARN",
    "task_msg_draft": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_MSG_DRAFT_ARN",
    "task_case_send": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_CASE_SEND_ARN",
    "task_diagnostics": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_DIAGNOSTICS_ARN",
    "task_timer": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_TIMER_ARN",
    "task_listener": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_LISTENER_ARN",
    "task_report_compiler": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/YOUR_REPORT_ARN",
}

# CREDENTIAL CHECK — Validates AWS credentials on startup
def check_credentials():
    """
    Validates that AWS credentials are set and working.
    Returns True if valid, False if not.
    Prints clear instructions if credentials are missing/expired.
    """
    print("\n" + "=" * 60)
    print("🔐 CHECKING AWS CREDENTIALS")
    print("=" * 60)

    # Check if environment variables are set
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")

    if not access_key or not secret_key or not session_token:
        print("\n❌ AWS CREDENTIALS NOT FOUND!")
        return False
    
    # Credentials are set — now verify they actually work
    print(f"\n   AWS_ACCESS_KEY_ID:     ✅ Set ({access_key[:8]}...)")
    print(f"   AWS_SECRET_ACCESS_KEY:  ✅ Set (****)")
    print(f"   AWS_SESSION_TOKEN:      ✅ Set ({session_token[:12]}...)")
    print("\n   ⏳ Verifying credentials with AWS STS...")

    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()

        account = identity["Account"]
        arn = identity["Arn"]
        user_id = identity["UserId"]

        print(f"\n   ✅ CREDENTIALS VALID!")
        print(f"   Account:  {account}")
        print(f"   ARN:      {arn}")
        print(f"   UserID:   {user_id}")
        print("\n" + "=" * 60)
        print("✅ CREDENTIALS OK — Server ready to invoke agents")
        print("=" * 60 + "\n")
        return True
    except boto3.exceptions.Boto3Error as e:
        print(f"\n   ❌ CREDENTIALS EXPIRED OR INVALID!")
        print(f"   Error: {e}")
        return False
    
    except Exception as e:
        print(f"\n   ❌ UNEXPECTED ERROR: {e}")
        print("=" * 60 + "\n")
        return False
    
# CREDENTIAL REFRESH — Endpoint to update creds without restart    
@app.post("/api/credentials")
async def update_credentials(creds: dict):
    """
    Allows updating credentials from the frontend without restarting.
    POST /api/credentials with JSON body:
    {
        "aws_access_key_id": "ASIA...",
        "aws_secret_access_key": "...",
        "aws_session_token": "..."
    }
    """
    os.environ["AWS_ACCESS_KEY_ID"] = creds.get("aws_access_key_id", "")
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds.get("aws_secret_access_key", "")
    os.environ["AWS_SESSION_TOKEN"] = creds.get("aws_session_token", "")

    # Verify the new credentials
    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        return {
            "status": "valid",
            "account": identity["Account"],
            "arn": identity["Arn"]
        }
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e)
        }
    
# CREDENTIAL STATUS — Check if current creds are still valid    
@app.get("/api/credentials/status")
async def credential_status():
    """Check if current credentials are still valid."""
    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        return {
            "status": "valid",
            "account": identity["Account"],
            "arn": identity["Arn"]
        }
    except Exception as e:
        return {
            "status": "expired",
            "error": str(e)
        }

# HELPER: Invoke agent and stream response chunks    
async def invoke_agent_stream(agent_name: str, message: str, websocket: WebSocket):
    """Invoke an agent and stream its response to the frontend via WebSocket."""

    client = boto3.client("bedrock-agentcore", region_name=REGION)
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
                        # Stream each chunk to frontend in real-time
                        await websocket.send_json({
                            "type": "agent_chunk",
                            "agent": agent_name,
                            "chunk": chunk,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        await asyncio.sleep(0)  # Yield to event loop
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
            "full_response": full_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return full_response

    except Exception as e:
        error_msg = str(e)

        # Check if it's a credential expiry
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

        return f"ERROR: {e}"
    
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

             # ─── STEP 1: Sensor Agent ───
            sensor_response = await invoke_agent_stream("sensor", payload, websocket)

            # ─── STEP 2: Coordinator Agent ───
            coordinator_response = await invoke_agent_stream("coordinator", sensor_response, websocket)

            # ─── STEP 3: Control Agent ───
            control_response = await invoke_agent_stream("control", coordinator_response, websocket)

            # ─── STEP 4: Task Agents ───
            await invoke_agent_stream("task_msg_draft", control_response, websocket)
            await invoke_agent_stream("task_diagnostics", control_response, websocket)
            await invoke_agent_stream("task_case_send", control_response, websocket)

            # ─── STEP 5: Report Compiler ───
            await invoke_agent_stream("task_report_compiler", control_response, websocket)

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