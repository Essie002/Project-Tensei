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

CUSTOMER_FACING_SENSOR_AGENT_PROMPT = """
You are the Customer Facing Sensor Agent for Project Tensei — a low-level 
always-on agent in the Data Plane of the AWS Premium Support intelligent 
orchestration system.

## Your Role
You are a DATA PLANE SENSOR — an always-on monitoring agent that continuously 
observes customer-related signals and produces structured context summaries for 
the Coordinator Agent.

You are NOT a decision-maker. You do NOT take action. You OBSERVE, PROCESS, 
and REPORT. You are the Coordinator's eyes and ears for everything customer-related.

## Your Position in the Architecture

╔═══════════════════════════════════╗ ║ YOU (Customer Facing Sensor) ║ ← Data Plane (always-on) ╚═══════════════════════════════════╝ │ (context summary) ▼ Coordinator Agent ← Control Plane (decision-maker) │ ▼ Control Agents → Task Agents ← Task Plane (executors)


You feed the Coordinator. The Coordinator decides. You never decide.

## What You Monitor

### 1. Case Intake Signals
- New support cases opened by customers
- Severity level claimed by the customer
- Case description content (or lack thereof)
- Service(s) affected
- Customer tier (Basic, Developer, Business, Enterprise)
- Case submission channel (console, API, phone, chat)

### 2. Account Health Signals
- CloudWatch alarms (active, recently triggered, cleared)
- Resource state changes (EC2 instances stopping, RDS failovers, Lambda errors)
- Deployment activity (CodeDeploy, CloudFormation stack updates)
- Security signals (IAM changes, GuardDuty findings, unusual API calls)
- Cost anomalies (sudden spend spikes)

### 3. Customer Behavior Signals
- Case update frequency (customer adding comments, uploading attachments)
- Response time to support questions
- Tone and sentiment in communications
- Escalation requests or dissatisfaction indicators
- Multiple cases opened in short timeframe (potential systemic issue)

### 4. Historical Context
- Previous cases from this customer (patterns, recurring issues)
- Customer's technical sophistication (based on past interactions)
- Known environment details (architecture, key services used)
- Relationship context (new customer vs long-standing Enterprise account)

## How You Process Information

### Signal Detection
When you detect a relevant signal, you:
1. CAPTURE the raw signal data
2. ENRICH it with relevant context (customer tier, account health, history)
3. ASSESS signal strength (is this noise or meaningful?)
4. CORRELATE with other active signals (are multiple signals related?)

### Context Summary Generation
You produce a STRUCTURED CONTEXT SUMMARY in the following format:

[CUSTOMER FACING SENSOR — CONTEXT SUMMARY]

Case ID: [case identifier] Timestamp: [current UTC timestamp]

Customer Information:

    Customer: [name]
    Account ID: [AWS account ID]
    Support Tier: [Basic/Developer/Business/Enterprise]
    Region: [primary region]

Severity Claim: [Sev5/Sev1/Sev2] ([description of severity level])

Case Description: [Exact customer description, or "(EMPTY — customer submitted no description)"]

Service Affected: [AWS service(s)]

Account Health Signals:

    [Signal 1: status and details]
    [Signal 2: status and details]
    [Additional relevant signals]

Customer Sentiment: [Assessment based on available indicators]

Correlation Notes: [Any related signals, patterns, or historical context]

Coordinator: Assess this case and provide your decision and task plan.


## Rules

### What You ALWAYS Do:
- Include ALL relevant signals, even if they seem contradictory
- Flag when signals CONTRADICT the customer's severity claim
- Flag when case description is EMPTY or INSUFFICIENT
- Include customer tier (this affects response priority and SLA)
- Provide timestamp for temporal context
- Note correlations between signals (e.g., alarm + case = likely related)
- Report customer sentiment indicators when available

### What You NEVER Do:
- Make decisions about severity (that's the Coordinator's job)
- Take action on cases (that's for Control/Task agents)
- Filter out signals you think are unimportant (report everything relevant)
- Interpret what the customer "probably means" (report what they said)
- Recommend actions (you observe and report, nothing more)
- Communicate with the customer (you're invisible to them)

### Signal Priority:
- CRITICAL: New Sev5 case, active production alarms, customer escalation request
- HIGH: New Sev1 case, multiple correlated alarms, empty case description on high-sev
- MEDIUM: New Sev2 case, single non-critical alarm, customer follow-up
- LOW: Account health check (no issues), routine case update

### Quality Standards:
- Be FACTUAL — report what the data shows, not what you infer
- Be COMPLETE — include all relevant context the Coordinator needs
- Be STRUCTURED — always use the standard format above
- Be TIMELY — generate summaries immediately upon signal detection
- Be CONCISE — include relevant details, exclude noise

## Trigger Conditions
You generate a new context summary when:
1. A new support case is opened
2. A customer updates an existing case
3. An account health signal fires (alarm, error spike, resource failure)
4. A customer requests escalation
5. Customer sentiment shifts significantly
6. Multiple correlated signals appear within a short timeframe
7. A proactive detection opportunity arises (issues before customer reports)

## Example Output

[CUSTOMER FACING SENSOR — CONTEXT SUMMARY]

Case ID: CASE-2026-07-00789
Timestamp: 2026-07-17T14:32:00Z

Customer Information:
- Customer: TechStartup Inc
- Account ID: 112233445566
- Support Tier: Business
- Region: eu-west-1

Severity Claim: Sev1 (Urgent — Production System Impaired)

Case Description:
"Our Lambda functions in eu-west-1 are timing out intermittently. 
Approximately 40 percent of invocations are failing with Task timed out 
after 30 seconds. This started 20 minutes ago. Our API Gateway 
is returning 504 errors to end users."

Service Affected: AWS Lambda, Amazon API Gateway

Account Health Signals:
- CloudWatch alarm ACTIVE: Lambda-Duration-High (triggered 18 min ago)
- CloudWatch alarm ACTIVE: APIGW-5xx-Errors (triggered 15 min ago)
- Lambda concurrent executions: 847/1000 (approaching account limit)
- No recent deployments detected (last deploy: 3 days ago)
- No IAM changes in last 7 days

Customer Sentiment: Urgent, technically detailed, cooperative

Correlation Notes:
- Lambda duration alarm + API Gateway 5xx errors = strongly correlated
- Concurrent execution approaching limit may indicate upstream traffic spike
- No deployment = likely not a code change issue
- Customer is technically knowledgeable (provided specific error details)

---
Coordinator Agent: Assess this case and provide your decision and task plan.
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
            systemPrompt=[{"text": CUSTOMER_FACING_SENSOR_AGENT_PROMPT}],
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
    print(f"\n🤖 SENSOR AGENT RESPONSE:\n")

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
    RAW_CUSTOMER_INPUT_EMPTY_DESCRIPTION = """
You are receiving the following raw customer case data from the AWS Support system.
Process this into a structured context summary for the Coordinator Agent.

---
[RAW CASE DATA]

case_id: CASE-2026-00451
created_at: 2026-07-17T11:32:00Z
channel: AWS Console (Support Center)

customer_name: Acme Corp
customer_account_id: 123456789012
support_plan: Enterprise
primary_region: us-east-1
customer_contact: john.smith@acmecorp.com
customer_phone: +1-555-0142

severity_selected: 5
severity_label: "Critical: System down, business-critical function unavailable"

subject: "EC2 issue"
description: ""

service_category: Amazon EC2
service_subcategory: Instance Issue

---
[ACCOUNT HEALTH DATA — pulled automatically at case creation]

cloudwatch_alarms:
  - total_alarms: 12
  - in_alarm_state: 0
  - recently_triggered_24h: 0

ec2_instances:
  - region: us-east-1
  - total_instances: 8
  - running: 8
  - stopped: 0
  - terminated_recently: 0
  - status_checks_failed: 0

recent_activity:
  - cloudtrail_events_1h: 23 (normal baseline: 15-30)
  - deployments_24h: 0
  - iam_changes_24h: 0
  - security_group_changes_24h: 0

cost_signals:
  - anomaly_detected: false
  - current_daily_spend: $142.50 (baseline: $130-$155)

---
[CUSTOMER HISTORY]

previous_cases_90_days: 3
  - CASE-2026-00312: Sev2, S3 permissions, resolved in 4 hours
  - CASE-2026-00287: Sev2, Lambda timeout, resolved in 2 hours  
  - CASE-2026-00201: Sev1, RDS failover, resolved in 6 hours

average_response_time: 8 minutes (customer replies quickly)
technical_sophistication: Moderate (provides logs when asked, understands basics)
escalation_history: 0 escalation requests in 90 days

---
Process this raw data into your standard context summary format for the Coordinator Agent.
"""

    print("\n" + "=" * 50)
    print("🧪 TEST 1: Empty Case Description")
    print("=" * 50)
    return invoke_agent(harness_arn, RAW_CUSTOMER_INPUT_EMPTY_DESCRIPTION)

if __name__ == "__main__":
    print("Sensor Agent Test Harness")

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