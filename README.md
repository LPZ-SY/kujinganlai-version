# Quantum Route Forge

## DeepBlock 比赛前端

完整的项目背景、技术方案、实验设置、真机结果、Web 操作和结论边界见
[`docs/Quantum_Route_Forge_项目完整文档.md`](docs/Quantum_Route_Forge_项目完整文档.md)。

新的比赛入口保留路线地图与参数控制，并把 Baihua DeepBlock 算法隔离在
`src/quantum_route_forge/deepblock/` 中。页面包含路线优化、B1/B2/B3 过程、
Hardware/Random/Simulator/Exact 公平对照以及可重载的本地运行历史。

```powershell
python app.py --port 8050
```

旧研究前端完整保留，使用独立端口启动：

```powershell
python app_research.py --port 8051
```

Hardware 模式默认只做 dry-run。只有在页面明确勾选真实提交确认后才会提交
Baihua 任务；真机失败返回 `FAILED` 或 `NOT_EVALUABLE`，不会回退并伪装为
hardware。比赛历史保存在 `results/competition_history/`。

`LPZ-SY/kujinganlai-version` is a reproducible research and demonstration platform for quantum-seeded fleet assignment and classical route refinement.

The project makes a deliberately narrow claim: real-hardware measurements can be evaluated as assignment candidates, compared with random and same-budget classical candidates, and tested for incremental contribution to a shared hybrid pipeline. It does **not** claim universal quantum advantage, speed advantage, or a pure-quantum solution of the complete vehicle-routing problem.

## What the system does

The production path has two layers:

1. A frozen QAOA-style proximity circuit produces a two-vehicle partition seed. The circuit uses fixed `gamma=1.1` and `beta=0.8`; it is not a direct QAOA encoding of the complete assignment BQM.
2. The shared BQM evaluator scores the seed, while the single-run product path uses it as a soft preference before classical simulated annealing, capacity repair, nearest-neighbor routing, and 2-opt.

Accordingly, the value displayed as **Classical full-assignment energy** in Single Run is the final classical BQM-search energy. It is never described as raw quantum-candidate energy.

## Repository structure

```text
app.py                                  Four-tab Dash experiment platform
run_cli.py                              Compatible single-run CLI
experiments/
  configs/qrf_hw_quality_v2.json        Historical unbalanced/auto matrix (audit only)
  configs/formal_hardware_matrix_v2.json Frozen balanced 4x3x2 protocol
  run_quantum_candidate_quality.py      CSV compatibility CLI using schema-v2 thresholds
  run_quarkstudio_candidate_quality.py  Single live/replay closed loop
  batch_candidate_quality.py            Resumable, quota-aware batch runner
  validate_formal_result_store.py       Strict task/evidence/provenance validator
  prepare_hybrid_input.py               Reproducible task-level fair-pool input builder
  hybrid_contribution.py                Fair C / C+R / C+Q comparison
  generate_paper_artifacts.py           Tables, CDFs, hit rates, convergence, conclusions
src/quantum_route_forge/
  models.py                             Shared serializable measurement/candidate/summary models
  quantum_measurements.py               Counts parsing, shots, bit order, source, evidence hashes
  candidate_quality.py                  Exact reference, dual thresholds, three quality gates
  result_store.py                       Immutable config and idempotent experiment artifacts
  quafu_bridge.py                       Existing SQC/SDK networking wrapped by shared models
  pipeline.py                           Compatible hybrid single-run pipeline
tests/                                  Offline unit, integration, replay, batch, fairness, UI tests
docs/
  current_state_audit.md                Frozen baseline audit
  baseline_manifest.json                Baseline hashes and replay result
  formal_experiment_protocol.md         Frozen matrix protocol and submission gates
  formal_24_task_dry_run.json           Exact 24-task manifest; no hardware access
  cross_backend_smoke_report.md         P10 Baihua/Dongling/Shenglian evidence report
results/experiments/<experiment_id>/    Reproducible experiment stores
```

## Installation

Python 3.12 is the validated runtime.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Offline tests, evidence replay, candidate analysis, dry runs, and history inspection require no token and no network access.

## Dash experiment platform

```powershell
.\.venv\Scripts\python.exe app.py --port 8050
```

Open `http://127.0.0.1:8050`.

The application provides four tabs:

- **Single Run** — defaults to a feasible 8-customer, 2-vehicle classical scenario; shows requested/actual backend, task ID, source, requested/received shots, capacity, and quantum coverage. Incomplete, replay, manual, or fallback measurements are explicitly not evaluable for formal statistics.
- **Candidate Quality** — preserves fresh-hardware versus replay provenance, evaluates complete counts, and displays absolute quality, random reference, classical-threshold reach, strict improvement, exact gap, and feasibility separately.
- **Batch Experiment** — previews the fixed-backend formal matrix, verifies its frozen threshold hash, caps the UI at one fresh task per invocation, requires an explicit confirmation checkbox, and supports resume/pause.
- **Experiment History** — lists task-level instance/backend/status/source provenance with dedicated filters and the result-store integrity state.

Manual bitstrings are always labeled `manual_debug` and are excluded from formal hardware statistics.

## Single-run CLI

Classical mode needs no token:

```powershell
.\.venv\Scripts\python.exe run_cli.py --mode classical --customers 8 --vehicles 2 --capacity 13 --seed 2026
```

Quantum submit through SQC uses the browser JWT access token:

```powershell
$env:QUAFU_API_TOKEN="<JWT>"
$env:QUAFU_BASE_URL="https://quafu-sqc.baqis.ac.cn/"
.\.venv\Scripts\python.exe run_cli.py --mode quantum --customers 8 --vehicles 2 --capacity 13 --quafu-wait false
```

The token is used in memory and is never written to evidence, manifests, or logs.

## Unified measurement model

Every adapter converts its result to `QuantumMeasurementResult`:

- `source`: `hardware`, `simulator`, `replay`, `manual_debug`, or `fallback`;
- task status, task ID, platform, backend, endpoint;
- requested and received shots;
- complete cleaned counts and derived most-frequent bitstring;
- selected customer order and `bit_order`;
- circuit/payload hashes, timestamps, evidence path, warnings.

Counts parsing supports nested payloads, JSON/Python-literal strings, count dictionaries, and probability dictionaries. Invalid keys and bit lengths are rejected. A received-shot mismatch is preserved as a warning and rates use `shots_received`, never the requested value. If an adapter exposes only one sample, the result explicitly records `shots_received=1` instead of fabricating a distribution.

Formal summaries accept only completed `hardware` measurements. Replay remains fully evaluable but visibly labeled as replay.

## Candidate-quality criteria

Thresholds are frozen before a hardware result is read. Schema v2 stores both classical diagnostics:

- `best_classical_energy_all`: minimum energy among all same-budget classical candidates;
- `best_classical_energy_feasible`: minimum energy among raw-feasible same-budget classical candidates.

If the fixed classical budget contains no feasible candidate, the feasible reach gate is `NOT_EVALUABLE`; it never falls back to an infeasible threshold.

For a measured candidate `z`:

```text
normalized_score(z) = (E(z) - E*) / (E_random_median - E*)
quality_gate_pass = raw_feasible and normalized_score <= 0.20
near_quality_gate_pass = raw_feasible and normalized_score <= 0.50
classical_reach_feasible_pass = raw_feasible and E(z) <= T_feasible + 1e-9
strict_improvement_feasible_pass = raw_feasible and E(z) < T_feasible - 1e-9
```

If the normalization denominator is zero, normalized fields are `null` and the absolute gate is not evaluable; the exact gap is still reported.

Report interpretation follows this order:

1. Absolute low-energy feasible-region hit rate versus uniform random.
2. Reach of the same-budget frozen feasible-classical threshold.
3. Strict improvement below that threshold.
4. Incremental contribution of C+Q versus the fair C+R control.

Reaching a classical threshold is not rewritten as “quantum beats classical.”

## Single QuarkStudio run or evidence replay

Live run requirements: two vehicles, 100% customer-to-qubit coverage, and shots that are a positive multiple of 1024.

```powershell
$env:QPU_API_TOKEN="<QPU_TOKEN>"
.\.venv\Scripts\python.exe experiments\run_quarkstudio_candidate_quality.py `
  --seed 2026 --customers 4 --vehicles 2 --capacity-pressure medium --shots 1024 `
  --outdir results\single_live
```

Offline replay does not read a token:

```powershell
.\.venv\Scripts\python.exe experiments\run_quarkstudio_candidate_quality.py `
  --seed 2026 --customers 4 --vehicles 2 --shots 1024 `
  --reuse-evidence results\quarkstudio_candidate_quality_validated\task_evidence.json `
  --outdir results\single_replay
```

Missing/failed counts produce a preserved evidence record and `NOT_EVALUABLE`, not fallback-positive output.

## Formal batch experiment

Formal v2 execution completed on 2026-08-02: all 24 predeclared hardware tasks returned 1024/1024 shots, requested and actual backends matched, and the strict validator reported a complete, valid store with zero errors. The preserved evidence is under `results/experiments/qrf_formal_hardware_matrix_v2`; the task-level report is `docs/formal_24_task_report.md`.

Preview the exact matrix and shot budget without submitting:

```powershell
.\.venv\Scripts\python.exe experiments\batch_candidate_quality.py `
  --config experiments\configs\formal_hardware_matrix_v2.json `
  --dry-run
```

The frozen v2 protocol is a balanced `4 instances x 3 fixed backends x 2 repeats = 24 tasks`
matrix. It forbids `backend=auto`, verifies the frozen threshold file and QASM/customer
order hashes, and prints 24 unique task keys without accessing hardware. Live submission also
requires `HEAD` to resolve to the frozen `execution_git_tag`, a clean tracked worktree, and the
protocol-enforced one-task cap.

The completed run used the following guarded one-task submission command after explicit confirmation:

```powershell
.\.venv\Scripts\python.exe experiments\batch_candidate_quality.py `
  --config experiments\configs\formal_hardware_matrix_v2.json `
  --confirm-live --max-hardware-tasks 1
```

Resume without duplicating completed `config_hash` values:

```powershell
.\.venv\Scripts\python.exe experiments\batch_candidate_quality.py `
  --config experiments\configs\formal_hardware_matrix_v2.json `
  --confirm-live --resume --max-hardware-tasks 1
```

Use `--retry-failed` to target failed records and `--reuse-evidence <path>` to exercise the same orchestration/evaluation/storage path offline. Every task is written immediately, so an interrupted run can recover from `tasks.jsonl`.

The historical `qrf_hw_quality_v2.json` is retained for auditability but is not eligible for
formal submission because it used `backend=auto` and did not repeat each fixed instance on
all three chips. The frozen formal v2 matrix contains four predeclared 4/6-customer,
two-vehicle instances, medium/tight capacity pressure, 1024 shots, and two repeats on each
of Baihua, Dongling, and Shenglian. Large 24/48-customer, four-vehicle pages remain
engineering demonstrations and are not mixed with the 100%-coverage main candidate-quality claim.

## Fair hybrid contribution experiment

`experiments/hybrid_contribution.py` compares:

- `C`: `N` classical candidates;
- `C+R`: `N/2` classical plus `N/2` uniform-random candidates;
- `C+Q`: `N/2` classical plus `N/2` measured quantum candidates;
- `Q-only`: diagnostic only.

All groups use the same total budget, evaluator, capacity repair, nearest-neighbor construction, 2-opt rounds, and final selection rule. C+R and C+Q reuse the exact same classical subset; only the added random versus measured-quantum half differs. Missing/non-hardware measured candidates make C+Q `NOT_EVALUABLE` instead of silently degrading to a classical pool. Results include `D_C`, `D_C_plus_R`, `D_C_plus_Q`, `delta_QR`, `delta_QC`, final winner source/rank, repair changes, and task-level bootstrap intervals. `--deduplicate-quantum` provides the required unique-candidate sensitivity check.

Prepare input directly from a complete validated result store:

```powershell
.\.venv\Scs���{h��춻�q�^traw["shots_received"] = sum(
        sum(trace.run.counts.values()) for trace in result.traces
    )
    return raw


def run_deepblock_optimization(
    *,
    instance: DispatchInstance,
    mode: str = "deepblock_simulator",
    backend: str = "Baihua",
    shots: int = 4096,
    candidate_k: int = 64,
    qaoa_depth: int = 1,
    pool_size: int = 16,
    block_size: int = 8,
    overlap: int = 3,
    seed: int = 2026,
    api_token: str = "",
    submit_hardware: bool = False,
    confirm_hardware_submit: bool = False,
    history_root: str | Path | None = None,
    save_history: bool = True,
) -> dict[str, Any]:
    """Run one fair DeepBlock comparison and return the UI's stable schema."""
    requested_mode = str(mode or "").strip().lower()
    if requested_mode not in MODE_ORDER:
        raise ValueError(f"unsupported mode: {mode}")
    if not instance.feasible_capacity:
        raise ValueError(
            "Total demand exceeds fleet capacity; increase capacity before running."
        )

    initial_result = capacity_constrained_kmeans(instance, seed=int(seed))
    initial_assignments = {
        vehicle: list(customers)
        for vehicle, customers in initial_result.assignments.items()
    }
    initial_routes = _routes_payload(initial_assignments, instance)
    initial_distance = float(sum(route["distance"] for route in initial_routes))
    config_base = dict(
        pool_size=int(pool_size),
        block_size=int(block_size),
        overlap=int(overlap),
        qaoa_depth=int(qaoa_depth),
        shots=int(shots),
        candidate_k=int(candidate_k),
        scan_order="forward",
        backend=str(backend or "Baihua"),
    )

    results: dict[str, DeepBlockResult] = {}
    chip_info: dict[str, Any] | None = None
    if submit_hardware:
        try:
            from quark.circuit import Backend
        except ImportError as exc:
            raise RuntimeError(
                "quarkcircuit==0.5.13 is required for Baihua calibration and compilation."
            ) from exc
        chip_info = dict(Backend(str(backend or "Baihua")).chip_info)
    # All arms receive the same immutable starting assignment and parameters.
    for arm_mode in MODE_ORDER:
        is_hardware = arm_mode == "deepblock_hardware"
        should_submit = bool(submit_hardware and requested_mode == arm_mode)
        config = DeepBlockConfig(
            **config_base,
            submit_hardware=should_submit,
            confirm_hardware_submit=bool(confirm_hardware_submit and should_submit),
        )
        results[arm_mode] = run_deepblock(
            instance=instance,
            initial_assignments=initial_assignments,
            mode=arm_mode,
            config=config,
            seed=int(seed),
            api_token=str(api_token or "").strip(),
            chip_info=chip_info if is_hardware else None,
        )

    selected = _result_payload(results[requested_mode], instance)
    comparisons: list[dict[str, Any]] = [
        {
            "method": "Initial",
            "mode": "classical_initial",
            "source": "classical",
            "status": "COMPLETED",
            "final_distance": initial_distance,
            "improvement": 0.0,
            "improvement_pct": 0.0,
            "accepted_moves": 0,
            "task_ids": [],
        }
    ]
    labels = {
        "deepblock_hardware": "Hardware",
        "deepblock_random": "Random",
        "deepblock_simulator": "Simulator",
        "deepblock_exact": "Exact",
    }
    for arm_mode in MODE_ORDER:
        item = _result_payload(results[arm_mode], instance)
        comparisons.append(
            {
                "method": labels[arm_mode],
                "mode": arm_mode,
                "source": item["source"],
                "status": item["status"],
                "final_distance": item["final_distance"],
                "improvement": item["improvement"],
                "improvement_pct": item["improvement_pct"],
                "accepted_moves": item["accepted_moves"],
                "task_ids": item["task_ids"],
                "backend": item["backend"],
                "shots_received": item["shots_received"],
            }
        )

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )
    arms_payload = {
        arm_mode: _result_payload(result, instance)
        for arm_mode, result in results.items()
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "seed": int(seed),
            "num_customers": len(instance.customers),
            "num_vehicles": instance.num_vehicles,
            "vehicle_capacity": instance.vehicle_capacity,
            "mode": requested_mode,
            "backend": str(backend or "Baihua"),
            "shots": int(shots),
            "candidate_k": int(candidate_k),
            "qaoa_depth": int(qaoa_depth),
            "pool_size": int(pool_size),
            "block_size": int(block_size),
            "overlap": int(overlap),
        },
        "fairness": {
            "same_instance": True,
            "same_initial_assignment": True,
            "same_blocks": True,
            "same_shots": True,
            "same_candidate_k": True,
            "same_capacity_repair": True,
            "same_route_evaluator": True,
            "same_acceptance_rule": "strict_true_distance_improvement",
        },
        "instance": _instance_payload(instance),
        "initial": {
            "distance": initial_distance,
            "assignments": {
                str(vehicle): [customer.customer_id for customer in customers]
                for vehicle, customers in sorted(initial_assignments.items())
            },
            "routes": initial_routes,
        },
        "selected": selected,
        "arms": arms_payload,
        "quantum_effect": low_energy_effect_from_payload(
            arms_payload["deepblock_hardware"]
        ),
        "comparisons": comparisons,
        "warnings": (
            [
                "Hardware is a guarded dry-run and is NOT_EVALUABLE until explicit submission is confirmed."
            ]
            if not submit_hardware
            else []
        ),
    }
    if save_history:
        root = Path(history_root) if history_root else Path("results") / "competition_history"
        CompetitionHistory(root).save(payload)
    return payload
