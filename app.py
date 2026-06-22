#!/usr/bin/env python3
"""BKK HÉV Car 1311 Tracker — Flask web UI."""

import os
import sys
import time
import threading

try:
    from flask import Flask, render_template, jsonify
except ImportError:
    sys.exit("Missing: pip install flask")

try:
    import requests
except ImportError:
    sys.exit("Missing: pip install requests")

API_KEY = os.getenv("BKK_API_KEY", "")
TARGET_CAR = "1311"
BASE_URL = "https://futar.bkk.hu/api/query/v1/ws/otp/api/where"
HEV_ROUTES = ["BKK_H5", "BKK_H6", "BKK_H7", "BKK_H8", "BKK_H9"]

app = Flask(__name__)

_cache = {"data": None, "ts": 0}
_shape_cache = {"data": None, "ts": 0}
_stops_cache = {"data": None, "ts": 0}
_lock = threading.Lock()
CACHE_TTL = 8
SHAPE_CACHE_TTL = 3600
STOPS_CACHE_TTL = 3600


def api_get(path, **params):
    r = requests.get(
        f"{BASE_URL}/{path}",
        params={"key": API_KEY, **params},
        headers={"User-Agent": "HEV1311WebTracker/1.0"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK":
        raise RuntimeError(data.get("text", "API error"))
    return data["data"]


def get_stop_name(stop_id):
    try:
        data = api_get("stop", stopId=stop_id)
        return data.get("entry", {}).get("name", stop_id)
    except Exception:
        return stop_id


def fetch_vehicle():
    for route_id in HEV_ROUTES:
        try:
            data = api_get("vehicles-for-route", routeId=route_id)
            for v in data.get("list", []):
                plate = v.get("licensePlate", "")
                if TARGET_CAR in plate.split("-"):
                    return v, route_id
        except requests.HTTPError as e:
            if e.response.status_code not in (404, 204):
                pass
        except Exception:
            pass
    return None, None


def get_status():
    now = time.time()
    with _lock:
        if _cache["data"] is not None and now - _cache["ts"] < CACHE_TTL:
            return _cache["data"]

    vehicle, route_id = fetch_vehicle()

    if vehicle:
        loc = vehicle.get("location", {})
        stop_id = vehicle.get("stopId", "")
        stop_name = get_stop_name(stop_id) if stop_id else "—"
        plate = vehicle.get("licensePlate", "")
        consist = plate.split("-")
        car_index = consist.index(TARGET_CAR) + 1 if TARGET_CAR in consist else None

        result = {
            "found": True,
            "route": route_id.replace("BKK_", ""),
            "trip": vehicle.get("tripId", "").replace("BKK_", ""),
            "lat": loc.get("lat"),
            "lon": loc.get("lon"),
            "bearing": vehicle.get("bearing"),
            "status": vehicle.get("status", ""),
            "stopName": stop_name,
            "consist": consist,
            "carIndex": car_index,
            "progress": vehicle.get("stopDistancePercent"),
            "lastUpdate": vehicle.get("lastUpdateTime"),
            "routeType": vehicle.get("vehicleRouteType", ""),
        }
    else:
        result = {"found": False}

    with _lock:
        _cache["data"] = result
        _cache["ts"] = now

    return result


def fetch_h5_shape():
    data = api_get("vehicles-for-route", routeId="BKK_H5")
    vehicles = data.get("list", [])
    if not vehicles:
        return None
    trip_id = vehicles[0].get("tripId")
    if not trip_id:
        return None
    trip_data = api_get("trip-details", tripId=trip_id)
    return trip_data.get("entry", {}).get("polyline", {}).get("points")


def fetch_h5_stops(trip_id):
    trip_data = api_get("trip-details", tripId=trip_id)
    entry = trip_data.get("entry", {})
    stops_ref = trip_data.get("references", {}).get("stops", {})
    result = []
    seen = set()
    for st in entry.get("stopTimes", []):
        sid = st.get("stopId", "")
        if sid in seen:
            continue
        seen.add(sid)
        s = stops_ref.get(sid, {})
        if s.get("lat") and s.get("lon"):
            result.append({
                "name": s.get("name", sid),
                "lat": s["lat"],
                "lon": s["lon"],
            })
    return result


@app.route("/api/stops")
def stops():
    now = time.time()
    with _lock:
        if _stops_cache["data"] is not None and now - _stops_cache["ts"] < STOPS_CACHE_TTL:
            return jsonify({"stops": _stops_cache["data"]})
    try:
        data = api_get("vehicles-for-route", routeId="BKK_H5")
        vehicles = data.get("list", [])
        trip_id = vehicles[0]["tripId"] if vehicles else None
        stop_list = fetch_h5_stops(trip_id) if trip_id else []
        with _lock:
            _stops_cache["data"] = stop_list
            _stops_cache["ts"] = now
        return jsonify({"stops": stop_list})
    except Exception as e:
        return jsonify({"stops": [], "error": str(e)})


@app.route("/api/route-shape")
def route_shape():
    now = time.time()
    with _lock:
        if _shape_cache["data"] is not None and now - _shape_cache["ts"] < SHAPE_CACHE_TTL:
            return jsonify({"points": _shape_cache["data"]})
    try:
        points = fetch_h5_shape()
        with _lock:
            _shape_cache["data"] = points
            _shape_cache["ts"] = now
        return jsonify({"points": points})
    except Exception as e:
        return jsonify({"points": None, "error": str(e)})


@app.route("/")
def index():
    return render_template("index.html", target_car=TARGET_CAR)


@app.route("/api/status")
def status():
    try:
        return jsonify(get_status())
    except Exception as e:
        return jsonify({"found": False, "error": str(e)}), 500


if __name__ == "__main__":
    if not API_KEY:
        print("WARNING: BKK_API_KEY not set — requests will fail with 401.")
        print("Set it with:  $env:BKK_API_KEY = 'your-key'  (PowerShell)")
    port = int(os.getenv("PORT", 5000))
    print(f"\nTracker running at http://localhost:{port}/\n")
    app.run(host="127.0.0.1", port=port, debug=False)
