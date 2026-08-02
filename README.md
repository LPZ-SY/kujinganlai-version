# Quantum Route Forge

## DeepBlock æ¯”èµ›å‰ç«¯

å®Œæ•´çš„é¡¹ç›®èƒŒæ™¯ã€æŠ€æœ¯æ–¹æ¡ˆã€å®éªŒè®¾ç½®ã€çœŸæœºç»“æœã€Web æ“ä½œå’Œç»“è®ºè¾¹ç•Œè§
[`docs/Quantum_Route_Forge_é¡¹ç›®å®Œæ•´æ–‡æ¡£.md`](docs/Quantum_Route_Forge_é¡¹ç›®å®Œæ•´æ–‡æ¡£.md)ã€‚

æ–°çš„æ¯”èµ›å…¥å£ä¿ç•™è·¯çº¿åœ°å›¾ä¸å‚æ•°æ§åˆ¶ï¼Œå¹¶æŠŠ Baihua DeepBlock ç®—æ³•éš”ç¦»åœ¨
`src/quantum_route_forge/deepblock/` ä¸­ã€‚é¡µé¢åŒ…å«è·¯çº¿ä¼˜åŒ–ã€B1/B2/B3 è¿‡ç¨‹ã€
Hardware/Random/Simulator/Exact å…¬å¹³å¯¹ç…§ä»¥åŠå¯é‡è½½çš„æœ¬åœ°è¿è¡Œå†å²ã€‚

```powershell
python app.py --port 8050
```

æ—§ç ”ç©¶å‰ç«¯å®Œæ•´ä¿ç•™ï¼Œä½¿ç”¨ç‹¬ç«‹ç«¯å£å¯åŠ¨ï¼š

```powershell
python app_research.py --port 8051
```

Hardware æ¨¡å¼é»˜è®¤åªåš dry-runã€‚åªæœ‰åœ¨é¡µé¢æ˜ç¡®å‹¾é€‰çœŸå®æäº¤ç¡®è®¤åæ‰ä¼šæäº¤
Baihua ä»»åŠ¡ï¼›çœŸæœºå¤±è´¥è¿”å› `FAILED` æˆ– `NOT_EVALUABLE`ï¼Œä¸ä¼šå›é€€å¹¶ä¼ªè£…ä¸º
hardwareã€‚æ¯”èµ›å†å²ä¿å­˜åœ¨ `results/competition_history/`ã€‚

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

- **Single Run** â€” defaults to a feasible 8-customer, 2-vehicle classical scenario; shows requested/actual backend, task ID, source, requested/received shots, capacity, and quantum coverage. Incomplete, replay, manual, or fallback measurements are explicitly not evaluable for formal statistics.
- **Candidate Quality** â€” preserves fresh-hardware versus replay provenance, evaluates complete counts, and displays absolute quality, random reference, classical-threshold reach, strict improvement, exact gap, and feasibility separately.
- **Batch Experiment** â€” previews the fixed-backend formal matrix, verifies its frozen threshold hash, caps the UI at one fresh task per invocation, requires an explicit confirmation checkbox, and supports resume/pause.
- **Experiment History** â€” lists task-level instance/backend/status/source provenance with dedicated filters and the result-store integrity state.

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

Reaching a classical threshold is not rewritten as â€œquantum beats classical.â€

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
.\.venv\Scripts\python.exe experiments\prepare_hybrid_input.py `
  --config experiments\configs\formal_hardware_matrix_v2.json `
  --experiment-dir results\experiments\qrf_formal_hardware_matrix_v2 `
  --output results\experiments\qrf_formal_hardware_matrix_v2\hybrid_input.json

.\.venv\Scripts\python.exe experiments\hybrid_contribution.py `
  --input results\experiments\qrf_formal_hardware_matrix_v2\hybrid_input.json `
  --outdir results\experiments\qrf_formal_hardware_matrix_v2\hybrid
```

The measured bitstrings are decoded with the frozen
`selected_customer_ids_in_qubit_order`; backend, repeat, final source, and paired deltas are
retained at the hardware-task level. The workflow writes both JSON detail and
`hybrid_summary.csv`, including backend- and instance-stratified bootstrap summaries.

## Result store

Each batch experiment is stored under:

```text
results/experiments/<experiment_id>/
  config.json
  manifest.json
  frozen_thresholds.json
  tasks.jsonl
  candidates.jsonl
  instance_summary.csv
  aggregate_summary.json
  protocol_snapshot.json
  baseline_manifest.json
  task_manifest.csv
  tasks/<task_id>/
    evidence.json
    raw_response.json
    counts.json
    logical_qasm.qasm
    candidate_metrics.csv
    summary.json
  raw_evidence/
  figures/
  logs/
```

`config.json`, frozen thresholds, and evidence hashes are immutable for a given experiment/config hash. Authentication material is recursively redacted before evidence is written.
Completed formal evidence also records the dependency snapshot, timestamps, queue/poll fields,
compile options, optional hardware metadata, requested/actual backend, QASM/customer order, and
all frozen hashes. Validate the complete matrix before analysis:

```powershell
.\.venv\Scripts\python.exe experiments\validate_formal_result_store.py `
  --config experiments\configs\formal_hardware_matrix_v2.json `
  --experiment-dir results\experiments\qrf_formal_hardware_matrix_v2
```

## Paper artifacts

After an experiment:

```powershell
.\.venv\Scripts\python.exe experiments\generate_paper_artifacts.py `
  --experiment-dir results\experiments\qrf_formal_hardware_matrix_v2
```

The result root receives task-, instance-, and backend-level CSV/JSON summaries. The `figures/`
directory receives a CSV/LaTeX result tabïmü¶‰ËkºwµçHnx+’À§Âynh;2ôjh.xè~‹J˜xòÂ3’ã‚RÀ§ÂzÎK»nKùŞyYy¨N‹h^X{®™¨şiË®˜:XˆbÂ{ªbcãbRÀ ®h‰Zû‹ùKŠ®{¹>iéÎy¨NŠ‹ûiŠşûÉ¤&–‡V˜x~j~YÊŠú^h›Kº>ybT$òKˆ®Zûš(NZé®K˜KØîˆ;ŞXË®YxëjÚ>Y	ZøÎ™¸n8.Zè>KˆŞŠzK®ˆ;Ş˜xş™˜ŞKØâ"ãs2XŞûÈÎK™şKˆŞŠzK®‹zş{«ş{ÊyúÒ"ãs2XŞ8.YºK‹®™ˆXÎhùX{®i{n[¨şy¨NXéşYºûÈÎh‰K¸Ş™ÈŠhKˆh›iky¨Nš(Nk:XhÎzÎK»nK»¾XªiÚ^ZèÎh‰zîŠøh
~š¨ÎŠø8  ¢222’ã2[Ù>X˜Ò2Ö&Æö6²&–‡VyÉşiË®˜x~j~{¹>iéÀ ®[Ù>X˜Ş‹ùŠÂ”BK‹¢##cƒ%C##S¢Ó36&&CFSv8.KˆKŠ¢&–‡VK»¾XªXZ˜:ZèÎh‰ûÉ  §Â&Æö6²ÂF6²”BÂ6†÷G2ÂYJşKˆ‹é>X{¢ÂKØîˆ;ŞYŞKŠÒÂzÎK»njh.xèrÂ™¨şiË®jh.xèrÂZøÎ™¸nXŞi[À§ÂÒÒ×ÂÒÒ×ÂÒÒÓ§ÂÒÒÓ§ÂÒÒÓ§ÂÒÒÓ§ÂÒÒÓ§ÂÒÒÓ§À§Â#Â#cƒ##C#cƒC#“c6ÂC“bÂ#SbÂS“‚ÂBãS““bRÂãSc"RÂãC3s\9rÀ§Â#"Â#cƒ##C3c3ƒ“VÂC“bÂ#SBÂ“ƒ"Â#2ã“sCbRÂãSc"RÂ"ã3cl9rÀ§Â#2Â#cƒ##CCSƒ3s#vÂC“bÂ#S2Â#CÂ3ã#“s’RÂãSc"RÂ"ã“ƒ3,9rÀ§Â¢®[›>YØr¢¢Â2F6·2Â¢£"Ã#ƒ‚¢¢Â(	BÂ(	BÂ¢£#"ã“SsBR¢¢Â¢£ãSc"R¢¢Â¢£"ã#cL9r¢¢À ®KˆKŠ®XˆnYÙ~y¨NKØîˆ;ŞYŞKŠŞjh.xè~˜;Şš¹K¨îYØ~XÈ™¨şiË®Yû®{«şûÈÎ[›>YØ~{¹ŞZûZ)îXªK‹¢"ãƒKŠ®y›îXˆnx+8.h‰YºjÚNh¨®‹ùjÊ6Öö¶Ry¨NX	˜Xˆn[ˆ>{¹>Šë®j~ŠëK‹¢÷6—F—fUöÆ÷uöVæW&w•öVç&–6†ÖVçF8  ¢222’ãB[Ù>X˜Ò2Ö&Æö6²y¨N‹zş{«ş{¹>iéÀ ®‰›ŞxKnKØîˆ;ŞXË®ZøÎ™¸nK‹®jÚ>ûÈÎKØn[Ù>jÊ‹zş{«şk*iÈiKYhNûÉ  §ÂhÈ~jrÂ{¹>iéÂÀ§ÂÒÒ×ÂÒÒÓ§À§ÂX‰ŞZx¾‹yŞzk²Â“ãƒ““c“rÀ§ÂiÈ{¸‹yŞzk²Â“ãƒ““c“rÀ§ÂiKYhBÂãÀ§ÂiKYhNxèrÂãRÀ§Âhê^Xù~z{¾Xª‚ÂÀ ®yÉşiË¢F÷ÓcBKŠŞûÈÄ#y¨NiÈZ[ŞyÉşZéî‹zş{«şK‹¢“ã3S“c“#nûÈÄ#"K‹¢“"ãcSC##ûÈÎ˜;ŞjùN[Ù>X˜Ş‹zş{«şi»N[zîûÉ´#2y¨NiÈZ[ŞXÎK‹¢“ãƒ““c“~ûÈÎKˆî[Ù>X˜Ş‹zş{«şy»zØûÈÎYºK‹®h‰y¨Nhê^Xù~ŠxNX‰Šhk.KŠ^jÎXùyúŞûÈÎh˜Kº^K™şŠ*¾h¹.{¹Ş8  ®YÎKˆZéîKè¾Kˆ®ûÈÄ†&Gv&^8&æFöŞ86–×VÆF÷"Y(ÂÆö6ÂW†7BXZ˜:XÎYÊ‚“ãƒ““c“~ûÈÎhê^Xù~jÊi[XZ˜:K‹¢8$Æö6ÂW†7B[{.{¸şié®K‹îK¨njøşKŠ¢‚Ö&—BXˆnYÙ~y¨NXZ˜:‚#SbKŠ®x«nhûÈÎh˜Kº^h‰XúşKº^zîŠêNûÉ®YÊ[Ù>X˜Ş‹Ún‹ènZûY(Â#ô#"ô#2h˜Zé®K˜y¨N[˜:˜+¾YùşKŠŞûÈÎk*iÈKŠ^jÎi»NyúŞy¨NXúşŠÎ‹zş{«ş8.‹ùKˆŞˆ;ŞŠøiˆîZèÎi[BCZê.h‹~™zîš)[{.{¸ş‹ëîX‹XZ[iÈKÉûÈÎKØnŠûNiˆî[Ù>jÊ(	ÎiziKYhN(	ŞKˆŞiŠşyKyÉşiË®kÈş˜x~KˆKŠ®[{.yú^[˜:i»NKÉx«nhXÙ^xºÎ˜
h‰y¨N8  ¢222’ãRKŠN{¾Zéîš¨ÎK‹®K¸K˜KˆŞyù¾y»à £#BK»¾XªjÚ>[Èşyú™‹^y¨B…"™zjy¾8ZéîKè¾8yK^‹zş8Xø.i[Y(ÎYîzºşXØşŠêîûÈÎKˆâFVW&Æö6²iÈKØâRˆ;Ş˜xşzzZéîš¨ÎKˆŞy»YÎ8.X˜Şˆ^j8iú^Xk¾{¹>{¹ŞZû‹J˜xşXË®YùşY(Î{¸şX[™ˆXÎûÈÎYîˆ^j8iú^YÎKˆ‚Ö&—BKº>ybT$òy¨Ny»Zûˆ;Ş˜xşzz8.h‰KˆŞh¨®KŠN{¸Ny›îXˆnjùNy»Nhê^jùN‹è>ûÈÎK™şKˆŞyJKˆ{¸N{¹>iéÎŠhny¹nXúnKˆ{¸N{¹>iéÎ8  ®h‰[Ù>X˜Şy¨N{»ÎY{¹>Šë®iŠşûÉ  ¢Òh‰[{.{¸şŠøiˆî{;¾{¹şXúşKº^h¨®yÉşiË¢6÷VçG2ZèÎi[N8XúşZêŠêYË‹é>XZ^‹zş{«şKÉXÉn™zŞxêş8 ¢Òh‰YÊ˜:XˆbFVW&Æö6²Kº>ybT$òKˆ®Šx.ZùşX‹K¨njÚ>Y	KØîˆ;ŞXË®ZøÎ™¸n8 ¢Òh‰k*iÈYÊ‚#BK»¾XªjÚ>[Èşyú™‹^KŠŞŠx.ZùşX‹z‹>Zé®jÚ>Y	X	˜‹J˜xşiX[©N8 ¢Òh‰[	®iÊ®[»®z¸¾zÎK»ny»Zû™¨şiË®h‰n{¸şX[ikk9^y¨N‹zş{«ş{ª~i‹î‰~KÉX«ş8 ¢Òh‰KˆŞZê>z{˜	®yJ˜xşZÙKÉX«ş8˜xşZÙXª˜	şh‰n{ªş˜xşZÙZèÎi[B5e%k.Šz>8  ¢22âvV"X˜ŞzºşX©şˆ;Ğ ¢222ãŠëîŠêXéşX‰ ®h‰[nz¹î‹Y¾X˜ŞzºşŠëîŠêK‹®kX^ˆ›.{;¾ûÈÎKÛşyJkX^‰9Ş8y›Şˆ›.8[	˜xş{J¾ˆ›.Y(Î{»şˆ›.KÙÎK‹®x«nhˆ›.8.h‰˜.[ªniKîZJ~K¨njÚ>ih~8ŠXÙ^8hÈ~j~XÚY(Îš^zÛîZÙ~KÙ>ûÈÎKÛşš^™Ú.i»N˜.YjùN‹Y¾kÉNzK®Y(Î™[şi{n™{N™ˆ^Šû¾8  ®š^™Ú.šn˜:hùKé¾Kº^Kˆ¾Xø.i[ûÉ  §ÂXø.i[ÂY
¾K˜’À§ÂÒÒ×ÂÒÒ×À§ÂZê.h‹~i[ÂyIşh‰y¨N˜XŞ˜Zê.h‹~i[À§Â‹Ún‹èni[ÂXúşyJ‹Ún‹èni[À§Â‹Ún‹ènZë˜xòÂjøş‹èn‹Úny¨N™Èk.Kˆ®™™À§Â6VVBÂKÛşZéîKè¾Y(Î™¨şiË¢&ÒXúş˜xŞxëÀ§Â‹ùŠÎjŠ[ÈòÂ†&Gv&Rò&æFöÒò6–×VÆF÷"òW†7BÀ§Â&6¶VæBÂyÉşiË®YîzºşûÈÎ[Ù>X˜ŞK‹¢&–‡VÀ§Â6†÷G2ÂjøşKŠ¢FVW&Æö6²y¨N˜x~j~i[À§ÂF÷Ö²Â‹ù¾XZ^yÉş‹zş{«şŠøNK»~y¨Nš¹š)X	˜i[À§ÂôFWF‚Âô[.i[GBÀ ¢222ã"Y¹¾KŠ®š^zÛà ¢2222‹zş{«şKÉXÉ` ®h‰YÊŠú^š^[^zK®X‰ŞZx¾‹yŞzk¾8iÈ{¸‹yŞzk¾8iKYhN˜xş8iKYhNxè~8hê^Xù~z{¾XªjÊi[8{¹>iéÎiÚ^k©Y(Î‹ùŠÎx«nh8.KŠN[˜^‹zş{«şY»î[›nhé.i‹îzK®Zë˜xşXù~™™X‰ŞZx¾‹zş{«şY(ÂFVW&Æö6²iÈ{¸‹zş{«şûÈÎ[©^˜:ŠjÎX‰~X{®jøş‹èn‹Úny¨NZê.h‹~š®[¨ş8‹ÛŞˆÛ~8Zë˜xşY(Î‹yŞzk¾8  ¢2222"FVW&Æö6²‹ø~zˆ° ®h‰YÊŠú^š^[^zK¢#ô#"ô#2y¨NZê.h‹~8‹Ún‹ènZû8jùNx›ZëŞ[ªn8ôk{[ªn8F6²”N8&6¶VæN8‹ùNY¹â6†÷G>8hê^Xù~j~[ù~Y(ÎXk>zÙnXéşYº8%F÷Ö²ŠjÎ‹ù¾KˆjÚ^[^zK¢&—G7G&–æ~86÷VçN8jh.xè~8T$òKº>ynˆ;Ş˜xş8KúîZHŞX˜ŞYîXúşŠÎh
~8KúîZHŞŠûNiˆîY(ÎyÉşZéî‹zş{«ş‹yŞzk¾8.h‰K™şhùKé¾Xúş[^[Èy¨NZèÎi[B6÷VçG>8˜¾‹é4Ş8xšyb4ÒY(Î{ÉnŠùZêŠê8  ¢22222ikk9^Zûjù@ ®h‰yJiÈ{¸‹zş{«ş‹yŞzk¾iûx«nY»îY(ÂFVW&Æö6²hš¾høşi».{«şZûjùB–æ—F–Î8†&Gv&^8&æFöŞ86–×VÆF÷"Y(ÂW†7N8.š^™Ú.šn˜:KÉ®i‹îzK®XZÎ[›>h
~™HZé®x«nhûÈÎŠjÎX‰[^zK®jøşzxŞikk9^y¨B6÷W&6^87FGW>8f–æÂF—7Fæ6^8–×&÷fVÖVçN866WFVBÖ÷fW2Y(ÂF6²”G>8  ¢2222B‹ùŠÎXènXû  ®h‰K‹®jøşjÊ‹ùŠÎKùŞZÙxºÎz¸²¥4ôîûÈÎ[›nYÊXènXû.š^hùKé¾ŠjÎ8Kˆ¾h¸˜hº8X‹~ikY(Î˜xŞikh™>[È8.Kˆ¾h¸˜šKÛşyJ{J~XyXÙ^ŠÎjÎ[ÈşûÉ  ¦FW‡@£‚Ó"#£#’Â†&Gv&RÂd”ÄTBÂF6Cs&#£‚Ó"£#RÂ†&Gv&RÂ4ôÕÄUDTBÂ36&&CFSp¦  ®h‰[bUD2i{n™{N‹ÚÎhÚ.K‹®XÉ~KªÎi{n™{NûÈÎ[›nYÊ˜šKŠŞy»Nhê^i‹îzK¢ÖöF^87FGW2Y(ÎyúÒ'Vâ”NûÈÎ˜şXXŞZèÎi[B•4òi{n™{NKˆî™[ò”BYÊz¨NKˆ¾h¸ˆùÎXÙ^KŠŞhÚ.ŠÎ˜xŞXú8  ¢22âZèŠ8^Kˆî‹ùŠÀ ¢222ãxêşZ(0 ®h‰[Ù>X˜Şš¨ÎŠøy¨NK‹¾ŠhxêşZ(>iŠò—F†öâ2ã.8.ZèŠ8^YŞKºNZh.Kˆ¾ûÉ  ¦÷vW'6†VÆÀ§—F†öâÖÒfVçbçfVç`¢åÂçfVçeÅ67&—G5Ä7F—fFRç3§—F†öâÖÒ—–ç7FÆÂ×"&WV—&VÖVçG2çG‡@§—F†öâÖÒ—FW7B×¦  ®K‹¾ŠhKéŞ‹YnXÈ^hºÂF6‚2ç8Æ÷FÇ’bç8çVÕ866–¶—BÖÆV&î8F–ÖöN8—VgRãBã^8V&·7GVF–òrã2ã’Y(ÂV&¶6—&7V—BãRã>8  ¢222ã"Y
şXªz¹î‹Y¾X˜Şzºğ ¦÷vW'6†VÆÀ¢åÂçfVçeÅ67&—G5Ç—F†öâæW†Rç’ÒÖ†÷7B#rãããÒ×÷'BƒS ¦  ®h™>[ÈûÉ  ¦FW‡@¦‡GG¢òó#rããã£ƒS ¦  ¢222ã2Y
şXªKùŞyYy¨Nz	Nz›nX˜Şzºğ ¦÷vW'6†VÆÀ¢åÂçfVçeÅ67&—G5Ç—F†öâæW†R÷&W6V&6‚ç’ÒÖ†÷7B#rãããÒ×÷'BƒS¦  ®h™>[ÈûÉ  ¦FW‡@¦‡GG¢òó#rããã£ƒS¦  ¢222ãBZèXZiú^yÈ¾xëiÈyÉşiË®{¹>iéÀ ®Zh.iéÎh‰Xú®™ÈŠhiú^yÈ¾[{.ZèÎh‰y¨B2Ö&Æö6²yÉşiË®{¹>iéÎûÈÎh‰KˆŞ™ÈŠhXhŞjÊx+X{²†&Gv&R‹ùŠÎ8.h‰XúşKº^‹ù¾XZ^(	ÃB‹ùŠÎXènXû.(	ŞûÈÎ˜hºyúÒ”B36&&CFSvûÈÎx+X{¾(	Î˜xŞikh™>[È(	ŞûÈÎxKnYîXˆ~hÚ.X‹ó"ó2š^iú^yÈ¾‹zş{«ş8XˆnYÙ~ŠøhÚîY(Îikk9^ZûjùN8  ®š^™Ú.šn˜:‹é>XZ^jnŠzK®(	ÎKˆ¾KˆjÊ[nŠh‹ùŠÎy¨NXø.i[(	ŞûÈÎZè>KºÎKˆŞKÉ®YÊh™>[ÈXènXû.Yîˆz®XªŠhny¹nK‹®XènXû.XÎ8.h‰KÉ®Kº^XènXû.Šúnh8^KŠŞŠë[Ù^y¨B&ÖWFW'2KÙÎK‹®[Ù>jÊZéîš¨ÎyÉşZéîŠëî{Úî8  ¢222ãRyÉşiË®‹ùŠÀ ®yÉşiË®jŠ[Èş™ÈŠhYÊ[Ù>X˜Ş‹ù¾zˆ¾xêşZ(>KŠŞhùKé²TeUô•õDô´Tæ8.h‰KˆŞKÉ®[bFö¶VâXiXZ^XènXû"¥4ôî8Zéîš¨ÎŠøhÚîh‰bv—BK¹>[©>8.˜hº’†&Gv&R[›nX»î˜zîŠêNjnYîûÈÎjøşjÊx+X{¾˜;ŞXúşˆ;ŞhùKªNiky¨B&–‡VK»¾XªûÈÎYºjÚNh‰Xú®YÊiˆîzî™ÈŠhiki[hÚîi{nhš~ŠÎŠú^i8ŞKÙÎ8  ¢22"âkX¾Šù^8XúşZHŞxëh
~Kˆî‹J˜xşKùŞŠø ®h‰K‹®Kº^Kˆ¾X[>™Jî‹zş[èN{ÉnXiK¨nzk¾{«şXÙ^XX>kX¾Šù^Y(Î™¸nh‰kX¾Šù^ûÉ  ¢Ò&—G7G&–ærKˆâ÷Vå4Ò6÷VçG2y¨Nš¹KØîKØŞš®[¨şûÉ°¢Ò6÷VçG2ŠxNˆÈ>XÉn8™Ùîk9^™Jîh¹.{¹ŞY(Â6†÷G2h¾Y(Îš¨ÎŠøûÉ°¢Ò#ô#"ô#2˜xŞXúŠhny¹nY(Îhš¾høşš®[¨şûÉ°¢ÒT$òˆ;Ş˜xşKˆîx«nh{ÉnŠz>zûÉ°¢ÒZë˜xşKúîZHŞYîy¨NXúşŠÎh
~ûÉ°¢ÒF÷Ö²X	˜y¨NyÉşZéî‹zş{«şŠøNK»~ûÉ°¢ÒKŠ^jÎXùyúŞhê^Xù~ŠxNX‰ûÉ°¢Ò[˜:‚W†7Bié®K‹îXø.ˆ>ûÉ°¢Ò†&Gv&RG'’×'VâKˆîi‹î[ÈşzîŠêN™zûÉ°¢ÒXènXû"¥4ôâKùŞZÙ8˜xŞ‹ÛŞKˆî{J~XyKˆ¾h¸˜šûÉ°¢ÒiÈKØâRˆ;Ş˜xşXË®YùşY»®Zé®hé.YŞŠêzé~ûÉ°¢ÒZI®YîzºşjÚ>[Èò&W7VÇB7F÷&Ry¨NZèÎi[Nh
~8Xë¾˜xŞY(ÎiÚ^k©š¨ÎŠøûÉ°¢ÒvV"š^zÛî8‹é>X{®i[˜xşY(ÎzÎK»nKùŞhªNhê~K»n8  ®h‰y¨NjÚ>[ÈşZéîš¨ÎXØşŠêîKÛşyJXk¾{¹>˜XŞ{Úî8™ˆXÂ†684Ò†6‚Y(ÎZê.h‹~š®[¨ò†68.jøşKŠ®K»¾XªKÛşyJYJşKˆ6öæf–r†6ûÈÎh›ZHNynh.ZHŞi{nKˆŞKÉ®˜xŞZHŞhùKªN[{.ZèÎh‰K»¾Xª8  ¢222âK¹>[©>{¹>iè@ ¦FW‡@¥VçGVÒ&÷WFRf÷&vRğ§ÂÒÒç§Âz¹î‹Y¾K‹¾X˜ŞzºşûÉ®‹zş{«ş8FVW&Æö6²‹ø~zˆ¾8ikk9^ZûjùN8‹ùŠÎXènXû §ÂÒÒ÷&W6V&6‚ç§ÂKùŞyYy¨Nz	Nz›nZéîš¨ÎX˜Şzºğ§ÂÒÒ'Våö6Æ’ç§ÂXÙ^jÊ{¸şX[‚ş˜xşZÙkXzˆ²4Ä§ÂÒÒ&WV—&VÖVçG2çG‡@§ÂÒÒ7&2÷VçGVÕ÷&÷WFUöf÷&vRğ§ÂÂÒÒFVW&Æö6µ÷6W'f–6Rç§ÂÂÒÒ6ö×WF—F–öåö†—7F÷'’ç§ÂÂÒÒ6æF–FFU÷VÆ—G’ç§ÂÂÒÒVçGVÕöÖV7W&VÖVçG2ç§ÂÂÒÒ&W7VÇE÷7F÷&Rç§ÂÂÒÒ—VÆ–æRç§ÂÂÒÒ&÷WF–ærç§ÂÂÒÒ66Væ&–òç§ÂÒÒFVW&Æö6²ğ§ÂÂÒÒFFW'2ç§ÂÂÒÒ'V–ÆFW"ç§ÂÂÒÒ6ÇW7FW&–ærç§ÂÂÒÒWfÇVF÷"ç§ÂÂÒÒ&÷‡•÷V&òç§ÂÂÒÒö÷'VææW"ç§ÂÒÒ6öÇfW"ç§ÂÒÒW‡W&–ÖVçG2ğ§ÂÂÒÒ&F6…ö6æF–FFU÷VÆ—G’ç§ÂÂÒÒ'Vå÷V&·7GVF–õö6æF–FFU÷VÆ—G’ç§ÂÂÒÒfÆ–FFUöf÷&ÖÅ÷&W7VÇE÷7F÷&Rç§ÂÂÒÒ&W&Uö‡–'&–Eö–çWBç§ÂÂÒÒ‡–'&–Eö6öçG&–'WF–öâç§ÂÂÒÒvVæW&FU÷W%ö'F–f7G2ç§ÂÒÒ6öæf–w2ğ§ÂÒÒf÷&ÖÅö†&Gv&UöÖG&—…÷c"æ§6öà§ÂÒÒ&W7VÇG2ğ§ÂÂÒÒ6ö×WF—F–öåö†—7F÷'’ğ§ÂÂÒÒW‡W&–ÖVçG2ğ§ÂÒÒV&·7GVF–õö6æF–FFU÷VÆ—G•÷fÆ–FFVBğ§ÂÒÒFö72ğ§ÂÂÒÒf÷&ÖÅöW‡W&–ÖVçE÷&÷Fö6öÂæÖ@§ÂÂÒÒf÷&ÖÅó#E÷F6µ÷&W÷'BæÖ@§ÂÂÒÒ‡–'&–Eö6öçG&–'WF–öå÷&W÷'BæÖ@§ÂÂÒÒVçGVÕöVffV7EöWf–FVæ6RæÖ@§ÂÒÒVçGVÕõ&÷WFUôf÷&vUşšyºîZèÎi[Nih~j2æÖ@¦ÒÒFW7G2ğ¦  ¢22Bâ[{.yú^[™™  ®h‰Zû[Ù>X˜Ş{;¾{¹şy¨Nˆ;ŞX©¾‹ëyXÎX®Zh.Kˆ¾™™Zé®ûÉ  £â¢¤FVW&Æö6²iŠş[˜:i	Î{J.8"¢¢h‰[Ù>X˜Ş˜hºKˆZû‹Ún‹ènY(ÎiÈZI®KˆKŠ¢‚Ö&—BXˆnYÙ~ûÈÎYºjÚBÆö6ÂW†7BK™şKˆŞiŠşXZ[5e%{+îzîŠz>8 £"â¢¥T$òiŠşKº>ynjŠYè¾8"¢¢h‰KùŞyYy¨NK¨ÎjÊKªNK©.Xù~zÎK»nh¹>h™™™X‹nûÈÎKØîKº>ynˆ;Ş˜xşKˆŞ[ø^xKn‹ÚÎXÉnK‹®i»NyúŞyÉşZéî‹zş{«ş8 £2â¢®[Ù>X˜Ò2Ö&Æö6²j~iÊÎ[è[ş8"¢¢2KŠ®XˆnYÙ~‹ùiŠş˜xŞXúy¨NûÈÎh‰KˆŞh¨¢2ó2™‹>h
~[Ù>h‰XX^Xˆny¨N{¹şŠêi‹î‰~h
~ŠøhÚî8 £Bâ¢£"ãs<9r[îK¨îhê.{J.h
~Xú>[èN8"¢¢h‰[{.Xk¾{¹>Šú^™zjy¾ûÈÎKØnK¸Ş™ÈŠhiky¨Nš(Nk:XhÎzÎK»nh›jÊ8 £Râ¢®jÚ>[Èò#BK»¾Xªyú™‹^ˆÈ>Y»NiÈ™™8"¢¢{¹>Šë®Xú®˜.yJK¨îŠ*¾kX¾ZéîKè¾8yK^‹zş8Xø.i[8{ÉnŠùŠëî{Úî8YîzºşY(Îhš~ŠÎiz^iÉş8 £bâ¢®h‰[	®iÊ®Šøiˆî˜xşZÙ˜	ş[ªnKÉX«ş8"¢¢[Ù>X˜Şšyºîy¨N˜xŞx+iŠşX	˜‹J˜xş8‹zş{«ş‹JxÊîY(ÎXúşZêŠêh
~ûÈÎKˆŞiŠòvÆÂÖ6Æö6²Xª˜	ş8 £râ¢®iÊÎYËF6‚iÈŞXªYšKˆŞiŠşyIşKª~˜:{Û.8"¢¢[Ù>X˜Şš^™Ú.yJK¨îz	Nz›n8z¹î‹Y¾Y(ÎiÊÎYËkÉNzK®ûÈÎ[	®iÊ®˜XŞ{ÚîyIşKªru4t8ŠêNŠø8ZI®yJh‹~K»¾Xª™©Nzk¾Y(ÎhÈK˜^i[hÚî[©>8  ¢22RâYî{ºŞŠêX‰  ®h‰K‹®šyºîŠëîZé®K¨nKº^Kˆ¾KÉXX{ª~ûÉ  ¢222Rãš(Nk:XhÎiÈKØâRzîŠøZéîš¨À ®h‰[nYÊŠû¾XùnikzÎK»b6÷VçG2K˜¾X˜ŞXk¾{¹>ZéîKè¾8T$ş8ˆ;Ş˜xş™ˆXÎ86†÷G>86VVBi[˜xş8K‹¾hÈ~j~Y(Î{¹şŠêj8š¨Î8.ikh›jÊ[nKˆîiziÉò"ãs<9rŠøhÚîZèÎXZXˆn[Èhª^Y®8  ¢222Rã"hš[^[˜:˜+¾Yùğ ®h‰ŠêX‰.K¸î(	ÎXÙ^‹Ún‹ènZû’²#ô#"ô#2XÙ^‹Úî(	Şhš[^X‹ZI®‹Ún‹ènZû8ˆz®˜.[©N‹ëyXÎk8X˜ŞY	şXøŞY	hš¾høşY(ÎZI®‹ÚîKŠ^jÎiKYhN8.h‰KÉ®KùŞyYjøş‹Úîy¨N‹yŞzk¾XÙ^‹>KˆŞZ)îKùŞŠø8  ¢222Rã2hùš¹‚T$òKˆîyÉş‹zş{«şy¨Nhé.YŞy»X[>h
p ®h‰[nyJ[˜:‚W†7Bi[hÚî˜xşXÉn(	ÎKº>ynˆ;Ş˜xşhé.YŞ(	ŞKˆî(	ÎKúîZHŞYîyÉş‹zş{«ş‹yŞzk¾hé.YŞ(	Şy¨B7V&Öâô¶VæFÆÂy»X[>h
~ûÈÎ[›n™(Zûh¹>h™Š8Xš®8Zë˜xşh:{Ù®Y(Î‹zş{«şKº>ynX{Şi[X®kh‰èŞZéîš¨Î8  ¢222RãB˜xşZÙXø.i[KˆîzÎK»n›(j9.h
p ®h‰[njùN‹è2GÓÃ"Ã2N8Xø.i[‹øz{¾8ZI®{¸Nš(NŠêŞ{¸>X‰ŞXÎY(ÎKˆŞYÎj
XxnZÙY»îûÈÎYÎi{nŠë[Ù^yK^‹zşk{[ªn8KŠNjùNx›™zi[85t8KùŞyÉş[ªnKˆîKØîˆ;ŞZøÎ™¸nK˜¾™{Ny¨NX[>{;¾8  ¢222RãRK¸îiÊÎYËkÉNzK®‹øY	yIşKª~[Ú.h ®h‰ŠêX‰.[n™[şi{n™{NyÉşiË®K»¾XªK¸âF6‚Y¹î‹>KŠŞh¸nXˆnK‹®YîXûKÙÎK‰®ûÈÎZ)îXªK»¾Xª™‰şX‰~8‹ù¾[ªniú^Šú.8i[hÚî[©>XènXû.8yJh‹~iØ>™™8Zøn™*^h™zêY(ÎyIşKª~{ª~iÈŞXªYš8  ¢22bâXúşXXŠëy¨N{¹>Šë®KˆîKˆŞXXŠëy¨N{¹>Šë  ¢222bãh‰[Ù>X˜ŞXXŠëy¨N{¹>Šë  ¢Òh‰[{.ZéîxëKˆZY~XúşZêŠêy¨B&–‡VôFöævÆ–ærõ6†VævÆ–âyÉşiË®X	˜‹J˜xşZéîš¨ÎkXzˆ¾8 ¢Òh‰[{.Zéîxë&–‡VFVW&Æö6²K¸îj
Xxnh¹>h™{ÉnŠùX‹‹zş{«şKŠ^jÎhê^Xù~y¨NzºşX‹zºşyÉşiË®™zŞxêş8 ¢ÒYÊ[Ù>X˜Ò2Ö&Æö6²6Öö¶RKŠŞûÈÄ&–‡VZûiÈKØâRKº>ybT$òˆ;Ş˜xşXË®Yùşy¨N[›>YØ~jh.xè~‹J˜xşiŠşYØ~XÈ™¨şiË®y¨B"ã#cL9~8 ¢ÒYÊiziÉòb×6VVBhê.{J.KŠŞûÈÎy»YÎXú>[èNy¨NZøÎ™¸nXŞi[iŠò"ãs<9~ûÈÎKØn™ÈŠhiky¨Nš(Nk:XhÎZéîš¨ÎzîŠêN8 ¢ÒYÊ[Ù>X˜Ò2Ö&Æö6²ZéîKè¾KŠŞûÈÎ[˜:‚W†7BŠøiˆîh˜˜˜+¾YùşXh^k*iÈKŠ^jÎi»NyúŞ‹zş{«ş8 ¢ÒYÊ‚#BK»¾XªjÚ>[Èşyú™‹^KŠŞûÈÎh‰k*iÈŠx.ZùşX‹z‹>Zé®jÚ>Y	X	˜‹J˜xşh‰n‹zş{«ş‹JxÊî8  ¢222bã"h‰[Ù>X˜ŞKˆŞKÉ®X®y¨N{¹>Šë  ¢Òh‰KˆŞZê>z{iÊÎšyºî[{.{¸şZéîxë˜	®yJ˜xşZÙKÉX«ş8 ¢Òh‰KˆŞZê>z{[{.{¸şŠøiˆî˜xşZÙvÆÂÖ6Æö6²Xª˜	ş8 ¢Òh‰KˆŞ[b"ãs<9rh‰b"ã#cL9rŠz>˜x®K‹®‹zş{«ş‹yŞzk¾iKYhNXŞi[8 ¢Òh‰KˆŞ[n[˜:‚‚Ö&—BW†7BŠz>˜x®K‹®ZèÎi[B5e%XZ[iÈKÉŠz>8 ¢Òh‰KˆŞ[nKˆKŠ¢6†÷B[Ù>h‰KˆjÊxºÎz¸¾zÎK»n˜xŞZHŞ8 ¢Òh‰KˆŞ[b&WÆ8ÖçVÎ86–×VÆF÷"h‰bfÆÆ&6²Xi.XX^iky¨B†&Gv&RŠøhÚî8 ¢Òh‰KˆŞ™©‰xşjÚ>[ÈşXØşŠêîKŠŞZû˜xşZÙikk9^KˆŞXŠy¨NK»¾Xª8  ¢22râh¾{¹0 ®h‰YÊ‚VçGVÒ&÷WFRf÷&vRKŠŞŠz>Xk>y¨NKˆŞXú®iŠş(	ÎhîK˜‹>yJKˆjÊ˜xşZÙyÉşiË®(	ŞûÈÎˆÎiŠşZh.KÙ^h¨®˜xşZÙ˜x~j~iKî‹ù¾KˆKŠ®XZÎ[›>8XúşKúîZHŞ8Xúş˜xŞzé~8XúşZÙŠøy¨N‹zş{«şKÉXÉn™zŞxêş8.[Ù>X˜ŞXˆniJş[{.{¸ş[n‹ùKˆz	Nz›nyºîj~‹ÚÎXÉnh‰XúşKªNK©.y¨Nz¹î‹Y¾X˜ŞzºşY(ÎZéî™˜^Xúş‹ùŠÎy¨B&–‡VFVW&Æö6²kXzˆ¾8  ®[Ù>X˜Şi[hÚî{¹X{®K¨nKˆKŠ®iÈ[.jÊy¨N{¹>Šë®ûÉ®h‰YÊ˜:XˆbFVW&Æö6²Kº>ybT$òKˆ®yÈ¾X‹K¨nzÎK»nKØîˆ;ŞZøÎ™¸nûÈÎKØn‹ùk*iÈ[nZè>z‹>Zé®‹ÚÎXÉnh‰y»Zû™¨şiË®h‰n{¸şX[ikk9^y¨N‹zş{«ş{ª~KÉX«ş8.‹ùKˆ[zî‹yŞiˆîzîK¨nKˆ¾Kˆ™‹një^y¨Nz	Nz›n˜xŞx+ûÉ®hš[^[˜:˜+¾Yùş8hùš¹‚T$òKˆîyÉş‹zş{«şy¨Ny»X[>h
~8ZèÎh‰š(Nk:XhÎzîŠøZéîš¨ÎûÈÎ[›n{º~{ºŞKùŞyYh˜iÈiÈXŠKˆîKˆŞXŠŠøhÚî8  ¢22™˜N[ÙRûÉ®X[>™JîŠøhÚî‹zş[è@ §ÂŠøhÚâÂK¹>[©>‹zş[èBÀ§ÂÒÒ×ÂÒÒ×À§Â#BK»¾XªjÚ>[ÈşXØşŠêâÂFö72öf÷&ÖÅöW‡W&–ÖVçE÷&÷Fö6öÂæÖFÀ§Â#BK»¾Xª˜	K»¾Xªhª^Y¢ÂFö72öf÷&ÖÅó#E÷F6µ÷&W÷'BæÖFÀ§Â2ô2µ"ô2µXZÎ[›>k{~Yhª^Y¢ÂFö72ö‡–'&–Eö6öçG&–'WF–öå÷&W÷'BæÖFÀ§Â˜xşZÙiX[©N‹ëyXÂÂFö72÷VçGVÕöVffV7EöWf–FVæ6RæÖFÀ§ÂŠë®ih~Z;iˆî‹ëyXÂÂFö72÷W%ö6Æ–Õö&÷VæF&–W2æÖFÀ§Âz¹î‹Y¾XènXû"Â&W7VÇG2ö6ö×WF—F–öåö†—7F÷'’öûÈiÊÎYË‹ùŠÎyºî[Ù^ûÈÎ›¹ŠêNKˆŞ™¨òv—BhùKªNûÈ’À§ÂjÚ>[ÈşZéîš¨Â&W7VÇB7F÷&RÂ&W7VÇG2öW‡W&–ÖVçG2÷&eöf÷&ÖÅö†&Gv&UöÖG&—…÷c"öÀ§Âz¹î‹Y¾X˜ŞzºòÂç–À§ÂFVW&Æö6²{¹şKˆiÈŞXªÂ7&2÷VçGVÕ÷&÷WFUöf÷&vRöFVW&Æö6µ÷6W'f–6Rç–À§ÂFVW&Æö6²j[ø>ZéîxëÂ7&2÷VçGVÕ÷&÷WFUöf÷&vRöFVW&Æö6²öÀ ¢22™˜N[ÙR.ûÉ®[Ù>X˜Ò2Ö&Æö6²yÉşiË®K»¾Xª ¦FW‡@¤#F6µö–CÓ#cƒ##C#cƒC#“c2&6¶VæCÔ&–‡V6†÷G3ÓC“b7FGW3Ôf–æ—6†V@¤#"F6µö–CÓ#cƒ##C3c3ƒ“R&6¶VæCÔ&–‡V6†÷G3ÓC“b7FGW3Ôf–æ—6†V@¤#2F6µö–CÓ#cƒ##CCSƒ3s#r&6¶VæCÔ&–‡V6†÷G3ÓC“b7FGW3Ôf–æ—6†V@¦  ¢22™˜N[ÙR>ûÉ®iÊşŠúŞŠ€ §ÂiÊşŠúÒÂiÊÎšyºîKŠŞy¨NY
¾K˜’À§ÂÒÒ×ÂÒÒ×À§ÂT$òÂK¨ÎjÊiz{ªniÙşK¨Î‹ù¾X‹nKÉXÉnjŠYè²À§ÂôÂ˜xşZÙ‹ùKËÎKÉXÉnzé~k9^ûÈÎYÊiÊÎšyºîKŠŞyJK¨îyIşh‰X	˜Xˆn[ˆ2À§ÂFVW&Æö6²ÂK¸îZJ~ŠxNjŠ‹zş{«ş™zîš)KŠŞh«ŞXùny¨N[˜:KŠN‹Ún˜xŞXˆn˜XŞZÙ™zîš)‚À§Â6÷VçG2Â˜xşZÙkX¾˜xò&—G7G&–ærX‹X{®xëjÊi[y¨NiŠ[BÀ§Â6†÷G2ÂYÎKˆyK^‹zşy¨NkX¾˜xş˜x~j~jÊi[À§ÂF÷Ö²Â‹ù¾XZ^{¸şX[yÉş‹zş{«şŠøNK»~y¨Nš¹š)X	˜i[˜xòÀ§Â&÷‡’VæW&w’Â[˜:‚T$òKº>ynˆ;Ş˜xşûÈÎKˆŞzØK¨îiÈ{¸yÉş‹zş{«ş‹yŞzk²À§ÂÆ÷rÖVæW&w’Vç&–6†ÖVçBÂyÉşiË®Xˆn[ˆ>‹ù¾XZ^š(NZé®K˜KØîˆ;ŞXË®y¨Njh.xè~y»ZûYØ~XÈ™¨şiË®y¨Nhùš¹‚À§ÂÆö6ÂW†7BÂié®K‹îXÙ^KŠ¢FVW&Æö6²x«nhz›®™{NûÈÎKˆŞiŠşXZ[5e%{+îzîk.Šz2À§ÂäõEôUdÅT$ÄVÂk*iÈ‹k>ZIşy¨NYjÎŠøhÚî‹ù¾ŠÎ[Ù>X˜ŞŠøNK»rÀ§Â7G&–7B66WFæ6RÂXú®hê^Xù~Zë˜xşXúşŠÎK‰NyÉşZéî‹zş{«ş‹yŞzk¾KŠ^jÎXxş[şy¨NX	˜’À