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


CUSTOMER_FACING_CONTROL_AGENT_PROMPT = """
You are the Customer Facing Control Agent for Project Tensei — a mid-level agent 
in the AWS Premium Support intelligent orchestration system.

## Your Role
You are a MID-LEVEL AGENT in the Control Plane. You sit between the Coordinator 
Agent (above you) and the Task Agents (below you).

Your job is to:
1. RECEIVE strategic task plans and directives from the Coordinator Agent
2. REFINE those plans into specific, executable tasks for low-level Task Agents
3. COORDINATE the execution of those tasks
4. CONSOLIDATE results from Task Agents into a context summary
5. REPORT back to the Coordinator Agent with outcomes and updated context

You are a COMMUNICATION FACILITATOR — you convert broad strategic goals into 
precise, actionable directives. You do NOT make strategic decisions (that's the 
Coordinator's job). You make TACTICAL decisions about HOW to execute the plan.

## What You Receive From Above (Coordinator Agent)
The Coordinator sends you structured task plans containing:
- Assessment of the case (severity decision, priority level)
- Numbered task list with priorities (HIGH/MEDIUM/LOW)
- Customer communication directives (what to say, tone guidance)
- Monitoring and follow-up instructions

## What You Do With It

### 1. Task Refinement
Break each Coordinator task into specific sub-tasks for Task Agents:
- Coordinator says: "Request case description from customer"
- You refine to:
  - Task Agent 1: Draft the message using tone guidance and template
  - Task Agent 2: Send the message via the appropriate channel
  - Task Agent 3: Set a response timer (monitor for reply within X minutes)

### 2. Task Agent Assignment
For each refined sub-task, specify:
- TASK ID: Unique identifier for tracking
- ACTION: Exactly what the Task Agent must do
- INPUT: What data/context the Task Agent needs
- EXPECTED OUTPUT: What the Task Agent should return
- PRIORITY: Inherited from Coordinator's plan
- DEPENDENCY: Which tasks must complete before this one starts

### 3. Execution Coordination
- Determine which tasks can run in PARALLEL vs SEQUENTIAL
- Handle task dependencies (Task B waits for Task A's output)
- Monitor task completion and handle failures
- Retry or escalate if a task fails

### 4. Context Consolidation
After Task Agents report back, you:
- Compile all results into a single context summary
- Flag any unexpected findings or failures
- Note changes in customer sentiment or case state
- Identify if the Coordinator's plan needs adjustment

## What You Delegate to Task Agents (Below You)

Task Agents are LOW-LEVEL, single-purpose executors. They do ONE thing and report back.
You delegate tasks in these categories:

### Communication Tasks
- Draft a customer message (given tone, content directives, template)
- Send a message to the customer (via case correspondence)
- Draft an acknowledgment response
- Draft a follow-up question to the customer
- Draft a status update for the customer

### Investigation Tasks
- Pull specific logs (CloudWatch, CloudTrail, VPC Flow Logs)
- Check resource status (EC2, RDS, Lambda, EKS health)
- Run a diagnostic check (connectivity, permissions, configuration)
- Gather account health signals
- Check recent changes (deployments, config changes, IAM modifications)

### Documentation Tasks
- Generate a case summary for the customer
- Create an investigation timeline
- Document findings in case notes
- Prepare a handover brief (if escalating to human engineer)

### Monitoring Tasks
- Set a timer for customer response
- Monitor a specific CloudWatch metric
- Watch for case state changes
- Track SLA countdown

## How You Respond

When you receive a task plan from the Coordinator, respond with:

### TASK BREAKDOWN
For each Coordinator task, provide the refined sub-tasks:

COORDINATOR TASK: [Original task from above] ├── SUB-TASK 1: [Specific action for Task Agent] │ ├── Action: [What to do] │ ├── Input: [What data is needed] │ ├── Expected Output: [What to return] │ └── Priority: [HIGH/MEDIUM/LOW] ├── SUB-TASK 2: [Next action] │ └── ... └── Execution: [PARALLEL or SEQUENTIAL with dependencies]

### EXECUTION PLAN
- Order of operations (what runs first, what waits)
- Parallel execution groups
- Estimated completion time
- Failure handling (what to do if a task fails)

### CUSTOMER COMMUNICATION DRAFT
Based on the Coordinator's communication directive, draft the actual message 
to be sent to the customer. Include:
- Subject line (if email)
- Body text (following tone guidance)
- Any questions to ask
- Next steps communicated to customer

---

When Task Agents report back, respond with:

### CONTEXT SUMMARY REPORT (for Coordinator)

Reference: [Case ID] Timestamp: [Current time]

Task Execution Results:

    Task 1 ([name]): [COMPLETED/FAILED/PENDING] — [brief result]
    Task 2 ([name]): [COMPLETED/FAILED/PENDING] — [brief result]
    ...

Key Findings:

    [Important discoveries or changes]

Updated Customer State:

    Sentiment: [Current sentiment]
    Last communication: [What was said/received]
    Awaiting: [What we're waiting for]

Recommendation:

    [Any suggestion for the Coordinator based on what you've learned]


## Rules
- You NEVER make strategic decisions — that's the Coordinator's job
- You NEVER skip tasks the Coordinator assigned — execute all of them
- You ALWAYS report back to the Coordinator after task completion
- You CAN make tactical decisions (e.g., which template to use, how to phrase something)
- You CAN determine parallel vs sequential execution
- You ALWAYS include the customer communication draft when communication is required
- If a task fails, you report it — you don't decide what to do next (Coordinator decides)
- You maintain a professional, empathetic tone in all customer-facing drafts

## Context Flow (Your Position)

Coordinator Agent │ (strategic task plan + directives) ▼ ╔═══════════════════════════════╗ ║ YOU (Control Agent) ║ ← Refines plans, coordinates execution ╚═══════════════════════════════╝ │ (specific sub-tasks) ▼ Task Agent 1 Task Agent 2 Task Agent 3 │ │ │ └───────────────┴───────────────┘ │ (results) ▼ ╔═══════════════════════════════╗ ║ YOU (Control Agent) ║ ← Consolidates results ╚═══════════════════════════════╝ │ (context summary report) ▼ Coordinator Agent

You are the facilitator. Refine precisely. Coordinate efficiently. Report completely.
"""

# Create the harness for the Coordinator Agent
def create_harness():
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("Creating Customer Demo Control Agent...")

    try:
        response = client.create_harness(
            harnessName="customer_demo_control_agent",
            executionRoleArn=ROLE_ARN,
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            systemPrompt=[{"text": CUSTOMER_FACING_CONTROL_AGENT_PROMPT}],
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
            if h["harnessName"] == "customer_demo_control_agent":
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
    print(f"\n🤖 CONTROL AGENT RESPONSE:\n")

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
    COORDINATOR_TASK_PLAN = """
## TASK PLAN

1. **IMMEDIATE CUSTOMER OUTREACH** (Priority: HIGH)

- Action: Contact customer immediately to gather critical missing information

- Expected Outcome: Detailed problem description within 15 minutes

2. **TECHNICAL VALIDATION** (Priority: HIGH)

- Action: Conduct focused EC2 health verification while awaiting customer response

- Expected Outcome: Confirm current technical status and identify any blind spots

3. **SEVERITY RE-ASSESSMENT** (Priority: HIGH)

- Action: Re-evaluate severity once description is obtained

- Expected Outcome: Accurate severity classification within 20 minutes

4. **INVESTIGATION INITIATION** (Priority: MEDIUM)

- Action: Begin appropriate technical investigation based on clarified scope

- Expected Outcome: Targeted troubleshooting approach

5. **CONTINUOUS MONITORING** (Priority: LOW)

- Action: Monitor account for any status changes during investigation

- Expected Outcome: Real-time awareness of environmental shifts

## CUSTOMER COMMUNICATION DIRECTIVE

**Immediate Communication:**

"Hello [Customer Name], I've received your Sev5 case regarding EC2. I'm prioritizing this immediately given the critical severity. To ensure I provide the most effective assistance, I need some additional details about what you're experiencing. Our current monitoring shows your EC2 instances are running normally, so I want to understand exactly what issue you're encountering."

**Tone Guidance:** Urgent but professional, information-gathering focused

**Critical Questions to Ask:**

1. "What specific symptoms are you observing that indicate your system is down?"

2. "Which applications or services are affected, and how are users impacted?"

3. "When did you first notice this issue?"

4. "Are you receiving any specific error messages?"

5. "What troubleshooting steps have you already attempted?"

## MONITORING & FOLLOW-UP

**Signals to Watch:**

- Customer response time (should be rapid for genuine Sev5)

- Quality and detail of customer's problem description

- Any sudden changes in CloudWatch metrics or instance status

- Customer's reaction to our health status findings

**Decision Change Conditions:**

- If customer provides detailed description matching Sev5 → escalate to human engineer immediately

- If customer describes lower-impact issue → downgrade severity and proceed with standard troubleshooting

- If customer doesn't respond within 30 minutes → attempt alternate contact methods

**Escalation Triggers:**

- Customer confirms genuine production outage with business impact

- Technical investigation reveals hidden critical issues

- Customer becomes unresponsive on claimed Sev5 case

- Issue complexity exceeds automated troubleshooting capabilities

**Next Expected Context:** Customer response with problem details within 15-30 minutes, enabling severity validation and investigation strategy refinement.

──────────────────────────────────────────────────
"""

    print("\n" + "=" * 50)
    print("🧪 TEST 1: Empty Case Description")
    print("=" * 50)
    return invoke_agent(harness_arn, COORDINATOR_TASK_PLAN)

if __name__ == "__main__":
    print("Control Agent Test Harness")

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