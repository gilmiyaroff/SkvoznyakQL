#!/usr/bin/env python3
"""Reconciliation and privacy checks for SKVOZNYAK v0.4 artifacts."""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit


def payload(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    match = re.search(r'<script id="data" type="application/json">(.*?)</script>', raw, re.S)
    if not match:
        raise AssertionError(f"Embedded payload not found in {path}")
    return json.loads(match.group(1))


def check(ok: bool, label: str, checks: list[dict]) -> None:
    checks.append({"check": label, "ok": bool(ok)})
    if not ok:
        raise AssertionError(label)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    pub, prv, checks = payload(args.public), payload(args.private), []
    check(pub["private"] is False and prv["private"] is True, "build modes are explicit", checks)
    for data, name in ((pub, "public"), (prv, "private")):
        audit = data["audit"]
        check(audit["meta_rows"] == 23060, f"{name}: 23,060 Meta rows", checks)
        check(audit["ads"] == 515, f"{name}: 515 unique ads", checks)
        check(audit["rows"] == 5654, f"{name}: 5,654 unique CRM deals", checks)
        check(audit["exact"] == 3596, f"{name}: 3,596 exact Ad ID matches", checks)
        check(audit["ctwa"] == 3512, f"{name}: 3,512 exact CTWA matches", checks)
        check(audit["ad_only"] == 84, f"{name}: 84 exact Ad-ID-only matches", checks)
        check(audit["unmatched"] == 2058, f"{name}: 2,058 deals without exact attribution", checks)
        check(audit["duplicates"] == 0, f"{name}: no duplicate Deal IDs", checks)
        check(len(data["fx"]) == 195, f"{name}: 195 daily FX rates", checks)
        check(all(re.fullmatch(r"\d{18}", ad["id"]) for ad in data["ads"]), f"{name}: every Meta Ad ID is an 18-digit string", checks)
        meta_spend = sum(float(row[2]) for row in data["m"])
        file_spend = sum(float(row["spend_usd"]) for row in audit["files"])
        check(math.isclose(meta_spend, file_spend, abs_tol=0.04), f"{name}: file and row spend reconcile", checks)
        by_day = defaultdict(float)
        by_ad = defaultdict(float)
        for row in data["m"]:
            by_day[row[0]] += row[2]
            by_ad[row[1]] += row[2]
        check(math.isclose(sum(by_day.values()), meta_spend, abs_tol=1e-6), f"{name}: day-level spend reconciles", checks)
        check(math.isclose(sum(by_ad.values()), meta_spend, abs_tol=1e-6), f"{name}: ad-level spend reconciles", checks)

    check(pub["deals"] == [], "public payload contains no deal rows", checks)
    check(len(prv["deals"]) == 3596, "private drill-down contains only exact-attributed deals", checks)
    public_text = json.dumps(pub, ensure_ascii=False)
    check(not re.search(r'"deal_id"\s*:', public_text), "public payload contains no Deal ID field", checks)
    check(not re.search(r'"manager"\s*:', public_text), "public payload contains no manager field", checks)
    check(not re.search(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', public_text, re.I), "public payload contains no email address", checks)
    check(not re.search(r'(?<!\d)(?:\+?7|8)[\s()\-]*\d{3}[\s()\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)', public_text), "public payload contains no Kazakhstan/Russia-style phone", checks)
    check(all(row[5] is None for row in pub["p"]), "public daily sales contain no individual revenue", checks)
    check(all(row[3] is None or (row[2] >= pub["k"] and row[3] % 10000 == 0) for row in pub["pr"]), "public monthly revenue obeys k-threshold and rounding", checks)
    for ad in pub["ads"]:
        url = ad.get("creative_url", "")
        if not url:
            continue
        parts = urlsplit(url)
        host = parts.netloc.lower().removeprefix("www.")
        check(parts.scheme == "https" and not parts.query and not parts.fragment and host in {"instagram.com", "fb.me"}, f"safe creative URL: {ad['id']}", checks)
    check(sum(row[2] for row in pub["m"]) == sum(row[2] for row in prv["m"]), "public/private Meta spend is identical", checks)
    check(pub["l"] == prv["l"], "public/private lead aggregates are identical", checks)

    report = {
        "status": "PASS",
        "checks_total": len(checks),
        "checks_passed": sum(item["ok"] for item in checks),
        "summary": {
            "meta_rows": pub["audit"]["meta_rows"],
            "unique_ads": pub["audit"]["ads"],
            "crm_deals": pub["audit"]["rows"],
            "exact_ad_id_matches": pub["audit"]["exact"],
            "confirmed_ctwa_matches": pub["audit"]["ctwa"],
            "unmatched_deals": pub["audit"]["unmatched"],
            "meta_spend_usd": round(sum(row[2] for row in pub["m"]), 2),
            "fx_days": len(pub["fx"]),
        },
        "monthly_files": pub["audit"]["files"],
        "checks": checks,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"PASS: {len(checks)} checks -> {args.report}")


if __name__ == "__main__":
    main()
