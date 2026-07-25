import socket
import select
import csv
import os
import threading

# Force working directory to be the script's folder so local files are found correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash.exceptions
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import datetime
import glob
import time
from collections import deque
import time
from collections import deque
import time
from frontend import (
    CUSTOM_CSS, DEFAULT_INDEX, COLORS,
    build_graph_page_layout, build_home_page_layout,
    build_sensor_card, build_empty_state, make_mini_bar
)

# Initialize MATLAB Engine gracefully
HAS_MATLAB = False
try:
    import matlab.engine
    print("\n🚀 [MATLAB] Booting MathWorks Engine in the background (this takes ~5s)...")
    eng = matlab.engine.start_matlab()
    HAS_MATLAB = True
    print("✅ [MATLAB] Engine successfully hooked into Python!")
except Exception as e:
    print(f"⚠️ [MATLAB ENGINE BYPASS] Running pure Python. Engine connection failed: {e}")

# Google Drive API Imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    HAS_GOOGLE_APIS = True
except ImportError:
    HAS_GOOGLE_APIS = False

SCOPES = ['https://www.googleapis.com/auth/drive.file']

#declaration of ports to listen to
ports_to_listen = [8000, 8001, 8002]
Headers = ['Time', 'X', 'Y', 'Z', 'SW420']

# --- THREAD-SAFE MEMORY BUFFERS ---
buffer_lock = threading.Lock()
sensor_buffers = {}
csv_write_buffers = {}

# --- MATLAB RESULTS CACHE (keyed by port) ---
matlab_cache = {}
matlab_cache_lock = threading.Lock()


def csv_files(port, msg):
    try:
        parsed = {}
        time_val = ""

        if ',' in msg and '=' not in msg:
            parts = [p.strip() for p in msg.split(',')]
            if len(parts) >= 4:
                time_val = parts[0]
                parsed['x'] = parts[1]
                parsed['y'] = parts[2]
                parsed['z'] = parts[3]
                parsed['sw420'] = parts[4] if len(parts) > 4 else '0'
        else:
            parts = msg.split("|")
            for part in parts:
                part = part.strip()
                if '=' in part:
                    key, value = part.split('=', 1)
                    parsed[key.strip().lower()] = value.strip()
            time_val = parsed.get('time', '')

        if time_val and len(time_val) <= 8:  
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            time_val = f"{today} {time_val}"

        row_data = [
            time_val,
            parsed.get('x', '0'),
            parsed.get('y', '0'),
            parsed.get('z', '0'),
            parsed.get('sw420', '0'),
        ]

        if parsed.get('x') is not None and parsed.get('y') is not None and parsed.get('z') is not None and time_val:
            with buffer_lock:
                if port not in sensor_buffers:
                    sensor_buffers[port] = deque(maxlen=1000)
                if port not in csv_write_buffers:
                    csv_write_buffers[port] = []
                
                sensor_buffers[port].append(row_data)
                csv_write_buffers[port].append(row_data)

    except Exception as e:
        print(f"Error buffering data for port {port}: {e}")

# --- CSV DISK WRITER DAEMON ---
def csv_flush_worker(interval=5):
    print(f"\n💾 [DISK WRITER] Background thread started. Writing to CSV every {interval} seconds...")
    while True:
        time.sleep(interval)
        
        # Atomically grab and lock the pending writes
        writes_to_flush = {}
        with buffer_lock:
            for port, writes in csv_write_buffers.items():
                if writes:
                    writes_to_flush[port] = list(writes)
                    csv_write_buffers[port].clear()
                    
        # Perform sluggish disk I/O without keeping the lock
        for port, rows in writes_to_flush.items():
            filename = f"sensor_data_{port}.csv"
            file_is_new = not os.path.exists(filename)
            try:
                with open(filename, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    if file_is_new:
                        writer.writerow(Headers)
                        print(f"Created new CSV file: {filename}")
                    writer.writerows(rows)
            except Exception as e:
                print(f"⚠️ [DISK WRITER] Failed to write {len(rows)} lines for port {port}: {e}")
        
def UDP_listener():
    sockets = []
    print(f"Starting simple listener on ports: {ports_to_listen}...")
    
    for port in ports_to_listen:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", port))
            sock.setblocking(False)
            sockets.append(sock)
            print(f"Successfully bound to port {port}")
        except Exception as e:
            print(f"Failed to bind to port {port}: {e}")

    if not sockets:
        print("No ports could be bound. Exiting.")
        return

    print("\n Waiting for ESP32 data... (Press Ctrl+C to stop)")

    try:
        while True:
            readable, _, _ = select.select(sockets, [], [], 0.1)
            for sock in readable:
                data, addr = sock.recvfrom(1024)
                port = sock.getsockname()[1]
                msg = data.decode('utf-8').strip()
                print(f" Port {port} | {msg}")
                csv_files(port, msg)
    except KeyboardInterrupt:
        print("\n Listener stopped by user.")
    finally:
        print("Closing network ports...")
        for sock in sockets:
            sock.close()

# --- GOOGLE DRIVE BACKUP SYSTEM ---
def authenticate_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                # Handle revoked/expired refresh token (e.g. invalid_grant)
                print(f"⚠️ [DRIVE SYNC] Token refresh failed ({e}). Deleting stale token and re-authenticating...")
                os.remove('token.json')
                creds = None
        if not creds:
            if not os.path.exists('credentials.json'):
                print("⚠️ [DRIVE SYNC] MISSING 'credentials.json' FILE! To enable Google Drive backup, download your OAuth 2.0 Client credentials from Google Cloud Console and save it as 'credentials.json' in this folder.")
                return None
            print("\n🚨 [DRIVE SYNC] Google Drive authorization required! A browser window should open. If not, click the link below.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def get_file_id(service, filename):
    results = service.files().list(
        q=f"name='{filename}' and trashed=false",
        spaces='drive',
        fields="files(id, name)"
    ).execute()
    items = results.get('files', [])
    if not items:
        return None
    return items[0]['id']

def sync_csv_to_drive():
    if not HAS_GOOGLE_APIS:
        print("⚠️ [DRIVE SYNC] Google API libraries not installed. Run 'pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'")
        return

    service = authenticate_drive()
    if not service:
        return

    # Only sync raw port files (e.g. sensor_data_8001.csv), not cleaned/processed variants
    import re
    csv_files = [f for f in glob.glob("sensor_data_*.csv")
                 if re.fullmatch(r'sensor_data_\d+\.csv', f)]
    if not csv_files:
        return

    for csv_file in csv_files:
        file_id = get_file_id(service, csv_file)
        media = MediaFileUpload(csv_file, mimetype='text/csv', resumable=True)
        try:
            if file_id:
                # Update existing file
                service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                print(f"✅ [DRIVE SYNC] Updated Drive file: {csv_file}")
            else:
                # Create brand new file
                file_metadata = {'name': csv_file}
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"🚀 [DRIVE SYNC] Uploaded new Drive file: {csv_file}")
        except Exception as e:
            print(f"❌ [DRIVE SYNC] Failed to upload {csv_file}: {e}")

def start_sync_loop(interval_minutes=5):
    print(f"\n🔄 [DRIVE SYNC] Background thread started. Backing up CSV files every {interval_minutes} minutes...")
    while True:
        try:
            sync_csv_to_drive()
        except Exception as e:
            print(f"⚠️ [DRIVE SYNC] Error: {e}")
        time.sleep(interval_minutes * 60)
# ----------------------------------


def run_matlab_analysis(port):
    """
    Process sensor data for `port` via MATLAB engine (falls back to Python).
    Returns (result_dict, error_string).  result_dict is None on failure.
    """
    import numpy as np

    filename = f"sensor_data_{port}.csv"
    if not os.path.exists(filename):
        return None, f"No CSV found: {filename}"

    df = pd.read_csv(filename).tail(500)
    for col in ['X', 'Y', 'Z']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['X', 'Y', 'Z', 'Time']).sort_values('Time').reset_index(drop=True)

    if len(df) < 2:
        return None, "Not enough valid data rows in CSV."

    x_arr = df['X'].tolist()
    y_arr = df['Y'].tolist()
    z_arr = df['Z'].tolist()
    mode_label = "Python (mean-removal)"

    if HAS_MATLAB:
        try:
            x_m, y_m, z_m = eng.matlab_processor(filename, nargout=3)
            n = len(df)
            x_arr = list(x_m[0])[-n:]
            y_arr = list(y_m[0])[-n:]
            z_arr = list(z_m[0])[-n:]
            mode_label = "MATLAB"
            print(f"[MATLAB] Analysis complete for port {port}: {n} samples.")
        except Exception as e:
            print(f"[MATLAB ERROR] {e} — falling back to Python mean-removal")
            x_arr = (df['X'] - df['X'].mean()).tolist()
            y_arr = (df['Y'] - df['Y'].mean()).tolist()
            z_arr = (df['Z'] - df['Z'].mean()).tolist()
            mode_label = f"Python fallback ({str(e)[:50]})"
    else:
        x_arr = (df['X'] - df['X'].mean()).tolist()
        y_arr = (df['Y'] - df['Y'].mean()).tolist()
        z_arr = (df['Z'] - df['Z'].mean()).tolist()

    # Spread identical-second timestamps across the second for continuity
    df['Time'] = df['Time'] + pd.to_timedelta(
        (df.groupby(df['Time'].dt.floor('s')).cumcount() /
         df.groupby(df['Time'].dt.floor('s'))['Time'].transform('count')).fillna(0) * 1000,
        unit='ms'
    )

    x_np  = np.array(x_arr, dtype=float)
    y_np  = np.array(y_arr, dtype=float)
    z_np  = np.array(z_arr, dtype=float)
    mag   = np.sqrt(x_np**2 + y_np**2 + z_np**2)

    metrics = {
        'x_rms':   round(float(np.sqrt(np.mean(x_np**2))), 4),
        'y_rms':   round(float(np.sqrt(np.mean(y_np**2))), 4),
        'z_rms':   round(float(np.sqrt(np.mean(z_np**2))), 4),
        'x_peak':  round(float(np.ptp(x_np)), 4),
        'y_peak':  round(float(np.ptp(y_np)), 4),
        'z_peak':  round(float(np.ptp(z_np)), 4),
        'mag_rms': round(float(np.sqrt(np.mean(mag**2))), 4),
    }

    result = {
        'port':      port,
        'times':     df['Time'].astype(str).tolist(),
        'x':         [round(v, 6) for v in x_arr],
        'y':         [round(v, 6) for v in y_arr],
        'z':         [round(v, 6) for v in z_arr],
        'metrics':   metrics,
        'mode':      mode_label,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'n_samples': len(df),
    }

    with matlab_cache_lock:
        matlab_cache[port] = result

    return result, None





def _blend_color(hex1: str, hex2: str, t: float) -> str:
    """Linearly blend two hex colors. t=0 → hex1, t=1 → hex2."""
    try:
        h1 = hex1.lstrip('#'); h2 = hex2.lstrip('#')
        r1,g1,b1 = int(h1[0:2],16), int(h1[2:4],16), int(h1[4:6],16)
        r2,g2,b2 = int(h2[0:2],16), int(h2[2:4],16), int(h2[4:6],16)
        r = int(r1 + (r2-r1)*t); g = int(g1 + (g2-g1)*t); b = int(b1 + (b2-b1)*t)
        return f'#{r:02x}{g:02x}{b:02x}'
    except Exception:
        return hex1


def run_july7_analysis(params=None):

    """Backward-compatibility wrapper — delegates to run_jul223_analysis."""
    return run_jul223_analysis(params=params)


# ═══════════════════════════════════════════════════════════════════════════
# jul223.m  →  Calls MATLAB jul223_runner.m for signal processing
# ═══════════════════════════════════════════════════════════════════════════
def run_jul223_analysis(params=None):
    """
    Historical 6-Dataset SHM Pipeline (jul223.m v11 equivalent).
    Calls jul223_runner.m via the MATLAB engine (all processing in MATLAB).
    Returns (image_url_list, error_string).
    """
    import json as _json

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'shm_output')
    os.makedirs(output_dir, exist_ok=True)
    csv_file   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sensor_data_8000.csv')
    assets_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

    def _to_url(p):
        try:
            rel = os.path.relpath(p, assets_root).replace('\\', '/')
            return f'/assets/{rel}'
        except Exception:
            return p

    if not HAS_MATLAB:
        return None, "MATLAB engine not available. Please start MATLAB and try again."

    try:
        print("[SHM] Calling jul223_runner via MATLAB engine...")
        result_json = eng.jul223_runner(csv_file, output_dir, nargout=1)
        payload     = _json.loads(str(result_json))
        if payload.get('status') != 'ok':
            return None, f"MATLAB error: {payload.get('message', 'unknown error')}"
        url_paths = [_to_url(p) for p in payload.get('images', [])]
        print(f"[SHM] jul223_runner complete. {len(url_paths)} figures saved.")
        return url_paths, None
    except Exception as e:
        return None, f"MATLAB engine error: {e}"

def run_jul23_live_analysis():
    """
    Live-capture SHM Pipeline (reads last 60 s of CSV).
    Calls jul23_runner.m via the MATLAB engine.
    Signal processing is performed entirely in MATLAB.
    Returns (image_url_list, error_string).
    """
    import json as _json

    output_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'shm_output')
    os.makedirs(output_dir, exist_ok=True)
    csv_file    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sensor_data_8000.csv')
    assets_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

    def _to_url(p):
        try:
            rel = os.path.relpath(p, assets_root).replace('\\', '/')
            return f'/assets/{rel}'
        except Exception:
            return p

    if not HAS_MATLAB:
        return None, "MATLAB engine not available. Please start MATLAB and try again."

    try:
        print("[SHM] Calling jul23_runner via MATLAB engine...")
        result_json = eng.jul23_runner(csv_file, output_dir, nargout=1)
        payload     = _json.loads(str(result_json))
        if payload.get('status') != 'ok':
            return None, f"MATLAB error: {payload.get('message', 'unknown error')}"
        url_paths = [_to_url(p) for p in payload.get('images', [])]
        print(f"[SHM] jul23_runner complete. {len(url_paths)} figures saved.")
        return url_paths, None
    except Exception as e:
        return None, f"MATLAB engine error: {e}"



def start_dashboard():
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    
    colors = COLORS
    app.index_string = DEFAULT_INDEX.replace('/* CUSTOM_CSS_PLACEHOLDER */', CUSTOM_CSS)

    app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        # Stores which port the user is currently viewing on the graph page
        dcc.Store(id='current-port-store', data=None),
        html.Div(style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'paddingTop': '40px'}, children=[
            html.H1('🌎 Earthquake Sensor Network', className='dashboard-title'),
        ]),
        html.Div(id='page-content')
    ])

    @app.callback(
        Output('page-content', 'children'),
        Output('current-port-store', 'data'),
        [Input('url', 'pathname')]
    )
    def display_page(pathname):
        # Separate graph pages: /graph/8000, /graph/8001, etc.
        port_for_graph = None
        is_graph_page = False

        if pathname and pathname.startswith('/graph/'):
            try:
                port_for_graph = int(pathname.split('/graph/')[1])
                is_graph_page = True
            except (ValueError, IndexError):
                pass
        elif pathname == '/graph':
            # Legacy fallback: redirect logic handled by showing first available port
            is_graph_page = True
            port_for_graph = ports_to_listen[0] if ports_to_listen else None

        if is_graph_page and port_for_graph is not None:
            port_color = colors.get(port_for_graph, '#38bdf8')
            return build_graph_page_layout(port_for_graph, port_color), port_for_graph
        else:
            return build_home_page_layout(), None


    @app.callback(Output('cards-container', 'children'), [Input('home-interval', 'n_intervals')])
    def update_home_cards(n):
        cards = []
        
        # Discover all available CSV files directly
        csv_files_list = glob.glob("sensor_data_*.csv")
        active_ports = []
        for f in csv_files_list:
            try:
                port_num = int(f.split('_')[-1].split('.')[0])
                active_ports.append(port_num)
            except: pass
            
        # Ensure we also check active listening ports even if they don't have CSVs yet
        all_ports = sorted(list(set(active_ports + ports_to_listen)))

        for port in all_ports:
            buffer_copy = None
            with buffer_lock:
                if port in sensor_buffers and sensor_buffers[port]:
                    buffer_copy = sensor_buffers[port][-1]
                    
            if buffer_copy:
                try:
                    last_row = dict(zip(Headers, buffer_copy))
                    port_color = colors.get(port, "#FFFFFF")
                    alert_active = str(last_row.get('SW420', '0')) != '0'
                    cards.append(build_sensor_card(port, last_row, port_color, alert_active))
                except Exception:
                    pass
            else:
                # Fallback: read last row from disk if buffer is empty but CSV exists
                filename = f"sensor_data_{port}.csv"
                if os.path.exists(filename):
                    try:
                        df = pd.read_csv(filename).tail(1)
                        if not df.empty:
                            last_row = df.iloc[-1].to_dict()
                            port_color = colors.get(port, "#FFFFFF")
                            alert_active = str(last_row.get('SW420', '0')) != '0'
                            cards.append(build_sensor_card(port, last_row, port_color, alert_active))
                    except Exception:
                        pass

        if not cards:
            return build_empty_state()
        return cards

    # --- PLAY / PAUSE: toggle the interval and update the button label ---
    @app.callback(
        Output('graph-interval', 'disabled'),
        Output('play-pause-btn', 'children'),
        Output('stream-status-label', 'children'),
        Output('is-paused-store', 'data'),
        [Input('play-pause-btn', 'n_clicks')],
        [State('is-paused-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_play_pause(n_clicks, is_paused):
        # Flip paused state on each click
        new_paused = not is_paused
        if new_paused:
            btn_label = '▶ Resume Updates'
            status = '🔴 Live stream paused — zoom & pan freely'
        else:
            btn_label = '⏸ Pause Updates'
            status = ''
        return new_paused, btn_label, status, new_paused

    @app.callback(
        Output('live-update-graph', 'figure'),
        [Input('graph-interval', 'n_intervals'), Input('current-port-store', 'data')]
    )
    def update_graph_live(n, current_port):
        # Only render data for the port this page belongs to
        if current_port is None:
            raise dash.exceptions.PreventUpdate

        port = int(current_port)
        port_color = colors.get(port, '#38bdf8')

        # Define per-axis colours so all 3 lines are distinct but port-themed
        axis_colors = {
            'X': port_color,
            'Y': _blend_color(port_color, '#ffffff', 0.35),
            'Z': _blend_color(port_color, '#ffffff', 0.65),
        }

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            subplot_titles=('X-Axis Acceleration', 'Y-Axis Acceleration', 'Z-Axis Acceleration'))
        fig.update_annotations(font=dict(family="Outfit", size=18, color="#e2e8f0"))

        MAX_LIVE_ROWS = 2000   # rows shown while actively streaming
        MAX_HIST_ROWS = 5000   # rows shown from CSV on page load / no live data

        def _load_df():
            """Try in-memory buffer first (live stream), fall back to full CSV history."""
            with buffer_lock:
                if port in sensor_buffers and len(sensor_buffers[port]) > 5:
                    # Active live stream — show last MAX_LIVE_ROWS from buffer
                    rows = list(sensor_buffers[port])
                    return pd.DataFrame(rows[-MAX_LIVE_ROWS:], columns=Headers)
            # No live data yet — load historical CSV so the graph isn't blank
            filename = f"sensor_data_{port}.csv"
            if os.path.exists(filename):
                try:
                    df_hist = pd.read_csv(filename, parse_dates=['Time'])
                    return df_hist.tail(MAX_HIST_ROWS)
                except Exception:
                    pass
            return None

        df = _load_df()
        if df is not None and not df.empty:
            try:
                for col in ['X', 'Y', 'Z']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
                df = df.sort_values('Time')
                df['Time'] = df['Time'] + pd.to_timedelta(
                    (df.groupby(df['Time'].dt.floor('s')).cumcount() /
                     df.groupby(df['Time'].dt.floor('s'))['Time'].transform('count')).fillna(0) * 1000,
                    unit='ms'
                )
                for row_idx, axis in enumerate(['X', 'Y', 'Z'], start=1):
                    fig.append_trace(
                        go.Scatter(
                            x=df['Time'], y=df[axis],
                            name=f'{axis}-Axis',
                            mode='lines',
                            line=dict(width=2, color=axis_colors[axis], shape='spline'),
                            customdata=[f"{port}|{axis}"] * len(df)
                        ),
                        row=row_idx, col=1
                    )
            except Exception:
                pass

        fig.update_layout(
            height=800,
            template='plotly_dark',
            showlegend=True,
            hovermode='x unified',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 23, 42, 0.2)',
            font=dict(family="Outfit", color="#f8fafc", size=14),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        bgcolor="rgba(15, 23, 42, 0.7)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
            hoverlabel=dict(bgcolor="rgba(10, 20, 40, 0.95)", font_size=14, font_family="Outfit",
                            font_color="#e2e8f0", bordercolor="rgba(56, 189, 248, 0.4)"),
            uirevision=f'sensor-live-chart-{port}',
        )
        for i in range(1, 4):
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)', row=i, col=1)
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)', row=i, col=1)
        return fig

    # --- CALLBACK FOR DEEP ANALYSIS MODAL ---
    @app.callback(
        Output('modal-overlay', 'style'),
        Output('modal-title', 'children'),
        Output('detailed-graph', 'figure'),
        [Input('live-update-graph', 'clickData'), Input('close-modal-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_graph_click(click_data, close_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'close-modal-btn':
            return {'display': 'none'}, "", go.Figure()

        if trigger_id == 'live-update-graph' and click_data:
            point = click_data['points'][0]
            if 'customdata' in point:
                tag = point['customdata']
                port_str, axis = tag.split('|')
                port = int(port_str)

                filename = f"sensor_data_{port}.csv"
                if os.path.exists(filename):
                    df = pd.read_csv(filename).tail(500)
                    df['X'] = pd.to_numeric(df['X'], errors='coerce')
                    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
                    df['Z'] = pd.to_numeric(df['Z'], errors='coerce')

                    # Sort chronologically and spread milliseconds to untangle identical timestamps
                    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
                    df = df.sort_values('Time')
                    df['Time'] = df['Time'] + pd.to_timedelta((df.groupby(df['Time'].dt.floor('s')).cumcount() / df.groupby(df['Time'].dt.floor('s'))['Time'].transform('count')).fillna(0) * 1000, unit='ms')

                    # Axis colour and label map
                    axis_color_map = {'X': '#38bdf8', 'Y': '#f472b6', 'Z': '#4ade80'}
                    axis_label_map = {'X': 'X-Axis Acceleration (m/s²)', 'Y': 'Y-Axis Acceleration (m/s²)', 'Z': 'Z-Axis Acceleration (m/s²)'}
                    axis_icon_map  = {'X': '↔️', 'Y': '↕️', 'Z': '⭥'}

                    axis_col   = axis          # 'X', 'Y', or 'Z'
                    line_color = axis_color_map.get(axis_col, colors.get(port, "#38bdf8"))
                    y_label    = axis_label_map.get(axis_col, f'{axis_col}-Axis')
                    icon       = axis_icon_map.get(axis_col, '')

                    # --- MATLAB DEEP ANALYSIS INJECTION ---
                    if HAS_MATLAB:
                        try:
                            # Pass filename to MATLAB, returning X, Y, Z dynamic arrays
                            x_m, y_m, z_m = eng.matlab_processor(filename, nargout=3)
                            
                            # Ensure dimension constraints are properly parsed into our dataframe window. 
                            # If MATLAB returns the absolute full array but our tail is 500:
                            x_m_flat = list(x_m[0])[-len(df):]
                            y_m_flat = list(y_m[0])[-len(df):]
                            z_m_flat = list(z_m[0])[-len(df):]

                            if axis_col == 'X':
                                df[axis_col] = x_m_flat
                            elif axis_col == 'Y':
                                df[axis_col] = y_m_flat
                            else:
                                df[axis_col] = z_m_flat
                            
                            print(f"[MATLAB] Successfully applied gravity-removal filter for {axis_col}.")
                        except Exception as e:
                            print(f"[MATLAB ERROR] Falling back to Python math: {e}")
                            df[axis_col] = df[axis_col] - df[axis_col].mean()
                    else:
                        # Fallback natively if engine isn't connected
                        df[axis_col] = df[axis_col] - df[axis_col].mean()

                    # Single focused graph — no subplots
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df['Time'],
                        y=df[axis_col],
                        name=f'Port {port} ({axis_col})',
                        mode='lines+markers',
                        line=dict(width=2.5, color=line_color, shape='spline'),
                        marker=dict(size=4, color=line_color),
                        fill='tozeroy',
                        fillcolor=line_color.replace(')', ', 0.08)').replace('rgb', 'rgba') if line_color.startswith('rgb') else f'rgba(56,189,248,0.06)',
                    ))

                    fig.update_layout(
                        template='plotly_dark',
                        height=480,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(15, 23, 42, 0.4)',
                        hovermode='x unified',
                        dragmode='select',
                        font=dict(family="Outfit", color="#e2e8f0", size=14),
                        margin=dict(l=50, r=40, t=20, b=60),
                        yaxis=dict(
                            title=dict(text=y_label, font=dict(size=14, color='#94a3b8')),
                            showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.08)',
                            zerolinecolor='rgba(255,255,255,0.15)',
                        ),
                        xaxis=dict(
                            title=dict(text='Time', font=dict(size=13, color='#94a3b8')),
                            showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)',
                        ),
                        hoverlabel=dict(
                            bgcolor="rgba(10, 20, 40, 0.95)",
                            font_size=14,
                            font_family="Outfit",
                            font_color="#e2e8f0",
                            bordercolor=line_color,
                        ),
                    )

                    axis_full = {'X': 'X-Axis', 'Y': 'Y-Axis', 'Z': 'Z-Axis'}.get(axis_col, axis_col)
                    return {'display': 'flex'}, f"🔍 Deep Analysis: Port {port} — {axis_full} Acceleration", fig

        raise dash.exceptions.PreventUpdate

    # --- CALLBACK FOR CALCULATING TIME DELTA ---
    @app.callback(
        Output('time-calc-output', 'children'),
        [Input('detailed-graph', 'selectedData')],
        prevent_initial_call=True
    )
    def calculate_time_delta(selected_data):
        if not selected_data or not selected_data.get('points'):
            return "👆 Click and Drag (Box-Select) across the chart to calculate the exact duration of a vibration event."
            
        points = selected_data['points']
        
        if len(points) < 2:
            return "Please select a wider area covering at least two data points."
            
        try:
            first_time_str = points[0]['x']
            last_time_str = points[-1]['x']
            
            t1 = pd.to_datetime(first_time_str)
            t2 = pd.to_datetime(last_time_str)
            
            delta = abs((t2 - t1).total_seconds())
            
            return f"⏱️ Selected Event Duration: {delta:.2f} Seconds (from {first_time_str.split(' ')[1]} to {last_time_str.split(' ')[1]})"
        except Exception as e:
            return f"Error calculating duration: {e}"

    # ════════════════════════════════════════════════════════════
    # MATLAB ANALYSIS PIPELINE CALLBACKS
    # ════════════════════════════════════════════════════════════

    @app.callback(
        Output('live-shm-images-store', 'data'),
        Output('matlab-status-label', 'children'),
        [Input('run-matlab-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def trigger_live_shm_analysis(n_clicks):
        """Run the live SHM pipeline (jul23) and store image URL list."""
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        
        image_urls, err = run_jul23_live_analysis()
        if err:
            return dash.no_update, f"❌ {err}"
        
        count = len(image_urls) if image_urls else 0
        ts    = datetime.datetime.now().strftime('%H:%M:%S')
        return image_urls, f"✅ {count} jul23 figures generated at {ts} — scroll down to browse the gallery"

    # --- CALLBACK: SHM ANALYSIS TRIGGER ---
    @app.callback(
        Output('shm-images-store', 'data'),
        Output('shm-status-label', 'children'),
        [Input('run-shm-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def trigger_shm_analysis(n_clicks):
        """Run the full july7 SHM pipeline and store image URL list."""
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        image_urls, err = run_july7_analysis()
        if err:
            return dash.no_update, f"❌ {err}"
        count = len(image_urls) if image_urls else 0
        ts    = datetime.datetime.now().strftime('%H:%M:%S')
        return image_urls, f"✅ {count} figures generated at {ts} — scroll down to browse the gallery"

    # --- CALLBACK: RENDER LIVE SHM GALLERY (jul23) ---
    @app.callback(
        Output('live-shm-gallery-container', 'children'),
        [Input('live-shm-images-store', 'data')],
        prevent_initial_call=True
    )
    def render_live_shm_gallery(image_urls):
        if not image_urls:
            return html.Div(className='shm-empty-state', children=[
                html.Div('📊', className='shm-empty-icon'),
                html.Div('Click "Run Live Capture" to generate graphs.', className='shm-empty-text'),
            ])

        def _label(url):
            fname = os.path.basename(url)
            # Friendly label map for live graphs
            label_map = {
                'live_A_full':     'Live A — Full Timeline',
                'live_B_raw':      'Live B — Raw Acceleration',
                'live_C_filtered': 'Live C — Filtered Sway',
                'live_D_drift':    'Live D — Drift / Rejected',
                'live_E_fft':      'Live E — High-Res FFT Segments',
                'live_6A_stft':     'Live 6A — STFT Spectrogram',
                'live_6B_manual':   'Live 6B — Manual FFT Segmentation',
                'live_6C_cwt':      'Live 6C — Continuous Wavelet Transform',
                'live_6D_staltal':  'Live 6D — STA/LTA Event Detection',
            }
            for key, display in label_map.items():
                if key in fname:
                    return display
            return fname.replace('_', ' ').replace('.png', '')

        # sort logic
        sort_order = {
            '_A_full': 10,
            '_B_raw': 20,
            '_C_filter': 30,
            '_C_filtered': 30,
            '_D_drift': 40,
            '_E_fft': 50,
            '6A_stft': 60,
            '6B_manual': 70,
            '6C_cwt': 80,
            '6D_staltal': 90,
        }

        def _sort_key(url):
            fname = os.path.basename(url.split('?')[0])
            base_score = 999
            for k, v in sort_order.items():
                if k in fname:
                    base_score = v
                    break
            import re
            seg_match = re.search(r'segs(\d+)-', fname)
            if seg_match:
                return (base_score, int(seg_match.group(1)))
            return (base_score, 0)

        image_urls = sorted(image_urls, key=_sort_key)

        tiles = []
        for url in image_urls:
            url_base = url.split('?')[0]
            if not os.path.basename(url_base).startswith('live_'):
                continue
                
            tiles.append(
                html.Div(className='shm-gallery-item', style={'display': 'block'}, children=[
                    html.Img(
                        id={'type': 'shm-gallery-img', 'index': url},
                        src=url, alt=_label(url),
                        n_clicks=0,
                        title='Click to view full size',
                        style={'cursor': 'zoom-in', 'display': 'block', 'width': '100%'}
                    ),
                    html.Div(_label(url_base), className='shm-gallery-item-label'),
                ])
            )
        
        if not tiles:
             return html.Div(className='shm-empty-state', children=[
                html.Div('🔍', className='shm-empty-icon'),
                html.Div('No live images found.', className='shm-empty-text'),
            ])
            
        return tiles

    # --- CALLBACK: SET FILTER TABS → update shm-set-filter store ---
    @app.callback(
        Output('shm-set-filter', 'data'),
        Output('shm-filter-all',      'style'),
        Output('shm-filter-set1',     'style'),
        Output('shm-filter-set2',     'style'),
        Output('shm-filter-set3',     'style'),
        Output('shm-filter-set4',     'style'),
        Output('shm-filter-set5',     'style'),
        Output('shm-filter-set6',     'style'),
        Output('shm-filter-part7',    'style'),
        Output('shm-filter-overview', 'style'),
        [Input('shm-filter-all',      'n_clicks'),
         Input('shm-filter-set1',     'n_clicks'),
         Input('shm-filter-set2',     'n_clicks'),
         Input('shm-filter-set3',     'n_clicks'),
         Input('shm-filter-set4',     'n_clicks'),
         Input('shm-filter-set5',     'n_clicks'),
         Input('shm-filter-set6',     'n_clicks'),
         Input('shm-filter-part7',    'n_clicks'),
         Input('shm-filter-overview', 'n_clicks')],
        prevent_initial_call=True
    )
    def update_shm_filter(c_all, c1, c2, c3, c4, c5, c6, p7, c_ov):
        """Highlight the active filter tab and store its value."""
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Base styles
        _base = lambda bg, border, color: {
            'background': bg, 'border': border, 'color': color,
            'padding': '7px 18px', 'borderRadius': '20px',
            'fontFamily': 'Outfit', 'fontSize': '13px', 'fontWeight': '600', 'cursor': 'pointer',
        }
        _active = lambda bg, border, color: {
            **_base(bg, border, color), 'fontWeight': '800',
            'boxShadow': f'0 0 14px {color}55',
        }

        styles = {
            'shm-filter-all':      _base('rgba(52,211,153,0.10)',  '1px solid rgba(52,211,153,0.3)',  '#34d399'),
            'shm-filter-set1':     _base('rgba(56,189,248,0.08)',  '1px solid rgba(56,189,248,0.2)',  '#38bdf8'),
            'shm-filter-set2':     _base('rgba(244,114,182,0.08)', '1px solid rgba(244,114,182,0.2)', '#f472b6'),
            'shm-filter-set3':     _base('rgba(74,222,128,0.08)',  '1px solid rgba(74,222,128,0.2)',  '#4ade80'),
            'shm-filter-set4':     _base('rgba(45,212,191,0.08)',  '1px solid rgba(45,212,191,0.2)',  '#2dd4bf'),
            'shm-filter-set5':     _base('rgba(129,140,248,0.08)', '1px solid rgba(129,140,248,0.2)', '#818cf8'),
            'shm-filter-set6':     _base('rgba(192,132,252,0.08)', '1px solid rgba(192,132,252,0.2)', '#c084fc'),
            'shm-filter-part7':    _base('rgba(251,191,36,0.08)',  '1px solid rgba(251,191,36,0.2)',  '#fbbf24'),
            'shm-filter-overview': _base('rgba(251,191,36,0.08)',  '1px solid rgba(251,191,36,0.2)',  '#fbbf24'),
        }

        active_map = {
            'shm-filter-all':      ('all',      _active('rgba(52,211,153,0.22)',  '2px solid #34d399', '#34d399')),
            'shm-filter-set1':     ('set1',     _active('rgba(56,189,248,0.22)',  '2px solid #38bdf8', '#38bdf8')),
            'shm-filter-set2':     ('set2',     _active('rgba(244,114,182,0.22)', '2px solid #f472b6', '#f472b6')),
            'shm-filter-set3':     ('set3',     _active('rgba(74,222,128,0.22)',  '2px solid #4ade80', '#4ade80')),
            'shm-filter-set4':     ('set4',     _active('rgba(45,212,191,0.22)',  '2px solid #2dd4bf', '#2dd4bf')),
            'shm-filter-set5':     ('set5',     _active('rgba(129,140,248,0.22)', '2px solid #818cf8', '#818cf8')),
            'shm-filter-set6':     ('set6',     _active('rgba(192,132,252,0.22)', '2px solid #c084fc', '#c084fc')),
            'shm-filter-part7':    ('part7',    _active('rgba(251,191,36,0.22)',  '2px solid #fbbf24', '#fbbf24')),
            'shm-filter-overview': ('overview', _active('rgba(251,191,36,0.22)',  '2px solid #fbbf24', '#fbbf24')),
        }

        filter_val, active_style = active_map.get(btn_id, ('all', styles['shm-filter-all']))
        styles[btn_id] = active_style

        return (filter_val,
                styles['shm-filter-all'], styles['shm-filter-set1'],
                styles['shm-filter-set2'], styles['shm-filter-set3'],
                styles['shm-filter-set4'], styles['shm-filter-set5'],
                styles['shm-filter-set6'], styles['shm-filter-part7'],
                styles['shm-filter-overview'])

    # --- CALLBACK: RENDER SHM GALLERY (responds to new images OR filter change) ---
    @app.callback(
        Output('shm-gallery-container', 'children'),
        [Input('shm-images-store', 'data'),
         Input('shm-set-filter',   'data')],
        prevent_initial_call=True
    )
    def render_shm_gallery(image_urls, active_filter):
        """
        Render the SHM PNG gallery.
        Filters by set prefix when a set tab is active.
        Also scans assets/shm_output/ for previously generated images when store is empty.
        """
        # If no fresh images in store, try loading previous run from disk
        if not image_urls:
            shm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'shm_output')
            if os.path.isdir(shm_dir):
                # Use file modification time as cache-buster — forces browser to reload updated images
                found = sorted([
                    f'/assets/shm_output/{f}?v={int(os.path.getmtime(os.path.join(shm_dir, f)))}'
                    for f in os.listdir(shm_dir)
                    if f.lower().endswith('.png')
                ])
                if found:
                    image_urls = found
                    print(f"[SHM Gallery] Loaded {len(found)} previously generated images from disk.")

        if not image_urls:
            return html.Div(className='shm-empty-state', children=[
                html.Div('📊', className='shm-empty-icon'),
                html.Div('Click "Run SHM Analysis" to generate graphs, then filter by set above.', className='shm-empty-text'),
            ])

        # Apply set filter
        filt = (active_filter or 'all').lower()
        FILTER_PREFIX = {
            'set1':    'set1_',
            'set2':    'set2_',
            'set3':    'set3_',
            'set4':    'set4_',
            'set5':    'set5_',
            'set6':    'set6_',
            'part7':   'part7',
            'overview': 'part',
        }
        prefix = FILTER_PREFIX.get(filt, '')

        # Check if there are ANY visible images
        visible_count = len([u for u in image_urls if not prefix or os.path.basename(u).startswith(prefix)])
        
        if visible_count == 0:
            label = filt.upper()
            return html.Div(className='shm-empty-state', children=[
                html.Div('🔍', className='shm-empty-icon'),
                html.Div(f'No images for {label} yet. Run SHM Analysis first.', className='shm-empty-text'),
            ])

        # Friendly label map
        label_map = {
            '_A_full':     'Graph A — Full Timeline',
            '_B_raw':      'Graph B — Raw Acceleration',
            '_C_filtered': 'Graph C — Filtered Sway',
            '_D_drift':    'Graph D — Drift / Rejected',
            '_E_fft':      'Graph E — High-Res FFT Segments',
            '6A_stft':     '6A — STFT Spectrogram',
            '6B_manual':   '6B — Manual FFT Segmentation',
            '6C_cwt':      '6C — Continuous Wavelet Transform',
            '6D_staltal':  '6D — STA/LTA Event Detection',
            'part2_fft':   '🔵 Overall FFT Comparison (3×3)',
            'part4_fft':   '🔵 Normal vs High-Res FFT Demo',
            'part5_fft':   '🔵 Normal Resolution 3×3 Grid',
            'part7_algo':  '🔵 Part 7 — Overall Algorithm Performance',
        }

        def _label(url):
            fname = os.path.basename(url)
            for key, display in label_map.items():
                if key in fname:
                    return display
            return fname.replace('_', ' ').replace('.png', '')

        # Apply logical sorting based on filename
        sort_order = {
            '_A_full': 10,
            '_B_raw': 20,
            '_C_filter': 30,
            '_C_filtered': 30,
            '_D_drift': 40,
            '_E_fft': 50,
            '6A_stft': 60,
            '6B_manual': 70,
            '6C_cwt': 80,
            '6D_staltal': 90,
            'part2': 100,
            'part4': 110,
            'part5': 120,
        }

        def _sort_key(url):
            fname = os.path.basename(url.split('?')[0])  # strip cache-busting query param
            base_score = 999
            for k, v in sort_order.items():
                if k in fname:
                    base_score = v
                    break
            
            # Extract segment number for correct numerical sorting of FFT segments
            import re
            seg_match = re.search(r'segs(\d+)-', fname)
            if seg_match:
                return (base_score, int(seg_match.group(1)))
            
            return (base_score, 0)

        image_urls = sorted(image_urls, key=_sort_key)

        tiles = []
        for url in image_urls:
            # Strip query params for basename comparison
            url_base = url.split('?')[0]
            # Determine visibility based on filter
            is_visible = True
            if os.path.basename(url_base).startswith('live_'):
                is_visible = False
            elif prefix and not os.path.basename(url_base).startswith(prefix):
                is_visible = False
                
            tiles.append(
                html.Div(className='shm-gallery-item', style={'display': 'block' if is_visible else 'none'}, children=[
                    html.Img(
                        id={'type': 'shm-gallery-img', 'index': url},
                        src=url, alt=_label(url),
                        n_clicks=0,
                        title='Click to view full size',
                        style={'cursor': 'zoom-in', 'display': 'block', 'width': '100%'}
                    ),
                    html.Div(_label(url_base), className='shm-gallery-item-label'),
                ])
            )
        return tiles

    # --- CALLBACK: SHM IMAGE MODAL ---
    @app.callback(
        Output('shm-image-modal', 'style'),
        Output('shm-modal-img', 'src'),
        Output('shm-modal-title', 'children'),
        [Input({'type': 'shm-gallery-img', 'index': dash.dependencies.ALL}, 'n_clicks'),
         Input('shm-modal-close', 'n_clicks')],
        prevent_initial_call=True
    )
    def toggle_shm_image_modal(img_clicks, close_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
        
        trigger = ctx.triggered[0]
        prop_id = trigger['prop_id']
        val = trigger['value']
        
        # Prevent modal from opening when filter tabs recreate images with n_clicks=0
        if not val:
            raise dash.exceptions.PreventUpdate

        # Extract the component ID part (remove the .n_clicks suffix)
        if prop_id.endswith('.n_clicks'):
            trigger_id = prop_id[:-9]
        else:
            trigger_id = prop_id.split('.')[0]
        
        # If closed via button
        if trigger_id == 'shm-modal-close':
            return {'display': 'none'}, '', ''
        
        # If clicked on an image
        if 'shm-gallery-img' in trigger_id:
            try:
                import json
                id_dict = json.loads(trigger_id)
                url = id_dict['index']
                
                # Reconstruct friendly label
                label_map = {
                    '_A_full':     'Graph A — Full Timeline',
                    '_B_raw':      'Graph B — Raw Acceleration',
                    '_C_filtered': 'Graph C — Filtered Sway',
                    '_D_drift':    'Graph D — Drift / Rejected',
                    '_E_fft':      'Graph E — High-Res FFT Segments',
                    '6A_stft':     '6A — STFT Spectrogram',
                    '6B_manual':   '6B — Manual FFT Segmentation',
                    '6C_cwt':      '6C — Continuous Wavelet Transform',
                    '6D_staltal':  '6D — STA/LTA Event Detection',
                    'part2_fft':   '🔵 Overall FFT Comparison (3×3)',
                    'part4_fft':   '🔵 Normal vs High-Res FFT Demo',
                    'part5_fft':   '🔵 Normal Resolution 3×3 Grid',
                }
                
                fname = os.path.basename(url)
                label = fname.replace('_', ' ').replace('.png', '')
                for key, display in label_map.items():
                    if key in fname:
                        label = display
                        break
                
                style = {
                    'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'width': '100vw', 'height': '100vh',
                    'backgroundColor': 'rgba(0,0,0,0.85)', 'backdropFilter': 'blur(10px)',
                    'zIndex': 9999, 'alignItems': 'center', 'justifyContent': 'center', 'flexDirection': 'column'
                }
                return style, url, label
            except Exception as e:
                print(f"[SHM Modal] Error: {e}")
                pass
                
        raise dash.exceptions.PreventUpdate



    @app.callback(
        Output('matlab-graph', 'figure'),
        Output('matlab-stats-row', 'children'),
        [Input('matlab-results-store', 'data')],
        prevent_initial_call=True
    )
    def render_matlab_content(data):
        """Render the processed graph and metric badges from the results store."""
        if not data:
            raise dash.exceptions.PreventUpdate

        x_arr   = data['x']
        y_arr   = data['y']
        z_arr   = data['z']
        times   = data['times']
        metrics = data['metrics']
        port    = data['port']

        matlab_colors = {'X': '#a78bfa', 'Y': '#f0abfc', 'Z': '#67e8f9'}
        fill_colors   = {'X': 'rgba(167,139,250,0.06)', 'Y': 'rgba(240,171,252,0.06)', 'Z': 'rgba(103,232,249,0.06)'}

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            subplot_titles=('X-Axis (Processed)', 'Y-Axis (Processed)', 'Z-Axis (Processed)'))
        fig.update_annotations(font=dict(family="Outfit", size=16, color="#a78bfa"))

        for row_idx, (col_name, col_data) in enumerate(
            zip(['X', 'Y', 'Z'], [x_arr, y_arr, z_arr]), start=1
        ):
            fig.append_trace(go.Scatter(
                x=times, y=col_data,
                name=f'{col_name}-Axis',
                mode='lines',
                line=dict(width=2, color=matlab_colors[col_name], shape='spline'),
                fill='tozeroy',
                fillcolor=fill_colors[col_name],
            ), row=row_idx, col=1)

        fig.update_layout(
            height=750,
            template='plotly_dark',
            showlegend=True,
            hovermode='x unified',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 23, 42, 0.2)',
            font=dict(family="Outfit", color="#f8fafc", size=13),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                bgcolor="rgba(15,23,42,0.7)", bordercolor="rgba(167,139,250,0.2)", borderwidth=1
            ),
            uirevision=f'matlab-chart-{port}',
        )
        for i in range(1, 4):
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(167,139,250,0.06)', row=i, col=1)
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(167,139,250,0.05)', row=i, col=1)

        # Build metric badge cards
        badge_defs = [
            ('X RMS',         metrics['x_rms'],   '#a78bfa'),
            ('Y RMS',         metrics['y_rms'],   '#f0abfc'),
            ('Z RMS',         metrics['z_rms'],   '#67e8f9'),
            ('X Peak–Peak',   metrics['x_peak'],  '#a78bfa'),
            ('Y Peak–Peak',   metrics['y_peak'],  '#f0abfc'),
            ('Z Peak–Peak',   metrics['z_peak'],  '#67e8f9'),
        ]
        badges = [
            html.Div(className='stat-badge', children=[
                html.Div(label, className='stat-badge-label'),
                html.Div(f"{val:.3f}", className='stat-badge-value', style={'color': color}),
                html.Div('m/s²', style={'fontSize': '10px', 'color': '#475569', 'marginTop': '2px'}),
            ])
            for label, val, color in badge_defs
        ]

        return fig, badges

    @app.callback(
        Output('live-graph-panel', 'style'),
        Output('matlab-graph-panel', 'style'),
        Output('shm-report-panel', 'style'),
        Output('live-tab-btn', 'className'),
        Output('matlab-tab-btn', 'className'),
        Output('shm-tab-btn', 'className'),
        [Input('live-tab-btn', 'n_clicks'),
         Input('matlab-tab-btn', 'n_clicks'),
         Input('shm-tab-btn', 'n_clicks'),
         Input('live-shm-images-store', 'data'),
         Input('shm-images-store', 'data')],
        [State('current-port-store', 'data')],
        prevent_initial_call=True
    )
    def manage_tabs(live_clicks, matlab_clicks, shm_clicks, live_shm_data, shm_data, current_port):
        """Switch between Live Stream, MATLAB Analysis, and SHM Report panels."""
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Reconstruct port-tinted border colour for the live panel
        port_color = colors.get(int(current_port), '#38bdf8') if current_port else '#38bdf8'
        try:
            pr, pg, pb = int(port_color[1:3], 16), int(port_color[3:5], 16), int(port_color[5:7], 16)
            port_border = f'1px solid rgba({pr},{pg},{pb},0.13)'
        except Exception:
            port_border = '1px solid rgba(56,189,248,0.13)'

        _base = dict(
            backgroundColor='rgba(15, 23, 42, 0.4)',
            backdropFilter='blur(20px)',
            borderRadius='24px',
            padding='25px',
            boxShadow='0 20px 50px rgba(0,0,0,0.5)',
        )
        live_show   = {**_base, 'display': 'block', 'border': port_border}
        live_hide   = {**_base, 'display': 'none',  'border': port_border}
        matlab_show = {**_base, 'display': 'block', 'border': '1px solid rgba(167,139,250,0.2)'}
        matlab_hide = {**_base, 'display': 'none',  'border': '1px solid rgba(167,139,250,0.2)'}
        shm_show    = {**_base, 'display': 'block', 'border': '1px solid rgba(52,211,153,0.2)', 'padding': '28px'}
        shm_hide    = {**_base, 'display': 'none',  'border': '1px solid rgba(52,211,153,0.2)', 'padding': '28px'}

        if trigger_id == 'live-tab-btn':
            return live_show, matlab_hide, shm_hide, \
                   'tab-btn tab-btn-live-active', 'tab-btn', 'tab-btn'

        elif trigger_id == 'matlab-tab-btn':
            return live_hide, matlab_show, shm_hide, \
                   'tab-btn', 'tab-btn tab-btn-matlab-active', 'tab-btn'

        elif trigger_id == 'shm-tab-btn':
            return live_hide, matlab_hide, shm_show, \
                   'tab-btn', 'tab-btn', 'tab-btn shm-tab-btn-active'

        elif trigger_id == 'live-shm-images-store':
            if not live_shm_data:
                raise dash.exceptions.PreventUpdate
            return live_hide, matlab_show, shm_hide, \
                   'tab-btn', 'tab-btn tab-btn-matlab-active', 'tab-btn'

        elif trigger_id == 'shm-images-store':
            if not shm_data:
                raise dash.exceptions.PreventUpdate
            return live_hide, matlab_hide, shm_show, \
                   'tab-btn', 'tab-btn', 'tab-btn shm-tab-btn-active'

        raise dash.exceptions.PreventUpdate

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    print("\n🚀 Starting Premium Web Server... Open your browser and go to http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050, threaded=True)

if __name__ == "__main__":
    import threading
    listener_thread = threading.Thread(target=UDP_listener, daemon=True)
    listener_thread.start()
    
    # Start massive I/O worker to write UDP RAM buffer to disk safely
    csv_writer_thread = threading.Thread(target=csv_flush_worker, args=(5,), daemon=True)
    csv_writer_thread.start()
    
    # Start Google Drive background sync thread (every 5 minutes)
    drive_thread = threading.Thread(target=start_sync_loop, args=(5,), daemon=True)
    drive_thread.start()
    
    start_dashboard()
