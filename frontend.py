# frontend.py

COLORS = {8000: '#00f2fe', 8001: '#ff0844', 8002: '#b100ff'} # Updated to more vibrant, neon tones

CUSTOM_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    /* Animated Particle-like Background Base */
    body {
        margin: 0;
        padding: 0;
        font-family: 'Outfit', sans-serif;
        background-color: #020617; /* Deepest slate */
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,0.2) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,30%,0.2) 0, transparent 50%);
        background-attachment: fixed;
        background-size: 200% 200%;
        color: #f8fafc;
        animation: gradient-shift 15s ease infinite;
        overflow-x: hidden;
    }

    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Vibrant Animated Title */
    .dashboard-title {
        text-align: center;
        padding: 40px 20px 20px 20px;
        font-weight: 800;
        font-size: 3.5rem;
        background: linear-gradient(to right, #00f2fe, #4facfe, #00f2fe);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 4s linear infinite;
        margin: 0;
        letter-spacing: -1px;
    }

    @keyframes shine {
        to { background-position: 200% center; }
    }

    /* Elevated Glassmorphism */
    .glass-card {
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-radius: 24px;
        padding: 35px 30px;
        width: 320px;
        text-align: center;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        border: 1px solid rgba(255, 255, 255, 0.05);
        position: relative;
        overflow: hidden;
    }

    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(to right, rgba(255,255,255,0) 0%, rgba(255,255,255,0.03) 50%, rgba(255,255,255,0) 100%);
        transform: skewX(-25deg);
        transition: all 0.75s;
    }

    .glass-card:hover::before {
        left: 125%;
    }

    .glass-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .card-title {
        font-weight: 800;
        margin: 0 0 25px 0;
        font-size: 2.2rem;
        letter-spacing: -0.5px;
        text-transform: uppercase;
    }

    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 5px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        font-size: 16px;
        font-weight: 400;
        transition: background 0.2s ease;
        border-radius: 8px;
    }

    .data-row:hover {
        background: rgba(255, 255, 255, 0.03);
        padding-left: 10px;
        padding-right: 10px;
    }

    .data-row:last-child {
        border-bottom: none;
    }

    .data-label {
        color: #94a3b8;
        font-weight: 400;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Premium Animated Button */
    .btn-premium {
        background: linear-gradient(135deg, #4f46e5 0%, #ec4899 100%);
        color: white;
        border: none;
        padding: 16px 28px;
        border-radius: 14px;
        cursor: pointer;
        font-weight: 800;
        width: 100%;
        font-size: 15px;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-shadow: 0 4px 15px rgba(236, 72, 153, 0.3);
        font-family: 'Outfit', sans-serif;
        margin-top: 25px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        position: relative;
        overflow: hidden;
        z-index: 1;
    }

    .btn-premium::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: #000;
        border-radius: 14px;
        z-index: -2;
    }

    .btn-premium::before {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 0%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.2);
        transition: all 0.4s;
        border-radius: 14px;
        z-index: -1;
    }

    .btn-premium:hover::before {
        width: 100%;
    }

    .btn-premium:hover {
        box-shadow: 0 8px 30px rgba(236, 72, 153, 0.5);
        transform: translateY(-2px);
    }

    .btn-back {
        background: rgba(30, 41, 59, 0.6);
        color: #cbd5e1;
        padding: 12px 28px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        backdrop-filter: blur(8px);
    }

    .btn-back:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
        transform: translateX(-5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    .alert-pulsing {
        animation: pulse-danger 1.5s infinite;
        background: rgba(239, 68, 68, 0.1);
        padding: 8px 16px;
        border-radius: 8px;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .status-stable {
        background: rgba(16, 185, 129, 0.1);
        padding: 8px 16px;
        border-radius: 8px;
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #10b981;
    }

    @keyframes pulse-danger {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    /* Sleek AI Launch Bar */
    .ai-launch-bar {
        display: flex;
        align-items: center;
        margin-top: 15px;
        margin-bottom: 30px;
        background: rgba(15, 23, 42, 0.8);
        padding: 12px 30px;
        border-radius: 50px;
        border: 1px solid rgba(56, 189, 248, 0.4);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(56, 189, 248, 0.1);
        backdrop-filter: blur(12px);
        transition: all 0.3s ease;
    }
    
    .ai-launch-bar:hover {
        border-color: rgba(56, 189, 248, 0.8);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 0 20px rgba(56, 189, 248, 0.2), 0 0 20px rgba(56, 189, 248, 0.2);
        transform: translateY(-2px);
    }

    /* Modal Overhaul */
    .modal-overlay {
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(2, 6, 23, 0.9);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        z-index: 1000;
        justify-content: center;
        align-items: center;
    }
    
    .modal-content {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 24px;
        width: 92vw;
        height: 92vh;
        padding: 40px;
        box-shadow: 0 25px 80px rgba(0,0,0,1), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative;
        display: flex;
        flex-direction: column;
    }
    
    .btn-close-modal {
        position: absolute;
        top: 30px; right: 35px;
        background: rgba(239, 68, 68, 0.1);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 10px 20px;
        border-radius: 12px;
        cursor: pointer;
        font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 16px;
        transition: all 0.2s;
        z-index: 10;
        backdrop-filter: blur(4px);
    }
    
    .btn-close-modal:hover {
        background: rgba(239, 68, 68, 0.9); color: #fff;
        box-shadow: 0 0 20px rgba(239,68,68,0.6);
        transform: scale(1.05);
    }
    
    /* Loading Spinner for Empty State */
    .loader {
        width: 48px;
        height: 48px;
        border: 5px solid rgba(56, 189, 248, 0.2);
        border-bottom-color: #38bdf8;
        border-radius: 50%;
        display: inline-block;
        box-sizing: border-box;
        animation: rotation 1s linear infinite;
        margin-bottom: 20px;
    }

    @keyframes rotation {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* ── Tab Switcher ─────────────────────────────────────── */
    .tab-switcher {
        display: flex;
        gap: 6px;
        background: rgba(10, 15, 30, 0.6);
        border-radius: 12px;
        padding: 5px;
        border: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 16px;
    }

    .tab-btn {
        padding: 9px 22px;
        border-radius: 8px;
        border: 1px solid transparent;
        background: transparent;
        color: #64748b;
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.25s ease;
        letter-spacing: 0.3px;
    }

    .tab-btn:hover {
        background: rgba(255,255,255,0.05);
        color: #cbd5e1;
    }

    .tab-btn-live-active {
        background: rgba(56, 189, 248, 0.12) !important;
        color: #38bdf8 !important;
        border-color: rgba(56, 189, 248, 0.35) !important;
    }

    .tab-btn-matlab-active {
        background: rgba(167, 139, 250, 0.12) !important;
        color: #a78bfa !important;
        border-color: rgba(167, 139, 250, 0.35) !important;
    }

    /* ── MATLAB Run Button ────────────────────────────────── */
    .btn-matlab {
        background: linear-gradient(135deg, #6d28d9 0%, #a78bfa 100%);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 10px;
        cursor: pointer;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 14px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(109, 40, 217, 0.35);
        letter-spacing: 0.4px;
        white-space: nowrap;
    }

    .btn-matlab:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(109, 40, 217, 0.6);
    }

    /* ── MATLAB Stats Badges ──────────────────────────────── */
    .matlab-stats-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        padding: 12px 4px;
        justify-content: center;
        margin-bottom: 8px;
    }

    .stat-badge {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(167, 139, 250, 0.15);
        border-radius: 14px;
        padding: 14px 20px;
        text-align: center;
        min-width: 105px;
        transition: all 0.25s ease;
    }

    .stat-badge:hover {
        border-color: rgba(167, 139, 250, 0.5);
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(109, 40, 217, 0.25);
    }

    .stat-badge-label {
        font-size: 10px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .stat-badge-value {
        font-size: 19px;
        font-weight: 800;
        font-family: 'Outfit', sans-serif;
    }

    /* ── MATLAB Status Label ──────────────────────────────── */
    .matlab-status {
        text-align: center;
        font-size: 13px;
        font-family: 'Outfit', sans-serif;
        padding: 4px 0 12px 0;
        color: #64748b;
        letter-spacing: 0.3px;
    }

    /* ── SHM Report Gallery ───────────────────────────────── */
    .shm-run-btn {
        background: linear-gradient(135deg, #059669 0%, #34d399 100%);
        color: white;
        border: none;
        padding: 12px 28px;
        border-radius: 12px;
        cursor: pointer;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 15px;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 18px rgba(5, 150, 105, 0.4);
    }

    .shm-run-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(5, 150, 105, 0.65);
    }

    .shm-tab-btn-active {
        background: rgba(52, 211, 153, 0.12) !important;
        color: #34d399 !important;
        border-color: rgba(52, 211, 153, 0.35) !important;
    }

    .shm-status {
        text-align: center;
        font-size: 13px;
        font-family: 'Outfit', sans-serif;
        padding: 4px 0 12px 0;
        color: #64748b;
        letter-spacing: 0.3px;
    }

    .shm-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(520px, 1fr));
        gap: 20px;
        padding: 10px 0;
    }

    .shm-gallery-item {
        background: rgba(10, 20, 40, 0.6);
        border: 1px solid rgba(52, 211, 153, 0.12);
        border-radius: 16px;
        overflow: hidden;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .shm-gallery-item:hover {
        border-color: rgba(52, 211, 153, 0.45);
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 0 20px rgba(52,211,153,0.1);
    }

    .shm-gallery-item img {
        width: 100%;
        height: auto;
        display: block;
        border-radius: 12px 12px 0 0;
    }

    .shm-gallery-item-label {
        padding: 10px 14px;
        font-size: 11px;
        font-family: 'Outfit', sans-serif;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .shm-empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 80px 20px;
        color: #334155;
        font-family: 'Outfit', sans-serif;
        gap: 16px;
    }

    .shm-empty-icon {
        font-size: 64px;
        opacity: 0.4;
    }

    .shm-empty-text {
        font-size: 18px;
        font-weight: 600;
        color: #475569;
        text-align: center;
    }

    .shm-meta-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        justify-content: center;
        margin-bottom: 16px;
    }

    .shm-meta-badge {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(52, 211, 153, 0.2);
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 12px;
        font-family: 'Outfit', sans-serif;
        color: #94a3b8;
        font-weight: 600;
    }
    """

DEFAULT_INDEX = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>Earthquake Dashboard</title>
            {%favicon%}
            {%css%}
            <style>
                /* CUSTOM_CSS_PLACEHOLDER */
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''

# ─────────────────────────────────────────────────────────────
# LAYOUT BUILDER FUNCTIONS
# Pure HTML/component builders — no data access, no callbacks.
# Imported and called from code1.py.
# ─────────────────────────────────────────────────────────────
from dash import dcc, html
import plotly.graph_objs as go
from plotly.subplots import make_subplots


def build_empty_initial_figure():
    """Dark pre-styled blank figure to prevent white flash on page load."""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=('X-Axis Acceleration', 'Y-Axis Acceleration', 'Z-Axis Acceleration'))
    fig.update_annotations(font=dict(family="Outfit", size=18, color="#e2e8f0"))
    fig.update_layout(
        height=800,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15, 23, 42, 0.2)',
        font=dict(family="Outfit", color="#f8fafc", size=14)
    )
    for i in range(1, 4):
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)', row=i, col=1)
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)', row=i, col=1)
    return fig


def make_mini_bar(val_str, axis, color):
    """Horizontal neon bar indicator used in sensor cards."""
    try:
        val = float(val_str)
    except Exception:
        val = 0.0

    if axis == 'Z':
        val = val - 9.81   # Remove gravity baseline

    max_val = 15.0
    percent_width = min((abs(val) / max_val) * 50, 50)

    if val < 0:
        left_pos = 50 - percent_width
        width_pos = percent_width
    else:
        left_pos = 50
        width_pos = percent_width

    return html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'}, children=[
        html.Span(f"{val_str}", style={
            'width': '45px', 'textAlign': 'right', 'fontSize': '14px',
            'fontFamily': 'monospace', 'fontWeight': '600'
        }),
        html.Div(style={
            'width': '80px', 'height': '8px',
            'background': 'rgba(255,255,255,0.08)', 'borderRadius': '4px', 'position': 'relative'
        }, children=[
            html.Div(style={
                'position': 'absolute', 'left': '50%', 'top': '0', 'bottom': '0',
                'width': '2px', 'background': 'rgba(255,255,255,0.3)', 'zIndex': '2'
            }),
            html.Div(style={
                'position': 'absolute',
                'left': f'{left_pos}%',
                'width': f'{width_pos}%',
                'height': '100%',
                'background': color,
                'borderRadius': '4px',
                'transition': 'all 0.3s ease',
                'boxShadow': f'0 0 8px {color}'
            })
        ])
    ])


def build_sensor_card(port, last_row, port_color, alert_active):
    """Glassmorphism sensor card for one port on the home page."""
    return html.Div(className='glass-card', style={'borderTop': f'5px solid {port_color}'}, children=[
        html.H2(f"Port {port}", className='card-title', style={'color': port_color}),

        html.Div(className='data-row', children=[
            html.Span("⏱️ Latest Ping", className='data-label'),
            html.Span(last_row.get('Time', 'N/A'), style={'fontFamily': 'monospace', 'fontWeight': '600'})
        ]),
        html.Div(className='data-row', children=[
            html.Span("↔️ X-Axis", className='data-label'),
            make_mini_bar(last_row.get('X', '0'), 'X', port_color)
        ]),
        html.Div(className='data-row', children=[
            html.Span("↕️ Y-Axis", className='data-label'),
            make_mini_bar(last_row.get('Y', '0'), 'Y', port_color)
        ]),
        html.Div(className='data-row', children=[
            html.Span("⭥ Z-Axis", className='data-label'),
            make_mini_bar(last_row.get('Z', '0'), 'Z', port_color)
        ]),

        html.Div(className='data-row', style={'justifyContent': 'center', 'paddingTop': '25px', 'borderBottom': 'none'}, children=[
            html.Span(
                "🚨 VIBRATIONAL ALERT" if alert_active else "✅ STABLE",
                className='alert-pulsing' if alert_active else 'status-stable',
                style={'fontWeight': '800', 'fontSize': '18px', 'letterSpacing': '1px'}
            )
        ]),

        dcc.Link(html.Button('Live Charts', className='btn-premium'), href=f'/graph/{port}')
    ])


def build_empty_state():
    """Spinner + message shown when no sensor data is available yet."""
    return html.Div(
        style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'marginTop': '80px'},
        children=[
            html.Div(className='loader'),
            html.H3("Awaiting Telemetry...", style={
                'textAlign': 'center', 'color': '#cbd5e1', 'fontWeight': '400',
                'fontFamily': 'Outfit', 'fontSize': '22px', 'letterSpacing': '1px'
            })
        ]
    )


def build_home_page_layout():
    """Shell layout for the home (overview) page — cards are filled by a callback."""
    return html.Div([
        html.Div(
            id='cards-container',
            style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center', 'gap': '35px', 'padding': '20px'}
        ),
        dcc.Interval(id='home-interval', interval=1000, n_intervals=0)
    ])


def _build_empty_matlab_figure():
    """Dark pre-styled blank figure shown in the MATLAB panel before first run."""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=('X-Axis (Processed)', 'Y-Axis (Processed)', 'Z-Axis (Processed)'))
    fig.update_annotations(font=dict(family="Outfit", size=16, color="#a78bfa"))
    fig.update_layout(
        height=750,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15, 23, 42, 0.2)',
        font=dict(family="Outfit", color="#f8fafc", size=13),
    )
    for i in range(1, 4):
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(167,139,250,0.06)', row=i, col=1)
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(167,139,250,0.05)', row=i, col=1)
    return fig


def build_graph_page_layout(port_for_graph, port_color):
    """Full layout for a per-port live graph page (/graph/<port>)."""
    r, g, b = int(port_color[1:3], 16), int(port_color[3:5], 16), int(port_color[5:7], 16)

    return html.Div(style={'padding': '0 40px 40px 40px', 'maxWidth': '1400px', 'margin': '0 auto'}, children=[

        # ── Top bar ──────────────────────────────────────────────
        html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginBottom': '20px'}, children=[
            dcc.Link('← Back to Overview', href='/', className='btn-back'),

            # Port identity badge
            html.Div(style={
                'background': f'rgba({r},{g},{b},0.15)',
                'border': f'1px solid {port_color}',
                'color': port_color,
                'padding': '8px 22px',
                'borderRadius': '30px',
                'fontWeight': '800',
                'fontSize': '18px',
                'fontFamily': 'Outfit',
                'letterSpacing': '1px',
            }, children=f'📡 PORT {port_for_graph}'),

            # Right controls: status label, Pause, Run MATLAB
            html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}, children=[
                html.Span(id='stream-status-label', style={'color': '#94a3b8', 'fontSize': '14px', 'fontFamily': 'Outfit'}),
                html.Button(
                    '⏸ Pause Updates',
                    id='play-pause-btn',
                    n_clicks=0,
                    style={
                        'background': 'rgba(56, 189, 248, 0.15)',
                        'border': '1px solid rgba(56, 189, 248, 0.4)',
                        'color': '#38bdf8',
                        'padding': '10px 22px',
                        'borderRadius': '10px',
                        'fontFamily': 'Outfit',
                        'fontSize': '15px',
                        'fontWeight': '600',
                        'cursor': 'pointer',
                        'transition': 'all 0.3s ease',
                        'backdropFilter': 'blur(10px)',
                    }
                ),

            ]),
        ]),

        # ── Tab Switcher ──────────────────────────────────────────
        html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '4px'}, children=[
            html.Div(className='tab-switcher', children=[
                html.Button('📡 Live Stream',     id='live-tab-btn',   n_clicks=0, className='tab-btn tab-btn-live-active'),
                html.Button('🔬 Live Capture (jul23)', id='matlab-tab-btn', n_clicks=0, className='tab-btn'),
                html.Button('📊 Historical (jul223)',      id='shm-tab-btn',    n_clicks=0, className='tab-btn'),
            ]),
        ]),

        # ── Status lines ─────────────────────────────────────────
        html.Div(id='matlab-status-label', className='matlab-status'),
        html.Div(id='shm-status-label', className='shm-status'),

        # ── Live Graph Panel (shown by default) ──────────────────
        html.Div(id='live-graph-panel', style={
            'backgroundColor': 'rgba(15, 23, 42, 0.4)',
            'backdropFilter': 'blur(20px)',
            'borderRadius': '24px',
            'padding': '25px',
            'boxShadow': '0 20px 50px rgba(0,0,0,0.5)',
            'border': f'1px solid rgba({r},{g},{b},0.13)',
        }, children=[
            html.H3(
                f"📊 Port {port_for_graph} — Live Sensor Stream. Zoom & Pan freely. Pause to lock view.",
                style={'textAlign': 'center', 'color': '#94a3b8', 'fontWeight': '400', 'margin': '0 0 15px 0', 'fontSize': '17px'}
            ),
            dcc.Graph(
                id='live-update-graph',
                figure=build_empty_initial_figure(),
                config={'scrollZoom': True, 'displayModeBar': True}
            ),
        ]),

        # ── Live Capture (jul23) Panel ─────────────────────────────
        html.Div(id='matlab-graph-panel', style={
            'display': 'none',
            'backgroundColor': 'rgba(15, 23, 42, 0.45)',
            'backdropFilter': 'blur(24px)',
            'borderRadius': '24px',
            'padding': '32px',
            'boxShadow': '0 24px 60px rgba(0,0,0,0.55)',
            'border': '1px solid rgba(167, 139, 250, 0.18)',
        }, children=[
            html.Div(style={
                'display': 'flex', 'alignItems': 'center',
                'justifyContent': 'space-between', 'marginBottom': '16px'
            }, children=[
                html.Div(children=[
                    html.H3('🔬 Live Capture (jul23) Report',
                        style={'margin': '0 0 4px 0', 'color': '#a78bfa',
                               'fontWeight': '800', 'fontSize': '20px', 'letterSpacing': '-0.3px'}),
                    html.Div(id='matlab-status-label',
                        style={'color': '#64748b', 'fontSize': '13px', 'fontFamily': 'Outfit'}),
                ]),
                dcc.Loading(id='live-shm-loading', type='circle', color='#a78bfa',
                    children=html.Button('🚀 Run Live Capture', id='run-matlab-btn', n_clicks=0,
                        style={
                            'background': 'linear-gradient(135deg, #a78bfa, #7c3aed)',
                            'border': 'none', 'color': '#fff',
                            'padding': '11px 22px', 'borderRadius': '12px',
                            'fontFamily': 'Outfit', 'fontSize': '14px', 'fontWeight': '700',
                            'cursor': 'pointer', 'boxShadow': '0 4px 20px rgba(167,139,250,0.35)',
                            'transition': 'all 0.2s',
                        }),
                ),
            ]),
            html.Hr(style={'border': 'none', 'borderTop': '1px solid rgba(255,255,255,0.06)', 'margin': '16px 0'}),
            html.Div(id='live-shm-gallery-container', style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fill, minmax(340px, 1fr))',
                'gap': '18px',
            }, children=[
                html.Div(style={
                    'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center',
                    'justifyContent': 'center', 'padding': '60px 20px',
                    'border': '2px dashed rgba(167,139,250,0.15)', 'borderRadius': '16px',
                    'gridColumn': '1 / -1',
                }, children=[
                    html.Div('🔬', style={'fontSize': '48px', 'marginBottom': '12px'}),
                    html.Div('Click "Run Live Capture" to generate jul23 graphs',
                        style={'color': '#475569', 'fontFamily': 'Outfit', 'fontSize': '15px'}),
                ]),
            ]),
        ]),

        # ── SHM Report Panel ─────────────────────────────────────
        html.Div(id='shm-report-panel', style={
            'display': 'none',
            'backgroundColor': 'rgba(15, 23, 42, 0.45)',
            'backdropFilter': 'blur(24px)',
            'borderRadius': '24px',
            'padding': '32px',
            'boxShadow': '0 24px 60px rgba(0,0,0,0.55)',
            'border': '1px solid rgba(52, 211, 153, 0.18)',
        }, children=[

            # ── Top header row ────────────────────────────────────
            html.Div(style={
                'display': 'flex', 'alignItems': 'center',
                'justifyContent': 'space-between', 'marginBottom': '8px'
            }, children=[
                html.Div(children=[
                    html.H3('📊 SHM Pipeline Report',
                        style={'margin': '0 0 4px 0', 'color': '#34d399',
                               'fontWeight': '800', 'fontSize': '20px', 'letterSpacing': '-0.3px'}),
                    html.Div(id='shm-status-label',
                        style={'color': '#64748b', 'fontSize': '13px', 'fontFamily': 'Outfit'}),
                ]),
                dcc.Loading(id='shm-loading', type='circle', color='#34d399',
                    children=html.Button('🚀 Run SHM Analysis', id='run-shm-btn', n_clicks=0,
                        style={
                            'background': 'linear-gradient(135deg, #34d399, #059669)',
                            'border': 'none', 'color': '#fff',
                            'padding': '11px 22px', 'borderRadius': '12px',
                            'fontFamily': 'Outfit', 'fontSize': '14px', 'fontWeight': '700',
                            'cursor': 'pointer', 'boxShadow': '0 4px 20px rgba(52,211,153,0.35)',
                            'transition': 'all 0.2s',
                        }),
                ),
            ]),

            # ── Divider ───────────────────────────────────────────
            html.Hr(style={'border': 'none', 'borderTop': '1px solid rgba(255,255,255,0.06)', 'margin': '16px 0'}),

            # ── Segmented filter tabs ─────────────────────────────
            html.Div(style={
                'display': 'inline-flex', 'gap': '6px', 'padding': '5px',
                'background': 'rgba(0,0,0,0.3)', 'borderRadius': '14px',
                'border': '1px solid rgba(255,255,255,0.06)', 'marginBottom': '22px',
            }, children=[
                html.Button('All',      id='shm-filter-all',      n_clicks=0, style={
                    'background': 'rgba(52,211,153,0.22)', 'border': '1px solid rgba(52,211,153,0.5)',
                    'color': '#34d399', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '800', 'cursor': 'pointer',
                    'boxShadow': '0 0 12px rgba(52,211,153,0.3)'}),
                html.Button('⚖ Set 1', id='shm-filter-set1',     n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#38bdf8', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('⚖ Set 2', id='shm-filter-set2',     n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#f472b6', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('⚖ Set 3', id='shm-filter-set3',     n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#4ade80', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('⚖ Set 4', id='shm-filter-set4',     n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#2dd4bf', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('⚖ Set 5', id='shm-filter-set5',     n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#818cf8', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('⚖ Set 6', id='shm-filter-set6',     n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#c084fc', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('📈 Part 7 (Overview)', id='shm-filter-part7', n_clicks=0, style={
                    'background': 'transparent', 'border': '1px solid transparent',
                    'color': '#fbbf24', 'padding': '8px 20px', 'borderRadius': '10px',
                    'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer'}),
                html.Button('📈 Overview', id='shm-filter-overview', n_clicks=0, style={'display': 'none'}),
            ]),

            # ── Gallery grid — populated by callback ──────────────
            html.Div(id='shm-gallery-container', style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fill, minmax(340px, 1fr))',
                'gap': '18px',
            }, children=[
                html.Div(style={
                    'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center',
                    'justifyContent': 'center', 'padding': '60px 20px',
                    'border': '2px dashed rgba(52,211,153,0.15)', 'borderRadius': '16px',
                    'gridColumn': '1 / -1',
                }, children=[
                    html.Div('📊', style={'fontSize': '48px', 'marginBottom': '12px'}),
                    html.Div('Click "Run SHM Analysis" to generate graphs',
                        style={'color': '#475569', 'fontFamily': 'Outfit', 'fontSize': '15px'}),
                    html.Div('Then use the tabs above to filter by set',
                        style={'color': '#334155', 'fontFamily': 'Outfit', 'fontSize': '13px', 'marginTop': '4px'}),
                ]),
            ]),
        ]),

        # ── Hidden state stores & polling interval ────────────────
        dcc.Store(id='matlab-results-store', data=None),
        dcc.Store(id='live-shm-images-store', data=None),
        dcc.Store(id='shm-images-store', data=None),
        dcc.Store(id='shm-set-filter', data='all'),
        dcc.Store(id='is-paused-store', data=False),
        dcc.Interval(id='graph-interval', interval=1000, n_intervals=0),

        # ── SHM Image Modal ───────────────────────────────────────
        html.Div(id='shm-image-modal', style={'display': 'none'}, children=[
            html.Button('✖ Close', id='shm-modal-close', n_clicks=0, style={
                'position': 'absolute', 'top': '30px', 'right': '40px',
                'background': 'rgba(255,255,255,0.15)', 'border': '1px solid rgba(255,255,255,0.3)',
                'color': 'white', 'padding': '12px 24px', 'borderRadius': '30px',
                'fontFamily': 'Outfit', 'fontWeight': 'bold', 'cursor': 'pointer',
                'transition': '0.2s', 'zIndex': 10000
            }),
            html.H3(id='shm-modal-title', style={
                'color': '#34d399', 'fontFamily': 'Outfit', 'marginBottom': '20px', 'fontWeight': '700',
                'fontSize': '22px', 'letterSpacing': '0.5px'
            }),
            html.Img(id='shm-modal-img', style={
                'maxWidth': '90vw', 'maxHeight': '80vh',
                'borderRadius': '16px', 'boxShadow': '0 20px 60px rgba(0,0,0,0.8)'
            })
        ]),

        # ── Deep Analysis Modal ───────────────────────────────────
        html.Div(id='modal-overlay', className='modal-overlay', style={'display': 'none'}, children=[
            html.Div(className='modal-content', children=[
                html.Button('✖ Close Analysis', id='close-modal-btn', className='btn-close-modal'),
                html.H2(id='modal-title', style={
                    'margin': '0 0 10px 0', 'color': '#38bdf8', 'textAlign': 'center', 'fontWeight': '800'
                }),
                html.Div(id='time-calc-output', style={
                    'textAlign': 'center', 'color': '#f472b6',
                    'fontSize': '18px', 'fontWeight': '600', 'margin': '0 0 15px 0'
                }),
                dcc.Graph(id='detailed-graph', style={'flex': '1'}),
            ])
        ])
    ])
