
# agent_flow_testing.py
# ============================================================
# PROJECT TENSEI — FULL AUTONOMOUS AGENT PIPELINE
# ============================================================
# Complete flow with feedback loop:
#   Sensor → Coordinator → Control (PLANNING) → Task Agents 
#   → Control (REPORTING) → Coordinator (FINAL ASSESSMENT)
#
# Three test scenarios:
#   1. Low Sev Proactive (Sev4) — notification only, no case
#   2. High Sev Proactive (Sev2) — notification + case auto-opened
#   3. Customer-Initiated Case — customer requested case via Support Assistant
# ============================================================

import boto3
import uuid
import time
import sys
import re
from datetime import datetime, timezone

# ============================================================
# CONFIG
# ============================================================
REGION = "us-east-1"
ACCOUNT_ID = "070638634443"

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
    "task_listener": "arn:aws:bedrock-agentcore:us-east-1:070638634443:harness/customer_demo_task_agent_listener-3m6bcTYDXV",
}


# ============================================================
# CREDENTIAL CHECK
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
        print("   Fix: Set your credentials:")
        print('   $env:AWS_ACCESS_KEY_ID="ASIA..."')
        print('   $env:AWS_SECRET_ACCESS_KEY="..."')
        print('   $env:AWS_SESSION_TOKEN="..."')
        print()
        sys.exit(1)


# ============================================================
# CONTEXT EXTRACTION HELPERS
# ============================================================
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


def extract_msg_draft_content(msg_draft_output):
    """
    Extract the actual message from msg_draft's output.
    Strips any meta-commentary and returns only the message.
    """
    if not msg_draft_output:
        return "MESSAGE DRAFT FAILED"

    # Remove the TASK COMPLETE line
    cleaned = re.sub(r'TASK COMPLETE.*?Control Agent\.?', '', msg_draft_output).strip()

    # Remove leading/trailing --- markers
    cleaned = re.sub(r'^---\s*', '', cleaned)
    cleaned = re.sub(r'\s*---$', '', cleaned)

    # If it starts with "Subject:" we're good
    if 'Subject:' in cleaned:
        subject_match = re.search(r'(Subject:.*)', cleaned, re.DOTALL)
        if subject_match:
            return subject_match.group(1).strip()

    # Remove common preamble patterns
    preamble_patterns = [
        r'^I understand\..*?\n',
        r'^I will draft.*?\n',
        r'^I\'ll.*?\n',
        r'^Here is the.*?:\s*\n',
        r'^Processing.*?\n',
    ]
    for pattern in preamble_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def validate_msg_draft(msg_draft_output):
    """
    Check if msg_draft actually returned a real message.
    Returns (is_valid, message_or_error)
    """
    if not msg_draft_output:
        return False, "msg_draft returned empty response"

    content = extract_msg_draft_content(msg_draft_output)

    has_subject = 'subject:' in content.lower()
    has_body = len(content) > 100
    has_greeting = any(word in content.lower() for word in ['dear', 'hello', 'hi ', 'team'])

    if has_subject and has_body:
        return True, content
    elif has_body and has_greeting:
        return True, content
    else:
        return False, f"msg_draft did not return a valid message. Got: {content[:200]}"


def build_task_results_summary(task_results):
    """
    Build a structured summary of all task agent results for the Control Agent
    to compile into its context summary report.
    """
    summary = "[TASK AGENT RESULTS — FOR CONTROL AGENT REPORTING]\n\n"

    for agent_name, output in task_results.items():
        summary += f"── {agent_name.upper()} RESULT ──\n"
        if output:
            # Trim to reasonable length per agent (keep it focused)
            trimmed = output[:1500] if len(output) > 1500 else output
            summary += f"{trimmed}\n\n"
        else:
            summary += "FAILED — No output received.\n\n"

    summary += "── END OF TASK AGENT RESULTS ──\n"
    summary += "\nCompile these results into your CONTEXT SUMMARY REPORT for the Coordinator Agent."
    return summary


# ============================================================
# AGENT INVOCATION
# ============================================================
def invoke_agent(agent_key, agent_name, context, session_id=None):
    """
    Invoke an agent and return its full response text.
    """
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    harness_arn = AGENT_ARNS[agent_key]

    if not session_id:
        session_id = str(uuid.uuid4()).replace("-", "") + "0"

    print(f"\n{'━' * 60}")
    print(f"  📨 INPUT TO {agent_name.upper()}")
    print(f"{'━' * 60}")
    preview = context[:500]
    if len(context) > 500:
        preview += f"\n... ({len(context) - 500} more characters)"
    print(preview)
    print(f"{'━' * 60}")
    print(f"\n  🤖 {agent_name.upper()} RESPONSE:\n")

    try:
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=[{"role": "user", "content": [{"text": context}]}],
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

        print(f"\n{'━' * 60}")
        return full_response, session_id

    except Exception as e:
        print(f"  ❌ Error invoking {agent_name}: {e}")
        return None, session_id


# ============================================================
# TASK AGENT EXECUTION
# ============================================================
def run_task_agents(control_output, scenario_type):
    """
    Execute task agents based on scenario type.
    Returns dict of all task agent outputs.
    """
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 4: TASK AGENT EXECUTION                           │")
    print("│  Invoking task agents per Control Agent's execution plan  │")
    print("└──────────────────────────────────────────────────────────┘")

    task_results = {}

    if scenario_type == "low_sev_proactive":
        # ─── Phase 1 (PARALLEL): msg_draft + diagnostics ───
        print("\n  ── Phase 1: msg_draft + diagnostics (parallel) ──")

        msg_input = """TASK ASSIGNMENT:
- Action: Draft a notification message for the customer
- Tone: Professional, informational, calm
- Content Directive: Inform the customer about a minor health event detected 
  in their environment. A single EC2 instance (i-0abc123def456, t3.medium) in 
  us-east-1a is experiencing intermittent status check failures. All other 
  instances are healthy. No immediate action required but we are monitoring.
  Let them know we detected it proactively.
  Include self-remediation options: instance reboot or stop/start cycle.
  Include option to open a support case if they want further investigation.
- Questions to Include: None (this is informational only)
- Case Context: No case opened. This is a notification only.
- Customer Name: NovaTech Solutions
- Account ID: 556677889900
- Service Affected: Amazon EC2
- Region: us-east-1

Return the FULL message text — subject line, body, and sign-off.
Do not describe what you are going to write. Just write the message."""

        msg_result, _ = invoke_agent("task_msg_draft", "Message Drafter", msg_input)
        task_results["msg_draft"] = msg_result
        time.sleep(2)

        # Validate
        is_valid, message_content = validate_msg_draft(msg_result)
        if is_valid:
            print(f"\n  ✅ msg_draft validated — message is {len(message_content)} chars")
        else:
            print(f"\n  ⚠️  WARNING: msg_draft validation failed: {message_content}")

        diag_input = """TASK ASSIGNMENT:
- Diagnostic Type: EC2 Health Check
- Target Resources:
  - Account ID: 556677889900
  - Instance ID: i-0abc123def456 (t3.medium)
  - Region: us-east-1
  - Availability Zone: us-east-1a
- Specific Checks:
  - Instance status checks (pass/fail history last 30 min)
  - System status checks (pass/fail history last 30 min)
  - CPU utilization trend (last 30 min)
  - Network connectivity
  - EBS volume health
  - Hypervisor communication
- Time Window: Last 30 minutes
- Context: CloudWatch alarm triggered for StatusCheckFailed. Instance is 
  still running but one status check is failing intermittently. All other 
  3 instances in the account are healthy. No recent deployments or config changes."""

        diag_result, _ = invoke_agent("task_diagnostics", "Diagnostics Runner", diag_input)
        task_results["diagnostics"] = diag_result
        time.sleep(2)

        # ─── Phase 2: notification_send (needs msg_draft output) ───
        print("\n  ── Phase 2: notification_send (sequential — needs msg_draft) ──")

        actual_message = extract_msg_draft_content(msg_result) if msg_result else "MESSAGE DRAFT FAILED"

        notif_input = f"""TASK ASSIGNMENT:
- Notification Type: Health Alert
- Message Content:
{actual_message}
- Recipient: NovaTech Solutions (Account: 556677889900)
- Contact: ops-team@novatech.io
- Priority: Standard
- Case Auto-Assigned: NO"""

        notif_result, _ = invoke_agent("task_notification_send", "Notification Sender", notif_input)
        task_results["notification_send"] = notif_result
        time.sleep(2)

        # ─── Phase 3: timer ───
        print("\n  ── Phase 3: timer ──")

        timer_input = """TASK ASSIGNMENT:
- Task Name: Low Sev Proactive Notification Pipeline
- Task Start Timestamp: 2026-07-24T10:00:00Z
- Expected Duration: 5 minutes
- Timeout Threshold: 10 minutes
- Tasks Tracked:
  - msg_draft: started 10:00:00, completed 10:00:45
  - diagnostics: started 10:00:00, completed 10:01:30
  - notification_send: started 10:01:32, completed 10:01:58"""

        timer_result, _ = invoke_agent("task_timer", "Task Timer", timer_input)
        task_results["timer"] = timer_result

    elif scenario_type == "high_sev_proactive":
        # ─── Phase 1 (PARALLEL): msg_draft x2 + diagnostics ───
        print("\n  ── Phase 1: msg_draft (notification) + msg_draft (correspondence) + diagnostics (parallel) ──")

        msg_notif_input = """TASK ASSIGNMENT:
- Action: Draft an EMERGENCY notification message
- Tone: Urgent, clear, action-oriented
- Content Directive: Alert the customer that a critical health event has been 
  detected in their RDS database (db-prod-primary, db.r5.2xlarge, us-west-2).
  Current state: CPU at 97%, memory at 128MB (from 8GB baseline), read latency 
  45ms (baseline 2ms), 487 active connections (baseline 50-80), replica lag 850ms.
  4 CloudWatch alarms are firing simultaneously.
  Inform them that a support case has been automatically assigned: CASE-2026-00892.
  Include a link to view the case correspondence section:
  https://support.aws.amazon.com/cases/CASE-2026-00892/correspondence
  Emphasize urgency — their production database is at risk of failure.
- Questions to Include: None (this is an alert, questions go in case correspondence)
- Customer Name: GlobalFinance Ltd
- Account ID: 998877665544
- Service Affected: Amazon RDS (PostgreSQL 14.9)
- Region: us-west-2

Return the FULL message text — subject line, body, and sign-off.
Do not describe what you are going to write. Just write the message."""

        msg_notif_result, _ = invoke_agent("task_msg_draft", "Message Drafter (Notification)", msg_notif_input)
        task_results["msg_draft_notification"] = msg_notif_result
        time.sleep(2)

        msg_case_input = """TASK ASSIGNMENT:
- Action: Draft a case correspondence message for the newly opened case
- Tone: Urgent but professional, reassuring that we are actively investigating
- Content Directive: This is the first message in case CASE-2026-00892. 
  Inform the customer:
  1. We proactively detected a critical issue with their RDS instance (db-prod-primary)
  2. Current state: CPU 97%, memory 128MB remaining, read latency 45ms (baseline 2ms),
     487 active connections (baseline 50-80), replica lag 850ms
  3. We are actively running diagnostics
  4. A deployment occurred 3 hours ago (v2.4.1 — new reporting module) which may be related
  5. An engineer is being paged for immediate assistance
- Questions to Include:
  - Have there been any recent application changes related to the v2.4.1 deployment?
  - Is this database serving production traffic right now?
  - Do you have a read replica that could take over if needed?
  - Can you identify any new queries from the reporting module that might be causing load?
- Case Context: CASE-2026-00892, Sev2, Amazon RDS
- Customer Name: GlobalFinance Ltd
- Contact: infrastructure@globalfinance.com

Return the FULL message text — subject line, body, and sign-off.
Do not describe what you are going to write. Just write the message."""

        msg_case_result, _ = invoke_agent("task_msg_draft", "Message Drafter (Correspondence)", msg_case_input)
        task_results["msg_draft_correspondence"] = msg_case_result
        time.sleep(2)

        diag_input = """TASK ASSIGNMENT:
- Diagnostic Type: RDS Performance Analysis
- Target Resources:
  - Account ID: 998877665544
  - RDS Instance: db-prod-primary (db.r5.2xlarge, PostgreSQL 14.9)
  - Region: us-west-2
  - Availability Zone: us-west-2a
- Specific Checks:
  - CPU utilization trend (last 1 hour)
  - Freeable memory trend (last 1 hour)
  - Read/Write latency (last 1 hour)
  - Active connections count vs baseline
  - Replica lag (db-prod-replica-1)
  - ReadIOPS and WriteIOPS
  - Recent slow queries or query count spike
  - Connection pool saturation indicators
- Time Window: Last 60 minutes
- Context: 4 CloudWatch alarms firing simultaneously. CPU at 97%, memory at 
  128MB (baseline 8GB), read latency 45ms (baseline 2ms), 487 active connections 
  (baseline 50-80). Application deployment v2.4.1 occurred 3 hours ago adding 
  a new reporting module. EC2 app servers also elevated at 78% CPU (baseline 25%)."""

        diag_result, _ = invoke_agent("task_diagnostics", "Diagnostics Runner", diag_input)
        task_results["diagnostics"] = diag_result
        time.sleep(2)

        # ─── Phase 2: notification_send + case_send (parallel) ───
        print("\n  ── Phase 2: notification_send + case_send (parallel — both need msg_draft) ──")

        actual_notif_message = extract_msg_draft_content(msg_notif_result) if msg_notif_result else "MESSAGE DRAFT FAILED"
        actual_case_message = extract_msg_draft_content(msg_case_result) if msg_case_result else "MESSAGE DRAFT FAILED"

        is_valid_notif, _ = validate_msg_draft(msg_notif_result)
        is_valid_case, _ = validate_msg_draft(msg_case_result)
        if is_valid_notif:
            print("  ✅ Notification message validated")
        else:
            print("  ⚠️  WARNING: Notification message validation failed")
        if is_valid_case:
            print("  ✅ Case correspondence message validated")
        else:
            print("  ⚠️  WARNING: Case correspondence message validation failed")

        notif_input = f"""TASK ASSIGNMENT:
- Notification Type: Health Alert (Emergency)
- Message Content:
{actual_notif_message}
- Recipient: GlobalFinance Ltd (Account: 998877665544)
- Contact: infrastructure@globalfinance.com
- Priority: Urgent
- Case Auto-Assigned: YES
  - Case ID: CASE-2026-00892
  - Link to correspondence: https://support.aws.amazon.com/cases/CASE-2026-00892/correspondence"""

        notif_result, _ = invoke_agent("task_notification_send", "Notification Sender", notif_input)
        task_results["notification_send"] = notif_result
        time.sleep(2)

        case_send_input = f"""TASK ASSIGNMENT:
- Case ID: CASE-2026-00892
- Message Content:
{actual_case_message}
- Recipient: GlobalFinance Ltd (infrastructure@globalfinance.com)"""

        case_send_result, _ = invoke_agent("task_case_send", "Case Correspondent", case_send_input)
        task_results["case_send"] = case_send_result
        time.sleep(2)

        # ─── Phase 3: response_listener + timer ───
        print("\n  ── Phase 3: response_listener + timer ──")

        listener_input = """TASK ASSIGNMENT:
- Case ID: CASE-2026-00892
- Timeout Threshold: 15 minutes
- Customer Response:
  "Thank you for the proactive alert. Yes, we deployed a new version of our 
  application 3 hours ago that includes a new reporting feature. It's possible 
  the new queries are causing the database load. The database is serving production 
  traffic — we have approximately 2000 active users right now. We do have a read 
  replica (db-prod-replica-1) but it's currently experiencing lag as well. 
  Please advise on immediate steps we can take."
"""
        listener_result, _ = invoke_agent("task_listener", "Response Listener", listener_input)
        task_results["response_listener"] = listener_result
        time.sleep(2)

        timer_input = """TASK ASSIGNMENT:
- Task Name: High Sev Proactive Pipeline (Sev2)
- Task Start Timestamp: 2026-07-24T10:00:00Z
- Expected Duration: 10 minutes
- Timeout Threshold: 15 minutes
- Tasks Tracked:
  - msg_draft (notification): started 10:00:00, completed 10:00:52
  - msg_draft (correspondence): started 10:00:00, completed 10:01:15
  - diagnostics: started 10:00:00, completed 10:02:30
  - notification_send: started 10:02:32, completed 10:02:58
  - case_send: started 10:02:32, completed 10:02:55
  - response_listener: started 10:03:00, completed 10:06:45"""

        timer_result, _ = invoke_agent("task_timer", "Task Timer", timer_input)
        task_results["timer"] = timer_result

    elif scenario_type == "customer_initiated":
        # ─── Phase 1 (PARALLEL): msg_draft + diagnostics ───
        print("\n  ── Phase 1: msg_draft + diagnostics (parallel) ──")

        msg_input = """TASK ASSIGNMENT:
- Action: Draft a case correspondence message acknowledging the customer's case
- Tone: Professional, reassuring, information-gathering
- Content Directive: This is the first message in case CASE-2026-00910. 
  The customer reported intermittent 504 Gateway Timeout errors from their 
  API Gateway (api-prod-v2) connected to Lambda functions in eu-west-1.
  Affected functions: order-api, search-service (user-auth is fine).
  ~30 percent of requests failing, started ~1 hour ago.
  Customer increased Lambda timeout from 15s to 30s with no improvement.
  No recent deployments or config changes.
  Acknowledge their case, confirm severity (Sev3), summarize what we understand,
  and let them know we are actively investigating.
- Questions to Include:
  - Can you confirm which API endpoints are most affected?
  - Are you seeing this across all Lambda functions or specific ones?
  - Have you noticed any pattern in timing (e.g., during peak hours)?
  - Has your traffic volume changed recently?
- Case Context: CASE-2026-00910, Sev3, API Gateway + Lambda
- Customer Name: StreamMedia Corp
- Contact: devops@streammedia.io
- Service Affected: Amazon API Gateway, AWS Lambda
- Region: eu-west-1

Return the FULL message text — subject line, body, and sign-off.
Do not describe what you are going to write. Just write the message."""

        msg_result, _ = invoke_agent("task_msg_draft", "Message Drafter", msg_input)
        task_results["msg_draft"] = msg_result
        time.sleep(2)

        is_valid, message_content = validate_msg_draft(msg_result)
        if is_valid:
            print(f"\n  ✅ msg_draft validated — message is {len(message_content)} chars")
        else:
            print(f"\n  ⚠️  WARNING: msg_draft validation failed")

        diag_input = """TASK ASSIGNMENT:
- Diagnostic Type: Lambda + API Gateway Health Check
- Target Resources:
  - Account ID: 334455667788
  - Region: eu-west-1
  - API Gateway: api-prod-v2 (REST API)
  - Lambda Functions: order-api, user-auth, search-service
- Specific Checks:
  - Lambda invocation errors per function (last 2 hours)
  - Lambda duration metrics vs timeout configuration per function
  - Lambda concurrent executions vs account limit
  - API Gateway 5xx error rate (last 2 hours)
  - API Gateway latency (p50, p90, p99)
  - Lambda cold start frequency
  - Lambda throttling events
- Time Window: Last 2 hours
- Context: Customer reports ~30% of requests returning 504 errors. 
  Started approximately 1 hour ago. order-api and search-service affected,
  user-auth appears normal. Customer increased timeout from 15s to 30s 
  with no improvement. No recent deployments. Concurrent executions at 650/1000."""

        diag_result, _ = invoke_agent("task_diagnostics", "Diagnostics Runner", diag_input)
        task_results["diagnostics"] = diag_result
        time.sleep(2)

        # ─── Phase 2: case_send (needs msg_draft) ───
        print("\n  ── Phase 2: case_send (sequential — needs msg_draft) ──")

        actual_message = extract_msg_draft_content(msg_result) if msg_result else "MESSAGE DRAFT FAILED"

        case_send_input = f"""TASK ASSIGNMENT:
- Case ID: CASE-2026-00910
- Message Content:
{actual_message}
- Recipient: StreamMedia Corp (devops@streammedia.io)"""

        case_send_result, _ = invoke_agent("task_case_send", "Case Correspondent", case_send_input)
        task_results["case_send"] = case_send_result
        time.sleep(2)

        # ─── Phase 3: response_listener + timer ───
        print("\n  ── Phase 3: response_listener + timer ──")

        listener_input = """TASK ASSIGNMENT:
- Case ID: CASE-2026-00910
- Timeout Threshold: 30 minutes
- Customer Response:
  "Hi, thanks for the quick response. The affected endpoints are /api/orders 
  and /api/search. The user-auth function seems fine. We're seeing it mostly 
  during peak hours (9am-11am GMT) but it's also happening sporadically outside 
  those times. We haven't deployed anything new but we did notice our traffic 
  has increased about 40% this week due to a marketing campaign we launched."
"""
        listener_result, _ = invoke_agent("task_listener", "Response Listener", listener_input)
        task_results["response_listener"] = listener_result
        time.sleep(2)

        timer_input = """TASK ASSIGNMENT:
- Task Name: Customer Initiated Case Pipeline (Sev3)
- Task Start Timestamp: 2026-07-24T14:30:00Z
- Expected Duration: 8 minutes
- Timeout Threshold: 15 minutes
- Tasks Tracked:
  - msg_draft: started 14:30:00, completed 14:30:48
  - diagnostics: started 14:30:00, completed 14:31:55
  - case_send: started 14:31:57, completed 14:32:20
  - response_listener: started 14:32:22, completed 14:38:10"""

        timer_result, _ = invoke_agent("task_timer", "Task Timer", timer_input)
        task_results["timer"] = timer_result

    return task_results


# ============================================================
# FULL PIPELINE (with feedback loop)
# ============================================================
def run_full_pipeline(raw_input, scenario_type, pipeline_name="Unnamed"):
    """
    Run the complete autonomous pipeline WITH feedback loop:
      Raw Input → Sensor → Coordinator → Control (PLANNING) 
      → Task Agents → Control (REPORTING) → Coordinator (FINAL)
    """
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print(f"║  🚀 FULL PIPELINE: {pipeline_name:<39}║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║  Sensor → Coordinator → Control → Tasks → Control → Coord║")
    print("╚════════════════════════════════════════════════════════════╝")

    results = {
        "pipeline_name": pipeline_name,
        "scenario_type": scenario_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stages": {},
    }

    # ─── STAGE 1: SENSOR AGENT ───
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 1/6: SENSOR AGENT                                 │")
    print("│  Processing raw data into structured context summary...  │")
    print("└──────────────────────────────────────────────────────────┘")

    sensor_output, _ = invoke_agent("sensor", "Sensor Agent", raw_input)

    if not sensor_output:
        print("\n❌ Pipeline FAILED at Stage 1 (Sensor Agent). Aborting.")
        results["stages"]["sensor"] = {"status": "FAILED"}
        return results

    results["stages"]["sensor"] = {"status": "SUCCESS", "output_length": len(sensor_output)}
    print(f"\n  ✅ Sensor Agent complete — {len(sensor_output)} chars")
    print("  ⏩ Passing context summary to Coordinator Agent...")
    time.sleep(2)

    # ─── STAGE 2: COORDINATOR AGENT (Initial Decision) ───
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 2/6: COORDINATOR AGENT (Initial Decision)         │")
    print("│  Assessing severity, making decisions, creating plan...  │")
    print("└──────────────────────────────────────────────────────────┘")

    coordinator_output, coordinator_session = invoke_agent(
        "coordinator", "Coordinator Agent", sensor_output
    )

    if not coordinator_output:
        print("\n❌ Pipeline FAILED at Stage 2 (Coordinator Agent). Aborting.")
        results["stages"]["coordinator_initial"] = {"status": "FAILED"}
        return results

    results["stages"]["coordinator_initial"] = {"status": "SUCCESS", "output_length": len(coordinator_output)}
    print(f"\n  ✅ Coordinator Agent complete — {len(coordinator_output)} chars")
    print("  ⏩ Extracting task plan for Control Agent...")
    time.sleep(2)

    # ─── STAGE 3: CONTROL AGENT (Planning Mode) ───
    control_input = extract_for_control_agent(coordinator_output)
    print(f"\n  📋 Extracted {len(control_input)} chars for Control Agent (from {len(coordinator_output)} total)")

    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 3/6: CONTROL AGENT (Planning Mode)                │")
    print("│  Refining tasks, planning execution order...             │")
    print("└──────────────────────────────────────────────────────────┘")

    control_output, control_session = invoke_agent(
        "control", "Control Agent", control_input
    )

    if not control_output:
        print("\n❌ Pipeline FAILED at Stage 3 (Control Agent). Aborting.")
        results["stages"]["control_planning"] = {"status": "FAILED"}
        return results

    results["stages"]["control_planning"] = {"status": "SUCCESS", "output_length": len(control_output)}
    print(f"\n  ✅ Control Agent (Planning) complete — {len(control_output)} chars")
    print("  ⏩ Executing task agents...")
    time.sleep(2)

    # ─── STAGE 4: TASK AGENTS ───
    task_results = run_task_agents(control_output, scenario_type)

    agents_succeeded = sum(1 for v in task_results.values() if v is not None)
    agents_failed = sum(1 for v in task_results.values() if v is None)

    results["stages"]["task_agents"] = {
        "status": "SUCCESS" if agents_failed == 0 else "PARTIAL",
        "agents_invoked": list(task_results.keys()),
        "agents_succeeded": agents_succeeded,
        "agents_failed": agents_failed,
    }

    print(f"\n  ✅ Task Agents complete — {agents_succeeded}/{len(task_results)} succeeded")
    print("  ⏩ Feeding results back to Control Agent (Reporting Mode)...")
    time.sleep(2)

    # ─── STAGE 5: CONTROL AGENT (Reporting Mode) ───
    # Feed task agent results back to the Control Agent so it can compile
    # its context summary report for the Coordinator
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 5/6: CONTROL AGENT (Reporting Mode)               │")
    print("│  Compiling task results into context summary report...   │")
    print("└──────────────────────────────────────────────────────────┘")

    task_results_summary = build_task_results_summary(task_results)

    control_report_output, _ = invoke_agent(
        "control", "Control Agent (Reporting)", task_results_summary, session_id=control_session
    )

    if not control_report_output:
        print("\n❌ Pipeline FAILED at Stage 5 (Control Agent Reporting). Aborting.")
        results["stages"]["control_reporting"] = {"status": "FAILED"}
        return results

    results["stages"]["control_reporting"] = {"status": "SUCCESS", "output_length": len(control_report_output)}
    print(f"\n  ✅ Control Agent (Reporting) complete — {len(control_report_output)} chars")
    print("  ⏩ Sending context summary report to Coordinator Agent...")
    time.sleep(2)

    # ─── STAGE 6: COORDINATOR AGENT (Final Assessment) ───
    # Feed the Control Agent's context summary report back to the Coordinator
    # so it can make its final assessment and determine next steps
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 6/6: COORDINATOR AGENT (Final Assessment)         │")
    print("│  Reviewing results, determining next steps...            │")
    print("└──────────────────────────────────────────────────────────┘")

    coordinator_final_output, _ = invoke_agent(
        "coordinator", "Coordinator Agent (Final)", control_report_output, session_id=coordinator_session
    )

    if not coordinator_final_output:
        print("\n❌ Pipeline FAILED at Stage 6 (Coordinator Final). Aborting.")
        results["stages"]["coordinator_final"] = {"status": "FAILED"}
        return results

    results["stages"]["coordinator_final"] = {"status": "SUCCESS", "output_length": len(coordinator_final_output)}
    print(f"\n  ✅ Coordinator Agent (Final) complete — {len(coordinator_final_output)} chars")

    # ─── PIPELINE COMPLETE ───
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  ✅ FULL PIPELINE COMPLETE (WITH FEEDBACK LOOP)           ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║  Scenario: {pipeline_name:<47}║")
    print(f"║                                                          ║")
    print(f"║  Stage 1 - Sensor:              ✅ {results['stages']['sensor']['output_length']:>5} chars             ║")
    print(f"║  Stage 2 - Coordinator (Init):  ✅ {results['stages']['coordinator_initial']['output_length']:>5} chars             ║")
    print(f"║  Stage 3 - Control (Planning):  ✅ {results['stages']['control_planning']['output_length']:>5} chars             ║")
    ta = results["stages"]["task_agents"]
    print(f"║  Stage 4 - Task Agents:         ✅ {ta['agents_succeeded']}/{len(ta['agents_invoked'])} succeeded             ║")
    print(f"║  Stage 5 - Control (Reporting): ✅ {results['stages']['control_reporting']['output_length']:>5} chars             ║")
    print(f"║  Stage 6 - Coordinator (Final): ✅ {results['stages']['coordinator_final']['output_length']:>5} chars             ║")
    print(f"║                                                          ║")
    print(f"║  FULL LOOP: Sensor → Coord → Control → Tasks            ║")
    print(f"║             → Control (report) → Coord (final)           ║")
    print("╚════════════════════════════════════════════════════════════╝")

    return results


# ============================================================
# TEST SCENARIOS
# ============================================================

RAW_SCENARIO_LOW_SEV_PROACTIVE = """
[PROACTIVE DETECTION — CLOUDWATCH HEALTH EVENT]

detection_type: CloudWatch Alarm Triggered
detection_time: 2026-07-24T10:15:00Z
event_source: CloudWatch → EventBridge → Sensor Agent

customer_name: NovaTech Solutions
customer_account_id: 556677889900
support_plan: Enterprise
primary_region: us-east-1
customer_contact: ops-team@novatech.io

---
[HEALTH EVENT DATA]

alarm_name: EC2-StatusCheck-i0abc123def456
alarm_state: ALARM
alarm_reason: "Instance status check failed 1 time(s) in the last 5 minutes"
previous_state: OK
state_change_time: 2026-07-24T10:14:32Z

resource_affected:
  - type: EC2 Instance
  - instance_id: i-0abc123def456
  - instance_type: t3.medium
  - availability_zone: us-east-1a
  - state: running
  - launch_time: 2026-06-15T08:00:00Z

cloudwatch_metrics_snapshot:
  - CPUUtilization: 12% (baseline: 10-15%)
  - NetworkIn: 2.1 MB/s (normal)
  - NetworkOut: 1.8 MB/s (normal)
  - StatusCheckFailed_Instance: 1 (intermittent)
  - StatusCheckFailed_System: 0

additional_context:
  - total_instances_in_account: 4
  - other_instances_healthy: YES
  - no_other_alarms_firing: YES
  - recent_deployments: NONE
  - recent_config_changes: NONE

---
[CUSTOMER HISTORY]

previous_cases_90_days: 1
  - CASE-2026-00780: Sev4, S3 bucket policy question, resolved in 30 minutes

average_response_time: 12 minutes
technical_sophistication: Moderate
escalation_history: 0

---
[NO ACTIVE CASE — This is a proactive detection]
"""

RAW_SCENARIO_HIGH_SEV_PROACTIVE = """
[PROACTIVE DETECTION — CLOUDWATCH HEALTH EVENT]

detection_type: Multiple CloudWatch Alarms — Critical Threshold Breach
detection_time: 2026-07-24T10:45:00Z
event_source: CloudWatch → EventBridge → Sensor Agent

customer_name: GlobalFinance Ltd
customer_account_id: 998877665544
support_plan: Enterprise
primary_region: us-west-2
customer_contact: infrastructure@globalfinance.com

---
[HEALTH EVENT DATA]

alarms_firing: 4

alarm_1:
  name: RDS-CPU-Critical
  state: ALARM
  reason: "CPU utilization exceeded 90% threshold — current value: 97.3%"
  state_change_time: 2026-07-24T10:37:00Z

alarm_2:
  name: RDS-FreeableMemory-Low
  state: ALARM
  reason: "Freeable memory below 500MB threshold — current value: 128MB"
  state_change_time: 2026-07-24T10:40:00Z

alarm_3:
  name: RDS-ReadLatency-High
  state: ALARM
  reason: "Read latency exceeded 20ms threshold — current value: 45ms"
  state_change_time: 2026-07-24T10:42:00Z

alarm_4:
  name: App-ErrorRate-High
  state: ALARM
  reason: "Application error rate exceeded 5% — current value: 12%"
  state_change_time: 2026-07-24T10:43:00Z

resource_affected:
  - type: RDS Instance
  - instance_id: db-prod-primary
  - instance_class: db.r5.2xlarge
  - engine: PostgreSQL 14.9
  - availability_zone: us-west-2a
  - status: available (degraded performance)
  - multi_az: YES
  - storage: 500 GB gp3

cloudwatch_metrics_snapshot:
  - CPUUtilization: 97.3% (baseline: 25-35%)
  - FreeableMemory: 128 MB (baseline: 8000 MB)
  - ReadLatency: 45ms (baseline: 2ms)
  - WriteLatency: 12ms (baseline: 1ms)
  - DatabaseConnections: 487 (baseline: 50-80)
  - ReplicaLag: 850ms (baseline: <10ms)
  - FreeStorageSpace: 380 GB (healthy)
  - ReadIOPS: 15000 (baseline: 2000)
  - WriteIOPS: 3500 (baseline: 500)

related_resources:
  - ec2_application_servers: 6/6 running, CPU average 78% (elevated from 25%)
  - read_replica: db-prod-replica-1, lag 850ms (normally <10ms)

additional_context:
  - application_deployment_3_hours_ago: YES
  - deployment_details: "v2.4.1 — new reporting module added"
  - no_rds_config_changes: YES
  - no_connection_pool_changes: YES

---
[CUSTOMER HISTORY]

previous_cases_90_days: 5
  - CASE-2026-00400: Sev2, RDS performance degradation, resolved in 3 hours
  - CASE-2026-00385: Sev3, RDS connection timeout, resolved in 1 hour
  - CASE-2026-00350: Sev4, RDS backup question, resolved in 20 minutes
  - CASE-2026-00320: Sev2, RDS failover event, resolved in 2 hours
  - CASE-2026-00290: Sev3, RDS storage optimization, resolved in 4 hours
  - Pattern: Customer has recurring RDS performance issues

average_response_time: 3 minutes (highly responsive)
technical_sophistication: High
escalation_history: 1 (6 months ago, resolved satisfactorily)

---
[NO ACTIVE CASE — This is a proactive detection]
[SEVERITY SIGNAL: CRITICAL — Multiple cascading failures detected]
"""

RAW_SCENARIO_CUSTOMER_INITIATED = """
[CUSTOMER-INITIATED CASE — APPROVED CONTEXT SUMMARY FROM SUPPORT ASSISTANT]

source: Customer Facing Support Assistant
submission_time: 2026-07-24T14:28:00Z
customer_approved: YES
customer_edits: Minor — added specific endpoint names

---
[CUSTOMER-APPROVED CONTEXT SUMMARY]

Customer: StreamMedia Corp
Account ID: 334455667788
Support Plan: Business
Region: eu-west-1
Contact: devops@streammedia.io

Issue Summary (approved by customer):
"We are experiencing intermittent 504 Gateway Timeout errors on our production 
API Gateway (api-prod-v2). The issue started approximately 1 hour ago. Our 
backend Lambda functions (order-api, user-auth, search-service) appear to be 
timing out before completing execution. This is affecting our end users who 
are receiving error pages when trying to browse and place orders."

Severity Indicated by Customer: Sev3 (Production system impaired)

Details Provided:
- Affected service: Amazon API Gateway + AWS Lambda
- Specific API: api-prod-v2 (REST API)
- Affected Lambda functions: order-api, user-auth, search-service
- Error type: 504 Gateway Timeout
- Frequency: Intermittent — approximately 30 percent of requests failing
- Started: ~1 hour ago (approximately 13:30 UTC)
- End user impact: YES — customers seeing error pages
- Recent deployments: NONE in last 5 days
- Recent config changes: NONE
- Workaround attempted: Increased Lambda timeout from 15s to 30s — no improvement

Customer's Question:
"Why are our Lambda functions suddenly timing out when nothing has changed on our end?"

---
[ACCOUNT HEALTH DATA — pulled at context summary creation]

cloudwatch_alarms:
  - Lambda-Duration-High: ALARM (triggered 45 min ago)
  - APIGW-5xx-Rate: ALARM (triggered 40 min ago)
  - Lambda-Errors-High: ALARM (triggered 35 min ago)

lambda_metrics:
  - order-api: avg duration 28s (timeout 30s), error rate 35%
  - user-auth: avg duration 4s (timeout 30s), error rate 2% (normal)
  - search-service: avg duration 27s (timeout 30s), error rate 32%
  - concurrent_executions: 650/1000

api_gateway_metrics:
  - 5xx_error_rate: 31%
  - latency_p99: 30000ms
  - total_requests_last_hour: 45000

---
[CUSTOMER HISTORY]

previous_cases_90_days: 2
  - CASE-2026-00850: Sev4, Lambda layer compatibility, resolved in 45 minutes
  - CASE-2026-00720: Sev3, API Gateway throttling, resolved in 2 hours

average_response_time: 5 minutes
technical_sophistication: High
escalation_history: 0

---
[CASE REQUESTED BY CUSTOMER — awaiting system to open case]
"""


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  PROJECT TENSEI — FULL AUTONOMOUS AGENT PIPELINE          ║")
    print("║  Sensor → Coord → Control → Tasks → Control → Coord      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Step 1: Check credentials
    check_credentials()

    # Step 2: Pick scenario
    print("📋 Available test scenarios:")
    print("   1. Low Sev Proactive (Sev4) — notification only, no case")
    print("   2. High Sev Proactive (Sev2) — notification + auto case + correspondence")
    print("   3. Customer-Initiated (Sev3) — case opened, correspondence")
    print("   4. Run ALL scenarios")
    print()

    choice = input("Select scenario (1/2/3/4) [default: 1]: ").strip() or "1"

    scenarios = {
        "1": ("Low Sev Proactive (Sev4)", RAW_SCENARIO_LOW_SEV_PROACTIVE, "low_sev_proactive"),
        "2": ("High Sev Proactive (Sev2)", RAW_SCENARIO_HIGH_SEV_PROACTIVE, "high_sev_proactive"),
        "3": ("Customer-Initiated (Sev3)", RAW_SCENARIO_CUSTOMER_INITIATED, "customer_initiated"),
    }

    if choice == "4":
        all_results = []
        for key in ["1", "2", "3"]:
            name, raw_input, scenario_type = scenarios[key]
            result = run_full_pipeline(raw_input, scenario_type, pipeline_name=name)
            all_results.append(result)
            if key != "3":
                print("\n⏳ Waiting 10 seconds before next scenario...\n")
                time.sleep(10)

        # Final summary
        print("\n")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  📊 ALL PIPELINES COMPLETE — SUMMARY                      ║")
        print("╠════════════════════════════════════════════════════════════╣")
        for r in all_results:
            stages = r["stages"]
            all_success = all(
                s.get("status") in ["SUCCESS", "PARTIAL"]
                for s in stages.values()
            )
            icon = "✅" if all_success else "❌"
            print(f"║  {icon} {r['pipeline_name']:<55}║")
        print("╚════════════════════════════════════════════════════════════╝")

    elif choice in scenarios:
        name, raw_input, scenario_type = scenarios[choice]
        run_full_pipeline(raw_input, scenario_type, pipeline_name=name)

    else:
        print(f"❌ Invalid choice: {choice}")
        sys.exit(1)

    print("\n✅ Done!")