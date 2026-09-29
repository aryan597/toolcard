# toolcard: which tools agents get wrong, and how

Pass rates tell you *that* an agent failed. This tells you **which tool, what went wrong, and how often**, graded exactly against ground truth with no LLM judge.

Data: the published τ²-bench runs from Sierra Research. That's 4 models (Claude 3.7 Sonnet, GPT-4.1, GPT-4.1-mini, o4-mini) on the airline and retail domains, 4 trials each, **2,624 episodes**. None of this data is ours; the grader is.

## Findings

![Agents cancel flights nobody asked them to cancel](charts/unwanted_cancellations.png)

![Which tool calls go wrong, and how often](charts/tool_errors.png)

**1. Same score, different danger.**
On airline, Claude 3.7 Sonnet fails 98/200 and o4-mini fails 81/200. But **50 of Claude's failures include an irreversible write nobody asked for** (41 are cancelled reservations), against 16 for o4-mini, which hands off to a human instead. A leaderboard ranks these as close. Operationally they're very different.

| airline | failed episodes | with an unwanted irreversible write | unwanted cancellation |
|---|---|---|---|
| Claude 3.7 Sonnet | 98/200 | 50 | 41 |
| GPT-4.1-mini | 89/200 | 41 | 40 |
| GPT-4.1 | 84/200 | 29 | 24 |
| o4-mini | 81/200 | 16 | 11 |

**2. Agents cancel when the user pushes.**
In the tasks behind these cancellations, the answer key says *"Agent does not cancel any reservation"* because policy doesn't allow it. The simulated user insists, and the agent cancels anyway. It happened in 15 of 50 airline tasks for GPT-4.1-mini.

**3. `book_reservation` is the hardest tool for every model: 28 to 42% correct.** The usual cause is a wrong `payment_methods` or `passengers` argument, not a wrong tool.

**4. Bag fees get charged wrongly.** `update_reservation_baggages` is 29 to 54% correct. The most common wrong argument is `nonfree_baggages`: the agent charges for bags that should have been free, or the reverse.

**5. Item swaps pick the wrong product variant.** In exchanges and order modifications, `new_item_ids` is the most common wrong argument for every model.

Full tables (per tool × model, which argument, unwanted writes, tool errors): [`out/REPORT.md`](out/REPORT.md).

## How it grades

For every tool τ²-bench marks as `WRITE` in its source (`@is_tool(ToolType.WRITE)`), each required call is classified as:

| category | meaning |
|---|---|
| OK | right tool, right arguments (respecting τ²'s `compare_args`) |
| WRONG_ARGS | right tool, wrong arguments; we name which one |
| WRONG_TOOL | a different write on the same order or reservation |
| HANDED_OFF | not done; the agent transferred to a human |
| MISSED | not done |

Writes the task didn't ask for are **UNWANTED**. Identical repeats are **DUPLICATE**. Writes the tool refused with an error are **REJECTED** (no side effect, so they aren't counted as failures).

**Which tools are writes.** τ²-bench's result files don't say which tools are writes, so `--tau2 <checkout>` reads it from τ²-bench's source. Without it, a built-in list is used (6 airline and 7 retail writes, matching the source as of Sept 2026). Either way, if the data contains a tool the grader doesn't know, the run stops with an error instead of silently skipping it.

**List order.** Lists like the item ids in a return are compared as unordered. We checked this instead of assuming it: comparing them in order (`--ordered`) flags 125 of the 1,835 runs τ²-bench marks correct, against 65 unordered, and every extra flag is an `item_ids` order difference on `return_delivered_order_items` that doesn't change the database.

## Is it accurate?

Checked against τ²-bench's own database check:
- **789 of 789** episodes the benchmark marks as failed are explained by a specific write-tool error.
- **65 of 1,835** episodes the benchmark marks as correct get flagged (3.5%). By hand, these are real differences from the answer key that happen not to change the final database: repeating the same address change, a different payment method on a £0 bag change, or answer-key writes that are no-ops.

Rates carry 95% Wilson intervals. Trials repeat the same tasks, so intervals are optimistic.

## What we know

| Claim | Evidence | Status | Limits |
|---|---|---|---|
| The grader explains every benchmark failure | 789 of 789 failed runs have a named write error | Measured | Only τ²-bench airline and retail, only these 4 models |
| It rarely flags correct runs | 65 of 1,835 (3.5%), checked by hand | Measured | "By hand" means one person read them |
| Every write tool is graded | Coverage check fails on unknown tools; built-in list matches τ²-bench source; tests | By construction | A tool τ²-bench mislabels as READ would be skipped, as in τ² itself |
| Ignoring list order is right for this data | Ordered comparison adds 60 flags, all on runs τ²-bench marks correct | Measured | Checked on this data only. A new domain where order matters needs `--ordered` |
| Claude 3.7 Sonnet made more unwanted cancellations than o4-mini (41 vs 11 of 200 airline runs) | rows.jsonl | Measured | Simulated users, mid-2025 models, 4 trials of the same 50 tasks |
| Agents cancel because the user pushes | The tasks behind the cancellations have a pushing user | Observed, not isolated | τ²'s users vary how hard they push. Isolating it is [ask-or-act v2](https://github.com/aryan597/ask-or-act) |


## Limits

- Simulated users (GPT-4.1), not real customers.
- Two domains.
- Models from mid-2025.
- The same grader runs on any τ²-bench results file, including new runs, e.g. local Qwen via LiteLLM.

## Run

```
git clone https://github.com/sierra-research/tau2-bench
python toolcard.py --tau2 tau2-bench tau2-bench/data/tau2/results/final/*_airline_*.json tau2-bench/data/tau2/results/final/*_retail_*.json
python -m pytest tests        # 17 regression tests
```
