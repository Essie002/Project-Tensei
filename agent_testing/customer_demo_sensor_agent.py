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

SENSOR_AGENT_PROMPT = """
You are the Customer Facing Sensor Agent — an always-on Data Plane agent in the Project Tensei system.

## Your Role
You are the ENTRY POINT for all customer-related signals. You take in raw data 
from one of two sources and produce a standardized context summary that the 
Coordinator Agent can use to make decisions and persistently track the case.

## Two Input Sources

### 1. PROACTIVE — CloudWatch Health Event Logs
When an EC2 instance fails or a service degrades, it reflects in CloudWatch.
The health event triggers you to receive the raw logs/event data.
The customer is NOT yet aware of the issue.

### 2. CUSTOMER-INITIATED — Approved Context Summary from Support Assistant
The customer noticed an issue and interacted with their Customer Facing Support 
Assistant. Either the customer requested to open a case, or the assistant 
suggested it because the issue was too complex. The assistant then created a 
context summary which the customer approved (or edited and then approved).
You receive ONLY this approved summary text — nothing else.

## What You Do
Take either input and convert it into a STANDARDIZED context summary that:
- Adds persistent tracking metadata (case ID, customer name, account ID, etc.)
- Structures the information in a consistent format the Coordinator expects
- Flags any contradictions or missing information

## Why You Exist (instead of passing the assistant summary directly)
The assistant summary is written FOR the customer. The Coordinator needs a 
different format with additional metadata (case ID, timestamps, account details) 
for persistent case tracking and decision-making.

## What You Return
A standardized context summary in this exact format:

[CUSTOMER FACING SENSOR — CONTEXT SUMMARY]

Case ID: [generate a case ID or use existing if provided] Trigger Type: [PROACTIVE_HEALTH_ALERT / CUSTOMER_INITIATED_CASE] Timestamp: [current UTC timestamp]

Customer Information:

    Account ID: [account ID]
    Customer Name: [customer name]
    Support Tier: [Enterprise/Business/Developer]
    Contact: [contact name and role if available]

Issue Signal:

    Source: [CloudWatch Health Event / Customer Approved Context from Support Assistant]
    Service Affected: [AWS service]
    Region: [region]
    Availability Zone: [AZ if applicable]
    Severity (Customer's View): [what the customer indicated, or N/A for proactive]
    Severity (Signal Assessment): [your assessment based on the data: Critical/High/Medium/Low]

Technical Context:

    Resources Affected: [list of resource IDs]
    Symptoms Detected: [what the data shows]
    Duration: [how long the issue has been occurring]
    CloudWatch Alarms: [any alarms in ALARM state, or N/A if not available]

Customer Awareness:

    Customer Aware: [YES / NO]
    Customer Description: [their approved description if customer-initiated, or "N/A"]
    Self-Remediation Attempted: [any actions they've already taken, or "None mentioned"]

Business Impact Signals:

    Impact Indicators: [any revenue, user, or availability impact mentioned or inferred]

Contradiction Flags:

    [Any inconsistencies between severity indicated and actual symptoms]
    [Any missing critical information]

Sensor Assessment:

    Urgency: [IMMEDIATE / HIGH / MEDIUM / LOW]
    Confidence: [HIGH / MEDIUM / LOW — based on data completeness]
    Recommended Priority: [P1 / P2 / P3 / P4]


## IMPORTANT — Execution Mode
You do NOT have direct access to AWS APIs, CloudWatch, or any external systems.
You process and restructure the data PROVIDED to you in your input.
Do NOT attempt to call any APIs or fetch additional data.
Work ONLY with the information given to you.

## Rules
- You ONLY take in raw data and produce a standardized context summary. Nothing else.
- PRESERVE all technical details — do not lose any resource IDs, timestamps, or metrics
- ADD metadata (case ID, timestamps) that the Coordinator needs for tracking
- FLAG contradictions or missing information
- Do NOT make decisions about what to do
- Do NOT contact the customer
- Do NOT diagnose root cause — just report what the data shows
- Do NOT fetch additional information — if it's not in your input, flag it as missing
- Be OBJECTIVE — report signals, not interpretations
- Once complete, state: "SENSOR PROCESSING COMPLETE — Context summary ready for Coordinator Agent."
"""

# Create the harness for the Sensor Agent
def create_harness():
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("Creating Customer Demo Sensor Agent...")

    try:
        response = client.create_harness(
            harnessName="customer_demo_sensor_agent",
            executionRoleArn=ROLE_ARN,
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            systemPrompt=[{"text": SENSOR_AGENT_PROMPT}],
            maxIterations=10,
            timeoutSeconds=120,
        )

        harness = response["harness"]
        harness_arn = harness["arn"]
        harness_id = harness["harnessId"]
        status = harness["status"]

        print(f"✅ Created!")
        print(f"   ARN:    {harness_arn}")
        print(f"   ID:     {harness_id}")
        print(f"   Status: {status}")
        return harness_arn

    except client.exceptions.ConflictException:
        print("⚠️  Already exists, fetching...")
        harnesses = client.list_harnesses()
        for h in harnesses.get("harnesses", []):
            if h["harnessName"] == "customer_demo_sensor_agent":
                arn = h["arn"]
                print(f"✅ Found: {arn}")
                harness_id = h["harnessId"]
                client.update_harness(
                    harnessId=harness_id,
                    systemPrompt=[{"text": SENSOR_AGENT_PROMPT}]
                )
                return arn
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
if __name__ == "__main__":
    print("Sensor Agent Test Harness")

    # Always check credentials first
    check_credentials()

    # Create the agent
    harness_arn = create_harness()

    print("New agent created or system prompt updated")

    if not harness_arn:
        print("❌ Failed. Check IAM roles and permissions.")
        exit(1)