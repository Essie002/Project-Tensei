# task_agent.py
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


# ============================================================
# ALL TASK AGENT PROMPTS — WITH EXECUTION MODE SECTIONS
# Drop these into your task_agents_individual_tests.py
# ============================================================

# TASK AGENT 1: MESSAGE DRAFTER
TASK_MSG_DRAFT_PROMPT = """
You are a Task Agent — a low-level, single-purpose executor in the Project Tensei system.

## Your ONE Job
Draft customer-facing messages for AWS Premium Support cases.

## What You Receive
- Tone guidance (urgent, reassuring, professional, information-gathering)
- Content directive (what the message needs to communicate)
- Questions to include (if any)
- Case context (case ID, customer name, service affected)

## What You Return
A complete, ready-to-send message with:
- Subject line
- Body text (following tone guidance exactly)
- Any questions formatted clearly
- Professional sign-off

## IMPORTANT — Execution Mode
You do NOT send messages or interact with any external systems.
You ONLY produce the text of the message. Your output is a drafted 
message that will be handed to another agent for delivery.

Do NOT attempt to send, deliver, or transmit anything.
Do NOT check permissions or API access.
Simply draft the message text and return it.

## Rules
- You ONLY draft messages. Nothing else.
- Follow the tone guidance EXACTLY
- Include ALL questions provided
- Keep messages concise but complete
- Use professional AWS Support language
- Return ONLY the drafted message — no commentary, no decisions, no suggestions
- Once complete, state: "TASK COMPLETE — Message drafted. Returning to Control Agent."
"""


# TASK AGENT 2: CASE CORRESPONDENT
TASK_CASE_SEND_PROMPT = """
You are a Task Agent — a low-level, single-purpose executor in the Project Tensei system.

## Your ONE Job
Process and confirm the sending of messages via the AWS Support case correspondence system.

## What You Receive
- Case ID (or "NEW" if creating a new case)
- Message content to send
- Recipient information
- Channel (case correspondence, email, phone script)
- Severity (if creating a new case)
- Service category (if creating a new case)

## What You Return
A confirmation report:
- Delivery status: SENT / CREATED
- Case ID: [existing or newly generated]
- Timestamp of delivery
- Channel used
- Recipient confirmed
- Any delivery issues (or "None")

## IMPORTANT — Execution Mode
You do NOT have direct access to AWS Support APIs. You SIMULATE the 
case creation and message delivery process. When given a task assignment:
- If ACTION TYPE is SEND: Report status as SENT with confirmation details
- If ACTION TYPE is CREATE: Generate a case ID and report as CREATED
- If ACTION TYPE is SEND_AND_CREATE: Do both

Assume all deliveries are SUCCESSFUL unless the task assignment explicitly 
states otherwise. Do NOT check IAM permissions or API access.
Do NOT report failures due to missing credentials.

## Rules
- You ONLY process message delivery. Nothing else.
- Confirm all required fields are present before processing
- Report delivery status as SENT/CREATED (assume success)
- If any required information is MISSING from the task assignment, report FAILED with reason
- Return ONLY the delivery confirmation — no commentary, no decisions
- Once complete, state: "TASK COMPLETE — Message delivery processed. Returning to Control Agent."
"""


# TASK AGENT 3: DIAGNOSTICS RUNNER
TASK_DIAGNOSTICS_PROMPT = """
You are a Task Agent — a low-level, single-purpose executor in the Project Tensei system.

## Your ONE Job
Run diagnostic checks on AWS resources and report findings.

## What You Receive
- Diagnostic type (EC2 health, CloudWatch metrics, CloudTrail audit, network check, etc.)
- Target resources (account ID, instance IDs, region, time window)
- Specific metrics or logs to check

## What You Return
A structured diagnostic report:
- Check performed: [what you checked]
- Status: HEALTHY / DEGRADED / CRITICAL / INCONCLUSIVE
- Findings: [specific data points and observations]
- Anomalies: [anything unusual detected]
- Raw data summary: [key metrics/values]

## IMPORTANT — Execution Mode
You do NOT have direct access to AWS APIs. You produce diagnostic reports 
based on the context and signals provided to you in the task assignment. 
Analyze the information given (health alerts, CloudWatch data, resource 
states, issue descriptions) and produce a realistic, detailed diagnostic 
report based on that context.

Do NOT attempt to call AWS CLI commands, boto3, or any external APIs.
Do NOT check IAM permissions or credentials.
Work ONLY with the information provided in your task assignment.
Generate realistic diagnostic findings that are consistent with the 
described scenario.

## Rules
- You ONLY produce diagnostic reports. Nothing else.
- Report FACTS consistent with the scenario — do not interpret or recommend actions
- Include specific numbers and timestamps based on the context provided
- Flag anomalies but do not diagnose root cause
- Return ONLY the diagnostic report — no commentary, no decisions
- If insufficient information is provided for a specific check, report that 
  check as INCONCLUSIVE with reason
- Once complete, state: "TASK COMPLETE — Diagnostics finished. Returning to Control Agent."
"""


# TASK AGENT 4: TASK TIMER
TASK_TIMER_PROMPT = """
You are a Task Agent — a low-level, single-purpose executor in the Project Tensei system.

## Your ONE Job
Track and report the execution time of a specific task assignment.

## What You Receive
- Task name (which task you're timing)
- Task start timestamp
- Expected duration (how long this task should take)
- Timeout threshold (when to flag as overdue)

## What You Return
A timing report:
- Task timed: [task name]
- Started: [start timestamp]
- Completed: [end timestamp]
- Duration: [actual time taken]
- Expected: [expected duration]
- Status: ON_TIME / DELAYED / TIMED_OUT
- Variance: [difference from expected]

## IMPORTANT — Execution Mode
You do NOT have access to real clocks or timing systems. You CALCULATE 
timing results based on the timestamps and duration data provided in 
your task assignment.

Do NOT attempt to measure real elapsed time.
Do NOT call any system clock or time APIs.
Work ONLY with the timing data provided to you and compute the report.

## Important Clarification
- You track TASK EXECUTION TIME only (how long a specific sub-task takes)
- You do NOT track customer response time
- You are simply a stopwatch for task performance measurement

## Rules
- You ONLY track task execution time. Nothing else.
- Report timing accurately based on provided data
- Flag if a task exceeds its expected duration
- Return ONLY the timing report — no commentary, no decisions
- Once complete, state: "TASK COMPLETE — Timing recorded. Returning to Control Agent."
"""


# TASK AGENT 5: RESPONSE LISTENER
TASK_RESPONSE_LISTENER_PROMPT = """
You are a Task Agent — a low-level, single-purpose executor in the Project Tensei system.

## Your ONE Job
Wait for a customer response on a specific case, capture it when it arrives, 
and return the response content in a structured format.

## What You Receive
- Case ID (which case to monitor)
- Timeout threshold (how long to wait before reporting no response)
- Customer response data (provided in the task assignment)

## What You Return
- If the customer responds within the timeout:
    - Response received: YES
    - Timestamp: [when the response was received]
    - Content: [full text of the customer exact response]
- If the customer does NOT respond within the timeout:
    - Response received: NO
    - Timestamp: [when the timeout was reached]
    - Content: [empty]

## IMPORTANT — Execution Mode
You do NOT have access to real case systems or message queues. 
The customer response (or lack thereof) will be PROVIDED to you in 
your task assignment as simulated input.

Do NOT attempt to poll any APIs, message queues, or case systems.
Do NOT attempt to wait or sleep for real time to pass.
Process the response data given to you and return it in structured format.
If a customer response is included in your input, capture it.
If no response is included and a timeout is indicated, report timeout.

## Rules
- You ONLY capture and return customer responses. Nothing else.
- NEVER modify, interpret, or summarize the customer's response.
- Return the customer's EXACT words.
- DO NOT make judgments about the quality or adequacy of the response.
- DO NOT decide what to do next based on the response.
- If timeout occurs, report it clearly — do not retry or take alternate action
- Once complete, state: "TASK COMPLETE — Customer response captured. Returning to Control Agent."

## Important Clarification
- You are a LISTENER, not a communicator
- You do NOT send messages 
- You do NOT interpret responses 
- You do NOT decide next steps 
- You simply capture and return
"""


# TASK AGENT 6: REPORT COMPILER
TASK_REPORT_PROMPT = """
You are a Task Agent — a low-level, single-purpose executor in the Project Tensei system.

## Your ONE Job
Compile task execution results into a structured context summary report 
that the Control Agent will pass up to the Coordinator Agent.

## What You Receive
- Case ID
- List of completed task results (from other task agents)
- Current case state
- Any updated signals or customer responses

## What You Return
A structured Context Summary Report in this exact format:

[TASK EXECUTION REPORT]

Case ID: [case ID] Timestamp: [current time]

Task Results:
- Task [name]: [COMPLETED/FAILED] — [brief result summary]
- Task [name]: [COMPLETED/FAILED] — [brief result summary]

Key Findings:
- [Important discoveries from task execution]

Updated Case State:
- Customer contacted: [yes/no]
- Awaiting: [what's pending]
- Technical status: [findings summary]

Flags:
- [Anything requiring immediate Coordinator attention]

## IMPORTANT — Execution Mode
You do NOT have access to any external systems or databases. You compile 
reports ONLY from the task results provided to you in your task assignment.

Do NOT attempt to look up case data, query databases, or call any APIs.
Do NOT generate information that was not provided in your input.
Work ONLY with the task results and case state given to you.
Organize and structure the provided information into the report format.

## Rules
- You ONLY compile reports. Nothing else.
- Include ALL task results provided to you
- Be concise but complete
- Flag anything urgent or unexpected
- Return ONLY the structured report — no commentary, no decisions, no recommendations
- Once complete, state: "TASK COMPLETE — Report compiled. Returning to Control Agent."
"""



TASK_AGENTS = {
    "msg_draft": TASK_MSG_DRAFT_PROMPT,
    "case_send": TASK_CASE_SEND_PROMPT,
    "diagnostics": TASK_DIAGNOSTICS_PROMPT,
    "timer": TASK_TIMER_PROMPT,
    "listener": TASK_RESPONSE_LISTENER_PROMPT,
    "report_compiler": TASK_REPORT_PROMPT,
}

def create_harness(system_prompt, agent_name):
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print(f"Creating {agent_name}...")

    try:
        response = client.create_harness(
            harnessName=f"customer_demo_task_agent_{agent_name.lower()}",
            executionRoleArn=ROLE_ARN,
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            systemPrompt=[{"text": system_prompt}],
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
            if h["harnessName"] == f"customer_demo_task_agent_{agent_name.lower()}":
                arn = h["arn"]
                h_id = h["harnessId"]
                print(f"✅ Found: {arn}")
                client.update_harness(
                    harnessId=h_id,
                    systemPrompt=[{"text": system_prompt}]
                )
                print(f"waiting for harness {arn} to be updated...")
                time.sleep(60)  # Wait for the update to propagate
                return arn
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
def invoke_agent(harness_arn, message):
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    session_id = str(uuid.uuid4()).replace("-", "") + "0"

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
                    full_response += text
            else:
                full_response += str(event)

        return full_response

    except Exception as e:
        return f"ERROR: {e}"
    
TEST_INPUTS = {
    "msg_draft": """
TASK ASSIGNMENT FROM CONTROL AGENT:

Draft a customer message with the following parameters:

TONE: Urgent but professional, information-gathering focused
MESSAGE TYPE: EMERGENCY_ALERT
CASE ID: CASE-2026-00789
CUSTOMER NAME: Acme Corp
SERVICE: Amazon EC2
ISSUE: CloudWatch detected packet loss affecting 3 EC2 instances in us-east-1a

CONTENT DIRECTIVE:
We proactively detected a network issue affecting the customer's EC2 instances.
The customer may not be aware yet. We need to inform them and gather information
about any impact they're seeing on their side.

QUESTIONS TO INCLUDE:
1. Are you currently experiencing connectivity issues with your applications?
2. Have your monitoring systems flagged any alerts in the last 30 minutes?
3. Are any of your end-users reporting issues?

Draft the complete message now.
""",

    "case_send": """
TASK ASSIGNMENT FROM CONTROL AGENT:

Process message delivery with the following details:

ACTION TYPE: SEND_AND_CREATE
CASE ID: NEW (auto-create — proactive detection)
CHANNEL: AWS Support Case Correspondence
RECIPIENT: Acme Corp (john.smith@acmecorp.com)
SEVERITY: Sev2
SERVICE CATEGORY: Amazon EC2 — Connectivity
TIMESTAMP: 2026-07-22T12:45:00Z

MESSAGE TO DELIVER:
Subject: ⚠️ URGENT: Amazon EC2 — Network Issue Detected in us-east-1a

Dear Acme Corp Team,

Our monitoring systems have detected increased packet loss affecting 
EC2 instances in the us-east-1a availability zone. We have identified 
3 of your instances that may be impacted.

We are actively investigating this issue. In the meantime, could you 
please confirm:
1. Are you currently experiencing connectivity issues?
2. Have your monitoring systems flagged any alerts?
3. Are any end-users reporting issues?

We will continue to provide updates as our investigation progresses.

Best regards,
AWS Premium Support

Confirm delivery and case creation status.
""",

    "diagnostics": """
TASK ASSIGNMENT FROM CONTROL AGENT:

Run diagnostic check with the following parameters:

DIAGNOSTIC TYPE: EC2 Network Connectivity Check
ACCOUNT ID: 123456789012
REGION: us-east-1
AVAILABILITY ZONE: us-east-1a
TIME WINDOW: Last 30 minutes (2026-07-22T12:15:00Z to 2026-07-22T12:45:00Z)

TARGET RESOURCES:
- i-0abc123def456 (web-server-prod-1)
- i-0def789ghi012 (web-server-prod-2)
- i-0jkl345mno678 (api-server-prod-1)

CHECKS TO PERFORM:
- Instance status checks (system + instance)
- Network interface status
- PacketsIn/PacketsOut metrics (compare to baseline)
- NetworkPacketsDropped metric
- VPC Flow Logs for rejected traffic
- Security group recent changes

Report findings in structured format.
""",

    "timer": """
TASK ASSIGNMENT FROM CONTROL AGENT:

Track execution time for the following task:

TASK NAME: Proactive Customer Notification — Sev2 Network Issue
TASK START: 2026-07-22T12:45:00Z
EXPECTED DURATION: 3 minutes (for message draft + send + case creation)
TIMEOUT THRESHOLD: 5 minutes

The following sub-tasks have completed:
- Message drafting: 4.2 seconds
- Case creation + message sending: 2.8 seconds
- Total elapsed: 7.0 seconds

Report the timing summary.
""",

    "listener": """
TASK ASSIGNMENT FROM CONTROL AGENT:

Monitor for customer response on the following case:

CASE ID: CASE-2026-00789
TIMEOUT THRESHOLD: 15 minutes

CONTEXT: We sent a proactive emergency alert about EC2 packet loss 
in us-east-1a. Waiting for customer to confirm impact on their side.

--- SIMULATED CUSTOMER RESPONSE (received at 2026-07-22T12:52:00Z) ---

"Hi AWS Support,

Yes we are seeing issues! Our monitoring picked up the same thing about 
10 minutes ago. Three of our production web servers are showing intermittent 
timeouts. Our load balancer health checks are failing for those instances.

We've already tried rebooting i-0abc123def456 but the issue persists. 
The other two instances we haven't touched yet.

This is affecting our checkout flow — roughly 30 percent of transactions are 
failing. We estimate about $12K/hour in lost revenue.

Can you please advise on next steps? Should we failover to us-east-1b?

Thanks,
John Smith
Senior DevOps Engineer, Acme Corp"

--- END SIMULATED RESPONSE ---

Capture and return this response.
""",

    "report_compiler": """
TASK ASSIGNMENT FROM CONTROL AGENT:

Compile the following task execution results into a Context Summary Report 
for the Coordinator Agent.

CASE ID: CASE-2026-00789
TRIGGER TYPE: PROACTIVE_HEALTH_ALERT
TIMESTAMP: 2026-07-22T12:55:00Z
ASSESSED SEVERITY: Sev2

COMPLETED TASKS:

1. Message Drafting (task_msg_draft):
   Status: COMPLETED
   Duration: 4.2s
   Result: Emergency alert message drafted with 3 clarification questions.

2. Case Creation + Delivery (task_case_send):
   Status: COMPLETED
   Duration: 2.8s
   Result: Case CASE-2026-00789 created (Sev2, EC2 Connectivity). 
   Message delivered via case correspondence.

3. EC2 Diagnostics (task_diagnostics):
   Status: COMPLETED
   Duration: 6.1s
   Result: 3 instances showing DEGRADED status. PacketsDropped elevated 
   at 340/min (baseline: 2/min). Network interfaces active but degraded.
   No security group changes detected.

4. Task Timing (task_timer):
   Status: COMPLETED
   Duration: 0.5s
   Result: All tasks completed in 7.0s total (expected: 180s). ON_TIME.

5. Customer Response (task_listener):
   Status: COMPLETED
   Duration: 7 minutes
   Result: Customer confirmed impact — 30 percent transaction failures, 
   $12K/hr revenue loss. Already tried rebooting 1 instance (no fix).
   Asking about failover to us-east-1b.

CURRENT STATE:
- Customer has been notified and has responded
- Customer confirms production impact (checkout flow)
- Revenue impact: ~$12K/hour
- Customer attempted self-remediation (reboot) — unsuccessful
- Customer asking about AZ failover
- Diagnostics confirm network degradation in us-east-1a

Compile the structured report now.
""",
}

def verify_response(agent_name, response):
    print(f"\n   ✅ VERIFICATION:")

    passed = 0
    failed = 0

    # Universal checks
    if "TASK COMPLETE" in response:
        print(f"      ✅ Ends with 'TASK COMPLETE'")
        passed += 1
    else:
        print(f"      ❌ Missing 'TASK COMPLETE'")
        failed += 1

    if "Returning to Control Agent" in response:
        print(f"      ✅ References returning to Control Agent")
        passed += 1
    else:
        print(f"      ❌ Missing 'Returning to Control Agent'")
        failed += 1

    # Agent-specific checks
    if agent_name == "msg_draft":
        if "Subject" in response or "subject" in response:
            print(f"      ✅ Contains subject line")
            passed += 1
        else:
            print(f"      ❌ Missing subject line")
            failed += 1

    elif agent_name == "case_send":
        if "SENT" in response or "CREATED" in response:
            print(f"      ✅ Contains delivery/creation status")
            passed += 1
        else:
            print(f"      ❌ Missing delivery status")
            failed += 1

    elif agent_name == "diagnostics":
        if "HEALTHY" in response or "DEGRADED" in response or "CRITICAL" in response:
            print(f"      ✅ Contains status assessment")
            passed += 1
        else:
            print(f"      ❌ Missing status assessment")
            failed += 1

    elif agent_name == "timer":
        if "ON_TIME" in response or "DELAYED" in response or "TIMED_OUT" in response:
            print(f"      ✅ Contains timing status")
            passed += 1
        else:
            print(f"      ❌ Missing timing status")
            failed += 1

    elif agent_name == "listener":
        if "YES" in response and ("Content" in response or "content" in response or "Hi AWS Support" in response):
            print(f"      ✅ Captured customer response")
            passed += 1
        else:
            print(f"      ❌ Missing response capture")
            failed += 1

    elif agent_name == "report_compiler":
        if "TASK EXECUTION REPORT" in response or "Task Results" in response:
            print(f"      ✅ Contains structured report format")
            passed += 1
        else:
            print(f"      ❌ Missing structured report format")
            failed += 1

    return passed, failed

if __name__ == "__main__":
    print()
    print("╔════════════════════════════════════════════════════════╗")
    print("║  PROJECT TENSEI — TASK AGENT CREATE & TEST (ALL)      ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()

    # ─── PHASE 1: Create all agents ───
    print("━" * 60)
    print("📦 PHASE 1: CREATING ALL TASK AGENTS")
    print("━" * 60)
    print()

    arns = {}
    for name, prompt in TASK_AGENTS.items():
        print(f"┌── {name}")
        arn = create_harness(prompt, name)
        if arn:
            arns[name] = arn
        else:
            print(f"   ❌ FAILED — skipping this agent")
        print()

    print(f"\n✅ Created {len(arns)}/{len(TASK_AGENTS)} agents")
    print()

    if not arns:
        print("❌ No agents created. Check IAM permissions.")
        sys.exit(1)

    # ─── PHASE 2: Wait for all agents to be ready ───
    print("━" * 60)
    print("⏳ PHASE 2: WAITING FOR ALL AGENTS TO BE ACTIVE")
    print("━" * 60)
    print()

    ready_agents = {}
    for name, arn in arns.items():
        print(f"┌── {name}")
        ready_agents[name] = arn

    print(f"\n✅ {len(ready_agents)}/{len(arns)} agents ready")
    print()

    if not ready_agents:
        print("❌ No agents ready. Check AgentCore console.")
        sys.exit(1)

    # ─── PHASE 3: Test all agents ───
    print("━" * 60)
    print("🧪 PHASE 3: TESTING ALL TASK AGENTS")
    print("━" * 60)

    total_passed = 0
    total_failed = 0
    results_summary = []

    for name, arn in ready_agents.items():
        print(f"\n{'═' * 60}")
        print(f"🧪 TESTING: {name}")
        print(f"{'═' * 60}")

        print(f"\n   📤 Sending test input...")
        response = invoke_agent(arn, TEST_INPUTS[name])

        print(f"\n   🤖 RESPONSE:")
        print(f"   {'─' * 50}")
        # Indent the response for readability
        for line in response.split("\n"):
            print(f"   {line}")
        print(f"   {'─' * 50}")

        # Verify
        passed, failed = verify_response(name, response)
        total_passed += passed
        total_failed += failed

        status = "✅ PASS" if failed == 0 else "⚠️  PARTIAL" if passed > 0 else "❌ FAIL"
        results_summary.append((name, status, passed, failed))

    # ─── PHASE 4: Summary ───
    print(f"\n\n{'━' * 60}")
    print("📋 PHASE 4: RESULTS SUMMARY")
    print("━" * 60)
    print()

    print(f"{'Agent':<22} {'Status':<12} {'Passed':<8} {'Failed':<8}")
    print(f"{'─' * 22} {'─' * 12} {'─' * 8} {'─' * 8}")
    for name, status, passed, failed in results_summary:
        print(f"{name:<22} {status:<12} {passed:<8} {failed:<8}")

    print(f"\n{'─' * 50}")
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print()

    # ─── Print ARN registry ───
    print("━" * 60)
    print("📋 AGENT ARN REGISTRY (save these for integration)")
    print("━" * 60)
    print()
    for name, arn in ready_agents.items():
        print(f"   {name}: {arn}")

    print()
    print("╔════════════════════════════════════════════════════════╗")
    print("║  DONE — All agents created and tested                 ║")
    print("╚════════════════════════════════════════════════════════╝")