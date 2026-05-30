"""
Rejection rate benchmark.

For each generator type and grid size, runs MAX_TRIALS "find one level" trials.
Each trial calls gen.generate() (max_attempts=1) in a loop until one level is
accepted or MAX_ATTEMPTS_PER_TRIAL is exceeded.

This directly measures:
  - mean number of attempts needed to find one accepted level
  - mean time to find one accepted level

The rejection rate is derived as (mean_attempts - 1) / mean_attempts.

Results saved to results/rejection_benchmark/.
"""

import json
import multiprocessing as mp
import os
import queue as _queue
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark._plot_style import DEFAULT_BAR_ALPHA, apply_thesis_style
from generators.constructive import ConstructiveGenerator
from generators.cooperative import CooperativeGenerator
from generators.level6_style import Level6StyleGenerator
from generators.random import (
    ConstrainedRandomCooperativeGenerator,
    RandomGenerator,
)

apply_thesis_style()

# Human-readable labels for the legend (no underscores, no jargon).
GENERATOR_LABELS = {
    "random": "Random (geom-validated)",
    "constrained_random_cooperative": "Random (geom-validated) + cooperation",
    "constructive": "Constructive (solvable)",
    "cooperative": "Constructive (cooperative)",
    "level6_style": "Constructive (Level-6 style)",
}

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

MAX_TRIALS = 200                    # number of accepted levels to find per (generator, size)
MAX_TRIALS_LARGE = 20               # reduced target for large grids (memory-leak-bound)
MAX_ATTEMPTS_PER_TRIAL = 500        # give up on a single trial after this many attempts
MAX_ATTEMPTS_PER_TRIAL_LARGE = 100  # faster give-up for large grids
TRIAL_TIMEOUT_LARGE = 30.0          # seconds: abort a large-grid trial if it exceeds this

# Base RNG seed for the generators, fixed for reproducibility (override with the
# REJECTION_SEED env var). Each generator instance is seeded with this value.
BASE_SEED = int(os.environ.get("REJECTION_SEED", "20260530"))

CONFIGS = [
    # (rows, cols, agents, lasers, is_large)
    (3, 3, 2, 1, False),
    (5, 5, 3, 2, False),
    (8, 8, 4, 3, True),
]

GENERATOR_SPECS = {
    "random": RandomGenerator,                 # was constrained_random_solvable
    "constrained_random_cooperative": ConstrainedRandomCooperativeGenerator,
    "constructive": ConstructiveGenerator,     # was constructive_solvable
    "cooperative": CooperativeGenerator,       # was constructive_cooperative
    "level6_style": Level6StyleGenerator,      # was constructive_level6_style
}

OUTPUT_DIR = Path(
    os.environ.get(
        "REJECTION_OUTPUT_DIR",
        str(Path(__file__).parent.parent.parent / "results" / "rejection_benchmark"),
    )
)

# (generator, size) combos to skip, e.g. ones that SIGSEGV the LLE C extension.
# Controlled via env so it can be set between resume runs without editing code:
#   REJECTION_SKIP="constrained_random_cooperative:8x8,other:5x5"
SKIP_COMBOS = set()
for _combo in os.environ.get("REJECTION_SKIP", "").split(","):
    _combo = _combo.strip()
    if ":" in _combo:
        _g, _s = _combo.split(":", 1)
        SKIP_COMBOS.add((_g.strip(), _s.strip()))

# Run each generation attempt in a respawnable worker subprocess so a native
# crash (a SIGSEGV in the pysat/Minisat C extension, see reproduce_lle_segfault*)
# only kills the worker, not the whole benchmark. On a crash we discard that one
# candidate and resample with a fresh seed. Default on; set REJECTION_ISOLATE=0
# to run generation in-process (faster, but a single crash aborts the run).
ISOLATE = os.environ.get("REJECTION_ISOLATE", "1") not in ("0", "false", "False", "")


# ---------------------------------------------------------------------------
# Generator factory
# ---------------------------------------------------------------------------

def _make_generator(cls, rows, cols, agents, lasers):
    """Create generator with max_attempts=1 so each generate() call = one attempt."""
    t_max = min(max(rows * cols // 2, 8), 20)
    common = dict(
        size=(rows, cols),
        agents=agents,
        lasers=lasers,
        t_max=t_max,
        max_attempts=1,
        seed=BASE_SEED,
    )
    try:
        return cls(**common)
    except (ValueError, TypeError):
        try:
            return cls(size=(rows, cols), agents=agents, lasers=lasers, t_max=t_max, max_attempts=1)
        except Exception:
            return None


def _gen_kwargs(rows, cols, agents, lasers):
    """Constructor kwargs for a single-attempt generator (seed added per spawn)."""
    t_max = min(max(rows * cols // 2, 8), 20)
    return dict(
        size=(rows, cols),
        agents=agents,
        lasers=lasers,
        t_max=t_max,
        max_attempts=1,
    )


# ---------------------------------------------------------------------------
# Crash-isolated generation (subprocess worker + respawn-on-crash)
# ---------------------------------------------------------------------------

def _construct_generator(gen_cls, kwargs):
    """Build a generator, tolerating classes that do not accept a seed kwarg."""
    try:
        return gen_cls(**kwargs)
    except (ValueError, TypeError):
        return gen_cls(**{k: v for k, v in kwargs.items() if k != "seed"})


def _isolated_attempt_worker(gen_cls, gen_kwargs, cmd_q, res_q):
    """Worker process: build one generator, run generate() once per 'go' message.

    A native crash (SIGSEGV in the pysat/Minisat C extension) terminates this
    process outright -- it cannot be caught with try/except. The parent detects
    the dead worker, counts the in-flight candidate as a crash, and respawns a
    fresh worker with a new seed so it does not replay the crashing candidate.
    """
    try:
        gen = _construct_generator(gen_cls, gen_kwargs)
    except Exception as exc:  # generator could not be constructed at all
        try:
            res_q.put(("init_error", f"{type(exc).__name__}: {exc}"))
        except Exception:
            pass
        return

    while True:
        try:
            msg = cmd_q.get()
        except (EOFError, OSError):
            return
        if msg == "stop":
            return
        try:
            gen.generate()
            res_q.put(("accepted",))
        except RuntimeError:
            res_q.put(("rejected",))
        except Exception as exc:  # python-level error: treated as a rejection upstream
            res_q.put(("error", f"{type(exc).__name__}: {exc}"))


def _run_isolated_cell(gen_cls, gen_kwargs, base_seed, trials, max_att, timeout, log):
    """Run one (generator, grid-size) cell with each attempt isolated in a
    respawnable subprocess.

    Returns (attempts_per_level, times_per_level, failed_trials, crashed_attempts).
    """
    attempts_per_level: list[int] = []
    times_per_level: list[float] = []
    failed_trials = 0
    crashed_attempts = 0
    spawn_count = 0
    state = {"worker": None, "cmd_q": None, "res_q": None}

    def _spawn():
        nonlocal spawn_count
        cmd_q = mp.Queue()
        res_q = mp.Queue()
        kw = dict(gen_kwargs)
        if base_seed is not None:
            kw["seed"] = base_seed + spawn_count
        worker = mp.Process(
            target=_isolated_attempt_worker,
            args=(gen_cls, kw, cmd_q, res_q),
            daemon=True,
        )
        worker.start()
        spawn_count += 1
        state.update(worker=worker, cmd_q=cmd_q, res_q=res_q)

    def _kill():
        worker = state["worker"]
        if worker is not None:
            try:
                if worker.is_alive():
                    worker.terminate()
                worker.join(timeout=2)
            except Exception:
                pass
        state.update(worker=None, cmd_q=None, res_q=None)

    _spawn()
    try:
        for trial in range(trials):
            attempts = 0
            t_start = time.perf_counter()
            found = False
            timed_out = False

            while attempts < max_att:
                if timeout and (time.perf_counter() - t_start) > timeout:
                    timed_out = True
                    break
                attempts += 1
                if attempts % 50 == 0:
                    log(
                        f"    trial {trial+1}/{trials}: {attempts} attempts "
                        f"({time.perf_counter()-t_start:.1f}s)..."
                    )
                if state["worker"] is None or not state["worker"].is_alive():
                    _spawn()
                state["cmd_q"].put("go")

                res = None
                while True:
                    if timeout and (time.perf_counter() - t_start) > timeout:
                        timed_out = True
                        break
                    try:
                        res = state["res_q"].get(timeout=0.5)
                        break
                    except _queue.Empty:
                        if not state["worker"].is_alive():
                            break  # crashed mid-attempt, no result produced

                if timed_out:
                    break
                if res is None:
                    crashed_attempts += 1
                    log(
                        f"      attempt {attempts}: worker crashed (SIGSEGV); "
                        f"discarding candidate and respawning (crashes={crashed_attempts})"
                    )
                    _kill()
                    _spawn()
                    continue  # crashed candidate counts as one (failed) attempt
                tag = res[0]
                if tag == "accepted":
                    found = True
                    break
                if tag in ("rejected", "error"):
                    continue
                if tag == "init_error":
                    log(f"      worker init failed: {res[1]}")
                    return attempts_per_level, times_per_level, trials, crashed_attempts

            t_elapsed = time.perf_counter() - t_start
            if found:
                attempts_per_level.append(attempts)
                times_per_level.append(t_elapsed)
                mean_so_far = float(np.mean(attempts_per_level))
                log(
                    f"    [{trial+1:>2}/{trials}] OK  attempts={attempts:>4}  "
                    f"time={t_elapsed:.2f}s  mean_attempts={mean_so_far:.1f}  "
                    f"crashes={crashed_attempts}"
                )
            else:
                failed_trials += 1
                reason = f"timeout>{timeout:.0f}s" if timed_out else f">{max_att} attempts"
                log(
                    f"    [{trial+1:>2}/{trials}] FAIL ({reason})  "
                    f"crashes={crashed_attempts}"
                )
    finally:
        worker = state["worker"]
        if worker is not None and worker.is_alive():
            try:
                state["cmd_q"].put("stop")
                worker.join(timeout=2)
            except Exception:
                pass
        _kill()

    return attempts_per_level, times_per_level, failed_trials, crashed_attempts


def _run_inline_cell(gen_cls, gen_kwargs, base_seed, trials, max_att, timeout, log):
    """In-process variant of _run_isolated_cell (no crash isolation)."""
    kw = dict(gen_kwargs)
    if base_seed is not None:
        kw["seed"] = base_seed
    gen = _construct_generator(gen_cls, kw)

    attempts_per_level: list[int] = []
    times_per_level: list[float] = []
    failed_trials = 0
    for trial in range(trials):
        attempts = 0
        t_start = time.perf_counter()
        found = False
        timed_out = False
        while attempts < max_att:
            if timeout and (time.perf_counter() - t_start) > timeout:
                timed_out = True
                break
            attempts += 1
            try:
                gen.generate()
                found = True
                break
            except RuntimeError:
                if attempts % 50 == 0:
                    log(
                        f"    trial {trial+1}/{trials}: {attempts} attempts "
                        f"({time.perf_counter()-t_start:.1f}s)..."
                    )
        t_elapsed = time.perf_counter() - t_start
        if found:
            attempts_per_level.append(attempts)
            times_per_level.append(t_elapsed)
            mean_so_far = float(np.mean(attempts_per_level))
            log(
                f"    [{trial+1:>2}/{trials}] OK  attempts={attempts:>4}  "
                f"time={t_elapsed:.2f}s  mean_attempts={mean_so_far:.1f}"
            )
        else:
            failed_trials += 1
            reason = f"timeout>{timeout:.0f}s" if timed_out else f">{max_att} attempts"
            log(f"    [{trial+1:>2}/{trials}] FAIL ({reason})")
    return attempts_per_level, times_per_level, failed_trials, 0


# ---------------------------------------------------------------------------
# Main benchmark loop
# ---------------------------------------------------------------------------

def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "benchmark_results.json"

    # Resume: load any previously-saved configs.
    results: dict = {}
    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as f:
                results = json.load(f)
            n_saved = sum(len(v) for v in results.values())
            print(f"  Resumed from {json_path}: {n_saved} configs already saved", flush=True)
        except Exception as e:
            print(f"  Warning: could not load existing JSON ({e}); starting fresh", flush=True)
            results = {}

    for gen_name, gen_cls in GENERATOR_SPECS.items():
        if gen_name not in results:
            results[gen_name] = {}
        for rows, cols, agents, lasers, is_large in CONFIGS:
            size_key = f"{rows}x{cols}"
            if (gen_name, size_key) in SKIP_COMBOS:
                print(f"  [{gen_name}] {size_key}: SKIP (listed in REJECTION_SKIP)", flush=True)
                results[gen_name][size_key] = {"skipped": True, "reason": "known SIGSEGV combo"}
                continue
            if "attempts_per_level_raw" in results[gen_name].get(size_key, {}):
                print(f"  [{gen_name}] {size_key}: SKIP (raw data already in JSON)", flush=True)
                continue
            trials = MAX_TRIALS_LARGE if is_large else MAX_TRIALS
            print(f"  [{gen_name}] {size_key} ({agents} agents, {lasers} lasers, {trials} trials) ...", flush=True)

            if _make_generator(gen_cls, rows, cols, agents, lasers) is None:
                print("    -> skipped (generator init failed)")
                results[gen_name][size_key] = {"skipped": True}
                continue

            max_att = MAX_ATTEMPTS_PER_TRIAL_LARGE if is_large else MAX_ATTEMPTS_PER_TRIAL
            timeout = TRIAL_TIMEOUT_LARGE if is_large else None

            gen_kwargs = _gen_kwargs(rows, cols, agents, lasers)

            def _log(msg):
                print(msg, flush=True)

            run_cell = _run_isolated_cell if ISOLATE else _run_inline_cell
            attempts_per_level, times_per_level, failed_trials, crashed_attempts = run_cell(
                gen_cls, gen_kwargs, BASE_SEED, trials, max_att, timeout, _log,
            )

            successful = len(attempts_per_level)
            mean_attempts = float(np.mean(attempts_per_level)) if attempts_per_level else None
            rejection_rate = ((mean_attempts - 1) / mean_attempts) if mean_attempts is not None else None

            if mean_attempts is not None:
                print(
                    f"    done: {successful}/{trials} trials ({failed_trials} failed, "
                    f"{crashed_attempts} crashed attempts), mean attempts={mean_attempts:.1f}, "
                    f"rejection rate={100*rejection_rate:.1f}%"
                )
            else:
                print(
                    f"    done: {successful}/{trials} trials ({failed_trials} failed, "
                    f"{crashed_attempts} crashed attempts) — no data"
                )

            notes = []
            if failed_trials:
                notes.append(f"{failed_trials} trials exhausted budget and are excluded from mean_attempts")
            if crashed_attempts:
                notes.append(f"{crashed_attempts} candidate(s) crashed the SAT C extension and were discarded/resampled")

            results[gen_name][size_key] = {
                "successful_trials": successful,
                "failed_trials": failed_trials,
                "crashed_attempts": crashed_attempts,
                "mean_attempts_per_level": mean_attempts,
                "std_attempts_per_level": float(np.std(attempts_per_level)) if attempts_per_level else None,
                "mean_time_per_level": float(np.mean(times_per_level)) if times_per_level else None,
                "rejection_rate": rejection_rate,
                # Raw per-trial values, kept so the boxplots can be regenerated
                # without re-running the benchmark.
                "attempts_per_level_raw": attempts_per_level,
                "times_per_level_raw": [float(t) for t in times_per_level],
                "note": "; ".join(notes) if notes else None,
            }

            # Incremental save so a crash doesn't lose completed configs.
            json_path = OUTPUT_DIR / "benchmark_results.json"
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"    -> saved partial results to {json_path}", flush=True)

    json_path = OUTPUT_DIR / "benchmark_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {json_path}")

    try:
        _make_plots(results)
    except Exception as e:
        print(f"Warning: plot generation failed: {e}")


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

SOLVABLE_GENS = ["random", "constructive"]
COOPERATIVE_GENS = ["constrained_random_cooperative", "cooperative"]


def _failure_note(data: dict) -> str:
    failed = data.get("failed_trials") or 0
    successful = data.get("successful_trials") or 0
    total = failed + successful
    if failed and total:
        return f"{failed}/{total} failed"
    return ""


def _grouped_boxplot(ax, results, generators, legend_labels, sizes, x, value_fn,
                     raw_key="attempts_per_level_raw"):
    """One coloured box per (generator, grid size) from raw per-trial values.

    raw_key selects which raw array to read (per-trial attempt counts or
    per-trial wall-clock times); value_fn maps each raw value to the plotted
    quantity. Returns legend handles (one coloured patch per generator).
    """
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    n = len(generators)
    width = 0.8 / n
    handles = []
    for i, gen in enumerate(generators):
        offset = (i - (n - 1) / 2) * width
        color = colors[i % len(colors)]
        positions, boxdata = [], []
        for j, s in enumerate(sizes):
            raw = results[gen].get(s, {}).get(raw_key) or []
            vals = [value_fn(a) for a in raw]
            if vals:
                positions.append(x[j] + offset)
                boxdata.append(vals)
        if boxdata:
            bp = ax.boxplot(
                boxdata, positions=positions, widths=width * 0.9,
                patch_artist=True, manage_ticks=False,
                medianprops=dict(color="black", linewidth=1.2),
                whiskerprops=dict(color="black", linewidth=1.0),
                capprops=dict(color="black", linewidth=1.0),
                flierprops=dict(
                    marker="o", markersize=2, markerfacecolor=color,
                    markeredgecolor="black", markeredgewidth=0.3, alpha=0.5,
                ),
            )
            for box in bp["boxes"]:
                box.set(facecolor=color, edgecolor="black", linewidth=0.8)
        handles.append(
            plt.Rectangle(
                (0, 0), 1, 1,
                facecolor=color, edgecolor="black", linewidth=0.8,
                label=legend_labels[i],
            )
        )
    return handles


def _legend_right(ax, handles=None):
    kwargs = dict(loc="center left", bbox_to_anchor=(1.02, 0.5))
    if handles is not None:
        kwargs["handles"] = handles
    ax.legend(**kwargs)


def _make_plots(results: dict):
    sizes = ["3x3", "5x5", "8x8"]
    x = np.arange(len(sizes))

    generators = list(results.keys())
    legend_labels = [GENERATOR_LABELS.get(g, g.replace("_", " ")) for g in generators]

    # --- Plot 1: Rejection rate per generator and grid size, bar ---
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    n = len(generators)
    width = 0.8 / n
    fig, ax = plt.subplots(figsize=(12, 7))
    for i, gen in enumerate(generators):
        rates = [((results[gen].get(s, {}).get("rejection_rate") or 0.0) * 100.0) for s in sizes]
        offset = (i - (n - 1) / 2) * width
        bars = ax.bar(
            x + offset, rates, width,
            label=legend_labels[i],
            color=colors[i % len(colors)],
            edgecolor="black", linewidth=0.8,
        )
        ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=7)
    ax.set_xlabel("Grid size")
    ax.set_ylabel("Rejection rate (\\%)" if plt.rcParams.get("text.usetex") else "Rejection rate (%)")
    ax.set_title("Rejection rate by generator and grid size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.set_ylim(0, 125)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper right")
    ax.grid(axis="y", which="major")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rejection_rate_by_generator.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "rejection_rate_by_generator.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Saved rejection_rate_by_generator.{png,pdf}")

    # --- Plot 2: Mean attempts per accepted level, bar (log scale) ---
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    n = len(generators)
    width = 0.8 / n
    fig, ax = plt.subplots(figsize=(12, 7))
    for i, gen in enumerate(generators):
        attempts = [(results[gen].get(s, {}).get("mean_attempts_per_level") or 1e-6) for s in sizes]
        offset = (i - (n - 1) / 2) * width
        bars = ax.bar(
            x + offset, attempts, width,
            label=legend_labels[i],
            color=colors[i % len(colors)],
            edgecolor="black", linewidth=0.8,
        )
        ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=7)
    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean attempts per accepted level (log scale)")
    ax.set_yscale("log")
    ax.set_ylim(0.9, ax.get_ylim()[1] * 4)
    ax.set_title("Mean attempts per accepted level by generator and grid size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper right")
    ax.grid(axis="y", which="major")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "mean_attempts_per_level.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "mean_attempts_per_level.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Saved mean_attempts_per_level.{png,pdf}")

    # --- Plot 3: Mean wall-clock duration per accepted level, bar (log scale) ---
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    n = len(generators)
    width = 0.8 / n
    fig, ax = plt.subplots(figsize=(12, 7))
    for i, gen in enumerate(generators):
        times = [(results[gen].get(s, {}).get("mean_time_per_level") or 1e-6) for s in sizes]
        offset = (i - (n - 1) / 2) * width
        bars = ax.bar(
            x + offset, times, width,
            label=legend_labels[i],
            color=colors[i % len(colors)],
            edgecolor="black", linewidth=0.8,
        )
        ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=7)
    ax.set_xlabel("Grid size")
    ax.set_ylabel("Mean time to find one accepted level (s, log scale)")
    ax.set_yscale("log")
    ax.set_ylim(1e-3, ax.get_ylim()[1] * 4)
    ax.set_title("Mean time to find one accepted level by generator and grid size")
    ax.set_xticks(x)
    ax.set_xticklabels(sizes)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper right")
    ax.grid(axis="y", which="major")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "time_per_accepted_level.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "time_per_accepted_level.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Saved time_per_accepted_level.{png,pdf}")


if __name__ == "__main__":
    print("=== Rejection Rate Benchmark ===")
    run()
    print("Done.")
