from __future__ import annotations

import logging
import os
from pathlib import Path

from google.adk.agents import LlmAgent

from agent.tools.approval_manager import create_approval_request, send_approval_email
from agent.tools.message_drafter import draft_contact_message
from agent.tools.rejection_logger import log_rejection
from config import settings

logger = logging.getLogger(__name__)

_CRITERIA_PATH = Path(__file__).parent.parent / "config" / "criteria.txt"

# Tell ADK to use Vertex AI as the backend
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

_SYSTEM_PROMPT = """\
You are a rental listing screening agent for Annecy, France.
Your task is to evaluate incoming rental listings and decide whether to forward
them to the user for review, based on their stated criteria.

## User's Rental Criteria
{criteria}

## Minimum score to notify user: {threshold}/100

---

## Workflow — follow these exact steps in order:

1. **Evaluate the listing** against the criteria above.
   - Assign an integer score from 0 to 100 reflecting how well the listing matches.
   - Be strict: a perfect match is 100, a total mismatch is 0.
   - Produce a list of 3-5 concise bullet-point reasons explaining the score.

2. **Score gate:**
   - If score < {threshold}:
     → Call `log_rejection` with the listing URL, score, and reasons list. Then STOP.
       Do NOT call any other tools.
   - If score >= {threshold}:
     → Continue to step 3.

3. Call `draft_contact_message` with the listing details to produce a contact message
   in French. The message should be polite, concise, and professional.

4. Call `create_approval_request` with all listing details, the score, reasons, and
   the draft message. It will return an approval token — save it for step 5.

5. Call `send_approval_email` using the token from step 4 and all listing details
   to email the user for approval.

## Rules:
- Never skip the score gate.
- Never send an approval email for a listing with score < {threshold}.
- The draft message must be written in French.
- Keep score reasons concise (one sentence each).
"""


def _load_criteria() -> str:
    try:
        text = _CRITERIA_PATH.read_text(encoding="utf-8").strip()
        # Strip comment lines so the LLM only sees actionable criteria
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
        return (
            "\n".join(lines).strip()
            or "(No criteria defined — fill in config/criteria.txt)"
        )
    except FileNotFoundError:
        return "(No criteria defined — fill in config/criteria.txt)"


def create_agent() -> LlmAgent:
    criteria = _load_criteria()
    system_prompt = _SYSTEM_PROMPT.format(
        criteria=criteria,
        threshold=settings.MIN_SCORE_TO_NOTIFY,
    )
    return LlmAgent(
        name="rental_screening_agent",
        model="gemini-2.5-flash",
        instruction=system_prompt,
        tools=[
            log_rejection,
            draft_contact_message,
            create_approval_request,
            send_approval_email,
        ],
    )
