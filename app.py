from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
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
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


def _history_option_label(row: dict[str, Any]) -> str:
    """Build a compact, single-line label for the history selector."""
    raw_time = str(row.get("time") or "")
    try:
        parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        display_time = parsed.astimezone(CHINA_STANDARD_TIME).strftime("%m-%d %H:%M")
    except ValueError:
        display_time = raw_time[:16] or "-- --:--"
    mode = {
        "deepblock_hardware": "Hardware",
        "deepblock_random": "Random",
        "deepblock_simulator": "Simulator",
        "deepblock_exact": "Exact",
    }.get(str(row.get("mode") or ""), str(row.get("mode") or "Unknown"))
    status = str(row.get("status") or "UNKNOWN").upper()
    run_id = str(row.get("run_id") or "")
    short_id = run_id.rsplit("-", 1)[-1] if run_id else "--------"
    return f"{display_time} | {mode} | {status} | {short_id}"


def _latest_history_payload():
    try:
        rows = HISTORY.rows()
        return HISTORY.load(rows[0]["run_id"]) if rows else None
    except (OSError, ValueError, KeyError):
        return None


INITIAL_PAYLOAD = _latest_history_payload()


def _initial_status_text():
    if not INITIAL_PAYLOAD:
        return "å°šæœªè¿è¡Œã€‚Hardware æœªæ˜ç¡®ç¡®è®¤æ—¶ä»…è¿›è¡Œ dry-runï¼Œä¸ä¼šæäº¤ä»»åŠ¡ã€‚"
    selected = INITIAL_PAYLOAD.get("selected", {})
    return (
        f"å·²è½½å…¥æœ€è¿‘è¿è¡Œ {INITIAL_PAYLOAD.get('run_id')} Â· "
        f"{selected.get('status')} Â· source={selected.get('source')}"
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


def _empty_figure(title: str, subtitle: str = "è¿è¡Œåæ˜¾ç¤º"):
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
        labels = ["Depot"] + [f"C{row['customer_id']} Â· d={row['demand']}" for row in customers] + ["Depot"]
        figure.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=f"è½¦è¾† {route.get('vehicle_id')}",
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
                html.H3("åŒæ¡ä»¶å…¬å¹³å¯¹ç…§", style={"margin": "5px 0 0", "fontSize": "20px"}),
            ]
        ),
        html.Div(
            [
                _field("å®¢æˆ·æ•°", _number("num-customers", 16, 4, 60)),
                _field("è½¦è¾†æ•°", _number("num-vehicles", 3, 2, 10)),
                _field("è½¦è¾†å®¹é‡", _number("vehicle-capacity", 24, 2, 100)),
                _field("Seed", _number("seed", 2026, 0, 999999)),
                _field(
                    "è¿è¡Œæ¨¡å¼",
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
                    "label": " æˆ‘ç¡®è®¤ï¼šHardware æ¨¡å¼å°†çœŸå®æäº¤æœ€å¤š 3 ä¸ª Baihua ä»»åŠ¡",
                    "value": "confirm",
                }
            ],
            value=[],
            style={"fontSize": "13px", "color": "#a86800", "marginTop": "13px"},
        ),
        html.Div(
            [
                html.Button("è¿è¡Œ DeepBlock å¯¹ç…§", id="run-btn", n_clicks=0, className="run-button"),
                html.Div("åŒä¸€å®ä¾‹ Â· åŒä¸€åˆå§‹åˆ†é… Â· åŒä¸€ Top-k Â· ä¸¥æ ¼æ”¹å–„æ‰æ¥å—", style={"fontSize": "12px", "color": MUTED}),
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
                html.Div(dcc.Graph(id="initial-route", figure=_empty_figure("åˆå§‹è·¯çº¿")), style={**PANEL, "padding": "5px"}),
                html.Div(dcc.Graph(id="final-route", figure=_empty_figure("æœ€ç»ˆè·¯çº¿")), style={**PANEL, "padding": "5px"}),
            ],
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px", "marginTop": "14px"},
        ),
        html.Div([html.H3("è½¦è¾†è·¯çº¿æ˜ç»†"), _table("route-table", 10)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
    ]
)


process_page = html.Div(
    [
        html.Div(
            [
                html.Div([html.Div("DEEPBLOCK TRACE", className="eyebrow"), html.H2("B1 Â· B2 Â· B3 æ‰«æè¿‡ç¨‹", style={"margin": "6px 0"})]),
                html.Div(id="process-badges", style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
        ),
        html.Div([html.H3("Block ä¸æ¥å—å†³ç­–"), _table("block-table", 10)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
        html.Div([html.H3("Top-k å€™é€‰ï¼ˆé€ bitstring çœŸè·¯çº¿è¯„ä»·ï¼‰"), _table("candidate-table", 16)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
        html.Details(
            [
                html.Summary("æŸ¥çœ‹å®Œæ•´ counts / QASM / ç¼–è¯‘å®¡è®¡", style={"cursor": "pointer", "fontWeight": 700, "color": "#2f80ed"}),
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
                html.Div(dcc.Graph(id="comparison-bars", figure=_empty_figure("æœ€ç»ˆè·ç¦»å¯¹æ¯”")), style={**PANEL, "padding": "5px"}),
                html.Div(dcc.Graph(id="scan-lines", figure=_empty_figure("æ‰«æè·ç¦»å˜åŒ–")), style={**PANEL, "padding": "5px"}),
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
                html.Div([html.Div("LOCAL HISTORY", className="eyebrow"), html.H2("è¿è¡Œå†å²ä¸è¯æ®é‡è½½", style={"margin": "6px 0"})]),
                html.Div(
                    [
                        dcc.Dropdown(
                            id="history-run-id",
                            placeholder="é€‰æ‹©è¿è¡Œè®°å½•",
                            className="history-dropdown",
                            style={"width": "520px", "maxWidth": "65vw"},
                        ),
                        html.Button("é‡æ–°æ‰“å¼€", id="open-history-btn", n_clicks=0, className="secondary-button"),
                        html.Button("åˆ·æ–°", id="refresh-history-btn", n_clicks=0, className="secondary-button"),
                    ],
                    style={"display": "flex", "gap": "10px", "alignItems": "center", "flexWrap": "wrap"},
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
        ),
        html.Div([_table("history-table", 12)], style={**PANEL, "padding": "18px", "marginTop": "14px"}),
        html.Div(id="history-detail", style={**PANEL, "padding": "18px", "marginTop": "14px"}),
    ]
)


app = Dash(__name__, title="Quantum Route Forge Â· DeepBlock", suppress_callback_exceptions=True)
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
                                html.H1("Baihua DeepBlock æ§åˆ¶å°", style={"margin": "3px 0", "fontSize": "30px"}),
                                html.Div("å¯å¤æ ¸çš„é‡å­å€™é€‰ç”Ÿæˆ Â· ç»å…¸çº¦æŸä¿®ößÍ-¢G§²ÚîÆ­yÒˆ›ØÚ×Ü›İÜÈH×BˆØ[™Y]WÜ›İÜÈH×Bˆ]šY[˜ÙHH×Bˆ›Üˆ˜XÙH[ˆÙ[XİY™Ù]
˜XÙ\È‹×JN‚ˆ›ØÚÈH˜XÙVÈ˜›ØÚÈ—Bˆ[ˆH˜XÙVÈœ[ˆ—Bˆ˜]ÚH˜XÙK™Ù]
˜Ø[™Y]\ÈŠHÜˆßBˆ›ØÚ×Ü›İÜË˜\[™
ˆÂˆœÙ\]Y[˜ÙHˆ˜XÙVÈœÙ\]Y[˜ÙH—Kˆ˜›ØÚÈˆ›ØÚÖÈ˜›ØÚ×ÚY—Kˆ™ZXÛWÜZ\ˆˆİŠ›ØÚÖÈ™ZXÛWÜZ\ˆ—JKˆ˜İ\İÛY\œÈˆİŠ›ØÚÖÈ˜İ\İÛY\—ÚYÈ—JKˆÚYˆ›ØÚÖÈÚY—Kˆ™\ˆ[–Èœ\˜[Y]\œÈ—VÈ™\—Kˆ\Ú×ÚYˆ[‹™Ù]
\Ú×ÚYŠHÜˆ¸ %‹ˆ˜˜XÚÙ[™ˆ[‹™Ù]
˜˜XÚÙ[™ŠHÜˆ¸ %‹ˆœÚİÈˆİ[J[‹™Ù]
˜Ûİ[È‹ßJK˜[Y\Ê
JKˆ˜XØÙ\Yˆ˜XÙVÈ˜XØÙ\Y—Kˆ™\İ[˜ÙHˆ›İ[™
˜XÙVÈ™\İ[˜ÙWØY\ˆ—KŠKˆ™XÚ\Ú[Ûˆˆ˜XÙVÈ™XÚ\Ú[Ûˆ—Kˆœİ]\Èˆ˜XÙVÈœİ]\È—KˆBˆ
Bˆ›Üˆ˜[šË›İÈ[ˆ[[Y\˜]J˜]Ú™Ù]
ÜÙœ™\]Y[˜ŞH‹×JKİ\LJN‚ˆØ[™Y]WÜ›İÜË˜\[™
ˆÂˆ˜›ØÚÈˆ›ØÚÖÈ˜›ØÚ×ÚY—Kˆœ˜[šÈˆ˜[šËˆ˜š]İš[™Èˆ›İÖÈ˜š]İš[™È—Kˆ˜Ûİ[ˆ›İÖÈ˜Ûİ[—Kˆœ›Ø˜Xš[]Hˆ›İ[™
›İÖÈœ›Ø˜Xš[]H—KŠKˆœ›ŞWÙ[™\™ŞHˆ›İ[™
›İÖÈœ›ŞWÙ[™\™ŞH—KŠKˆ™™X\ÚX›Hˆ›İÖÈ™™X\ÚX›WØY\—Ü™\Z\ˆ—Kˆœ™\Z\™Yˆ›İÖÈœ™\Z\™Y—Kˆœ™\Z\ˆˆ›İÖÈœ™\Z\—Üİ[[X\H—KˆYWÙ\İ[˜ÙHˆ›İ[™
›İÖÈYWÙ\İ[˜ÙH—KŠKˆš[\›İ™[Y[ˆ›İ[™
›İÖÈš[\›İ™[Y[—KŠKˆ˜XØÙ\Yˆ›ÛÛ
˜]Ú™Ù]
˜XØÙ\YŠH[™˜]ÚÈ˜XØÙ\Y—VÈ˜š]İš[™È—HOH›İÖÈ˜š]İš[™È—JKˆBˆ
Bˆ]šY[˜ÙK˜\[™
ˆÂˆ˜›ØÚÈˆ›ØÚËˆœÛİ\˜ÙHˆ˜XÙVÈœÛİ\˜ÙH—Kˆœİ]\Èˆ˜XÙVÈœİ]\È—Kˆ\Ú×ÚYˆ[‹™Ù]
\Ú×ÚYŠKˆ˜˜XÚÙ[™ˆ[‹™Ù]
˜˜XÚÙ[™ŠKˆœÚİÈˆ[‹™Ù]
œÚİÈŠKˆ˜Ûİ[Èˆ[‹™Ù]
˜Ûİ[ÈŠKˆœX\ÛHˆ[‹™Ù]
œX\ÛHŠKˆœ\ÚXØ[ÜX\ÛHˆ[‹™Ù]
œ\ÚXØ[ÜX\ÛHŠKˆ˜ÛÛ\[][Ûˆˆ[‹™Ù]
˜ÛÛ\[][ÛˆŠKˆ›Y\ÜØYÙHˆ[‹™Ù]
›Y\ÜØYÙHŠKˆBˆ
Bˆ›ØÚ×ØÛÛ[[œÈHŞÈ›˜[YHˆÙ^Kœ™\XÙJ—È‹ˆŠK]J
KšYˆÙ^_H›ÜˆÙ^H[ˆ
›ØÚ×Ü›İÜÖÌKšÙ^\Ê
HYˆ›ØÚ×Ü›İÜÈ[ÙH×JWBˆØ[™Y]WØÛÛ[[œÈHŞÈ›˜[YHˆÙ^Kœ™\XÙJ—È‹ˆŠK]J
KšYˆÙ^_H›ÜˆÙ^H[ˆ
Ø[™Y]WÜ›İÜÖÌKšÙ^\Ê
HYˆØ[™Y]WÜ›İÜÈ[ÙH×JWBˆ˜YÙ\ÈHÂˆ[”Ü[ŠˆœÛİ\˜ÙO^ÜÙ[XİY™Ù]
	ÜÛİ\˜ÙIÊ_H‹Û\ÜÓ˜[YOHœİ]\Ë\[ŠKˆ[”Ü[Šˆ˜˜XÚÙ[™^ÜÙ[XİY™Ù]
	Ø˜XÚÙ[™	ÊHÜˆ	ø %	ßH‹Û\ÜÓ˜[YOHœİ]\Ë\[ŠKˆ[”Ü[Šˆ\ÚÜÏ^Û[ŠÙ[XİY™Ù]
	İ\Ú×ÚYÉË×JJ_H‹Û\ÜÓ˜[YOHœİ]\Ë\[ŠKˆ[”Ü[ŠˆœÚİÈ™XÙZ]™Y^ÜÙ[XİY™Ù]
	ÜÚİ×Ü™XÙZ]™Y	Ë
_H‹Û\ÜÓ˜[YOHœİ]\Ë\[ŠKˆBˆ]X[[WÙY™™XİH^[ØY™Ù]
œ]X[[WÙY™™XİŠHÜˆßBˆYˆ]X[[WÙY™™Xİ™Ù]
™]˜[XX›HŠN‚ˆ˜YÙ\Ë™^[™
ˆÂˆ[”Ü[Šˆˆ¹§ 9/cŒL	z ïzaãú-*:aãÏ^ÌL
ˆ]X[[WÙY™™XİÉÛYX[—Ú\™Ø\™WÛX\ÜÉ×N‹Œ™ŸIH‹ˆÛ\ÜÓ˜[YOHœİ]\Ë\[‹ˆ
Kˆ[”Ü[Šˆˆ¹æî9kîygaùc :f£ù§.^Ü]X[[WÙY™™XİÉÙ[œšXÚY[	×N‹Œ™ŸpåÈ‹ˆÛ\ÜÓ˜[YOHœİ]\Ë\[‹ˆ
KˆBˆ
B‚ˆÛÛ\\š\ÛÛœÈH^[ØY™Ù]
˜ÛÛ\\š\ÛÛœÈ‹×JBˆ˜\ˆHÛË‘šYİ\™JˆÛË˜\ŠˆVÜ›İÖÈ›Y]Ù—H›Üˆ›İÈ[ˆÛÛ\\š\ÛÛœ×KˆOVÂˆ›İÖÈ™š[˜[Ù\İ[˜ÙH—BˆYˆ›İÖÈœİ]\È—HOHÓÓTUQ‚ˆ[ÙH›Û™Bˆ›Üˆ›İÈ[ˆÛÛ\\š\ÛÛœÂˆKˆ^VÂˆˆÜ›İÖÉÙš[˜[Ù\İ[˜ÙI×N‹Œ™ŸH‚ˆYˆ›İÖÈœİ]\È—HOHÓÓTUQ‚ˆ[ÙH“‹ÑH‚ˆ›Üˆ›İÈ[ˆÛÛ\\š\ÛÛœÂˆKˆ^ÜÚ][ÛH›İ]ÚYH‹ˆX\šÙ\^È˜ÛÛÜˆˆÈˆÎLXMÈ‹ˆÍØÍXÙ˜È‹ˆÙŒ˜NLØˆ‹ˆÌ™Y‹ˆÌŒ˜L˜ˆ—_Kˆ
Bˆ
Bˆ˜\‹\]WÛ^[İ]
ˆ[\]OHœİWİÚ]H‹ˆ]OH¹§ 9îâ9ç'ùk§º-ëùî¯ú-çyé®ûï":-¢¹/cº-¢¹io{ï"H‹ˆ\\—Ø™ØÛÛÜHœ™Ø˜J
H‹ˆİØ™ØÛÛÜHˆÙ˜™™™ˆ‹ˆZYÚMLˆX\™Ú[^È›ˆKœˆˆŒˆMK˜ˆˆÍ_Kˆ›Û^È˜ÛÛÜˆˆS’ßKˆX^\Ï^È™ÜšYÛÛÜˆˆˆÙNYYˆŸKˆ
BˆØØ[ˆHÛË‘šYİ\™J
Bˆ›Üˆ[™^
\›WÛ[ÙK\›JH[ˆ[[Y\˜]J^[ØY™Ù]
˜\›\È‹ßJKš][\Ê
JN‚ˆ\ÈHØ\›VÈ˜˜\Ù[[™WÙ\İ[˜ÙH—WH
Èİ˜XÙVÈ™\İ[˜ÙWØY\ˆ—H›Üˆ˜XÙH[ˆ\›K™Ù]
˜XÙ\È‹×JWBˆÈHÈ’[š]X[—H
ÈÙˆİ˜XÙVÉØ›ØÚÉ×VÉØ›ØÚ×ÚY	×_p­Şİ˜XÙVÉÜÙ\]Y[˜ÙI×_Hˆ›Üˆ˜XÙH[ˆ\›K™Ù]
˜XÙ\È‹×JWBˆØØ[‹˜Yİ˜XÙJˆÛË”ØØ]\Šˆ^ËˆO^\Ëˆ[ÙOH›[™\ÊÛX\šÙ\œÈ‹ˆ˜[YOX\›VÈœÛİ\˜ÙH—K]J
Kˆ[™O^È˜ÛÛÜˆˆÓÓÔ”ÖÚ[™^	H[ŠÓÓÔ”ÊWKÚYˆ‹Kˆ
Bˆ
BˆØØ[‹\]WÛ^[İ]
ˆ[\]OHœİWİÚ]H‹ˆ]OH‘Y\›ØÚÈ9¢jù£ãú-çyé®ùcæ9c%ˆ‹ˆ\\—Ø™ØÛÛÜHœ™Ø˜J
H‹ˆİØ™ØÛÛÜHˆÙ˜™™™ˆ‹ˆZYÚMLˆX\™Ú[^È›ˆKœˆˆŒˆMK˜ˆˆÍ_Kˆ›Û^È˜ÛÛÜˆˆS’ßKˆX^\Ï^È™ÜšYÛÛÜˆˆˆÙNYYˆŸKˆ
BˆÛÛ\\š\ÛÛ—Ü›İÜÈHÂˆÂˆ›Y]Ùˆ›İÖÈ›Y]Ù—KˆœÛİ\˜ÙHˆ›İÖÈœÛİ\˜ÙH—Kˆœİ]\Èˆ›İÖÈœİ]\È—Kˆ™š[˜[Ù\İ[˜ÙHˆ›İ[™
›İÖÈ™š[˜[Ù\İ[˜ÙH—KŠKˆš[\›İ™[Y[ˆ›İ[™
›İÖÈš[\›İ™[Y[—KŠKˆš[\›İ™[Y[Üİˆ›İ[™
›İÖÈš[\›İ™[Y[Üİ—KÊKˆ˜XØÙ\YÛ[İ™\Èˆ›İÖÈ˜XØÙ\YÛ[İ™\È—Kˆ\Ú×ÚYÈˆ‹‹š›Ú[Š›İË™Ù]
\Ú×ÚYÈ‹×JJHÜˆ¸ %‹ˆBˆ›Üˆ›İÈ[ˆÛÛ\\š\ÛÛœÂˆBˆÛÛ\\š\ÛÛ—ØÛÛ[[œÈHŞÈ›˜[YHˆÙ^Kœ™\XÙJ—È‹ˆŠK]J
KšYˆÙ^_H›ÜˆÙ^H[ˆÛÛ\\š\ÛÛ—Ü›İÜÖÌWBˆ˜Z\›™\ÜÈH^[ØY™Ù]
™˜Z\›™\ÜÈ‹ßJBˆ˜Z\›™\Ü×İ^H[‘]ŠˆÂˆ[”İ›Û™Ê¹ak9nlù )úe yk¦»ï&ˆ‹İ[O^È˜ÛÛÜˆˆˆÌ™YŸJKˆ[”Ü[Šˆ9æî9d#9k§¹/¢ÈÈ9b'yiâùb!ºacHÈŒKPŒÈÈÚİÈÈÜZÈÈ9/ë¹i#HÈ:-ëùî¯ú+á9.íùfjÈ9.)y¨/9£©ycåú)á9b&HŠKˆ[”Ü[Šˆ0­È9aj:`ê:`&º/áÈˆYˆ[
˜Z\›™\ÜË˜[Y\Ê
JH[ÙHˆ0­È:+íù¨à9§éH‹İ[O^È˜ÛÛÜˆˆˆÌMŒˆŸJKˆBˆ
Bˆ\İÜWÙ]Z[H[‘]ŠˆÂˆ[’Êˆ¹odùbcyîäù§§0­ÈÜ^[ØY™Ù]
	Ü[—ÚY	Ê_HŠKˆ[”
ˆˆÜ^[ØYÉØÜ™X]YØ]	×_H0­ÈÙYY^Ü^[ØYÉÜ\˜[Y]\œÉ×VÉÜÙYY	×_H0­È‚ˆˆÜ^[ØYÉÜ\˜[Y]\œÉ×VÉÛ[WØİ\İÛY\œÉ×_Hİ\İÛY\œÈ0­ÈÜ^[ØYÉÜ\˜[Y]\œÉ×VÉÛ[Wİ™ZXÛ\É×_H™ZXÛ\È‹ˆİ[O^È˜ÛÛÜˆˆUUQKˆ
Kˆ[”
ˆˆœÛİ\˜ÙO^ÜÙ[XİY™Ù]
	ÜÛİ\˜ÙIÊ_H0­È˜XÚÙ[™^ÜÙ[XİY™Ù]
	Ø˜XÚÙ[™	ÊHÜˆ	ø %	ßH0­È‚ˆˆ\ÚÈQÏ^ÉË	Ëš›Ú[ŠÙ[XİY™Ù]
	İ\Ú×ÚYÉË×JJHÜˆ	ø %	ßH0­Èİ]\Ï^ÜÙ[XİY™Ù]
	Üİ]\ÉÊ_H‚ˆ
Kˆ
ˆ[”
ˆˆ¹§ 9/cŒL	HUP“È: ïzaãùc.¹gçûï&’\™Ø\™H‚ˆˆÌL
ˆ]X[[WÙY™™XİÉÛYX[—Ú\™Ø\™WÛX\ÜÉ×N‹Œ™ŸIHœÈ[šY›Ü›H‚ˆˆÌL
ˆ]X[[WÙY™™XİÉÛYX[—İ[šY›Ü›WÛX\ÜÉ×N‹Œ™ŸIH0­È‚ˆˆÜ]X[[WÙY™™XİÉÙ[œšXÚY[	×N‹Œ™ŸpåÈ0­È‚ˆˆÜ]X[[WÙY™™XİÉÜÜÚ]]™WØ›ØÚÜÉ×_KŞÜ]X[[WÙY™™XİÉİİ[Ø›ØÚÜÉ×_H›ØÚÜÈ9..¹«hùd$H‹ˆİ[O^È˜ÛÛÜˆˆˆÌMŒˆ‹™›ÛÙZYÚˆÌKˆ
BˆYˆ]X[[WÙY™™Xİ™Ù]
™]˜[XX›HŠBˆ[ÙH›Û™Bˆ
Kˆ[”
•Ø\›š[™ÜÎˆˆ
È
ˆ‹š›Ú[Š^[ØY™Ù]
Ø\›š[™ÜÈ‹×JJHÜˆ››Û™HŠKİ[O^È˜ÛÛÜˆˆˆØNŸJKˆBˆ
Bˆ™]\›ˆ
ˆY]šXÜËˆ[š]X[ÙšYİ\™Kˆš[˜[ÙšYİ\™Kˆ›İ]WÜ›İÜËˆ›İ]WØÛÛ[[œËˆ›ØÚ×Ü›İÜËˆ›ØÚ×ØÛÛ[[œËˆØ[™Y]WÜ›İÜËˆØ[™Y]WØÛÛ[[œËˆ˜YÙ\ËˆœÛÛ‹™[\Ê]šY[˜ÙK[œİ\™WØ\ØÚZOQ˜[ÙK[™[LŠKˆ˜\‹ˆØØ[‹ˆÛÛ\\š\ÛÛ—Ü›İÜËˆÛÛ\\š\ÛÛ—ØÛÛ[[œËˆ˜Z\›™\Ü×İ^ˆ\İÜWÙ]Z[ˆ
B‚‚\˜Ø[˜XÚÊˆİ]]
š\İÜK]X›H‹™]HŠKˆİ]]
š\İÜK]X›H‹˜ÛÛ[[œÈŠKˆİ]]
š\İÜK\[‹ZY‹›Ü[ÛœÈŠKˆ[œ]
œ™Yœ™\ÚZ\İÜKXˆ‹›—ØÛXÚÜÈŠKˆ[œ]
œ[‹\İÜ™H‹™]HŠKŠB™Yˆ™Yœ™\ÚÚ\İÜJØÛXÚÜËÜ^[ØY
N‚ˆ›İÜÈHTÕÔ–Kœ›İÜÊ
BˆÛÛ[[œÈHŞÈ›˜[YHˆÙ^Kœ™\XÙJ—È‹ˆŠK]J
KšYˆÙ^_H›ÜˆÙ^H[ˆ
›İÜÖÌKšÙ^\Ê
HYˆ›İÜÈ[ÙH×JWBˆÜ[ÛœÈHÂˆÈ›X™[ˆÚ\İÜWÛÜ[Û—ÛX™[
›İÊK˜[YHˆ›İÖÈœ[—ÚY—_Bˆ›Üˆ›İÈ[ˆ›İÜÂˆBˆ™]\›ˆ›İÜËÛÛ[[œËÜ[ÛœÂ‚‚˜\š[™^Üİš[™ÈHˆˆ‚QĞÕTH[‚[‚ˆXY‚ˆÉ[Y]\É_Bˆ]OÉ]]I_Oİ]O‚ˆÉY˜]šXÛÛ‰_BˆÉXÜÜÉ_Bˆİ[O‚ˆœ›ÛİÈÛÛÜ‹\ØÚ[YNˆYÚÈBˆ
ˆÈ›Ş\Ú^š[™Îˆ›Ü™\‹X›ŞÈBˆ›ÙHÂˆX\™Ú[ˆÂˆ›Û\Ú^™NˆM\Âˆ[™KZZYÚˆKNÂˆ˜XÚÙÜ›İ[™‚ˆ˜YX[YÜ˜YY[
Ú\˜ÛH]L‰H	K™Ø˜JMKMÌKMKŒŒ
K˜[œÜ\™[ÌIJKˆ˜YX[YÜ˜YY[
Ú\˜ÛH]	H	K™Ø˜JMLKLŒËMKŒM
K˜[œÜ\™[	JKˆ[™X\‹YÜ˜YY[
NYËÙÙ˜Y™ˆ	KÙŒÙ™˜ˆL	JNÂˆ›ÛY˜[Z[Nˆ”ÙYÛÙHRH‹“ZXÜ›ÜÛÙXRZH‹Ø[œË\Ù\šYÂˆBˆ›ÙÛË[X\šÈÂˆÚYˆMÈZYÚˆMÈ\Ü^NˆÜšYÈXÙKZ][\ÎˆÙ[\Âˆ›Ü™\‹\˜Y]\ÎˆMœÈÛÛÜˆÙ™™™™™È›Û]ÙZYÚˆLÈ]\‹\ÜXÚ[™ÎˆL\Âˆ˜XÚÙÜ›İ[™ˆ[™X\‹YÜ˜YY[
MYYËÌÙMÙKÍØÍXÙ˜ÊNÂˆ›Ş\ÚYİÎˆL™Ø˜JËLŒNŒŒŠNÂˆBˆ™^YXœ›İÈÈ›Û\Ú^™NˆL\È]\‹\ÜXÚ[™Îˆ‹ÈÛÛÜˆÌ™YÈ›Û]ÙZYÚˆÈBˆœİ]\Ë\[Âˆ\Ü^Nˆ[›[™KY›^È[YÛ‹Z][\ÎˆÙ[\ÈZ[‹ZZYÚˆÈY[™Îˆ\LÂˆ›Ü™\ˆ\ÛÛYØÙ™LÈ›Ü™\‹\˜Y]\ÎˆNN\Âˆ˜XÚÙÜ›İ[™ˆÙYY™ÈÛÛÜˆÌÌMXÈ›Û\Ú^™NˆLœÈ›Û]ÙZYÚˆÌÂˆBˆœİ]\ËX˜[›™\ˆÂˆX\™Ú[ˆLÜÈY[™ÎˆL\M\È›Ü™\‹[YˆÜÛÛYÌ™YÂˆ›Ü™\‹\˜Y]\ÎˆÈ˜XÚÙÜ›İ[™ˆÙY™™ÈÛÛÜˆÍMÎÎÈ›Û\Ú^™NˆLÜÂˆ›Ş\ÚYİÎˆœN™Ø˜JŒËLËMNŒÊNÂˆBˆœ[‹X]Û‹œÙXÛÛ™\KX]ÛˆÂˆ›Ü™\ˆÈ›Ü™\‹\˜Y]\ÎˆLÈY[™ÎˆL\NÈİ\œÛÜˆÚ[\Âˆ›Û\Ú^™NˆMÈ›Û]ÙZYÚˆÈÛÛÜˆÙ™™™™™È˜XÚÙÜ›İ[™ˆ[™X\‹YÜ˜YY[
LYËÌÙMÙKÍØÍXÙ˜ÊNÂˆ›Ş\ÚYİÎˆN™Ø˜JÎKL‹ŒLKŒN
NÂˆBˆœÙXÛÛ™\KX]ÛˆÈÛÛÜˆÌÍNMÎÈ˜XÚÙÜ›İ[™ˆÙ™™™™™È›Ü™\ˆ\ÛÛYØÙY™XNÈ›Ş\ÚYİÎˆ›Û™NÈBˆ[œ]”Ù[XİXÛÛ›Û™\ÚY›ÜİÛˆ”Ù[XİXÛÛ›ÛÂˆ›Ü™\‹\˜Y]\Îˆ\Z[\Ü[È›Ü™\ˆ\ÛÛYØÙ™YXHZ[\Ü[Âˆ˜XÚÙÜ›İ[™ˆÙ™™™™™ˆZ[\Ü[ÈÛÛÜˆÌNÌMLÈZ[\Ü[Âˆ›Û\Ú^™NˆMZ[\Ü[Âˆ›Ş\ÚYİÎˆœ\™Ø˜JKL‹LKŒ
NÂˆBˆ[œ]™›Øİ\ÈÈ›Ü™\‹XÛÛÜˆÍNYHZ[\Ü[Èİ][™Nˆ›Û™NÈ›Ş\ÚYİÎˆÜ™Ø˜JËLŒÍËŒL
NÈBˆ”Ù[Xİ[Y[K[İ]\ˆÈ˜XÚÙÜ›İ[™ˆÙ™™™™™ˆZ[\Ü[È›Ü™\‹XÛÛÜˆØÙ™YXHZ[\Ü[ÈBˆ”Ù[Xİ]˜[YK[X™[”Ù[Xİ\XÙZÛ\ˆÈÛÛÜˆÌNÌMLÈZ[\Ü[ÈBˆ”Ù[Xİ[Ü[ÛˆÈÛÛÜˆÌMˆZ[\Ü[È˜XÚÙÜ›İ[™ˆÙ™™™™™ˆZ[\Ü[ÈBˆ”Ù[Xİ[Ü[Û‹š\ËY›Øİ\ÙYÈ˜XÚÙÜ›İ[™ˆÙYY™ˆZ[\Ü[ÈBˆš\İÜKY›ÜİÛˆ”Ù[XİXÛÛ›ÛÈZ[‹ZZYÚˆœZ[\Ü[ÈZYÚˆœZ[\Ü[ÈBˆš\İÜKY›ÜİÛˆ”Ù[Xİ\XÙZÛ\‹ˆš\İÜKY›ÜİÛˆ”Ù[Xİ]˜[YHÈ[™KZZYÚˆZ[\Ü[ÈBˆš\İÜKY›ÜİÛˆ”Ù[Xİ]˜[YK[X™[Âˆ\Ü^Nˆ›ØÚÈZ[\Ü[Èİ™\™›İÎˆY[ˆZ[\Ü[Âˆ^[İ™\™›İÎˆ[\Ú\ÈZ[\Ü[ÈÚ]K\ÜXÙNˆ›İÜ˜\Z[\Ü[ÂˆBˆš\İÜKY›ÜİÛˆ”Ù[Xİ[Y[K[İ]\ˆÂˆZ[‹]ÚYˆLŒZ[\Ü[È‹Z[™^ˆLLZ[\Ü[ÂˆBˆš\İÜKY›ÜİÛˆ”Ù[Xİ[Ü[ÛˆÂˆZ[‹ZZYÚˆZ[\Ü[ÈY[™ÎˆLLœZ[\Ü[Âˆ[™KZZYÚˆŒZ[\Ü[Èİ™\™›İÎˆY[ˆZ[\Ü[Âˆ^[İ™\™›İÎˆ[\Ú\ÈZ[\Ü[ÈÚ]K\ÜXÙNˆ›İÜ˜\Z[\Ü[ÂˆBˆXˆÈ˜XÚÙÜ›İ[™ˆ™Ø˜JMKMKMKÍŠHZ[\Ü[ÈÛÛÜˆÍÌYˆZ[\Ü[È›Ü™\ˆZ[\Ü[ÈY[™ÎˆMZ[\Ü[È›Û\Ú^™NˆM\Z[\Ü[ÈBˆX‹K\Ù[XİYÈÛÛÜˆÌ™YZ[\Ü[È›Ü™\‹]ÜˆœÛÛYÌ™YZ[\Ü[È˜XÚÙÜ›İ[™ˆÙ™™™™™ˆZ[\Ü[È›Û]ÙZYÚˆÌÈBˆX‹XÛÛ[ÈY[™Ë]ÜˆM\ÈBˆYYXH
X^]ÚYˆL
HÂˆÛY]šXË\›İÈÈÜšY][\]KXÛÛ[[œÎˆYœˆYœˆZ[\Ü[ÈBˆBˆÜİ[O‚ˆÚXY‚ˆ›ÙO‚ˆÉX\Ù[I_Bˆ›Ûİ\ÉXÛÛ™šYÉ_^É\ØÜš\É_^É\™[™\™\‰_OÙ›Ûİ\‚ˆØ›ÙO‚Ú[‚ˆˆˆ‚‚‚šYˆ×Û˜[YW×ÈOH—×ÛXZ[—×È‚ˆ\œÙ\ˆH\™Ü\œÙK\™İ[Y[\œÙ\Š\ØÜš\[ÛH”]X[[H›İ]H›Ü™ÙHÛÛ\]][ÛˆRHŠBˆ\œÙ\‹˜YØ\™İ[Y[
‹KZÜİ‹Y˜][HŒLËŒŒŒHŠBˆ\œÙ\‹˜YØ\™İ[Y[
‹K\Ü‹\OZ[Y˜][NL
Bˆ\œÙ\‹˜YØ\™İ[Y[
‹KYXYÈ‹Xİ[ÛHœİÜ™WİYHŠBˆ\™ÜÈH\œÙ\‹œ\œÙWØ\™ÜÊ
Bˆ\œ[ŠÜİX\™ÜËšÜİÜX\™ÜËœÜXYÏX\™ÜË™XYÊB