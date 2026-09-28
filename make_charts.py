"""The tool report card's two charts, from out/rows.jsonl. Run from anywhere: python make_charts.py"""
import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = Path(__file__).resolve().parent
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
BAD, GOOD, NEUTRAL = "#e34948", "#2a78d6", "#b9b8b2"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False,
})


def header(fig, title, subtitle, source):
    h = fig.get_figheight()
    fig.text(0.02, 1 - 0.18 / h, title, fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 1 - 0.62 / h, subtitle, fontsize=11.5, color=INK2, va="top")
    fig.text(0.02, 0.02, source, fontsize=9, color=MUTED, va="bottom")


MODELS = [("claude-3-7-sonnet", "Claude 3.7 Sonnet"), ("gpt-4.1-mini", "GPT-4.1-mini"),
          ("gpt-4.1", "GPT-4.1"), ("o4-mini", "o4-mini")]


def toolcard_charts():
    d = HERE / "charts"
    d.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(HERE / "out/rows.jsonl")]
    short = lambda m: m.split("-2025")[0]

    # 1. unwanted cancellations per model (airline): episodes out of 200
    ep = collections.defaultdict(set)
    for r in rows:
        if r["domain"] == "airline" and r["cat"] == "UNWANTED" and r["tool"] == "cancel_reservation":
            ep[short(r["model"])].add((r["task"], r["trial"]))
    data = [(label, len(ep[m])) for m, label in MODELS]
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=200)
    fig.subplots_adjust(left=0.2, right=0.9, top=0.7, bottom=0.16)
    for y, (label, n) in zip(range(len(data))[::-1], data):
        ax.barh(y, 200, height=0.56, color="#efeee9", zorder=1)
        ax.barh(y, n, height=0.56, color=BAD, zorder=2)
        ax.text(n + 3, y, f"{n}", va="center", fontsize=12, fontweight="bold", color=INK)
        ax.text(-3, y, label, va="center", ha="right", fontsize=11.5, color=INK)
    ax.set_xlim(0, 200); ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_xticks([0, 50, 100, 150, 200]); ax.tick_params(axis="x", length=0)
    ax.grid(axis="x", color=GRID, zorder=0); ax.set_axisbelow(True)
    ax.set_xlabel("airline conversations (of 200)", color=INK2, fontsize=10)
    header(fig, "Agents cancel flights nobody asked them to cancel.",
           "Conversations where the agent cancelled a reservation the task did not allow.\n"
           "None of these tasks allows a cancellation in its answer key. The customer pushes, the agent cancels anyway.",
           "tau2-bench published runs (Sierra Research), airline domain, 50 tasks x 4 trials per model. Graded against ground truth, no LLM judge.")
    fig.savefig(d / "unwanted_cancellations.png"); plt.close(fig)

    # 2. per-tool wrong-rate heatmap
    req = [r for r in rows if r["cat"] not in ("DUPLICATE", "UNWANTED", "REJECTED")]
    c = collections.defaultdict(lambda: [0, 0])
    for r in req:
        k = (r["tool"], short(r["model"])); c[k][1] += 1; c[k][0] += r["cat"] != "OK"
    tools = [t for t in sorted({t for t, _ in c}, key=lambda t: -sum(c[(t, m)][0] for m, _ in MODELS) / sum(c[(t, m)][1] for m, _ in MODELS))
             if sum(c[(t, m)][1] for m, _ in MODELS) >= 40]
    grid = [[c[(t, m)][0] / c[(t, m)][1] for m, _ in MODELS] for t in tools]
    cmap = LinearSegmentedColormap.from_list("bad", ["#fbeceb", "#f3a8a4", "#e34948", "#9b1f1f"])
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(tools) + 2.6), dpi=200)
    fig.subplots_adjust(left=0.33, right=0.97, top=1 - 1.75 / (0.5 * len(tools) + 2.6), bottom=0.07)
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=0.8, aspect="auto")
    for i, t in enumerate(tools):
        for j, (m, _) in enumerate(MODELS):
            v = grid[i][j]
            ax.text(j, i, f"{100*v:.0f}%", ha="center", va="center", fontsize=10.5,
                    color="white" if v > 0.45 else INK, fontweight="bold" if v > 0.45 else "normal")
    ax.set_xticks(range(len(MODELS))); ax.set_xticklabels([l for _, l in MODELS], fontsize=10.5)
    ax.xaxis.tick_top(); ax.tick_params(length=0)
    ax.set_yticks(range(len(tools))); ax.set_yticklabels(tools, fontsize=10.5, family="DejaVu Sans Mono")
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, len(MODELS))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(tools))], minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    header(fig, "Which tool calls go wrong, and how often.",
           "Share of required write calls the agent got wrong (wrong arguments, wrong tool, skipped or handed off).\n"
           "Flight booking goes wrong 58 to 72% of the time for every model.",
           "tau2-bench published runs (Sierra Research), airline + retail, 2,624 conversations. Tools with 40+ required calls.")
    fig.savefig(d / "tool_errors.png"); plt.close(fig)


if __name__ == "__main__":
    toolcard_charts()
    print("ok")
