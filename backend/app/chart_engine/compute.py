"""CLI entrypoint for testing the chart engine.

Usage:
    python -m app.chart_engine.compute --date 1990-05-15 --time 14:30 --lat 55.75 --lon 37.62
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from app.chart_engine.chart import build_chart


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a natal chart")
    parser.add_argument("--date", required=True, help="Birth date (YYYY-MM-DD)")
    parser.add_argument("--time", required=True, help="Birth time UTC (HH:MM)")
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--tz", default="UTC", help="IANA timezone (default: UTC)")
    parser.add_argument("--house-system", default="P", help="House system: P=Placidus, E=Equal")
    args = parser.parse_args()

    dt = datetime.strptime(f"{args.date} {args.time}", "%Y-%m-%d %H:%M").replace(tzinfo=UTC)

    chart = build_chart(
        birth_datetime=dt,
        latitude=args.lat,
        longitude=args.lon,
        timezone_name=args.tz,
        house_system=args.house_system,
    )

    # Pretty print
    print(f"\n{'=' * 60}")
    print(f"Natal Chart: {dt.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Location: {args.lat}, {args.lon} ({args.tz})")
    print(f"House System: {chart.house_system}")
    print(f"{'=' * 60}\n")

    print("PLANETS:")
    for p in chart.planets:
        retro = " ℞" if p.is_retrograde else ""
        house_str = f" (House {p.house})" if p.house else ""
        print(f"  {p.name:12} {p.sign:12} {p.sign_degree:6.2f}°{retro}{house_str}")

    print("\nHOUSES:")
    for h in chart.houses:
        print(f"  House {h.number:2}  {h.sign:12} {h.longitude:7.2f}°")

    print(f"\nASPECTS ({len(chart.aspects)}):")
    for a in chart.aspects:
        app = "Applying" if a.is_applying else "Separating"
        print(f"  {a.planet_a:12} {a.aspect_type:12} {a.planet_b:12}  orb: {a.orb:.2f}° ({app})")

    print()


if __name__ == "__main__":
    main()
