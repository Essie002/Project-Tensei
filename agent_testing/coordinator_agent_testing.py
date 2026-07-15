
# coordinator_agent.py
import boto3
import uuid
import time
import sys

# ============================================================
# CONFIG — Your Isengard account
# ============================================================
REGION = "us-east-1"
ACCOUNT_ID = "070638634443"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/agent_core_execution_role"
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# ============================================================
# CREDENTIAL CHECK — Runs every time
# ============================================================
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

# ============================================================
# SYSTEM PROMPT — Project Tensei Coordinator Agent
# ============================================================
SYSTEM_PROMPT = """
You are the Coordinator Agent for Project Tensei — an AI-powered intelligent 
support orchestration system for AWS Premium Support Engineering.

## Who You Are
You are the HIGH-LEVEL AGENT at the center of a hub-and-spoke + hierarchical 
architecture. You are the ONLY decision-making authority in this system. All 
context flows to you from sensor agents, and all decisions flow from you to 
control agents.

## Your Scope
You manage the ENTIRE AWS Premium Support workflow — from the moment a customer 
opens a case to resolution. This includes:
- Case intake and severity validation
- Intelligent engineer routing and paging
- Proactive issue detection and co-investigation
- Engineer handover with full context preservation
- Admin task orchestration (emails, correspondence, case updates)
- SLA monitoring and escalation management
- Workload balancing across the support team

## What You Receive
You receive continuous context feeds from three always-on sensor agents:

1. CUSTOMER FACING SENSOR:
   - Incoming/pending support cases
   - Case descriptions, severity claims, service affected
   - Customer tier (Basic, Developer, Business, Enterprise)
   - Account health signals (CloudWatch alarms, resource state)
   - Customer sentiment and communication history

2. QUEUE FACING SENSOR:
   - Support queue state (depth, priority mix, inbound rate)
   - SLA timers across all active cases
   - Case aging and escalation status
   - Queue bottlenecks and capacity alerts

3. CSE FACING SENSOR:
   - Engineer availability and online status
   - Current case assignments and workload scores
   - Expertise tags (primary + secondary skills)
   - Shift schedules and break status
   - Active SLA status per engineer

## Your Decision Authority

### Case Intake & Severity
- Validate severity against case description
- Downgrade misclassified severity (e.g., Sev5 with no production impact)
- Request additional information when case description is insufficient
- Prioritize based on customer tier + actual impact

### Intelligent Routing
- Match cases to engineers based on skill, availability, and workload
- NEVER page an engineer handling a past-SLA case
- NEVER page an engineer with availability score below 50
- Consider expertise match, workload balance, and shift timing
- Trigger escalation when no suitable engineer is available

### Investigation & Resolution Support
- Guide co-investigation between AI and customer
- Determine when to escalate from AI to human engineer
- Ensure context is preserved across all handovers
- Track investigation progress and suggest next steps

### Admin & Communication
- Draft emails to management (routing decisions, escalations)
- Generate case breakdowns for assigned engineers
- Draft customer status updates
- Update ticket correspondence and case notes
- Coordinate engineer-to-engineer handovers

### SLA & Escalation Management
- Monitor cumulative wait time across handoffs
- Trigger escalation chains before SLA breach
- Ensure no case silently breaches while bouncing between teams

## How You Respond
For every scenario, provide:
1. ASSESSMENT: What's happening and what's the priority
2. DECISION: What action to take and why (with clear reasoning)
3. DELEGATION: Which control agent(s) to task and with what directive
4. FOLLOW-UP: What to monitor next

You are auditable. Always explain your reasoning clearly.
"""

# ============================================================
# CREATE HARNESS
# ============================================================
def create_harness():
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("Creating Project Tensei Coordinator Agent...")

    try:
        response = client.create_harness(
            harnessName="tensei_coordinator",
            executionRoleArn=ROLE_ARN,
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            systemPrompt=[{"text": SYSTEM_PROMPT}],
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
            if h["harnessName"] == "tensei_coordinator":
                arn = h["arn"]
                print(f"✅ Found: {arn}")
                return arn
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ============================================================
# INVOKE AGENT
# ============================================================
def invoke_agent(harness_arn, message, session_id=None):
    client = boto3.client("bedrock-agentcore", region_name=REGION)

    if not session_id:
        session_id = str(uuid.uuid4()).replace("-", "") + "0"

    print(f"\n{'─' * 50}")
    print(f"📨 INPUT:")
    print(f"{'─' * 50}")
    print(message[:300])
    print(f"{'─' * 50}")
    print(f"\n🤖 COORDINATOR RESPONSE:\n")

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

# ============================================================
# TEST SCENARIOS
# ============================================================
def test_high_sev_relay(harness_arn):
    """Test: High sev relay scenario (mentor's example)"""

    scenario = """
SENSOR CONTEXT:

[CUSTOMER SENSOR]:
- New ticket: Case #12345
- Severity: Sev5 (customer-reported)
- Description: (EMPTY - no description provided)
- Customer: Acme Corp (Enterprise Support tier)
- Service: EC2

[CSE SENSOR]:
- CSE John: Handling Case #11111 (Sev2, PAST SLA by 45 min). Availability: 15/100. Skills: EC2, Networking
- CSE Sarah: No active cases. Availability: 95/100. Skills: EC2, S3, DynamoDB

[QUEUE SENSOR]:
- Queue: 2 CSEs active (John, Sarah)
- Pending: Case #12345 awaiting routing
- SLA timer: Sev5 requires 15-min response

What is your decision?
"""

    print("\n" + "=" * 50)
    print("🧪 TEST 1: High Sev Relay (Invalid Sev5)")
    print("=" * 50)
    return invoke_agent(harness_arn, scenario)


def test_proactive_detection(harness_arn):
    """Test: Proactive issue detection before customer opens a case"""

    scenario = """
SENSOR CONTEXT:

[CUSTOMER SENSOR]:
- No new tickets from this customer
- BUT: CloudWatch alarm triggered for customer MegaCorp (Enterprise tier)
- Alarm: EC2 instance i-0abc123 CPU at 99% for 10 minutes
- Additional signal: 3 Lambda timeout errors in last 5 minutes
- Customer has not opened a case yet

[CSE SENSOR]:
- CSE Mike: Available. Workload: 2/5. Skills: EC2, Lambda, CloudWatch
- CSE Lisa: Available. Workload: 1/5. Skills: Networking, VPC

[QUEUE SENSOR]:
- Queue depth: Low (3 active cases, all within SLA)
- No pending escalations

Should we proactively reach out to the customer? What's your assessment?
"""

    print("\n" + "=" * 50)
    print("🧪 TEST 2: Proactive Issue Detection")
    print("=" * 50)
    return invoke_agent(harness_arn, scenario)


def test_engineer_handover(harness_arn):
    """Test: Engineer-to-engineer handover with context preservation"""

    scenario = """
SENSOR CONTEXT:

[CUSTOMER SENSOR]:
- Active case: Case #99999 (Sev2)
- Customer: GlobalTech (Business Support tier)
- Service: EKS
- Description: "Pods failing to pull images from ECR after VPC change"
- Case opened 2 hours ago, AI co-investigation completed
- AI findings: Checked pod logs (confirmed), checked ECR permissions (OK), 
  checked NetworkPolicy (inconclusive, 45% confidence)
- Customer sentiment: Calm but wants resolution

[CSE SENSOR]:
- CSE David (currently assigned): Shift ending in 10 minutes
- CSE Rachel: Coming online. Workload: 0/5. Skills: EKS, Networking, VPC
- CSE Tom: Available. Workload: 3/5. Skills: EKS, Containers

[QUEUE SENSOR]:
- Case #99999 SLA: 1 hour remaining
- No other urgent cases pending

David's shift is ending. How do you handle the handover?
"""

    print("\n" + "=" * 50)
    print("🧪 TEST 3: Engineer Handover")
    print("=" * 50)
    return invoke_agent(harness_arn, scenario)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    print()
    print("╔════════════════════════════════════════════════╗")
    print("║  PROJECT TENSEI — COORDINATOR AGENT           ║")
    print("║  AWS Premium Support Orchestration            ║")
    print("╚════════════════════════════════════════════════╝")
    print()

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
    response, session_id = test_high_sev_relay(harness_arn)

    # Test 2: Proactive detection (new capability)
    test_proactive_detection(harness_arn)

    # Test 3: Engineer handover (the "wow" moment)
    test_engineer_handover(harness_arn)

    # Follow-up in same session as Test 1 (tests memory)
    if session_id:
        print("\n" + "=" * 50)
        print("🧪 TEST 4: Follow-up (Memory Test)")
        print("=" * 50)
        invoke_agent(
            harness_arn,
            "Draft a short email to John's manager explaining why he wasn't paged for Case #12345.",
            session_id
        )

    print("\n\n✅ All tests complete!")
    print(f"Harness ARN: {harness_arn}")