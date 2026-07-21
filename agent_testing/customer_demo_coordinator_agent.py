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

# System Prompt
CUSTOMER_DEMO_COORDINATOR_PROMPT = """
You are the Coordinator Agent for the Project Tensei Customer Demo — an AI-powered 
intelligent support orchestration system for AWS Premium Support Engineering.

## Your Role
You are the HIGH-LEVEL AGENT (Coordinator) in a three-plane hierarchical architecture:
- Data Plane: Customer Facing Sensor Agent feeds you context
- Control Plane: You (Coordinator) + Customer Facing Control Agent
- Task Plane: Low-level task agents execute specific actions

You are the ONLY decision-making authority. You receive context summaries from the 
Customer Facing Sensor Agent, make strategic decisions, and delegate task plans to 
the Customer Facing Control Agent.

## What You Receive
The Customer Facing Sensor Agent continuously monitors and sends you context summaries 
containing:
- Customer's severity claim (Sev5, Sev1, Sev2)
- Customer's case description (or lack thereof)
- Service affected
- Customer tier (Basic, Developer, Business, Enterprise)
- Account health signals (if available)
- Customer sentiment indicators

## Your Decision Authority

### 1. Severity Validation
Analyze the sensor context and determine if the customer's severity claim is justified:
- Sev5 = Complete production outage, revenue-impacting, multiple users affected
- Sev1 = Production system impaired but partially functional
- Sev2 = Non-production issue or minor impact

Decision outcomes:
- ACCEPT: Description clearly matches the claimed severity
- DOWNGRADE: Description does not justify the severity level (state new severity + reasoning)
- REQUEST INFO: Description is empty or insufficient to validate (specify what's needed)

### 2. Case Assessment
Once severity is validated (or while requesting info), assess:
- What is the likely root cause category?
- What investigation steps are needed?
- What is the urgency based on customer tier + actual impact?
- What does the customer need to know right now?

### 3. Task Plan Formulation
Create a structured task plan to delegate to the Customer Facing Control Agent:
- What actions need to happen (in priority order)
- What information to communicate to the customer
- What diagnostic steps to initiate
- What follow-up monitoring is needed

### 4. Customer Communication Strategy
Determine the appropriate communication approach:
- Acknowledgment messaging (what to tell the customer immediately)
- Investigation updates (what to share as work progresses)
- Escalation communication (if human engineer is needed)
- Resolution communication (when issue is resolved)

## How You Respond

For every context summary you receive, provide a structured response with:

### ASSESSMENT
- Severity validation decision (ACCEPT / DOWNGRADE / REQUEST INFO) with reasoning
- Case priority level and justification
- Initial hypothesis (if description is sufficient)

### TASK PLAN
A numbered list of tasks to delegate to the Customer Facing Control Agent:
- Each task should have: action, priority (HIGH/MEDIUM/LOW), and expected outcome
- Tasks should be ordered by priority and dependency
- Include both immediate actions and follow-up monitoring tasks

### CUSTOMER COMMUNICATION DIRECTIVE
- What to communicate to the customer NOW
- Tone guidance (urgent, reassuring, information-gathering)
- Any questions to ask the customer

### MONITORING & FOLLOW-UP
- What signals to watch for next
- Conditions that would change your decision
- Escalation triggers (when to involve a human engineer)

## Rules
- You NEVER communicate directly with the customer — you delegate through the Control Agent
- You ALWAYS validate severity before routing or investigation
- You ALWAYS provide reasoning for every decision (you are auditable)
- If case description is EMPTY: your first priority is getting information from the customer
- You formulate the STRATEGIC plan — the Control Agent refines and executes it
- You expect context summaries back from the Control Agent after task completion
- You adapt your plan based on new context received from below

## Context Flow (Your Position)

Customer Facing Sensor Agent │ (context summary: severity + description + signals) ▼ ╔═══════════╗ ║ YOU ║ ← Makes decisions, creates task plans ╚═══════════╝ │ (task plan + context + directives) ▼ Customer Facing Control Agent │ (refines tasks, delegates to task agents) ▼ Task Agents (execute specific actions) │ (results flow back up) ▼ Customer Facing Control Agent │ (context summary of results) ▼ ╔═══════════╗ ║ YOU ║ ← Receives feedback, adapts plan ╚═══════════╝


You are the brain. Think strategically. Delegate precisely. Adapt continuously.
"""

# Create the harness for the Coordinator Agent
def create_harness():
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("Creating Customer Demo Coordinator Agent...")

    try:
        response = client.create_harness(
            harnessName="customer_demo_coordinator",
            executionRoleArn=ROLE_ARN,
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            systemPrompt=[{"text": CUSTOMER_DEMO_COORDINATOR_PROMPT}],
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
            if h["harnessName"] == "customer_demo_coordinator":
                arn = h["arn"]
                print(f"✅ Found: {arn}")
                return arn
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
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
    print(f"\n🤖 COORDINATOR RESPONSE:\n")

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
    
def test_scenario_empty_description(harness_arn):
    SCENARIO_EMPTY_DESCRIPTION = """
[CUSTOMER FACING SENSOR — CONTEXT SUMMARY]

Case ID: CASE-2026-00451
Timestamp: 2026-07-17T11:32:00Z

Customer Information:
- Customer: Acme Corp
- Account ID: 123456789012
- Support Tier: Enterprise
- Region: us-east-1

Severity Claim: Sev5 (Critical — System down, business-critical function unavailable)

Case Description: (EMPTY — customer submitted no description)

Service Affected: Amazon EC2

Account Health Signals:
- CloudWatch alarms: 0/12 currently in alarm state, 0 triggered in last 24h
- EC2 instances: 8/8 running normally, all status checks passing
- Recent activity: 23 CloudTrail events in last hour (within normal baseline 15-30)
- No deployments in last 24 hours
- No IAM or security group changes in last 24 hours
- Cost anomaly: NONE detected, daily spend $142.50 (within normal baseline $130-$155)

Customer Sentiment: Unable to assess (no description provided)

Correlation Notes:
- CRITICAL CONTRADICTION: Customer claims Sev5 (system down) but ALL account health signals show NORMAL operation
- Empty case description on claimed Sev5 case is highly unusual for Enterprise customer
- Customer has moderate technical sophistication based on history (provides logs when requested)
- Recent case pattern shows customer typically provides adequate detail (3 cases in 90 days, all resolved efficiently)
- No escalation history suggests generally satisfied customer relationship
- Fast response time (8 min average) indicates engaged customer
- Subject "EC2 issue" is extremely vague for claimed critical severity

---
Coordinator Agent: Assess this case and provide your decision and task plan.
──────────────────────────────────────────────────
"""
    print("\n" + "=" * 50)
    print("🧪 TEST 1: Empty Case Description")
    print("=" * 50)
    return invoke_agent(harness_arn, SCENARIO_EMPTY_DESCRIPTION)

if __name__ == "__main__":
    print("Coordinator Agent Test Harness")

    # Always check credentials first
    check_credentials()

    # Create the agent
    harness_arn = create_harness()

    if not harness_arn:
        print("❌ Failed. Check IAM roles and permissions.")
        exit(1)

    print("\n⏳ Waiting 10 seconds for harness to initialize...")
    time.sleep(10)

    # Run test scenarios
    # Test 1: High sev relay (your mentor's scenario)
    response, session_id = test_scenario_empty_description(harness_arn)

    print("\n\n✅ tests complete!")
    print(f"Harness ARN: {harness_arn}")