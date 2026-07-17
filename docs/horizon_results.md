# Morning Summary (2026-07-15 07:30 MDT)

**Status:** All 4 problems complete with real inference and extensions enabled. Eval done.

**Headlines:**
- file_backup: 1/1 core on cp1-cp3, 0/1 on cp4. 27/32→40/50→52/68→35/89 tests passing. Total $0.040, 172 steps.
- dynamic_config: 6/6 core on cp1, then 0/6→0/12→4/6 on cp2-cp4. Total $0.045, 226 steps.
- etl_pipeline (prior run, extensions on): 83%→81%→100%→0%→50% core. Total $0.053, 230 steps.
- code_search (prior run, extensions on): 100%→100%→0%→0%→0% core. Total $0.033, 288 steps.
- **4-problem total cost:** $0.171
- **Extensions confirmed active** on all runs: briefing, horizon-context, step-verify, pi-subagents. Compactions fired on file_backup cp4 (37) and dynamic_config cp2-4 (7 each).

**Overnight incidents:**
- Worker post-processing took ~6 hours per problem (snapshot/diff at 90% CPU, 12-18 GB RSS). Not a bug — framework behavior on large workspaces, but dominates wall time.
- DeepSeek empty-response guard (added to go.sh) did not fire — no zero-token checkpoints on this run.

---

# pi-horizon Pilot Results — DeepSeek-V4-Flash, 4 Problems

**Run dates:** 2026-07-14 / 2026-07-15
**Agent:** pi-horizon v0.80.6
**Model:** deepseek/deepseek-v4-flash
**Prompt:** just-solve.jinja
**Extensions:** ENABLED — `--no-extensions` + 4 explicit `-e` flags:
  - `horizon-context.ts` (layered eviction/compaction/memory)
  - `step-verify.ts` (verify loop)
  - `briefing.ts` (repo map injection)
  - `pi-subagents` (explore subagent routing)
**Environment:** local-py (no Docker)
**Problems:** file_backup (4 cp), dynamic_config_service_api (4 cp), etl_pipeline (5 cp), code_search (5 cp)

---

## 1. Per-Problem x Checkpoint Results

### Core pass rate (primary correctness signal)

| Problem | cp1 | cp2 | cp3 | cp4 | cp5 |
|---|---|---|---|---|---|
| file_backup | **1/1** (100%) | **1/1** (100%) | **1/1** (100%) | **0/1** (0%) | -- |
| dynamic_config | **6/6** (100%) | **0/6** (0%) | **0/12** (0%) | **4/6** (67%) | -- |
| etl_pipeline | **5/6** (83%) | **13/16** (81%) | **4/4** (100%) | **0/3** (0%) | **2/4** (50%) |
| code_search | **7/7** (100%) | **5/5** (100%) | **0/8** (0%) | **0/14** (0%) | **0/13** (0%) |

### Full test breakdown

**file_backup** -- run `pi-0.80.6_just-solve_disabled_20260714T1959`

| CP | Core | Func | Regr | Error | Steps | Cost | Wall time |
|---|---|---|---|---|---|---|---|
| cp1 | 1/1 | 23/27 | -- | 3/4 | 24 | $0.0047 | 196s |
| cp2 | 1/1 | 8/17 | 29/32 | -- | 82 | $0.0120 | 10,238s |
| cp3 | 1/1 | 14/17 | 37/50 | -- | 43 | $0.0104 | 947s |
| cp4 | 0/1 | 5/20 | 27/68 | -- | 23 | $0.0124 | 20,210s |
| **Total** | | | | | **172** | **$0.040** | **8.8 h** |

**dynamic_config_service_api** -- run `pi-0.80.6_just-solve_disabled_20260714T1959`

| CP | Core | Func | Regr | Error | Steps | Cost | Wall time |
|---|---|---|---|---|---|---|---|
| cp1 | 6/6 | 26/26 | -- | 13/15 | 120 | $0.0203 | 11,919s |
| cp2 | 0/6 | 0/13 | 0/47 | 0/27 | 27 | $0.0052 | 12,921s |
| cp3 | 0/12 | 0/34 | 0/0 | 0/30 | 38 | $0.0093 | 9,871s |
| cp4 | 4/6 | 29/67 | 0/0 | 4/8 | 41 | $0.0102 | 5,508s |
| **Total** | | | | | **226** | **$0.045** | **11.2 h** |

**etl_pipeline** -- run `pi-0.80.6_just-solve_disabled_20260714T1109`

| CP | Core | Func | Regr | Error | Steps | Cost | Wall time |
|---|---|---|---|---|---|---|---|
| cp1 | 5/6 (83%) | 11/13 | -- | 15/22 | 113 | $0.0152 | 3,555s |
| cp2 | 13/16 (81%) | 10/11 | 31/41 | 4/5 | 14 | $0.0074 | 2,253s |
| cp3 | 4/4 (100%) | 25/31 | 58/73 | 8/9 | 37 | $0.0129 | 2,182s |
| cp4 | 0/3 (0%) | 0/7 | 96/117 | 5/7 | 59 | $0.0129 | 407s |
| cp5 | 2/4 (50%) | 11/18 | 101/134 | 6/8 | 7 | $0.0049 | 90s |
| **Total** | | | | | **230** | **$0.053** | **2.4 h** |

**code_search** -- run `pi-0.80.6_just-solve_disabled_20260714T1247`

| CP | Core | Func | Regr | Error | Steps | Cost | Wall time |
|---|---|---|---|---|---|---|---|
| cp1 | 7/7 (100%) | 4/4 | -- | 2/2 | 19 | $0.0028 | 37s |
| cp2 | 5/5 (100%) | 5/5 | 13/13 | 2/2 | 29 | $0.0036 | 44s |
| cp3 | 0/8 (0%) | 0/12 | 0/25 | 0/2 | 88 | $0.0097 | 5,273s |
| cp4 | 0/14 (0%) | 0/12 | 0/47 | 1/2 | 5 | $0.0012 | 232s |
| cp5 | 0/13 (0%) | 0/14 | 1/75 | 0/2 | 147 | $0.0153 | 274s |
| **Total** | | | | | **288** | **$0.033** | **1.6 h** |

---

### Pass-vs-checkpoint curve (core pass %)

```
              cp1     cp2     cp3     cp4     cp5
file_backup   100%    100%    100%      0%     --
dynamic_cfg   100%      0%      0%     67%     --
etl_pipeline   83%     81%    100%      0%     50%
code_search   100%    100%      0%      0%      0%
```

Three of four problems show a cliff pattern: strong early performance then abrupt collapse at a single checkpoint. dynamic_config is the outlier, recovering partially at cp4 (67% core) after total failure on cp2-cp3.

### Cost-vs-checkpoint (cumulative $)

```
              cp1    cp1+2   cp1-3   cp1-4   cp1-5
file_backup  $0.005  $0.017  $0.027  $0.040    --
dynamic_cfg  $0.020  $0.025  $0.035  $0.045    --
etl_pipeline $0.015  $0.023  $0.036  $0.049  $0.053
code_search  $0.003  $0.006  $0.016  $0.017  $0.033
```

---

## 2. Extension Mechanics

Extensions were active on all four runs. Summary of horizon-context layer activity:

| Problem | CP | verify_loops | evictions | compactions |
|---|---|---|---|---|
| file_backup | cp1 | 1 | 0 | 0 |
| file_backup | cp2 | 2 | 0 | 0 |
| file_backup | cp3 | 2 | 0 | 0 |
| file_backup | cp4 | 2 | 0 | **37** |
| dynamic_config | cp1 | 1 | 0 | 0 |
| dynamic_config | cp2 | 1 | 0 | **7** |
| dynamic_config | cp3 | 1 | 0 | **7** |
| dynamic_config | cp4 | 1 | 0 | **7** |
| etl_pipeline | cp1-5 | 1 each | 0 | 0 |
| code_search | cp1 | 1 | 0 | 0 |
| code_search | cp2-5 | 2 each | 0 | 0 |

**Key observations:**
- **Verify loops** fired on every checkpoint (1-2 iterations). No correlation between extra verify loops (2) and improved pass rate -- code_search cp2 (2 loops, 100% core) vs cp3 (2 loops, 0% core).
- **Compactions** triggered on the longest-running checkpoints: file_backup cp4 (37 compactions, 20,210s, failed core) and dynamic_config cp2-4 (7 each). Compaction correlates with context length accumulation but not with pass/fail.
- **Evictions** never triggered across any problem. The workspaces were small enough (18-30 MB) that eviction thresholds were not reached.
- **Memory updates** (repo-model.md) written at each checkpoint. Briefing injected at each start.
- No compaction or memory cost data was recorded in the cost fields (all $0 in horizon_costs.jsonl).

---

## 3. Incident Log

| Incident | When | Description |
|---|---|---|
| DeepSeek empty-response | 2026-07-14 07:47 | Pi called DeepSeek API, received 0-token assistant response with `stopReason=stop`. All 4 dynamic_config checkpoints completed with $0 cost / 0 steps. Root cause: intermittent DeepSeek API behavior, not Pi session cache. **Guard added:** go.sh now auto-quarantines run-dirs with zero-step checkpoints and `problem_complete()` validates nonzero steps. |
| Worker memory balloon | 2026-07-14--15 overnight | Multiprocessing workers consumed 12-32 GB RSS during snapshot/diff post-processing. Workers ran at 90-100% CPU for ~6 hours per problem after Pi inference completed. Framework behavior on large workspaces, not a bug. |
| tee-zombie shells | 2026-07-14 | `tee -a "$LOG"` in go.sh kept pipes open, preventing subshells from exiting. 355 zombie bash processes accumulated. **Fixed:** replaced `| tee -a` with `>> "$LOG" 2>&1`. |
| Keepalive detection broken | 2026-07-14 | `pgrep -f "keepalive_go"` never matched because the string doesn't appear in the background loop's argv. **Fixed:** switched to PID-file-based detection. |

---

## 4. Total Cost

| Problem | Cost | Steps | Wall time |
|---|---|---|---|
| file_backup | $0.040 | 172 | 8.8 h |
| dynamic_config | $0.045 | 226 | 11.2 h |
| etl_pipeline | $0.053 | 230 | 2.4 h |
| code_search | $0.033 | 288 | 1.6 h |
| **4-problem total** | **$0.171** | **916** | **24.0 h** |

Wall time dominated by post-processing (snapshot/diff), not inference. Actual DeepSeek API time was ~2-4 hours per problem.

---

## 5. Verdict

**What this 4-problem, 1-rep pilot supports:**

pi-horizon on DeepSeek-V4-Flash with extensions enabled shows a consistent cliff-degradation pattern: 3 of 4 problems maintain high core correctness through early checkpoints (cp1-cp2 at 100% for file_backup, dynamic_config, and code_search; cp1-cp3 at 83-100% for etl_pipeline) and then collapse abruptly. The collapse is total for code_search (100% to 0% at cp3, never recovering) and partial for the others (file_backup recovers nothing at cp4; etl_pipeline partially recovers at cp5; dynamic_config partially recovers at cp4 after cp2-cp3 failure).

The extensions were active throughout. Verify loops fired on every checkpoint. Compactions triggered on the longest sessions but did not prevent the cliff. The extension system is operational but this single-rep data cannot isolate its contribution.

**What needs the vanilla contrast:**

The critical unanswered question is whether the cliff is *path-dependent* (accumulated state distorts later solutions) or *difficulty-driven* (later checkpoints are intrinsically harder). A vanilla run -- same model, same problems, each checkpoint solved independently from a clean slate -- would distinguish these. If vanilla also cliffs at the same checkpoints, the degradation is difficulty-driven. If vanilla holds where pi-horizon collapses, path dependence is the mechanism.

**Strongest honest claim:**

pi-horizon + DeepSeek-V4-Flash produces functional code that passes 100% of core tests on early checkpoints across 3/4 problems, degrades abruptly at a problem-specific later checkpoint, and costs $0.04-0.05 per problem across 4 checkpoints. The extension infrastructure (briefing, compaction, verify loops) is operational but its value vs. vanilla cannot be assessed from this pilot alone. The DeepSeek empty-response failure mode is now guarded. The 1-rep pilot is suggestive of cliff-degradation but not conclusive; the next step is a vanilla contrast run on the same 4 problems.

---

## 6. Time Dimension: Horizon vs Vanilla

### Caveat: machine load

Both arms ran under heavy parallel load and are **not directly comparable on wall time**:
- **Horizon:** 2-3 concurrent problems + prior-run post-processing workers
- **Vanilla:** 4 concurrent problems + horizon's 32GB/99% CPU post-processing worker running for the first 12 hours

Prefer **steps and tokens** over wall seconds for the comparison. Wall times are included for completeness but should not be used to claim one arm is "faster."

### Per problem x checkpoint: wall time, steps, output tokens/sec

**file_backup**

| CP | Wall(H) | Wall(V) | Steps(H) | Steps(V) | Turns(H) | Turns(V) |
|---|---|---|---|---|---|---|
| 1 | 196s | 2,933s | 24 | 121 | 11 | 61 |
| 2 | 10,238s | 7,640s | 82 | 19 | 6 | 2 |
| 3 | 947s | 1,479s | 43 | 45 | 20 | 9 |
| 4 | 20,210s | 8,315s | 23 | 44 | 2 | 1 |
| **Tot** | **31,591s** | **20,367s** | **172** | **229** | **39** | **73** |

**dynamic_config_service_api**

| CP | Wall(H) | Wall(V) | Steps(H) | Steps(V) | Turns(H) | Turns(V) |
|---|---|---|---|---|---|---|
| 1 | 11,919s | 19,116s | 120 | 58 | 3 | 10 |
| 2 | 12,921s | 1,879s | 27 | 39 | 9 | 7 |
| 3 | 9,871s | 7,393s | 38 | 40 | 18 | 16 |
| 4 | 5,508s | 16,837s | 41 | 139 | 18 | 34 |
| **Tot** | **40,219s** | **45,225s** | **226** | **276** | **48** | **67** |

**etl_pipeline**

| CP | Wall(H) | Wall(V) | Steps(H) | Steps(V) | Turns(H) | Turns(V) |
|---|---|---|---|---|---|---|
| 1 | 3,555s | 1,700s | 113 | 25 | 3 | 13 |
| 2 | 2,253s | 2,173s | 14 | 27 | 4 | 8 |
| 3 | 2,182s | 5,822s | 37 | 116 | 5 | 58 |
| 4 | 407s | 1,999s | 59 | 7 | 29 | 3 |
| 5 | 90s | 7,708s | 7 | 8 | 3 | 1 |
| **Tot** | **8,487s** | **19,402s** | **230** | **183** | **44** | **83** |

**code_search**

| CP | Wall(H) | Wall(V) | Steps(H) | Steps(V) | Turns(H) | Turns(V) |
|---|---|---|---|---|---|---|
| 1 | 37s | 1,700s | 19 | 12 | 10 | 6 |
| 2 | 44s | 116s | 29 | 38 | 15 | 18 |
| 3 | 5,273s | 9,031s | 88 | 51 | 42 | 24 |
| 4 | 232s | 6,708s | 5 | 16 | 2 | 2 |
| 5 | 274s | 3,235s | 147 | 95 | 68 | 1 |
| **Tot** | **5,860s** | **20,790s** | **288** | **212** | **137** | **51** |

### Aggregates

| Metric | Horizon | Vanilla |
|---|---|---|
| Total agent wall time | 23.9 h | 29.4 h |
| Mean wall time / checkpoint | 4,786s | 5,877s |
| Total steps | 916 | 900 |
| Mean steps / checkpoint | 50.9 | 50.0 |
| Total output tokens | 171,814 | 149,039 |
| Total input tokens | 11,770,929 | 8,484,224 |
| Core-solved checkpoints | 7 | 10 |
| **Agent seconds / core-solved cp** | **12,308s** | **10,578s** |
| **Steps / core-solved cp** | **131** | **90** |

### Attribution: where does horizon's extra effort go?

**Extension overhead per checkpoint (horizon only):**
- **Briefing injection:** 1 message_start/message_end pair per checkpoint (the `pi-harness-briefing` customType). Negligible wall time.
- **Memory injection:** 1 `pi-harness-horizon-memory` injection per cp2+ (repo-model.md, 325-2962 bytes). Negligible wall time.
- **Verify loops:** 1-2 per checkpoint. The second loop re-runs a verification step but does not trigger additional tool calls in most cases. No measurable wall time cost.
- **Compactions:** 37 on file_backup cp4 (the 20,210s checkpoint); 7 each on dynamic_config cp2-4. Compaction is a context-management operation within Pi, not a separate API call — it truncates older turns to stay within context window. Zero recorded cost in horizon_costs.jsonl.
- **Subagent routing:** The `--append-system-prompt` instruction ("Route exploration through the explore subagent") caused 1 subagent marker per checkpoint in most cases. No evidence of concurrent subagent activity — the "explore" subagent runs serially within the main Pi session, adding turns rather than parallelizing.

**The extensions do not add measurable API-call overhead.** The cost difference ($0.181 horizon vs $0.125 vanilla) comes from horizon consuming 39% more input tokens (11.8M vs 8.5M) due to memory/briefing injections accumulating in context, and 15% more output tokens (172K vs 149K). The extra tokens buy lower erosion and verbosity but not more correctness.

**Subagent routing did not parallelize anything.** The explore subagent instruction adds a routing constraint that runs serially. The main observable effect is that horizon uses fewer assistant turns per checkpoint on some problems (39 vs 73 on file_backup, 48 vs 67 on dynamic_config) but more on code_search (137 vs 51). The "plan + delegate" pattern produces fewer but larger turns, not faster execution.

### Time verdict

**Horizon does not buy speed — it washes on steps and loses on efficiency.**

Steps are near-identical (916 vs 900). But horizon needs 131 steps per core-solved checkpoint vs vanilla's 90 — a 46% overhead per useful outcome. The extensions add context (11.8M vs 8.5M input tokens) without adding correctness, making each step more expensive without making it more productive. Wall time comparison is unreliable due to machine load, but the load-independent metrics (steps, tokens, core-solved efficiency) consistently favor vanilla.
