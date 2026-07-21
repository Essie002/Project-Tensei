# coordinator_agent.py
import boto3
import uuid
import time
import sys

# CONFIG — Your Isengard account
REGION = "us-east-1"
ACCOUNT_ID = "070638634443"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/agent_core_execution_role"
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# CREDENTIAL CHECK — Runs every time
def check_credentials():
    """Verify AWS credentials are valid before doing anything else."""
    print("🔑 Checking AWS credentials...")
    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        print(f"   ✅ Credentials valid!")
        print(f"   Account:  {identity['Account']}")
        print(f"   Role:     {identity['Arn']}")
        print()
        return True
    except Exception as e:
        print(f"   ❌ Credentials FAILED: {e}")
        print()
        print("   Fix: Set your credentials in PowerShell:")
        print('   $Env:AWS_ACCESS_KEY_ID="ASIA..."')
        print('   $Env:AWS_SECRET_ACCESS_KEY="..."')
        print('   $Env:AWS_SESSION_TOKEN="..."')
        print('   $Env:AWS_DEFAULT_REGION="us-east-1"')
        print()
        sys.exit(1)

SENSOR_AGENT_CONTEXT_SEV5 = """
[TEST SCENARIO STARTS HERE]
"""

SENSOR_AGENT_CONTEXT_SEV1 = """
[TEST SCENARIO STARTS HERE]
"""

SENSOR_AGENT_CONTEXT_SEV2 = """
[TEST SCENARIO STARTS HERE]
"""

SENSOR_AGENT_CONTEXT_SEV3 = """
[TEST SCENARIO STARTS HERE]
"""

SENSOR_AGENT_CONTEXT_SEV4 = """
[TEST SCENARIO STARTS HERE]
"""

# Invoke agent
def invoke_agent(harness_arn, context, session_id=None):
    client = boto3.client("bedrock-agentcore", region_name=REGION)

    if not session_id:
        session_id = str(uuid.uuid4()).replace("-", "") + "0"

    print(f"\n{'─' * 50}")
    print(f"📨 INPUT:")
    print(f"{'─' * 50}")
    print(context[:300])
    print(f"{'─' * 50}")
    print(f"\n🤖 AGENT RESPONSE:\n")

    try:
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=[{"role": "user", "content": [{"text": context}]}]
        )

        full_response = ""
        for event in response.get("stream", []):
            if hasattr(event, "get"):
                if "contentBlockDelta" in event:
                    text = event["contentBlockDelta"].get("delta", {}).get("text", "")
                    print(text, end="", flush=True)
                    full_response += text
            else:
                chunk = str(event)
                print(chunk, end="", flush=True)
                full_response += chunk

        print(f"\n{'─' * 50}")
        return full_response, session_id

    except Exception as e:
        print(f"❌ Error invoking: {e}")
        return None, session_id
    
def test_scenario_empty_description(harness_arn, scenario):
    print("\n" + "=" * 50)
    print("🧪 Running Test...")
    print("=" * 50)
    return invoke_agent(harness_arn, scenario)

if __name__ == "__main__":
    check_credentials()