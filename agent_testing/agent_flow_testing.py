# agent_flow_testing.py
# ============================================================
# PROJECT TENSEI — AUTONOMOUS AGENT PIPELINE
# ============================================================
# This script chains all 3 agents together automatically:
#   Sensor Agent → Coordinator Agent → Control Agent
#
# No copy-pasting needed. Each agent's output flows directly
# as input to the next agent in the pipeline.
# ============================================================

import boto3
import uuid
import time
import sys
import json
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
REGION = "us-east-1"
ACCOUNT_ID = "070638634443"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/agent_core_execution_role"
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Agent harness names (must match what's already created)
SENSOR_HARNESS_NAME = "customer_demo_sensor_agent"
COORDINATOR_HARNESS_NAME = "customer_demo_coordinator"
CONTROL_HARNESS_NAME = "customer_demo_control_agent"

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
        print('   export AWS_ACCESS_KEY_ID="ASIA..."')
        print('   export AWS_SECRET_ACCESS_KEY="..."')
        print('   export AWS_SESSION_TOKEN="..."')
        print('   export AWS_DEFAULT_REGION="us-east-1"')
        print()
        sys.exit(1)


# ============================================================
# HARNESS MANAGEMENT
# ============================================================
def get_or_create_harness(harness_name, system_prompt):
    """Get existing harness ARN or create a new one."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    # First, try to find existing harness
    try:
        harnesses = client.list_harnesses()
        for h in harnesses.get("harnesses", []):
            if h["harnessName"] == harness_name:
                arn = h["arn"]
                print(f"   ✅ Found existing: {harness_name}")
                print(f"      ARN: {arn}")
                return arn
    except Exception as e:
        print(f"   ⚠️  Could not list harnesses: {e}")

    # If not found, create it
    print(f"   📦 Creating: {harness_name}...")
    try:
        response = client.create_harness(
            harnessName=harness_name,
            executionRoleArn=ROLE_ARN,
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            systemPrompt=[{"text": system_prompt}],
            maxIterations=10,
            timeoutSeconds=120,
        )
        harness_arn = response["harness"]["arn"]
        print(f"   ✅ Created: {harness_arn}")
        return harness_arn

    except client.exceptions.ConflictException:
        print(f"   ⚠️  Conflict — harness exists but wasn't found in list. Retrying...")
        harnesses = client.list_harnesses()
        for h in harnesses.get("harnesses", []):
            if h["harnessName"] == harness_name:
                return h["arn"]
        return None

    except Exception as e:
        print(f"   ❌ Failed to create {harness_name}: {e}")
        return None


def get_all_harnesses():
    """Fetch ARNs for all 3 agents. Returns dict or None on failure."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("🔍 Locating agent harnesses...")
    harnesses = {}

    try:
        response = client.list_harnesses()
        for h in response.get("harnesses", []):
            if h["harnessName"] == SENSOR_HARNESS_NAME:
                harnesses["sensor"] = h["arn"]
                print(f"   ✅ Sensor Agent:      {h['arn']}")
            elif h["harnessName"] == COORDINATOR_HARNESS_NAME:
                harnesses["coordinator"] = h["arn"]
                print(f"   ✅ Coordinator Agent: {h['arn']}")
            elif h["harnessName"] == CONTROL_HARNESS_NAME:
                harnesses["control"] = h["arn"]
                print(f"   ✅ Control Agent:     {h['arn']}")
    except Exception as e:
        print(f"   ❌ Error listing harnesses: {e}")
        return None

    # Validate all 3 are found
    missing = []
    if "sensor" not in harnesses:
        missing.append(SENSOR_HARNESS_NAME)
    if "coordinator" not in harnesses:
        missing.append(COORDINATOR_HARNESS_NAME)
    if "control" not in harnesses:
        missing.append(CONTROL_HARNESS_NAME)

    if missing:
        print(f"\n   ❌ Missing harnesses: {', '.join(missing)}")
        print("   Run the individual agent scripts first to create them:")
        print("     python customer_demo_sensor_agent.py")
        print("     python customer_demo_coordinator_agent.py")
        print("     python customer_demo_control_agent.py")
        return None

    print()
    return harnesses


# ============================================================
# AGENT INVOCATION
# ============================================================
def invoke_agent(harness_arn, agent_name, context, session_id=None):
    """
    Invoke an agent and return its full response text.
    This is the core function that enables chaining.
    """
    client = boto3.client("bedrock-agentcore", region_name=REGION)

    if not session_id:
        session_id = str(uuid.uuid4()).replace("-", "") + "0"

    print(f"\n{'━' * 60}")
    print(f"  📨 INPUT TO {agent_name.upper()}")
    print(f"{'━' * 60}")
    # Show first 500 chars of input for visibility
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

        print(f"\n{'━' * 60}")
        return full_response, session_id

    except Exception as e:
        print(f"  ❌ Error invoking {agent_name}: {e}")
        return None, session_id


# ============================================================
# AUTONOMOUS PIPELINE
# ============================================================
def run_pipeline(harnesses, raw_input, pipeline_name="Unnamed"):
    """
    Run the full autonomous pipeline:
      Raw Input → Sensor Agent → Coordinator Agent → Control Agent
    
    Each agent's output automatically becomes the next agent's input.
    Returns all outputs for inspection.
    """
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print(f"║  🚀 AUTONOMOUS PIPELINE: {pipeline_name:<33}║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║  Raw Input → Sensor → Coordinator → Control Agent        ║")
    print("╚════════════════════════════════════════════════════════════╝")

    results = {
        "pipeline_name": pipeline_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stages": {},
    }

    # ─── STAGE 1: SENSOR AGENT ───────────────────────────────────
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 1/3: SENSOR AGENT                                 │")
    print("│  Processing raw case data into structured context...     │")
    print("└──────────────────────────────────────────────────────────┘")

    sensor_output, _ = invoke_agent(
        harnesses["sensor"],
        "Sensor Agent",
        raw_input
    )

    if not sensor_output:
        print("\n❌ Pipeline FAILED at Stage 1 (Sensor Agent). Aborting.")
        results["stages"]["sensor"] = {"status": "FAILED", "output": None}
        return results

    results["stages"]["sensor"] = {"status": "SUCCESS", "output": sensor_output}
    print(f"\n  ✅ Sensor Agent complete — output length: {len(sensor_output)} chars")
    print("  ⏩ Passing output to Coordinator Agent...\n")

    # Small delay to avoid throttling
    time.sleep(2)

    # ─── STAGE 2: COORDINATOR AGENT ──────────────────────────────
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 2/3: COORDINATOR AGENT                            │")
    print("│  Making decisions and creating task plan...               │")
    print("└──────────────────────────────────────────────────────────┘")

    coordinator_output, _ = invoke_agent(
        harnesses["coordinator"],
        "Coordinator Agent",
        sensor_output  # ← AUTO-FED from Sensor Agent
    )

    if not coordinator_output:
        print("\n❌ Pipeline FAILED at Stage 2 (Coordinator Agent). Aborting.")
        results["stages"]["coordinator"] = {"status": "FAILED", "output": None}
        return results

    results["stages"]["coordinator"] = {"status": "SUCCESS", "output": coordinator_output}
    print(f"\n  ✅ Coordinator Agent complete — output length: {len(coordinator_output)} chars")
    print("  ⏩ Passing output to Control Agent...\n")

    # Small delay to avoid throttling
    time.sleep(2)

    # ─── STAGE 3: CONTROL AGENT ──────────────────────────────────
    print("\n")
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  STAGE 3/3: CONTROL AGENT                                │")
    print("│  Refining tasks and coordinating execution...            │")
    print("└──────────────────────────────────────────────────────────┘")

    control_output, _ = invoke_agent(
        harnesses["control"],
        "Control Agent",
        coordinator_output  # ← AUTO-FED from Coordinator Agent
    )

    if not control_output:
        print("\n❌ Pipeline FAILED at Stage 3 (Control Agent). Aborting.")
        results["stages"]["control"] = {"status": "FAILED", "output": None}
        return results

    results["stages"]["control"] = {"status": "SUCCESS", "output": control_output}
    print(f"\n  ✅ Control Agent complete — output length: {len(control_output)} chars")

    # ─── PIPELINE COMPLETE ────────────────────────────────────────
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  ✅ PIPELINE COMPLETE                                     ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║  Sensor output:      {len(sensor_output):>6} chars                        ║")
    print(f"║  Coordinator output: {len(coordinator_output):>6} chars                        ║")
    print(f"║  Control output:     {len(control_output):>6} chars                        ║")
    print("╚════════════════════════════════════════════════════════════╝")

    return results


# ============================================================
# TEST SCENARIOS (Raw inputs that start the pipeline)
# ============================================================

# Scenario 1: Empty description on a Sev5 case
RAW_SCENARIO_EMPTY_SEV5 = """
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

# Scenario 2: Genuine Sev1 with clear description
RAW_SCENARIO_GENUINE_SEV1 = """
You are receiving the following raw customer case data from the AWS Support system.
Process this into a structured context summary for the Coordinator Agent.

---
[RAW CASE DATA]

case_id: CASE-2026-00789
created_at: 2026-07-22T09:15:00Z
channel: AWS Console (Support Center)

customer_name: TechStartup Inc
customer_account_id: 112233445566
support_plan: Business
primary_region: eu-west-1
customer_contact: devops@techstartup.io

severity_selected: 1
severity_label: "Urgent: Production system impaired"

subject: "Lambda functions timing out — API Gateway returning 504s"
description: "Our Lambda functions in eu-west-1 are timing out intermittently. Approximately 40% of invocations are failing with 'Task timed out after 30 seconds'. This started 20 minutes ago. Our API Gateway is returning 504 errors to end users. We have not made any deployments in the last 3 days. Affected functions: order-processor, payment-handler, inventory-sync."

service_category: AWS Lambda
service_subcategory: Function Execution

---
[ACCOUNT HEALTH DATA — pulled automatically at case creation]

cloudwatch_alarms:
  - total_alarms: 8
  - in_alarm_state: 2
  - alarm_details:
    - Lambda-Duration-High: ALARM (triggered 18 min ago)
    - APIGW-5xx-Errors: ALARM (triggered 15 min ago)

lambda_functions:
  - region: eu-west-1
  - total_functions: 12
  - functions_with_errors: 3 (order-processor, payment-handler, inventory-sync)
  - concurrent_executions: 847/1000 (approaching account limit)
  - average_duration_last_5min: 28.4 seconds (baseline: 2.1 seconds)

api_gateway:
  - 5xx_error_rate: 41% (baseline: 0.2%)
  - 4xx_error_rate: 3% (normal)
  - latency_p99: 30000ms (baseline: 450ms)

recent_activity:
  - cloudtrail_events_1h: 45 (normal baseline: 30-50)
  - deployments_24h: 0
  - iam_changes_24h: 0
  - lambda_config_changes_7d: 0

cost_signals:
  - anomaly_detected: true
  - reason: "Lambda duration spike causing 3x normal compute cost"
  - current_daily_spend: $89.20 (baseline: $28-$35)

---
[CUSTOMER HISTORY]

previous_cases_90_days: 1
  - CASE-2026-00650: Sev2, S3 CORS configuration, resolved in 1 hour

average_response_time: 5 minutes
technical_sophistication: High (provides specific error details, function names, timestamps)
escalation_history: 0

---
Process this raw data into your standard context summary format for the Coordinator Agent.
"""

# Scenario 3: Proactive detection — no case opened yet
RAW_SCENARIO_PROACTIVE = """
You are receiving the following PROACTIVE DETECTION signal. No customer case has 
been opened yet. Process this into a structured context summary for the Coordinator Agent.

---
[PROACTIVE DETECTION — ACCOUNT HEALTH ALERT]

detection_type: Anomaly detected before customer report
detection_time: 2026-07-22T13:45:00Z

customer_name: GlobalFinance Ltd
customer_account_id: 998877665544
support_plan: Enterprise
primary_region: us-west-2
customer_contact: infrastructure@globalfinance.com

---
[ACCOUNT HEALTH DATA — proactive monitoring]

cloudwatch_alarms:
  - total_alarms: 25
  - in_alarm_state: 4
  - alarm_details:
    - RDS-CPU-Critical: ALARM (triggered 8 min ago, threshold: 90%, current: 97%)
    - RDS-FreeableMemory-Low: ALARM (triggered 5 min ago, threshold: 500MB, current: 128MB)
    - RDS-ReadLatency-High: ALARM (triggered 3 min ago)
    - App-ErrorRate-High: ALARM (triggered 2 min ago)

rds_instances:
  - region: us-west-2
  - instance: db-prod-primary (db.r5.2xlarge)
  - status: available (but degraded performance)
  - cpu_utilization: 97.3%
  - freeable_memory: 128 MB
  - read_latency: 45ms (baseline: 2ms)
  - write_latency: 12ms (baseline: 1ms)
  - active_connections: 487 (baseline: 50-80)
  - replica_lag: 850ms (baseline: <10ms)

ec2_instances:
  - application_servers: 6/6 running
  - cpu_average: 78% (elevated from baseline 25%)

recent_activity:
  - cloudtrail_events_1h: 89 (baseline: 40-60, ELEVATED)
  - deployments_24h: 1 (application deployment 3 hours ago)
  - rds_config_changes: 0
  - connection_pool_changes: 0

cost_signals:
  - anomaly_detected: false (too early to reflect in billing)

---
[CUSTOMER HISTORY]

previous_cases_90_days: 5
  - Most recent: CASE-2026-00400: Sev2, RDS performance, resolved in 3 hours
  - Pattern: Customer has had RDS performance issues before (2 of 5 cases)

average_response_time: 3 minutes (highly responsive)
technical_sophistication: High
escalation_history: 1 (6 months ago, resolved satisfactorily)

---
[NO ACTIVE CASE — This is a proactive detection]

Process this proactive detection signal into your standard context summary format.
Flag that this is a PROACTIVE detection (customer has not opened a case yet).
Recommend to the Coordinator whether proactive outreach is warranted.
"""


# ============================================================
# MAIN — Run the autonomous pipeline
# ============================================================
if __name__ == "__main__":

    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  PROJECT TENSEI — AUTONOMOUS AGENT PIPELINE               ║")
    print("║  Sensor → Coordinator → Control (fully automated)         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Step 1: Check credentials
    check_credentials()

    # Step 2: Find all agent harnesses
    harnesses = get_all_harnesses()
    if not harnesses:
        print("\n❌ Cannot run pipeline without all 3 agents. Exiting.")
        sys.exit(1)

    # Step 3: Pick which scenario to run (or run all)
    print("\n📋 Available test scenarios:")
    print("   1. Empty Sev5 case (contradiction detection)")
    print("   2. Genuine Sev1 (Lambda timeouts)")
    print("   3. Proactive detection (RDS degradation, no case opened)")
    print("   4. Run ALL scenarios")
    print()

    choice = input("Select scenario (1/2/3/4) [default: 1]: ").strip() or "1"

    scenarios = {
        "1": ("Empty Sev5 — Contradiction Detection", RAW_SCENARIO_EMPTY_SEV5),
        "2": ("Genuine Sev1 — Lambda Timeouts", RAW_SCENARIO_GENUINE_SEV1),
        "3": ("Proactive Detection — RDS Degradation", RAW_SCENARIO_PROACTIVE),
    }

    if choice == "4":
        # Run all scenarios
        all_results = []
        for key in ["1", "2", "3"]:
            name, raw_input = scenarios[key]
            result = run_pipeline(harnesses, raw_input, pipeline_name=name)
            all_results.append(result)
            if key != "3":  # Don't sleep after the last one
                print("\n⏳ Waiting 5 seconds before next scenario...\n")
                time.sleep(5)

        # Final summary
        print("\n")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  📊 ALL PIPELINES COMPLETE — SUMMARY                      ║")
        print("╠════════════════════════════════════════════════════════════╣")
        for r in all_results:
            status_icons = []
            for stage_name in ["sensor", "coordinator", "control"]:
                stage = r["stages"].get(stage_name, {})
                status_icons.append("✅" if stage.get("status") == "SUCCESS" else "❌")
            icons = " → ".join(status_icons)
            print(f"║  {r['pipeline_name'][:40]:<40} {icons}  ║")
        print("╚════════════════════════════════════════════════════════════╝")

    elif choice in scenarios:
        name, raw_input = scenarios[choice]
        run_pipeline(harnesses, raw_input, pipeline_name=name)

    else:
        print(f"❌ Invalid choice: {choice}")
        sys.exit(1)

    print("\n✅ Done!")
