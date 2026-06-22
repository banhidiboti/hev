#!/usr/bin/env python3
"""BKK HÉV Car 1311 Tracker — uses the BudapestGO REST API (futar.bkk.hu)."""

import os
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH = True
    console = Console()
except ImportError:
    RICH = False

TARGET_CAR = "1311"
BASE_URL = "https://futar.bkk.hu/api/query/v1/ws/otp/api/where"
# All suburban railway (HÉV) routes in Budapest
HEV_ROUTES = ["BKK_H5", "BKK_H6", "BKK_H7", "BKK_H8", "BKK_H9"]
REFRESH_INTERVAL = 10

STOP_STATUS_LABELS = {
    "IN_TRANSIT_TO":      "In transit to",
    "STOPPED_AT":         "Stopped at",
    "INCOMING_AT":        "Incoming at",
}

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def bearing_to_compass(deg: float) -> str:
    return COMPASS[round(deg / 22.5) % 16]


def api_get(path: str, api_key: str, **params):
    r = requests.get(
        f"{BASE_URL}/{path}",
        params={"key": api_key, **params},
        headers={"User-Agent": "HEV1311Tracker/1.0"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"API error: {data.get('text', 'unknown')}")
    return data["data"]


def get_stop_name(stop_id: str, api_key: str) -> str:
    try:
        data = api_get("stop", api_key, stopId=stop_id)
        return data.get("entry", {}).get("name", stop_id)
    except Exception:
        return stop_id


def find_car_on_route(route_id: str, api_key: str):
    data = api_get("vehicles-for-route", api_key, routeId=route_id)
    for vehicle in data.get("list", []):
        plate = vehicle.get("licensePlate", "")
        if TARGET_CAR in plate.split("-"):
            return vehicle, route_id
    return None, None


def find_car(api_key: str):
    for route_id in HEV_ROUTES:
        try:
            v, r = find_car_on_route(route_id, api_key)
            if v:
                return v, r
        except requests.HTTPError as e:
            if e.response.status_code not in (404, 204):
                raise
        except Exception:
            pass
    return None, None


def render_found(vehicle: dict, route_id: str, api_key: str):
    loc = vehicle.get("location", {})
    lat = loc.get("lat", 0)
    lon = loc.get("lon", 0)
    bearing = vehicle.get("bearing")
    status = vehicle.get("status", "")
    stop_id = vehicle.get("stopId", "")
    trip_id = vehicle.get("tripId", "")
    plate = vehicle.get("licensePlate", "—")
    last_update = vehicle.get("lastUpdateTime")
    pct = vehicle.get("stopDistancePercent")

    stop_name = get_stop_name(stop_id, api_key) if stop_id else "—"
    status_label = STOP_STATUS_LABELS.get(status, status)
    updated = datetime.fromtimestamp(last_update).strftime("%H:%M:%S") if last_update else "—"

    osm_url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=15/{lat:.6f}/{lon:.6f}"

    consist_cars = plate.split("-")
    car_index = consist_cars.index(TARGET_CAR) + 1 if TARGET_CAR in consist_cars else "?"
    consist_display = " · ".join(
        f"[bold]{c}[/bold]" if c == TARGET_CAR else c for c in consist_cars
    ) if RICH else plate

    if RICH:
        console.clear()
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("k", style="bold cyan", min_width=20)
        t.add_column("v")

        t.add_row("Car", f"[bold green]{TARGET_CAR}[/bold green]  (car {car_index} of {len(consist_cars)} in consist)")
        t.add_row("Consist", consist_display)
        t.add_row("Last update", updated)
        t.add_row("", "")
        t.add_row("Route", route_id.replace("BKK_", ""))
        t.add_row("Trip", trip_id.replace("BKK_", ""))
        t.add_row("", "")
        t.add_row("Latitude", f"{lat:.6f}°")
        t.add_row("Longitude", f"{lon:.6f}°")
        if bearing is not None:
            t.add_row("Bearing", f"{bearing:.0f}°  {bearing_to_compass(bearing)}")
        if pct is not None:
            t.add_row("Segment progress", f"{pct:.0f}%")
        t.add_row("", "")
        t.add_row("Status", f"{status_label}  [italic]{stop_name}[/italic]")
        t.add_row("", "")
        t.add_row("OpenStreetMap", f"[link={osm_url}]{osm_url}[/link]")

        console.print(Panel(
            t,
            title=f"[bold green] BKK HÉV Car {TARGET_CAR} — FOUND [/bold green]",
            border_style="green",
        ))
    else:
        print(f"\n{'='*56}")
        print(f"  BKK HÉV Car {TARGET_CAR} — FOUND  (updated {updated})")
        print(f"{'='*56}")
        print(f"  Consist:   {plate}")
        print(f"  Route:     {route_id.replace('BKK_', '')}")
        print(f"  Trip:      {trip_id.replace('BKK_', '')}")
        print(f"  Position:  {lat:.6f}°N  {lon:.6f}°E")
        if bearing is not None:
            print(f"  Bearing:   {bearing:.0f}°  {bearing_to_compass(bearing)}")
        if pct is not None:
            print(f"  Progress:  {pct:.0f}% along segment")
        print(f"  Status:    {status_label}  {stop_name}")
        print(f"\n  Map: {osm_url}")
        print(f"{'='*56}")


def render_not_found():
    ts = datetime.now().strftime("%H:%M:%S")
    if RICH:
        console.clear()
        console.print(Panel(
            f"[yellow]Car {TARGET_CAR} is not in any live HÉV feed right now ({ts}).[/yellow]\n\n"
            "It may be out of service, in the depot, or between trips.",
            title=f"[bold yellow] BKK HÉV Car {TARGET_CAR} — NOT IN SERVICE [/bold yellow]",
            border_style="yellow",
        ))
    else:
        print(f"\n  [{ts}]  Car {TARGET_CAR} not found — may be out of service.")


def main():
    api_key = os.getenv("BKK_API_KEY", "")
    if not api_key:
        sys.exit(
            "No API key found. Set BKK_API_KEY:\n"
            "  PowerShell:  $env:BKK_API_KEY = 'your-key'\n"
            "  bash:        export BKK_API_KEY=your-key\n"
            "  Get one free at: https://opendata.bkk.hu/keys"
        )

    print(f"Tracking HÉV car {TARGET_CAR} across H5–H9 — refreshing every {REFRESH_INTERVAL}s. Ctrl+C to quit.\n")

    while True:
        try:
            vehicle, route_id = find_car(api_key)
            if vehicle:
                render_found(vehicle, route_id, api_key)
            else:
                render_not_found()

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except requests.HTTPError as e:
            print(f"\nHTTP {e.response.status_code}: {e}")
            if e.response.status_code == 401:
                print("API key rejected. Check BKK_API_KEY is correct.")
        except requests.RequestException as e:
            print(f"\nNetwork error: {e}")
        except Exception as e:
            print(f"\nError: {e}")

        try:
            print(f"\nRefreshing in {REFRESH_INTERVAL}s… (Ctrl+C to stop)")
            time.sleep(REFRESH_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    main()
