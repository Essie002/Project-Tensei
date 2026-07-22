"""
Project Tensei — AgentCore client.

This is the ONLY module that talks to AWS. It wraps the AgentCore "harness" API
the team's agents already use, so the gateway targets the exact same deployed
agents.

IMPORTANT — this mirrors agent_testing/customer_demo_coordinator_agent.py:
  * boto3 client "bedrock-agentcore-control" is used to look up the harness ARN
    by name (list_harnesses), and to create it if missing (create_harness).
  * boto3 client "bedrock-agentcore" is used to invoke it (invoke_harness),
    streaming the reply as `contentBlockDelta` events.

The browser can NEVER call this directly — it needs AWS credentials. That's why
this lives server-side behind the gateway, which holds the credentials.
"""

import uuid

import boto3

import config

# Two clients, exactly as the agent scripts use:
#   - control plane: manage/lookup harnesses
#   - data plane:    invoke a harness
_control = boto3.client("bedrock-agentcore-control", region_name=config.REGION)
_runtime = boto3.client("bedrock-agentcore", region_name=config.REGION)

# Cache the resolved harness ARN so we only look it up once per process.
_harness_arn_cache: str | None = None


def check_credentials() -> dict:
    """Return the caller identity, or raise if AWS credentials are missing/invalid.

    Mirrors the credential check in the agent scripts so failures are obvious.
    """
    sts = boto3.client("sts", region_name=config.REGION)
    return sts.get_caller_identity()


def resolve_harness_arn() -> str:
    """Find the ARN of the configured harness by name.

    Looks up an existing harness (the team already deployed these via the agent
    scripts). We do NOT create it here — the gateway should only connect to
    agents that already exist, not deploy new ones.
    """
    global _harness_arn_cache
    if _harness_arn_cache:
        return _harness_arn_cache

    harnesses = _control.list_harnesses()
    for h in harnesses.get("harnesses", []):
        if h["harnessName"] == config.HARNESS_NAME:
            _harness_arn_cache = h["arn"]
            return _harness_arn_cache

    # Not found — the team must deploy it first with the agent_testing scripts.
    raise RuntimeError(
        f"Harness '{config.HARNESS_NAME}' not found in account {config.ACCOUNT_ID} "
        f"({config.REGION}). Deploy it first by running the matching script in "
        f"agent_testing/, or set TENSEI_HARNESS_NAME to an existing harness."
    )


def new_session_id() -> str:
    """Create a runtime session id in the same format the agents use.

    (UUID hex + a trailing char — the agent scripts append '0' to guarantee the
    id is long enough / non-empty.)
    """
    return str(uuid.uuid4()).replace("-", "") + "0"


def invoke_agent(message: str, session_id: str) -> str:
    """Send `message` to the harness and return the full text reply.

    This reproduces the streaming loop from the agent scripts: the response
    arrives as a stream of events; we concatenate the `contentBlockDelta` text
    deltas into one string. Passing the same `session_id` across calls preserves
    conversation context (the agent's memory), just like the scripts' Test 4.
    """
    response = _runtime.invoke_harness(
        harnessArn=resolve_harness_arn(),
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": message}]}],
    )

    full_response = ""
    for event in response.get("stream", []):
        # Structured delta events carry incremental text.
        if hasattr(event, "get"):
            if "contentBlockDelta" in event:
                full_response += event["contentBlockDelta"].get("delta", {}).get("text", "")
        else:
            # Fallback: some events arrive as raw values — stringify them.
            full_response += str(event)

    return full_response
