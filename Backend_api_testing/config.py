"""
Project Tensei — Gateway configuration.

All account/agent-specific values live here. They are read from environment
variables first (so nothing sensitive is committed), falling back to the values
already used by the team's agent scripts in `agent_testing/`.

These defaults are copied verbatim from the agent files
(customer_demo_coordinator_agent.py etc.) so the gateway targets the same
harnesses the team already deployed.
"""

import os

# AWS region the AgentCore harnesses are deployed in (from the agent scripts).
REGION = os.getenv("TENSEI_REGION", "us-east-1")

# The Isengard account the harnesses live in (from the agent scripts).
ACCOUNT_ID = os.getenv("TENSEI_ACCOUNT_ID", "070638634443")

# Which harness the customer-facing chat should talk to. The frontend is the
# customer's chat panel, so the natural target is the customer-demo coordinator
# (the decision-making "brain" that the sensor/control agents feed into).
#
# Options that already exist in agent_testing/:
#   - "customer_demo_coordinator"   (customer-facing coordinator)  <-- default
#   - "tensei_coordinator"          (full internal coordinator)
#   - "customer_demo_control_agent" (mid-level control agent)
HARNESS_NAME = os.getenv("TENSEI_HARNESS_NAME", "customer_demo_coordinator")

# CORS: the frontend is a static page (opened from a file, or served on a
# different port), so the browser will make cross-origin calls to this gateway.
# For local development we allow all origins. Lock this down before production.
#
# PLACEHOLDER: replace "*" with the exact origin the frontend is served from
# (e.g. "http://localhost:5500") once that is known, so the gateway does not
# accept cross-origin calls from arbitrary sites.
ALLOWED_ORIGINS = os.getenv("TENSEI_ALLOWED_ORIGINS", "*").split(",")
