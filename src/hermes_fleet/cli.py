"""Command-line interface for Hermes Fleet Control."""

from __future__ import annotations

import argparse
import json
import sys

from .discover import collect_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-fleet", description="Local-first Hermes Agent fleet status.")
    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="Show read-only fleet status")
    status.add_argument("--home", help="Hermes home to inspect, defaults to $HERMES_HOME or ~/.hermes")
    status.add_argument("--json", action="store_true", help="Print schema-versioned JSON")

    return parser


def render_status(data: dict) -> str:
    profiles = data["profiles"]
    counts: dict[str, int] = {}
    for profile in profiles:
        counts[profile["overall"]] = counts.get(profile["overall"], 0) + 1

    lines = [
        f"Hermes Fleet status ({len(profiles)} profiles)",
        f"home: {data['hermes_home']}",
        " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "no profiles discovered",
        "",
        f"{'PROFILE':18} {'PLATFORMS':24} {'GATEWAY':12} {'OVERALL':10}",
        "-" * 70,
    ]
    for profile in profiles:
        configured = [p["platform"] for p in profile["platforms"] if p["configured"]]
        platform_text = ",".join(configured) if configured else "-"
        gateway = profile["gateway"]
        gateway_text = gateway["state"] if gateway.get("pid") is None else f"{gateway['state']}:{gateway['pid']}"
        lines.append(f"{profile['name'][:18]:18} {platform_text[:24]:24} {gateway_text[:12]:12} {profile['overall'][:10]:10}")
    lines.append("")
    lines.append("Safety: read-only; secret values are not retained or printed.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "status"):
        status = collect_status(home=getattr(args, "home", None)).to_dict()
        if getattr(args, "json", False):
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(render_status(status))
        return 0
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
