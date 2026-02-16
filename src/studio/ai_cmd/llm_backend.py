from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from ..utils import get_logger
from .rules_backend import plan_from_rules
from .schemas import Action, ActionPlan

logger = get_logger("ai_cmd.llm_backend")


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return None


def plan_with_llm(
    request: str,
    context: dict[str, Any],
    endpoint: str,
    model: str,
    api_key_env: str,
    dry_run: bool = False,
) -> ActionPlan:
    api_key = os.environ.get(api_key_env, "")
    if not endpoint or not model or not api_key:
        logger.warning("LLM backend disabled/misconfigured; falling back to rules backend.")
        return plan_from_rules(request=request, context=context, dry_run=dry_run)

    system = (
        "You are a planner that converts natural language into deterministic studio ActionPlan JSON. "
        "Return strict JSON only with fields: request, backend, context, dry_run, actions[]. "
        "Action type values: compile_only, apply_patch, rerun_subset, adjust_inference_params, "
        "adjust_prompt_templates, schedule_evolve."
    )
    user = json.dumps({"request": request, "context": context}, ensure_ascii=True)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        obj = json.loads(raw)
        content = obj["choices"][0]["message"]["content"]
        planned = _extract_json(content)
        if not planned:
            raise ValueError("LLM output did not contain valid JSON")

        actions = [Action(type=a.get("type", "compile_only"), payload=a.get("payload", {})) for a in planned.get("actions", [])]
        return ActionPlan(
            request=request,
            backend="llm",
            context=planned.get("context", context),
            dry_run=dry_run,
            actions=actions,
        )
    except Exception as exc:
        logger.warning("LLM backend failed (%s); using rules backend.", exc)
        return plan_from_rules(request=request, context=context, dry_run=dry_run)
