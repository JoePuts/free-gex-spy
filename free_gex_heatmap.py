import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import webbrowser
import os
import time

# =========================================================
# CONFIG
# =========================================================

TICKERS = [
    "SPY",
    "QQQ",
    "NVDA",
    "TSLA",
    "AAPL",
    "META",
    "MSFT",
    "AMZN"
]

OUTPUT_DIR = "gamma_dashboards"

AUTO_REFRESH_SECONDS = 60
EXPIRATION_COUNT = 3

os.makedirs(OUTPUT_DIR, exist_ok=True)

THEMES = {
    "SPY": "#7CFFB2",
    "QQQ": "#57D9FF",
    "NVDA": "#76FF7A",
    "TSLA": "#FF5A5A",
    "AAPL": "#D0D0D0",
    "META": "#4DA3FF",
    "MSFT": "#4CC2FF",
    "AMZN": "#FFB347"
}

print("Starting Institutional Gamma Dashboard...")

# =========================================================
# BUILD DASHBOARD
# =========================================================

def build_heatmap(ticker_symbol):

    try:
        ticker = yf.Ticker(ticker_symbol)

        hist = ticker.history(period="1d")

        if hist.empty:
            print(f"No data for {ticker_symbol}")
            return None

        current_price = hist['Close'].iloc[-1]

        expirations = ticker.options[:EXPIRATION_COUNT]

    except Exception as e:
        print(f"Error loading {ticker_symbol}: {e}")
        return None

    theme_color = THEMES.get(ticker_symbol, "#00FF88")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # =====================================================
    # NAVBAR
    # =====================================================

    nav_buttons = ""

    for t in TICKERS:

        color = THEMES.get(t, "#666")

        nav_buttons += f'''
        <a href="{t}_heatmap.html"
           class="ticker-button"
           style="border-color:{color};">
           {t}
        </a>
        '''

    # =====================================================
    # HTML START
    # =====================================================

    html = f'''
<!DOCTYPE html>
<html>

<head>

<title>{ticker_symbol} Gamma Dashboard</title>

<meta http-equiv="refresh" content="{AUTO_REFRESH_SECONDS}">

<style>

html {{
    scroll-behavior: smooth;
}}

body {{
    background: #050505;
    color: white;
    font-family: Arial;
    margin: 0;
    padding: 20px;
}}

h1 {{
    text-align: center;
    color: {theme_color};
    font-size: 42px;
    margin-bottom: 10px;
    letter-spacing: 1px;
}}

.timestamp {{
    text-align: center;
    color: #888;
    margin-bottom: 20px;
    font-size: 14px;
}}

.navbar {{
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 22px;
}}

.ticker-button {{
    text-decoration: none;
    color: white;
    background: #111;
    border: 2px solid #444;
    padding: 10px 16px;
    border-radius: 8px;
    font-weight: bold;
    transition: 0.2s;
}}

.ticker-button:hover {{
    background: #1a1a1a;
}}

.metrics-bar {{

    position: sticky;
    top: 0;

    z-index: 99999;

    display: flex;
    justify-content: center;
    gap: 18px;
    flex-wrap: wrap;

    background: rgba(8,8,8,0.97);

    padding: 14px;

    margin-bottom: 24px;

    border-bottom: 2px solid #222;

    backdrop-filter: blur(10px);
}}

.metric-card {{
    background: #101010;
    border: 1px solid #222;
    border-radius: 10px;
    padding: 14px 22px;
    min-width: 170px;
    text-align: center;
}}

.metric-label {{
    color: #777;
    font-size: 12px;
    margin-bottom: 6px;
    letter-spacing: 1px;
}}

.metric-value {{
    font-size: 28px;
    font-weight: bold;
}}

.price-value {{
    color: #00FF88;
}}

.call-wall {{
    color: #57D9FF;
}}

.put-wall {{
    color: #FF5A5A;
}}

.gamma-flip {{
    color: #FFD700;
}}

.container {{
    display: flex;
    gap: 18px;
    justify-content: center;
    align-items: flex-start;
    width: 100%;
}}

.day-section {{
    flex: 1 1 32%;
    min-width: 420px;
}}

h3 {{

    text-align: center;

    color: #ccc;

    background: #101010;

    padding: 12px;

    position: sticky;

    top: 110px;

    z-index: 1000;

    border-bottom: 2px solid #222;

    margin: 0;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: #0d0d0d;
}}

th, td {{
    padding: 10px;
    border-bottom: 1px solid #161616;
    text-align: right;
}}

th {{
    background: #111;
    color: #aaa;
}}

.strike {{
    background: #000;
    font-weight: bold;
}}

.pct {{
    text-align: center;
    font-weight: bold;
}}

.bar {{
    height: 28px;
    border-radius: 2px;
}}

.current {{
    background: #161616 !important;
    border-left: 4px solid white;
}}

.call-wall-row {{
    border-left: 4px solid #57D9FF !important;
}}

.put-wall-row {{
    border-left: 4px solid #FF5A5A !important;
}}

.gamma-flip-row {{
    border-left: 4px solid #FFD700 !important;
}}

@keyframes goldGlow {{

    0% {{
        box-shadow: 0 0 8px #FFD700;
    }}

    100% {{
        box-shadow: 0 0 24px #FFD700;
    }}
}}

@keyframes purpleGlow {{

    0% {{
        box-shadow: 0 0 8px #8B00FF;
    }}

    100% {{
        box-shadow: 0 0 24px #AA00FF;
    }}
}}

@keyframes tealGlow {{

    0% {{
        box-shadow: 0 0 8px #00D4FF;
    }}

    100% {{
        box-shadow: 0 0 20px #00FFFF;
    }}
}}

.kingpin {{
    animation: goldGlow 1.3s infinite alternate;
}}

.purple-bar {{
    animation: purpleGlow 1.4s infinite alternate;
}}

.teal-bar {{
    animation: tealGlow 1.5s infinite alternate;
}}

#topBtn {{

    position: fixed;

    bottom: 30px;

    right: 30px;

    z-index: 9999;

    background: #111;

    color: white;

    border: 2px solid #666;

    padding: 14px 18px;

    border-radius: 12px;

    cursor: pointer;
}}

#currentBtn {{

    position: fixed;

    bottom: 95px;

    right: 30px;

    z-index: 9999;

    background: #111;

    color: #00FF88;

    border: 2px solid #00FF88;

    padding: 14px 18px;

    border-radius: 12px;

    cursor: pointer;
}}

</style>

<script>

function scrollToTop() {{
    window.scrollTo({{
        top: 0,
        behavior: 'smooth'
    }});
}}

function jumpToCurrent() {{

    const current = document.querySelector('.current');

    if(current) {{

        current.scrollIntoView({{
            behavior: 'smooth',
            block: 'center'
        }});
    }}
}}

</script>

</head>

<body onload="jumpToCurrent()">

<button id="topBtn" onclick="scrollToTop()">
↑ TOP
</button>

<button id="currentBtn" onclick="jumpToCurrent()">
🎯 CURRENT
</button>

<h1>{ticker_symbol} Gamma Dashboard</h1>

<div class="timestamp">
Price: <b>{current_price:.2f}</b>
• Updated: {now_str}
• Refresh: {AUTO_REFRESH_SECONDS}s
</div>

<div class="navbar">
{nav_buttons}
</div>
'''

    first_exp = True

    # =====================================================
    # EXPIRATION LOOP
    # =====================================================

    for exp in expirations:

        exp_date = (
            pd.to_datetime(exp)
            .strftime('%m/%d/%Y')
            .lstrip('0')
            .replace('/0', '/')
        )

        opt = None

        for attempt in range(3):

            try:
                opt = ticker.option_chain(exp)
                break

            except Exception:

                print(f"Retry {attempt+1}/3 {ticker_symbol} {exp}")

                time.sleep(2)

        if opt is None:
            continue

        calls = opt.calls.copy()
        puts = opt.puts.copy()

        calls['type'] = 'call'
        puts['type'] = 'put'

        df_exp = pd.concat([calls, puts], ignore_index=True)

        spot = current_price

        # =================================================
        # FLOW MODEL
        # =================================================

        df_exp['flow'] = (
            df_exp['openInterest']
            * 100
            * spot
            * np.where(df_exp['type'] == 'call', 1, -1)
        )

        heatmap_df = (
            df_exp.groupby('strike')['flow']
            .sum()
            .reset_index()
        )

        heatmap_df = heatmap_df.sort_values('strike')

        # =================================================
        # WALLS
        # =================================================

        call_side = heatmap_df[heatmap_df['flow'] > 0]

        put_side = heatmap_df[heatmap_df['flow'] < 0]

        call_wall = None
        put_wall = None
        gamma_flip = None

        if not call_side.empty:

            call_wall = call_side.loc[
                call_side['flow'].idxmax()
            ]['strike']

        if not put_side.empty:

            put_wall = put_side.loc[
                put_side['flow'].idxmin()
            ]['strike']

        heatmap_df['cumulative'] = (
            heatmap_df['flow'].cumsum()
        )

        flip_candidates = heatmap_df[
            heatmap_df['cumulative'] > 0
        ]

        if not flip_candidates.empty:

            gamma_flip = flip_candidates.iloc[0]['strike']

        # =================================================
        # METRICS BAR
        # =================================================

        if first_exp:

            html += f'''

<div class="metrics-bar">

<div class="metric-card">
<div class="metric-label">LIVE PRICE</div>
<div class="metric-value price-value">
${current_price:.2f}
</div>
</div>

<div class="metric-card">
<div class="metric-label">CALL WALL</div>
<div class="metric-value call-wall">
{call_wall}
</div>
</div>

<div class="metric-card">
<div class="metric-label">PUT WALL</div>
<div class="metric-value put-wall">
{put_wall}
</div>
</div>

<div class="metric-card">
<div class="metric-label">GAMMA FLIP</div>
<div class="metric-value gamma-flip">
{gamma_flip}
</div>
</div>

</div>

<div class="container">
'''

            first_exp = False

        # =================================================
        # PERCENT DISTANCE
        # =================================================

        heatmap_df['pct'] = (
            (
                heatmap_df['strike']
                - spot
            )
            / spot
            * 100
        ).round(1)

        heatmap_df['pct_str'] = (
            heatmap_df['pct'].astype(str)
            + '%'
        )

        # =================================================
        # SCALE FLOW
        # =================================================

        max_flow = heatmap_df['flow'].abs().max()

        if max_flow > 0:

            scale = 400_000_000 / max_flow

            heatmap_df['flow'] *= scale

        heatmap_df['flow_m'] = (
            heatmap_df['flow'] / 1_000_000
        ).round(1)

        heatmap_df['dollar_str'] = (
            heatmap_df['flow_m']
            .apply(
                lambda x:
                f"${x:,.1f}M"
                if x >= 0
                else f"-${abs(x):,.1f}M"
            )
        )

        # =================================================
        # STRIKE FILTER
        # =================================================

        heatmap_df = heatmap_df[
            (
                heatmap_df['strike']
                >= current_price * 0.88
            )
            &
            (
                heatmap_df['strike']
                <= current_price * 1.12
            )
        ]

        if heatmap_df.empty:
            continue

        # =================================================
        # CURRENT PRICE TRACKER
        # =================================================

        heatmap_df['distance_to_price'] = (
            heatmap_df['strike']
            - current_price
        ).abs()

        current_idx = heatmap_df[
            'distance_to_price'
        ].idxmin()

        heatmap_df['is_current'] = False

        heatmap_df.loc[
            current_idx,
            'is_current'
        ] = True

        # =================================================
        # NODE CLASSIFICATION
        # =================================================

        heatmap_df['is_king'] = False
        heatmap_df['is_purple'] = False
        heatmap_df['is_teal'] = False

        # KINGPIN

        max_abs_idx = (
            heatmap_df['flow']
            .abs()
            .idxmax()
        )

        heatmap_df.loc[
            max_abs_idx,
            'is_king'
        ] = True

        # PURPLE NODE

        negative_nodes = heatmap_df[
            heatmap_df['flow'] < 0
        ].copy()

        negative_nodes = negative_nodes.drop(
            index=max_abs_idx,
            errors='ignore'
        )

        purple_idx = None

        if not negative_nodes.empty:

            purple_idx = (
                negative_nodes['flow']
                .idxmin()
            )

            heatmap_df.loc[
                purple_idx,
                'is_purple'
            ] = True

        # TEAL NODES

        remaining_negatives = (
            negative_nodes.drop(
                index=purple_idx,
                errors='ignore'
            )
        )

        teal_count = min(3, len(remaining_negatives))

        if teal_count > 0:

            teal_indices = (
                remaining_negatives
                .sort_values('flow')
                .head(teal_count)
                .index
            )

            heatmap_df.loc[
                teal_indices,
                'is_teal'
            ] = True

        # =================================================
        # BAR COLOR FUNCTION
        # =================================================

        def get_bar_color(
            flow,
            is_king,
            is_purple,
            is_teal
        ):

            if is_king:
                return "#FFD700"

            if is_purple:
                return "#8B00FF"

            if is_teal:
                return "#00D4FF"

            if flow < 0:
                return "#FF4444"

            return "#00FF88"

        # =================================================
        # HTML TABLE
        # =================================================

        html += f'''
<div class="day-section">

<h3>{exp_date}</h3>

<table>

<tr>
<th>STRIKE</th>
<th>%</th>
<th>GAMMA FLOW</th>
</tr>
'''

        for _, row in heatmap_df.iterrows():

            width = min(
                abs(row['flow']) / 4_000_000,
                100
            )

            color = get_bar_color(
                row['flow'],
                row['is_king'],
                row['is_purple'],
                row['is_teal']
            )

            extra_class = ""

            if row['is_king']:
                extra_class = "kingpin"

            elif row['is_purple']:
                extra_class = "purple-bar"

            elif row['is_teal']:
                extra_class = "teal-bar"

            row_class = ""

            if row['is_current']:
                row_class += " current"

            if row['strike'] == call_wall:
                row_class += " call-wall-row"

            if row['strike'] == put_wall:
                row_class += " put-wall-row"

            if row['strike'] == gamma_flip:
                row_class += " gamma-flip-row"

            html += f'''
<tr class="{row_class}">

<td class="strike">
{row['strike']}
</td>

<td class="pct">
{row['pct_str']}
</td>

<td>

<div
class="bar {extra_class}"
style="
width:{width}%;
background:{color};
">
</div>

<div style="
margin-top:4px;
font-size:12px;
color:#aaa;
">
{row['dollar_str']}
</div>

</td>

</tr>
'''

        html += '''
</table>
</div>
'''

    html += '''
</div>
</body>
</html>
'''

    # =====================================================
    # SAVE FILE
    # =====================================================

    filepath = os.path.join(
        OUTPUT_DIR,
        f"{ticker_symbol}_heatmap.html"
    )

    with open(filepath, "w", encoding="utf-8") as f:

        f.write(html)

    print(f"Built {filepath}")

    return filepath

# =========================================================
# MAIN LOOP
# =========================================================

opened = False

while True:

    print(
        f"\nRefreshing dashboards..."
    )

    first_file = None

    for ticker in TICKERS:

        filepath = build_heatmap(ticker)

        if filepath and first_file is None:

            first_file = filepath

    if first_file and not opened:

        webbrowser.open(
            "file://" + os.path.abspath(first_file)
        )

        opened = True

    print(
        f"Sleeping {AUTO_REFRESH_SECONDS}s..."
    )

    time.sleep(AUTO_REFRESH_SECONDS)
