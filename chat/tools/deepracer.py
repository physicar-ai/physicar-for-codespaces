import json

from typing import Annotated, Optional

import requests
from pydantic import Field

from physicar.chat.types import TextContent


def _get(path):
    r = requests.get("http://localhost" + path, timeout=5)
    r.raise_for_status()
    return r.json()


def _post(path, timeout=5, **data):
    r = requests.post("http://localhost" + path, json=data, timeout=timeout)
    r.raise_for_status()
    return r.json()


def info():
    """Check DeepRacer state and list available models.

    Returns the current state (loaded model, whether inference is running,
    action selection mode, speed scale) plus the models available on disk.
    """
    state = _get('/deepracer/status')
    models = [
        {
            "name": m["name"],
            "sensors": m.get("sensors", []),
            "valid": m.get("is_valid", False),
        }
        for m in _get('/deepracer/models').get('models', [])
    ]
    tool_call_output_contents = [
        TextContent(text=json.dumps({"state": state, "available_models": models}, ensure_ascii=False)),
    ]
    return tool_call_output_contents


def command(
    action: Annotated[Optional[str], Field(description="load / unload / start / stop (omit to only change settings)")] = None,
    model_name: Annotated[Optional[str], Field(description="model name (for load/unload; see deepracer-info for the list)")] = None,
    action_mode: Annotated[Optional[str], Field(description="how actions are picked: greedy(best) / stochastic(sample) / mean(weighted avg)")] = None,
    speed_percent: Annotated[Optional[float], Field(description="speed scale percent 50~150 (100=normal)")] = None,
):
    """Control DeepRacer autonomous driving.

    Actions:
    - load: load a trained model into memory
    - unload: remove model from memory
    - start: begin autonomous driving with the loaded model
    - stop: stop autonomous driving

    action_mode / speed_percent apply immediately when given, and can be
    combined with an action (e.g. slow down and start in one call).
    """
    results = {}

    if action_mode is not None:
        results["action_mode"] = _post(
            '/deepracer/set_config',
            key='action_selection',
            string_value=action_mode,
            float_value=0.0,
        )
    if speed_percent is not None:
        results["speed_percent"] = _post(
            '/deepracer/set_config',
            key='speed_percent',
            string_value='',
            float_value=float(speed_percent),
        )

    if action == "load":
        # Model loading can take tens of seconds (TF graph init) — the
        # default 5s timeout would give up while the load succeeds.
        results["action"] = _post('/deepracer/load_model', timeout=40, model_name=model_name)
    elif action == "unload":
        results["action"] = _post('/deepracer/unload_model', model_name=model_name or "")
    elif action == "start":
        results["action"] = _post('/deepracer/control', start=True)
    elif action == "stop":
        results["action"] = _post('/deepracer/control', start=False)
    elif action is not None:
        results["action"] = {"success": False, "message": f"Unknown action: {action}. Use: load, unload, start, stop"}

    if not results:
        results = {"success": False, "message": "Nothing to do: give an action and/or a setting (action_mode, speed_percent)."}

    tool_call_output_contents = [
        TextContent(text=json.dumps(results, ensure_ascii=False)),
    ]
    return tool_call_output_contents
