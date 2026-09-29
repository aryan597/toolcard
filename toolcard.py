"""Per-tool failure report card from published agent trajectories.

Grades every write-tool call an agent made against the task's ground-truth actions.
No LLM judge: a failure is an exact, checkable difference.

Categories per ground-truth write:
  OK           called with the right arguments
  WRONG_ARGS   right tool, wrong arguments (we name which argument)
  WRONG_TOOL   a different write tool on the same order/reservation instead
  HANDED_OFF   never called; the agent transferred to a human instead
  MISSED       never called
Extra agent writes not in ground truth:
  DUPLICATE    identical to a write it already made
  UNWANTED     a write the task didn't ask for

Usage: python toolcard.py [--tau2 path/to/tau2-bench] [--ordered] <results.json> [...]  -> REPORT.md + rows.jsonl

Which tools count as writes: tau2-bench marks each tool READ, WRITE, THINK or GENERIC in its source
(@is_tool(ToolType.WRITE)). Its result files don't carry those types, so:
  --tau2 <repo>  reads the types from the tau2-bench source (recommended), and
  without it, the built-in lists below are used. They match tau2-bench's source as of Sept 2026.
Either way, any tool name in the data that isn't a known tool stops the run with an error, so a new or
renamed write can't silently go ungraded.

List arguments are compared as unordered by default (e.g. the passengers on a booking). --ordered compares
them in order. On the published runs both give the same results; see README.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

BUILTIN = {  # tool -> type, from tau2-bench src/tau2/domains/<domain>/tools.py
    "airline": {"book_reservation": "WRITE", "cancel_reservation": "WRITE", "send_certificate": "WRITE",
                "update_reservation_baggages": "WRITE", "update_reservation_flights": "WRITE",
                "update_reservation_passengers": "WRITE", "get_reservation_details": "READ",
                "get_user_details": "READ", "list_all_airports": "READ", "search_direct_flight": "READ",
                "search_onestop_flight": "READ", "get_flight_status": "READ", "calculate": "GENERIC",
                "transfer_to_human_agents": "GENERIC", "think": "THINK"},
    "retail": {"cancel_pending_order": "WRITE", "exchange_delivered_order_items": "WRITE",
               "modify_pending_order_address": "WRITE", "modify_pending_order_items": "WRITE",
               "modify_pending_order_payment": "WRITE", "modify_user_address": "WRITE",
               "return_delivered_order_items": "WRITE", "find_user_id_by_name_zip": "READ",
               "find_user_id_by_email": "READ", "get_order_details": "READ", "get_product_details": "READ",
               "get_item_details": "READ", "get_user_details": "READ", "list_all_product_types": "READ",
               "calculate": "GENERIC", "transfer_to_human_agents": "GENERIC", "think": "THINK"},
}
ORDERED = False  # set by --ordered


def tool_types(tau2_root) -> dict:
    """{domain: {tool: type}} read from the tau2-bench source, for every domain it has."""
    import re
    out = {}
    for f in sorted(Path(tau2_root, "src", "tau2", "domains").glob("*/tools.py")):
        src = f.read_text(encoding="utf-8")
        found = re.findall(r"^\s*@is_tool\(\s*ToolType\.(\w+)[^)]*\)\s*\n\s*def (\w+)", src, re.M)
        if found:
            out[f.parent.name] = {name: kind for kind, name in found}
    if not out:
        raise SystemExit(f"no tools found under {tau2_root}/src/tau2/domains: is that a tau2-bench checkout?")
    return out


class UnknownTools(Exception):
    pass


def check_coverage(types: dict, seen: dict) -> None:
    """seen: {domain: set of tool names in the data}. Fails loudly on anything the grader doesn't know."""
    problems = []
    for domain, names in sorted(seen.items()):
        known = types.get(domain)
        if known is None:
            problems.append(f"domain '{domain}' has no tool list")
            continue
        missing = sorted(n for n in names if n not in known)
        if missing:
            problems.append(f"{domain}: {', '.join(missing)}")
    if problems:
        raise UnknownTools("toolcard doesn't know these tools, so it can't tell if they're writes: "
                           + "; ".join(problems) + ". Pass --tau2 <tau2-bench checkout> or update BUILTIN.")


WRITES = {t for tools in BUILTIN.values() for t, k in tools.items() if k == "WRITE"}  # all domains
TARGET_KEYS = ("order_id", "reservation_id", "user_id")


def norm(v):
    if isinstance(v, list):
        items = [norm(x) for x in v]
        if ORDERED:
            return items
        try:
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))
        except TypeError:
            return items
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def args_of(call) -> dict:
    a = call["function"]["arguments"]
    if isinstance(a, str):
        try:
            a = json.loads(a) if a.strip() else {}
        except json.JSONDecodeError:
            a = {"_unparsed": a}
    return norm(a or {})


def agent_calls(traj):
    """(name, args, rejected) for every call; rejected = the tool answered with an Error (no side effect)."""
    calls, pos = [], {}
    for i, m in enumerate(traj):
        if m.get("role") == "assistant":
            for c in m.get("tool_calls") or []:
                pos[c.get("id")] = len(calls)
                calls.append([c["function"]["name"], args_of(c), False, i])
        elif m.get("role") == "tool":
            j = pos.get(m.get("tool_call_id"))
            if j is None:  # ids missing (some traces): take the latest call without a result
                j = next((k for k in range(len(calls) - 1, -1, -1) if calls[k][3] is not None), None)
            if j is not None:
                calls[j][2] = str(m.get("content", "")).startswith("Error")
                calls[j][3] = None
    return [(n, a, r) for n, a, r, _ in calls]


def tool_errors(traj):
    names = {}
    for m in traj:
        if m.get("role") == "assistant":
            for c in m.get("tool_calls") or []:
                names[c.get("id")] = c["function"]["name"]
    out = []
    for m in traj:
        if m.get("role") == "tool":
            txt = str(m.get("content", ""))
            if txt.startswith("Error"):
                out.append((m.get("name") or names.get(m.get("tool_call_id"), "?"), txt[:90]))
    return out


def target(args):
    return next((args[k] for k in TARGET_KEYS if k in args), None)


def diff_keys(want: dict, got: dict):
    keys = sorted(set(want) | set(got))
    return [k for k in keys if want.get(k) != got.get(k)]


def grade(ep, writes_set=None):
    """ep: {"actions": [{"name", "kwargs", "compare"}], "traj": [...]} -> (rows, tool errors)"""
    WRITES = writes_set if writes_set is not None else globals()["WRITES"]
    gt = [(a["name"], norm(a["kwargs"]), a.get("compare")) for a in ep["actions"] if a["name"] in WRITES]
    calls = agent_calls(ep["traj"])
    writes = [(n, a) for n, a, rej in calls if n in WRITES and not rej]
    handed_off = any(n == "transfer_to_human_agents" for n, _, _ in calls)
    used = [False] * len(writes)
    rows = [{"tool": n, "cat": "REJECTED", "why": "tool returned an error"} for n, _, rej in calls if n in WRITES and rej]
    # pass 1: exact matches
    pending = []
    def same_args(want, got, compare):
        keys = compare if compare else sorted(set(want) | set(got))
        return all(want.get(k) == got.get(k) for k in keys)

    for name, want, compare in gt:
        hit = next((i for i, (n, a) in enumerate(writes) if not used[i] and n == name and same_args(want, a, compare)), None)
        if hit is not None:
            used[hit] = True
            rows.append({"tool": name, "cat": "OK", "why": ""})
        else:
            pending.append((name, want, compare))
    # pass 2: explain the misses
    for name, want, compare in pending:
        same = [i for i, (n, a) in enumerate(writes) if not used[i] and n == name]
        if same:
            dk = lambda got: [k for k in diff_keys(want, got) if not compare or k in compare]
            i = min(same, key=lambda i: len(dk(writes[i][1])))
            used[i] = True
            keys = dk(writes[i][1])
            rows.append({"tool": name, "cat": "WRONG_ARGS", "why": ",".join(keys)})
            continue
        tgt = target(want)
        other = [i for i, (n, a) in enumerate(writes) if not used[i] and n != name and tgt is not None and target(a) == tgt]
        if other:
            used[other[0]] = True
            rows.append({"tool": name, "cat": "WRONG_TOOL", "why": f"called {writes[other[0]][0]}"})
        elif handed_off:
            rows.append({"tool": name, "cat": "HANDED_OFF", "why": "transferred to human"})
        else:
            rows.append({"tool": name, "cat": "MISSED", "why": ""})
    # extras
    seen = []
    for i, (n, a) in enumerate(writes):
        if used[i]:
            seen.append((n, a))
            continue
        if (n, a) in seen or any((n, a) == (writes[j][0], writes[j][1]) for j in range(i) if j != i):
            rows.append({"tool": n, "cat": "DUPLICATE", "why": "same call repeated"})
        else:
            rows.append({"tool": n, "cat": "UNWANTED", "why": "write not in task"})
        seen.append((n, a))
    return rows, tool_errors(ep["traj"])


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def pct(k, n):
    lo, hi = wilson(k, n)
    return f"{100*k/n:.0f}% ({100*lo:.0f}-{100*hi:.0f})" if n else "-"


def load(path):
    """Yield (model, domain, episode) from tau-bench (v1) or tau2-bench result files."""
    raw = json.load(open(path))
    stem = Path(path).stem
    if isinstance(raw, dict) and "simulations" in raw:  # tau2-bench
        info = raw.get("info") or {}
        model = ((info.get("agent_info") or {}).get("llm") or "").strip()
        domain = ((info.get("environment_info") or {}).get("domain_name") or "").strip()
        if not model or not domain:  # older files: <model>_<domain>_..., model names use "-" not "_"
            parts = stem.split("_")
            if len(parts) < 2:
                raise ValueError(f"can't tell model and domain from {path}")
            model, domain = model or parts[0], domain or parts[1]
        tasks = {t["id"]: t for t in raw["tasks"]}
        for s in raw["simulations"]:
            crit = tasks[s["task_id"]].get("evaluation_criteria") or {}
            acts = [{"name": a["name"], "kwargs": a.get("arguments") or {}, "compare": a.get("compare_args")}
                    for a in crit.get("actions") or [] if a.get("requestor", "assistant") == "assistant"]
            traj = []
            for m in s["messages"]:
                if m.get("role") == "assistant":
                    traj.append({"role": "assistant", "tool_calls": [
                        {"id": c.get("id"), "function": {"name": c["name"], "arguments": c.get("arguments") or {}}}
                        for c in m.get("tool_calls") or []]})
                elif m.get("role") == "tool":
                    err = str(m.get("error")) == "True" or str(m.get("content", "")).startswith("Error")
                    traj.append({"role": "tool", "tool_call_id": m.get("id"),
                                 "content": ("Error: " if err and not str(m.get("content", "")).startswith("Error") else "") + str(m.get("content", ""))})
            db = (s.get("reward_info") or {}).get("db_check") or {}
            yield model, domain, {"task_id": s["task_id"], "trial": s.get("trial"), "actions": acts, "traj": traj,
                                  "ref_ok": bool(db.get("db_match")) if db else s["reward_info"]["reward"] == 1}
    else:  # tau-bench v1 historical trajectories
        model, domain = stem.rsplit("-", 1)
        for ep in raw:
            acts = [{"name": a["name"], "kwargs": a["kwargs"]} for a in ep["info"]["task"]["actions"]]
            yield model, domain, {"task_id": ep["task_id"], "trial": ep.get("trial"), "actions": acts,
                                  "traj": ep["traj"], "ref_ok": ep["reward"] == 1}


def main(argv):
    global ORDERED
    args, types, paths = list(argv), BUILTIN, []
    while args:
        a = args.pop(0)
        if a == "--tau2":
            types = tool_types(args.pop(0))
        elif a == "--ordered":
            ORDERED = True
        else:
            paths.append(a)
    if not paths:
        raise SystemExit(__doc__)
    out = Path(__file__).resolve().parent / "out"
    out.mkdir(exist_ok=True)
    loaded = [(m, d, ep) for p in paths for m, d, ep in load(p)]
    seen = defaultdict(set)
    for _, d, ep in loaded:
        seen[d].update(a["name"] for a in ep["actions"])
        seen[d].update(n for n, _, _ in agent_calls(ep["traj"]))
    check_coverage(types, seen)
    writes = {d: {t for t, k in types[d].items() if k == "WRITE"} for d in seen}
    rows, errs, eps = [], [], []
    for model, domain, ep in loaded:
        r, e = grade(ep, writes[domain])
        fail = any(x["cat"] not in ("OK", "REJECTED") for x in r)
        eps.append({"model": model, "domain": domain, "task": ep["task_id"], "trial": ep["trial"],
                    "ref_ok": ep["ref_ok"], "write_fail": fail})
        for x in r:
            rows.append({"model": model, "domain": domain, "task": ep["task_id"], "trial": ep["trial"], **x})
        for t, msg in e:
            errs.append({"model": model, "tool": t, "msg": msg})
    with open(out / "rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    report(rows, errs, eps, out / "REPORT.md")


def report(rows, errs, eps, path):
    models = sorted({r["model"] for r in rows})
    L = ["# Tool report card: which tools agents get wrong, and how", "",
         "Source: tau2-bench published results (Sierra Research), 4 models, airline + retail. Every write-tool call is compared with the task's",
         "ground-truth actions. No LLM judge. Rates are per required call, with 95% Wilson intervals. Trials repeat the same",
         "tasks, so intervals are optimistic.", ""]

    # validation
    L += ["## Does the grader agree with the benchmark's own check?", "",
          "| model | domain | episodes | benchmark says correct, we flag a write error | benchmark says wrong, explained by a write error |",
          "|---|---|---|---|---|"]
    for (m, d), g in sorted(group(eps, ("model", "domain")).items()):
        ok = [e for e in g if e["ref_ok"]]
        bad = [e for e in g if not e["ref_ok"]]
        fp = sum(e["write_fail"] for e in ok)
        cov = sum(e["write_fail"] for e in bad)
        L.append(f"| {m} | {d} | {len(g)} | {fp}/{len(ok)} | {cov}/{len(bad)} ({100*cov/max(1,len(bad)):.0f}%) |")
    L += ["", "Failures not explained by a write error are wrong answers to questions (tau-bench's output check) or",
          "tasks where the right move was no write at all.", ""]

    # per tool
    L += ["## Per tool", "", "| tool | model | required | correct | wrong args | wrong tool | handed off | missed | most common reason |",
          "|---|---|---|---|---|---|---|---|---|"]
    by = group([r for r in rows if r["cat"] not in ("DUPLICATE", "UNWANTED", "REJECTED")], ("tool", "model"))
    order = sorted({t for t, _ in by}, key=lambda t: (-sum(len(by.get((t, m), [])) for m in models), t))
    for t in order:
        for m in models:
            g = by.get((t, m), [])
            if not g:
                continue
            c = Counter(x["cat"] for x in g)
            n = len(g)
            reasons = Counter(f'{x["cat"].lower().replace("_", " ")}: {x["why"]}' if x["why"] else x["cat"].lower()
                              for x in g if x["cat"] != "OK")
            top = reasons.most_common(1)[0] if reasons else ("", 0)
            L.append(f"| `{t}` | {m} | {n} | {pct(c['OK'], n)} | {c['WRONG_ARGS']} | {c['WRONG_TOOL']} | "
                     f"{c['HANDED_OFF']} | {c['MISSED']} | {top[0]} ({top[1]}) |" if top[1] else
                     f"| `{t}` | {m} | {n} | {pct(c['OK'], n)} | 0 | 0 | 0 | 0 | - |")

    # which argument
    L += ["", "## When the arguments were wrong, which argument?", "", "| tool | model | argument | times |", "|---|---|---|---|"]
    wa = Counter((r["tool"], r["model"], k) for r in rows if r["cat"] == "WRONG_ARGS" for k in r["why"].split(","))
    for (t, m, k), v in wa.most_common(15):
        L.append(f"| `{t}` | {m} | `{k}` | {v} |")

    # extras
    L += ["", "## Writes nobody asked for (and writes the tool refused)", "", "| tool | model | unwanted | duplicate | refused by tool |", "|---|---|---|---|---|"]
    ex = Counter((r["tool"], r["model"], r["cat"]) for r in rows if r["cat"] in ("DUPLICATE", "UNWANTED", "REJECTED"))
    for t, m in sorted({(t, m) for t, m, _ in ex}, key=lambda k: (-(ex[(k[0], k[1], 'UNWANTED')] + ex[(k[0], k[1], 'DUPLICATE')]), k)):
        L.append(f"| `{t}` | {m} | {ex[(t, m, 'UNWANTED')]} | {ex[(t, m, 'DUPLICATE')]} | {ex[(t, m, 'REJECTED')]} |")

    # tool errors
    L += ["", "## Errors the tools returned", "", "| tool | model | error | times |", "|---|---|---|---|"]
    ec = Counter((e["tool"], e["model"], e["msg"]) for e in errs)
    for (t, m, msg), v in ec.most_common(12):
        L.append(f"| `{t}` | {m} | {msg.replace('|', '/')} | {v} |")

    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def group(items, keys):
    g = defaultdict(list)
    for x in items:
        g[tuple(x[k] for k in keys)].append(x)
    return g


if __name__ == "__main__":
    main(sys.argv[1:])
