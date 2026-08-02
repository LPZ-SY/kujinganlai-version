from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quantum_route_forge.competition_history import CompetitionHistory  # noqa: E402
from quantum_route_forge.deepblock_service import run_deepblock_optimization  # noqa: E402
from quantum_route_forge.scenario import generate_dispatch_instance  # noqa: E402


COLORS = ["#2f80ed", "#7c5cfc", "#f2a93b", "#22a06b", "#e65f8e", "#5b8def"]
INK = "#183153"
MUTED = "#6e809b"
PANEL = {
    "background": "linear-gradient(145deg, rgba(255,255,255,.99), rgba(248,251,255,.99))",
    "border": "1px solid #dce6f2",
    "borderRadius": "18px",
    "boxShadow": "0 14px 38px rgba(67,90,124,.10)",
}
HISTORY = CompetitionHistory(ROOT / "results" / "competition_history")


def _latest_history_payload():
    try:
        rows = HISTORY.rows()
        return HISTORY.load(rows[0]["run_id"]) if rows else None
    except (OSError, ValueError, KeyError):
        return None


INITIAL_PAYLOAD = _latest_history_payload()


def _initial_status_text():
    if not INITIAL_PAYLOAD:
        return "尚未运行。Hardware 未明确确认时仅进行 dry-run，不会提交任务。"
    selected = INITIAL_PAYLOAD.get("selected", {})
    return (
        f"已载入最近运行 {INITIAL_PAYLOAD.get('run_id')} · "
        f"{selected.get('status')} · source={selected.get('source')}"
    )


def _field(label: str, control, hint: str = ""):
    return html.Div(
        [
            html.Label(label, style={"fontSize": "13px", "fontWeight": 700, "color": "#405b7d"}),
            control,
            html.Small(hint, style={"color": "#7b8da6", "lineHeight": "1.25"}) if hint else None,
        ],
        style={"display": "flex", "flexDirection": "column", "gap": "6px"},
    )


def _number(component_id: str, value: int, minimum: int, maximum: int, step: int = 1):
    return dcc.Input(
        id=component_id,
        type="number",
        value=value,
        min=minimum,
        max=maximum,
        step=step,
        style={"width": "100%", "height": "38px"},
    )


def _empty_figure(title: str, subtitle: str = "运行后显示"):
    figure = go.Figure()
    figure.add_annotation(
        text=f"<b>{title}</b><br><span style='font-size:13px;color:#7188aa'>{subtitle}</span>",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": "#7186a2", "size": 17},
    )
    figure.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=410,
        margin={"l": 25, "r": 25, "t": 40, "b": 25},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def _route_figure(instance: dict[str, Any], routes: list[dict[str, Any]], title: str):
    figure = go.Figure()
    depot = instance.get("depot", [0, 0])
    figure.add_trace(
        go.Scatter(
            x=[depot[0]],
            y=[depot[1]],
            mode="markers+text",
            text=["DEPOT"],
            textposition="top center",
            name="Depot",
            marker={"size": 19, "symbol": "star", "color": "#183153", "line": {"color": "#73b8ff", "width": 2}},
        )
    )
    for index, route in enumerate(routes or []):
        customers = route.get("customers", [])
        xs = [depot[0]] + [row["x"] for row in customers] + [depot[0]]
        ys = [depot[1]] + [row["y"] for row in customers] + [depot[1]]
        labels = ["Depot"] + [f"C{row['customer_id']} · d={row['demand']}" for row in customers] + ["Depot"]
        figure.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=f"车辆 {route.get('vehicle_id')}",
                text=labels,
                hovertemplate="%{text}<br>x=%{x:.2f}, y=%{y:.2f}<extra></extra>",
                line={"width": 2.6, "color": COLORS[index % len(COLORS)]},
                marker={"size": 8, "color": COLORS[index % len(COLORS)]},
            )
        )
    figure.update_layout(
        template="plotly_white",
        title={"text": title, "x": 0.03, "font": {"size": 17}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#fbfdff",
        height=440,
        margin={"l": 35, "r": 20, "t": 55, "b": 35},
        legend={"orientation": "h", "y": -0.14},
        font={"color": INK},
        xaxis={"gridcolor": "#e8eef6", "zeroline": False},
        yaxis={"gridcolor": "#e8eef6", "zeroline": False, "scaleanchor": "x", "scaleratio": 1},
    )
    return figure


def _metric(label: str, value: str, tone: str = "#2f80ed"):
    return html.Div(
        [
            html.Div(label, style={"fontSize": "12px", "letterSpacing": "1px", "textTransform": "uppercase", "color": MUTED}),
            html.Div(value, style={"fontSize": "26px", "fontWeight": 800, "color": tone, "marginTop": "5px"}),
        ],
        style={**PANEL, "padding": "15px 17px", "minHeight": "70px"},
    )


def _table(component_id: str, page_size: int = 10):
    return dash_table.DataTable(
        id=component_id,
        data=[],
        columns=[],
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto", "borderRadius": "12px"},
        style_header={
            "backgroundColor": "#edf4fc",
            "color": "#294866",
            "fontWeight": 700,
            "border": "1px solid #d5e1ef",
        },
        style_cell={
            "backgroundColor": "#ffffff",
            "color": "#405b7d",
            "border": "1px solid #e0e8f2",
            "fontFamily": "Segoe UI, Microsoft YaHei, sans-serif",
            "fontSize": "13px",
            "lineHeight": "1.4",
            "padding": "10px",
            "textAlign": "left",
            "maxWidth": "280px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_data_conditional=[
            {"if": {"filter_query": "{accepted} = true"}, "backgroundColor": "#e8f8f1", "color": "#137b55"}
        ],
    )


controls = html.Div(
    [
        html.Div(
            [
                html.Div("RUN CONFIG", style={"fontSize": "12px", "letterSpacing": "2px", "color": "#2f80ed"}),
                html.H3("同条件公平对照", style={"margin": "5px 0 0", "fontSize": "20px"}),
            ]
        ),
        html.Div(
            [
                _field("客户数", _number("num-customers", 16, 4, 60)),
                _field("车辆数", _number("num-vehicles", 3, 2, 10)),
                _field("车辆容量", _number("vehicle-capacity", 24, 2, 100)),
                _field("Seed", _number("seed", 2026, 0, 999999)),
                _field(
                    "运行模式",
                    dcc.Dropdown(
                        id="mode",
                        value="deepblock_simulator",
                        clearable=False,
                        options=[
                            {"label": "Baihua Hardware", "value": "deepblock_hardware"},
                            {"label": "Uniform Random", "value": "deepblock_random"},
                            {"label": "Ideal Simulator", "value": "deepblock_simulator"},
                            {"label": "Local Exact", "value": "deepblock_exact"},
                        ],
                    ),
                ),
                _field("Backend", dcc.Input(id="backend", value="Baihua", style={"width": "100%", "height": "38px"})),
                _field("Shots", _number("shots", 4096, 1, 100000)),
                _field("Top-k", _number("candidate-k", 64, 1, 256)),
                _field(
                    "QAOA depth",
                    dcc.Dropdown(
                        id="qaoa-depth",
                        value=1,
                        clearable=False,
                        options=[{"label": f"p = {value}", "value": value} for value in (1, 2, 3)],
                    ),
                ),
            ],
            style={"display": "grid", "gridTemplateColumns": "repeat(3, minmax(135px, 1fr))", "gap": "12px", "marginTop": "16px"},
        ),
        dcc.Checklist(
            id="hardware-confirm",
            options=[
                {
                    "label": " 我确认：Hardware 模式将真实提交最多 3 个 Baihua 任务",
                    "value": "confirm",
                }
            ],
            value=[],
            style={"fontSize": "13px", "color": "#a86800", "marginTop": "13px"},
        ),
        html.Div(
            [
                html.Button("运行 DeepBlock 对照", id="run-btn", n_clicks=0, className="run-button"),
                html.Div("同一实例 · 同一初始分配 · 同一 Top-k · 严格改善才接受", style={"fontSize": "12px", "color": MUTED}),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "15px", "marginTop": "14px"},
        ),
    ],
    style={**PANEL, "padding": "20px"},
)


route_page = html.Div(
    [
        html.Div(id="metric-row", style={"display": "grid", "gridTemplateColumns": "repeat(5, 1fr)", "gap": "12px"}),
        html.Div(
            [
                html.Div(dcc.Graph(id="initial-route", figure=_empty_figure("初始路线")), style={**PANEL, "padding": "5px"}),
                html.Div(dcc.Graph(id="final-route", figure=_empty_figure("最终路线")), style={**PANEL, "padding": "5px"}),
            ],
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "14px"},
        ),
        html.Div([html.H3("车辆路线明细"), _table("route-table", 10)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
    ]
)


process_page = html.Div(
    [
        html.Div(
            [
                html.Div([html.Div("DEEPBLOCK TRACE", className="eyebrow"), html.H2("B1 · B2 · B3 扫描过程", style={"margin": "6px 0"})]),
                html.Div(id="process-badges", style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
        ),
        html.Div([html.H3("Block 与接受决策"), _table("block-table", 10)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
        html.Div([html.H3("Top-k 候选（逐 bitstring 真路线评价）"), _table("candidate-table", 16)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
        html.Details(
            [
                html.Summary("查看完整 counts / QASM / 编译审计", style={"cursor": "pointer", "fontWeight": 700, "color": "#2f80ed"}),
                html.Pre(id="evidence-json", style={"whiteSpace": "pre-wrap", "fontSize": "12px", "lineHeight": "1.5", "color": "#5f7390", "maxHeight": "560px", "overflow": "auto"}),
            ],
            style={**PANEL, "padding": "18px", "marginTop": "14px"},
        ),
    ]
)


comparison_page = html.Div(
    [
        html.Div(id="fairness-strip", style={**PANEL, "padding": "14px 18px"}),
        html.Div(
            [
                html.Div(dcc.Graph(id="comparison-bars", figure=_empty_figure("最终距离对比")), style={**PANEL, "padding": "5px"}),
                html.Div(dcc.Graph(id="scan-lines", figure=_empty_figure("扫描距离变化")), style={**PANEL, "padding": "5px"}),
            ],
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "14px"},
        ),
        html.Div([html.H3("Initial / Hardware / Random / Simulator / Exact"), _table("comparison-table", 10)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
    ]
)


history_page = html.Div(
    [
        html.Div(
            [
                html.Div([html.Div("LOCAL HISTORY", className="eyebrow"), html.H2("运行历史与证据重载", style={"margin": "6px 0"})]),
                html.Div(
                    [
                        dcc.Dropdown(id="history-run-id", placeholder="选择 run ID", style={"minWidth": "310px"}),
                        html.Button("重新打开", id="open-history-btn", n_clicks=0, className="secondary-button"),
                        html.Button("刷新", id="refresh-history-btn", n_clicks=0, className="secondary-button"),
                    ],
                    style={"display": "flex", "gap": "10px", "alignItems": "center"},
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
        ),
        html.Div([_table("history-table", 12)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
        html.Div(id="history-detail", style={**PANEL, "padding": "18px", "marginTop": "14px"}),
    ]
)


app = Dash(__name__, title="Quantum Route Forge · DeepBlock", suppress_callback_exceptions=True)
app.layout = html.Div(
    [
        dcc.Store(id="run-store", data=INITIAL_PAYLOAD),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("QRF", className="logo-mark"),
                        html.Div(
                            [
                                html.Div("QUANTUM ROUTE FORGE", className="eyebrow"),
                                html.H1("Baihua DeepBlock 控制台", style={"margin": "3px 0", "fontSize": "30px"}),
                                html.Div("可复核的量子候选生成 · 经典约束修复 · 真实路线单调接受", style={"color": MUTED}),
                            ]
                        ),
                    ],
                    style={"display": "flex", "gap": "16px", "alignItems": "center"},
                ),
                html.Div(
                    [
                        html.Span("Baihua", className="status-pill"),
                        html.Span("≤ 8 qubits / block", className="status-pill"),
                        html.Span("Hardware ≠ fallback", className="status-pill"),
                    ],
                    style={"display": "flex", "gap": "8px"},
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "18px"},
        ),
        controls,
        html.Div(id="run-status", children=_initial_status_text(), className="status-banner"),
        dcc.Tabs(
            id="tabs",
            value="route",
            children=[
                dcc.Tab(label="01  路线优化", value="route", children=[route_page]),
                dcc.Tab(label="02  DeepBlock 过程", value="process", children=[process_page]),
                dcc.Tab(label="03  方法对比", value="comparison", children=[compm��nm�G����ƭy�          "blocks": [],
        }
    hardware_mean = sum(row["hardware_mass"] for row in rows) / len(rows)
    uniform_mean = sum(row["uniform_mass"] for row in rows) / len(rows)
    return {
        "evaluable": True,
        "definition": "exact bottom 10% proxy-QUBO energy rank",
        "blocks": rows,
        "mean_hardware_mass": hardware_mean,
        "mean_uniform_mass": uniform_mean,
        "enrichment": hardware_mean / uniform_mean,
        "difference_percentage_points": 100.0 * (hardware_mean - uniform_mean),
        "positive_blocks": sum(bool(row["positive"]) for row in rows),
        "total_blocks": len(rows),
        "interpretation": (
            "positive_low_energy_enrichment"
            if hardware_mean > uniform_mean
            else "no_positive_low_energy_enrichment"
        ),
    }


def _routes_payload(
    assignments: dict[int, list[Customer]],
    instance: DispatchInstance,
) -> list[dict[str, Any]]:
    plans = build_route_plans(assignments=assignments, depot=instance.depot, two_opt_rounds=2)
    return [
        {
            "vehicle_id": route.vehicle_id,
            "customer_ids": [customer.customer_id for customer in route.customers],
            "customers": [
                {
                    "customer_id": customer.customer_id,
                    "x": customer.x,
                    "y": customer.y,
                    "demand": customer.demand,
                }
                for customer in route.customers
            ],
            "load": route.load,
            "distance": route.distance,
        }
        for route in plans
    ]


def _instance_payload(instance: DispatchInstance) -> dict[str, Any]:
    return {
        "depot": list(instance.depot),
        "num_vehicles": instance.num_vehicles,
        "vehicle_capacity": instance.vehicle_capacity,
        "total_demand": instance.total_demand,
        "customers": [
            {
                "customer_id": customer.customer_id,
                "x": customer.x,
                "y": customer.y,
                "demand": customer.demand,
            }
            for customer in instance.customers
        ],
    }


def _result_payload(result: DeepBlockResult, instance: DispatchInstance) -> dict[str, Any]:
    raw = result.payload()
    raw["routes"] = _routes_payload(result.assignments, instance)
    raw["improvement_pct"] = (
        100.0 * result.improvement / result.baseline_distance
        if result.baseline_distance > 0
        else 0.0
    )
    raw["task_ids"] = [
        trace.run.task_id for trace in result.traces if trace.run.task_id
    ]
    raw["backend"] = next(
        (trace.run.backend for trace in result.traces if trace.run.backend),
        "",
    )
    raw["shots_received"] = sum(
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
