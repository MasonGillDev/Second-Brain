"""Backend API for Chicago Train Tracker — proxies CTA Train Tracker API to avoid CORS."""

import urllib.request
import urllib.parse
from pathlib import Path
from quart import Blueprint, request, Response, jsonify

# Primary key; falls back to the public demo key if blank
CTA_API_KEY = "975fff10afb14fb3aa5c44bc5b4ef14d"
# Correct CTA Train Tracker arrivals endpoint
CTA_ARRIVALS_URL = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"


def create_blueprint(data_dir: Path) -> Blueprint:
    bp = Blueprint("chicago-train-tracker-api", __name__)

    @bp.route("/arrivals", methods=["GET"])
    async def get_arrivals():
        mapid = request.args.get("mapid", "").strip()
        if not mapid:
            return jsonify({"error": "mapid parameter required"}), 400

        params = urllib.parse.urlencode({
            "key": CTA_API_KEY,
            "mapid": mapid,
        })
        url = f"{CTA_ARRIVALS_URL}?{params}"
        print(f"[CTA] GET {url}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ChicagoTrainTracker/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read().decode("utf-8")
            print(f"[CTA] OK — {len(data)} bytes")
            return Response(data, content_type="text/xml")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"[CTA] HTTPError {e.code}: {body}")
            return jsonify({"error": f"CTA API error {e.code}", "detail": body}), 502
        except Exception as e:
            print(f"[CTA] Exception: {e}")
            return jsonify({"error": str(e)}), 500

    return bp
