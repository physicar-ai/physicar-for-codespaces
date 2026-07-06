import json

from typing import Annotated, Optional

from pydantic import Field

import requests
from physicar.chat.types import TextContent


def search(
    query: Annotated[str, Field(description="search query")],
):
    """Search iTunes for music tracks."""
    import urllib.request
    import urllib.parse

    params = urllib.parse.urlencode({'term': query, 'media': 'music', 'limit': 5})
    try:
        req = urllib.request.Request(
            f"https://itunes.apple.com/search?{params}",
            headers={'User-Agent': 'PhysiCar/1.0'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        tool_call_output_contents = [
            TextContent(
                text=json.dumps({"success": False, "results": [], "message": str(e)}),
            ),
        ]
        return tool_call_output_contents

    results = []
    for t in data.get('results', []):
        preview = t.get('previewUrl')
        if not preview:
            continue
        view_url = (
            t.get('trackViewUrl')
            or t.get('collectionViewUrl')
            or t.get('artistViewUrl')
        )
        results.append({
            "title": t.get('trackName', ''),
            "artist": t.get('artistName', ''),
            "album": t.get('collectionName', ''),
            "duration_ms": t.get('trackTimeMillis', 0),
            "genre": t.get('primaryGenreName', ''),
            "preview_url": preview,
            "artwork": t.get('artworkUrl100', ''),
            "view_url": view_url,
        })

    tool_call_output_contents = [
        TextContent(
            text=json.dumps({
                "success": True,
                "results": results,
                "attribution": "Preview provided courtesy of iTunes.",
                "notice": "When showing these preview results to the user, always include the track title and the iTunes Store link (view_url) so they can purchase or listen to the full song.",
            }, ensure_ascii=False),
        ),
    ]
    return tool_call_output_contents


def player(
    action: Annotated[str, Field(description="play / stop / volume / status")],
    url: Annotated[Optional[str], Field(description="preview URL from music-search")] = None,
    volume: Annotated[float, Field(description="0.0~1.0")] = 0.5,
):
    """Control music playback. Use music-search first to get the preview URL."""
    if not hasattr(player, '_current_id'):
        player._current_id = None

    try:
        if action == "status":
            r = requests.get("http://localhost/audio", timeout=5)
            r.raise_for_status()
            result = r.json()

        elif action == "play":
            if not url:
                result = {"success": False, "message": "url required"}
            else:
                r = requests.post("http://localhost/audio/play", json={
                    "url": url,
                    "volume": max(0.0, min(1.0, volume)),
                    "replace": True,
                }, timeout=10)
                r.raise_for_status()
                result = r.json()
                player._current_id = result.get("id")

        elif action == "stop":
            r = requests.post("http://localhost/audio/stop",
                              json={"all": True}, timeout=5)
            r.raise_for_status()
            player._current_id = None
            result = {"success": True}

        elif action == "volume":
            if not player._current_id:
                result = {"success": False, "message": "nothing is playing"}
            else:
                r = requests.post("http://localhost/audio/volume", json={
                    "id": player._current_id,
                    "volume": max(0.0, min(1.0, volume)),
                }, timeout=5)
                r.raise_for_status()
                result = r.json()

        else:
            result = {
                "success": False,
                "message": f"Unknown action: {action}. Use: play, stop, volume, status",
            }
    except requests.RequestException as e:
        result = {"success": False, "message": str(e)}

    tool_call_output_contents = [
        TextContent(text=json.dumps(result, ensure_ascii=False)),
    ]
    return tool_call_output_contents
