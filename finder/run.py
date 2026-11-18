"""Deal Ladder: find and rank live UK transaction services, corporate finance, IB and PE roles
for the profile in the PROFILE_JSON secret (or profile.example.json).

    cd jobs
    python3 -m finder.run                 # everything; writes data/jobs.json and data/report.md
    python3 -m finder.run --top 40        # print more rows
    python3 -m finder.run --only greenhouse,workday
    python3 -m finder.run --probe         # check every configured employer still answers

Optional keys (free) widen the search to the whole UK market:
    ADZUNA_APP_ID / ADZUNA_APP_KEY   https://developer.adzuna.com
    REED_API_KEY                     https://www.reed.co.uk/developers
"""
import argparse
import os
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import scoring, sources
from .text import region_of

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    return json.loads((ROOT / name).read_text())


def plan(cfg, profile, only):
    """List of (label, kind, callable) for every source to query."""
    tasks = []
    for kind in ("greenhouse", "lever", "ashby", "smartrecruiters", "successfactors", "workday", "oracle",
                 "workable", "eightfold", "oleeo", "kpmg", "radancy", "avature", "goldman", "rothschild", "jibe", "gresearch"):
        fn = getattr(sources, kind)
        for firm in cfg.get(kind, []):
            tasks.append((firm["name"], kind, lambda f=firm, fn=fn: _regions(f, fn(f))))
    tasks.append(("eFinancialCareers", "efc", lambda: sources.efc(
        profile["efc_keywords"], title_ok=lambda t: scoring.interest_of(t, "")[0] >= .4)))
    tasks.append(("Adzuna", "adzuna", lambda: sources.adzuna(profile["search_queries"])))
    tasks.append(("Reed", "reed", lambda: sources.reed(profile["search_queries"])))
    if only:
        tasks = [t for t in tasks if t[1] in only]
    return tasks


def _regions(firm, rows):
    """A firm can be limited to some countries ("regions": ["UK"]), e.g. when its board name is shared with another company."""
    if not firm.get("regions") or rows is None:
        return rows
    return [r for r in rows if region_of(r.get("location")) in firm["regions"]]


def dedupe(jobs):
    seen, out = {}, []
    for j in jobs:
        key = (re.sub(r"\W+", "", j["company"].lower())[:14], re.sub(r"\W+", "", j["title"].lower()),
               re.sub(r"\W+", "", (j["location"] or "").lower())[:10])
        if key in seen:
            prev = seen[key]
            if not prev.get("salary_min") and j.get("salary_min"):  # keep the one with a salary
                out[out.index(prev)] = j
                seen[key] = j
            continue
        seen[key] = j
        out.append(j)
    return out


def fmt_money(v):
    return f"£{v / 1000:,.0f}k" if v else "-"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma list of source kinds: greenhouse,lever,ashby,smartrecruiters,successfactors,workday,oracle,workable,eightfold,oleeo,kpmg,radancy,avature,goldman,rothschild,jibe,gresearch,efc,adzuna,reed")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--probe", action="store_true", help="only report which sources answer")
    ap.add_argument("--out", default=str(ROOT / "data"))
    a = ap.parse_args(argv)

    # Your real profile can live in a PROFILE_JSON secret so it never appears in a public repo.
    if os.environ.get("PROFILE_JSON"):
        profile = json.loads(os.environ["PROFILE_JSON"])
    else:
        profile = load("profile.json" if (ROOT / "profile.json").exists() else "profile.example.json")
    cfg = load("sources.json")
    aliases = cfg["firm_aliases"]
    tasks = plan(cfg, profile, set(a.only.split(",")) if a.only else None)
    t0 = time.time()
    raw, status = [], []
    with ThreadPoolExecutor(10) as ex:
        futs = {ex.submit(fn): (label, kind) for label, kind, fn in tasks}
        for f in as_completed(futs):
            label, kind = futs[f]
            try:
                rows = f.result()
            except Exception as e:
                status.append({"source": label, "kind": kind, "ok": False, "error": str(e)[:200]})
                print(f"  ! {label}: {str(e)[:120]}", file=sys.stderr)
                continue
            if rows is None:
                status.append({"source": label, "kind": kind, "ok": None, "error": "no API key set (optional)"})
                continue
            status.append({"source": label, "kind": kind, "ok": True, "count": len(rows)})
            print(f"  {label}: {len(rows)} roles", file=sys.stderr)
            for r in rows:
                r["src"] = label  # which source it came from, so it can be carried over if that source fails
            raw += rows
    if a.probe:
        for s in sorted(status, key=lambda s: (s["ok"] is not True, s["source"])):
            print(("OK  " if s["ok"] else "--  " if s["ok"] is None else "ERR ") + s["source"], s.get("count", s.get("error")))
        return 0

    # Adzuna/Reed are UK-only already; keep a light location check for the rest.
    raw = [j for j in raw if j["source"] in ("adzuna", "reed", "efinancialcareers") or region_of(j["location"]) == "UK"]
    jobs = [scoring.score(j, profile, aliases) for j in dedupe(raw)]
    prefs = profile["preferences"]
    jobs = [j for j in jobs if j["interest"] >= prefs["min_interest"]]
    jobs += carry_over(Path(a.out) / "jobs.json", status)
    jobs = [j for j in jobs if j["region"] == "UK"]
    jobs.sort(key=lambda j: -j["match"])
    # Keep the top list of roles open to him, plus the best of those that need deal experience (hidden on the page by default).
    n = prefs["max_results"]
    ok = [j for j in jobs if j.get("deal_exp") != "required"][:n]
    need = [j for j in jobs if j.get("deal_exp") == "required"][:prefs.get("max_required", 120)]
    jobs = sorted(ok + need, key=lambda j: -j["match"])
    if os.environ.get("DUMP_RAW"):  # full adverts, for testing the rules
        (Path(a.out) / "raw.json").write_text(json.dumps(jobs, ensure_ascii=False))
    for j in jobs:
        j["description"] = j["description"][:280]

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seconds": round(time.time() - t0),
        "sources": sorted(status, key=lambda s: s["source"]),
        "total_seen": len(raw),
        "jobs": jobs,
    }
    (out / "jobs.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    (out / "report.md").write_text(report(payload, 60))
    print(report(payload, a.top))
    return 0


def carry_over(prev_file, status, days=7):
    """A source that failed today (e.g. Workday refusing GitHub's servers) keeps the roles it had
    in the last file for up to a week, marked with the date they were last seen live."""
    failed = {s["source"] for s in status if s["ok"] is False}
    if not failed or not prev_file.exists():
        return []
    try:
        prev = json.loads(prev_file.read_text())
    except ValueError:
        return []
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    out, kept = [], {}
    for j in prev.get("jobs", []):
        if j.get("src") in failed:
            since = j.get("stale_since") or prev.get("generated_at", "")[:10]
            if since >= cutoff:
                j["stale_since"] = since
                out.append(j)
                kept[j["src"]] = kept.get(j["src"], 0) + 1
    for s in status:
        if s["source"] in kept:
            s["carried"] = kept[s["source"]]
    if out:
        print(f"  kept {len(out)} roles from the last run for {len(kept)} sources that failed today", file=sys.stderr)
    return out


def report(p, n):
    lines = [f"# Deal Ladder - best live UK deal roles - {p['generated_at'][:16].replace('T', ' ')} UTC", "",
             f"{p['total_seen']} UK vacancies scanned from {sum(1 for s in p['sources'] if s['ok'])} sources; "
             f"{len(p['jobs'])} kept after filtering for TS, corporate finance, IB and PE.", "",
             "Match = pay x how reachable it is x fit with deal areas x work-from-home bonus x London preference. "
             "Roles that require previous deal experience are listed last here and hidden on the page by default.", "",
             "| # | Role | Employer | Where | Pay | Level | WFH | Reach | Deal experience | Match |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    rows = sorted(p["jobs"], key=lambda j: (j.get("deal_exp") == "required", -j["match"]))
    for i, j in enumerate(rows[:n], 1):
        pay = fmt_money(j["comp"]) + ("" if j["comp_basis"] == "advertised" else " est")
        title = j["title"].replace("|", "/")[:70]
        lines.append(f"| {i} | [{title}]({j['url']}) | {j['company'][:28]} | {j['location'][:24].replace('|', '/')} | "
                     f"{pay} | {j['level']} | {j['workplace_type']} | {int(j['reach'] * 100)}% | {j.get('deal_exp') or '-'} | "
                     f"{fmt_money(j['match'])} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
