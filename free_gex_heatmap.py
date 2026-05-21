import pandas as pd
import yfinance as yf
import numpy as np
from scipy.stats import norm
from datetime import datetime
import webbrowser
import os
import time
import math

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
EXPIRATION_COUNT = 4
RISK_FREE_RATE = 0.045

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

print("Starting REAL Institutional Gamma Dashboard...")

# =========================================================
# BLACK SCHOLES GAMMA
# =========================================================

def calculate_gamma(S, K, iv, T, r=0.045):

    try:

        if iv <= 0:
            return 0

        if T <= 0:
            return 0

        d1 = (
            np.log(S / K)
            + (r + 0.5 * iv**2) * T
        ) / (iv * np.sqrt(T))

        gamma = (
            norm.pdf(d1)
            /
            (
                S
                * iv
                * np.sqrt(T)
            )
        )

        return gamma

    except:
        return 0

# =========================================================
# REAL GEX ENGINE
# =========================================================

def calculate_real_gex(df, spot, days_to_exp):

    T = max(days_to_exp / 365, 0.002)

    gex_values = []

    for _, row in df.iterrows():

        try:

            strike = float(row['strike'])

            oi = float(row.get('openInterest', 0))

            volume = float(row.get('volume', 0))

            iv = float(
                row.get(
                    'impliedVolatility',
                    0.25
                )
            )

            option_type = row['type']

            gamma = calculate_gamma(
                S=spot,
                K=strike,
                iv=iv,
                T=T
            )

            # =================================================
            # TRUE GAMMA EXPOSURE
            # =================================================

            gex = (
                gamma
                * oi
                * 100
                * spot
                * spot
                * 0.01
            )

            # =================================================
            # VOLUME WEIGHTING
            # =================================================

            volume_weight = (
                1
                + min(volume / max(oi, 1), 3)
            )

            gex *= volume_weight

            # =================================================
            # DISTANCE WEIGHTING
            # =================================================

            distance_pct = (
                abs(strike - spot)
                / spot
            )

            distance_weight = math.exp(
                -distance_pct * 8
            )

            gex *= distance_weight

            # =================================================
            # CALLS POSITIVE
            # PUTS NEGATIVE
            # =================================================

            if option_type == 'put':
                gex *= -1

            gex_values.append(gex)

        except:

            gex_values.append(0)

    df['gex'] = gex_values

    return df

# =========================================================
# LEVEL ENGINE
# =========================================================

def calculate_levels(df, spot):

    grouped = (
        df.groupby('strike')['gex']
        .sum()
        .reset_index()
        .sort_values('strike')
    )

    # =====================================================
    # CALL WALL
    # =====================================================

    calls = grouped[grouped['gex'] > 0]

    call_wall = None

    if not calls.empty:

        filtered_calls = calls[
            calls['strike'] >= spot * 0.985
        ]

        if filtered_calls.empty:
            filtered_calls = calls

        call_wall = filtered_calls.loc[
            filtered_calls['gex'].idxmax()
        ]['strike']

    # =====================================================
    # PUT WALL
    # =====================================================

    puts = grouped[grouped['gex'] < 0]

    put_wall = None

    if not puts.empty:

        filtered_puts = puts[
            puts['strike'] <= spot * 1.015
        ]

        if filtered_puts.empty:
            filtered_puts = puts

        put_wall = filtered_puts.loc[
            filtered_puts['gex'].idxmin()
        ]['strike']

    # =====================================================
    # TRUE GAMMA FLIP
    # =====================================================

    grouped['net_gex'] = (
        grouped['gex'].cumsum()
    )

    gamma_flip = None

    for i in range(1, len(grouped)):

        prev_val = grouped.iloc[i - 1]['net_gex']
        curr_val = grouped.iloc[i]['net_gex']

        if prev_val < 0 and curr_val > 0:

            gamma_flip = grouped.iloc[i]['strike']
            break

    # FALLBACK

    if gamma_flip is None:

        closest = grouped.iloc[
            grouped['net_gex'].abs().argsort()[:1]
        ]

        gamma_flip = closest['strike'].iloc[0]

    return (
        grouped,
        call_wall,
        put_wall,
        gamma_flip
    )

# =========================================================
# NODE CLASSIFICATION
# =========================================================

def classify_nodes(df):

    df['is_gold'] = False
    df['is_purple'] = False
    df['is_teal'] = False

    # =====================================================
    # GOLD NODE
    # MOST DEALER BUYING
    # =====================================================

    positive = df[df['gex'] > 0]

    if not positive.empty:

        gold_idx = positive['gex'].idxmax()

        df.loc[
            gold_idx,
            'is_gold'
        ] = True

    # =====================================================
    # PURPLE NODE
    # MOST DEALER SELLING
    # =====================================================

    negative = df[df['gex'] < 0]

    if not negative.empty:

        purple_idx = negative['gex'].idxmin()

        df.loc[
            purple_idx,
            'is_purple'
        ] = True

    # =====================================================
    # TEAL NODES
    # SECONDARY MAJOR LEVELS
    # =====================================================

    remaining = df[
        (~df['is_gold'])
        &
        (~df['is_purple'])
    ]

    top_secondary = remaining.reindex(
        remaining['gex'].abs().sort_values(
            ascending=False
        ).head(3).index
    )

    df.loc[
        top_secondary.index,
        'is_teal'
    ] = True

    return df

# =========================================================
# BUILD DASHBOARD
# =========================================================

def build_heatmap(ticker_symbol):

    try:

        ticker = yf.Ticker(ticker_symbol)

        hist = ticker.history(period="1d")

        if hist.empty:
            return None

        current_price = hist['Close'].iloc[-1]

        expirations = ticker.options[:EXPIRATION_COUNT]

    except Exception as e:

        print(f"ERROR {ticker_symbol}: {e}")
        return None

    theme_color = THEMES.get(
        ticker_symbol,
        "#00FF88"
    )

    now_str = datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S'
    )

    # =====================================================
    # NAV BUTTONS
    # =====================================================

    nav_buttons = ""

    for t in TICKERS:

        nav_buttons += f'''
<a href="{t}_heatmap.html">{t}</a>
'''

    # =====================================================
    # HTML
    # =====================================================

    html = f'''
<!DOCTYPE html>
<html>

<head>

<title>{ticker_symbol} Gamma Dashboard</title>

<meta http-equiv="refresh"
      content="{AUTO_REFRESH_SECONDS}">

<style>

body {{
    background:#030303;
    color:white;
    margin:0;
    font-family:Arial;
}}

.sidebar {{
    position:fixed;
    left:0;
    top:0;
    bottom:0;
    width:85px;
    background:#050505;
    border-right:1px solid #111;
    z-index:99999;
}}

.sidebar a {{
    display:block;
    padding:22px 10px;
    text-align:center;
    color:#777;
    text-decoration:none;
    border-bottom:1px solid #111;
    font-weight:900;
}}

.sidebar a:hover {{
    background:#08151c;
    color:white;
}}

.content {{
    margin-left:85px;
}}

.topbar {{
    position:sticky;
    top:0;
    background:rgba(0,0,0,.96);
    z-index:9999;
    padding:24px;
    border-bottom:1px solid #111;
    backdrop-filter:blur(8px);
}}

.title {{
    text-align:center;
    font-size:70px;
    color:{theme_color};
    font-weight:900;
}}

.timestamp {{
    text-align:center;
    color:#777;
    margin-top:10px;
    font-size:14px;
}}

.metrics {{
    display:flex;
    justify-content:center;
    gap:18px;
    margin-top:28px;
    flex-wrap:wrap;
}}

.metric {{
    width:220px;
    background:#050505;
    border:1px solid #1a1a1a;
    border-radius:20px;
    padding:22px;
    text-align:center;
}}

.metric-label {{
    color:#777;
    font-size:13px;
}}

.metric-value {{
    font-size:58px;
    font-weight:900;
    margin-top:8px;
}}

.green {{ color:#00FF99; }}
.blue {{ color:#19d3ff; }}
.red {{ color:#ff4d5a; }}
.yellow {{ color:#ffe600; }}

.grid {{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
    padding:12px;
}}

.panel {{
    background:#050505;
    border:1px solid #111;
}}

.exp-title {{
    position:sticky;
    top:205px;
    background:#111;
    text-align:center;
    padding:10px;
    font-weight:900;
    z-index:500;
}}

.table-wrap {{
    max-height:calc(100vh - 260px);
    overflow:auto;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

td {{
    border-bottom:1px solid #111;
    padding:10px;
    font-weight:900;
}}

tr:hover {{
    background:#07141d;
}}

.current {{
    background:#05192a !important;
}}

.pct-red {{
    background:#5a0000;
    color:white;
    text-align:center;
}}

.pct-green {{
    background:#004d00;
    color:white;
    text-align:center;
}}

.bar {{
    height:30px;
    border-radius:6px;
}}

@keyframes goldGlow {{

    0% {{
        box-shadow:0 0 8px #ffe600;
    }}

    100% {{
        box-shadow:0 0 30px #ffe600;
    }}
}}

@keyframes purpleGlow {{

    0% {{
        box-shadow:0 0 8px #b026ff;
    }}

    100% {{
        box-shadow:0 0 30px #b026ff;
    }}
}}

@keyframes tealGlow {{

    0% {{
        box-shadow:0 0 6px #19d3ff;
    }}

    100% {{
        box-shadow:0 0 24px #19d3ff;
    }}
}}

.gold {{
    animation:goldGlow 1.2s infinite alternate;
}}

.purple {{
    animation:purpleGlow 1.2s infinite alternate;
}}

.teal {{
    animation:tealGlow 1.5s infinite alternate;
}}

#currentBtn {{

    position:fixed;
    right:20px;
    bottom:85px;
    z-index:999999;

    background:#002b22;

    color:#00ff99;

    border:2px solid #00ff99;

    padding:16px;

    border-radius:14px;

    cursor:pointer;

    font-weight:900;
}}

#topBtn {{

    position:fixed;
    right:20px;
    bottom:20px;

    z-index:999999;

    background:#111;

    color:white;

    border:none;

    padding:16px;

    border-radius:14px;

    cursor:pointer;

    font-weight:900;
}}

</style>

<script>

function jumpCurrent() {{

    const current =
        document.querySelector('.current');

    if(current) {{

        current.scrollIntoView({{
            behavior:'smooth',
            block:'center'
        }});
    }}
}}

function topScroll() {{

    window.scrollTo({{
        top:0,
        behavior:'smooth'
    }});
}}

</script>

</head>

<body onload="jumpCurrent()">

<button id="currentBtn"
        onclick="jumpCurrent()">

🎯 CURRENT

</button>

<button id="topBtn"
        onclick="topScroll()">

↑ TOP

</button>

<div class="sidebar">

{nav_buttons}

</div>

<div class="content">

<div class="topbar">

<div class="title">

{ticker_symbol} Institutional Gamma Dashboard

</div>

<div class="timestamp">

LIVE DATA • Updated {now_str}

</div>
'''

    first_exp = True

    all_exp_data = []

    # =====================================================
    # EACH EXPIRATION
    # =====================================================

    for exp in expirations:

        try:

            option_chain = ticker.option_chain(exp)

            calls = option_chain.calls.copy()
            puts = option_chain.puts.copy()

            calls['type'] = 'call'
            puts['type'] = 'put'

            df = pd.concat([
                calls,
                puts
            ])

            exp_date = pd.to_datetime(exp)

            days_to_exp = max(
                (exp_date - pd.Timestamp.now()).days,
                1
            )

            df = calculate_real_gex(
                df,
                current_price,
                days_to_exp
            )

            grouped, call_wall, put_wall, gamma_flip = calculate_levels(
                df,
                current_price
            )

            grouped = classify_nodes(grouped)

            grouped['pct'] = (
                (
                    grouped['strike']
                    - current_price
                )
                / current_price
                * 100
            ).round(1)

            grouped = grouped[
                (
                    grouped['strike']
                    >= current_price * 0.94
                )
                &
                (
                    grouped['strike']
                    <= current_price * 1.06
                )
            ]

            grouped['distance'] = (
                grouped['strike']
                - current_price
            ).abs()

            current_idx = grouped[
                'distance'
            ].idxmin()

            grouped['is_current'] = False

            grouped.loc[
                current_idx,
                'is_current'
            ] = True

            all_exp_data.append({
                'exp': exp,
                'grouped': grouped,
                'call_wall': call_wall,
                'put_wall': put_wall,
                'gamma_flip': gamma_flip
            })

            # =================================================
            # TOP METRICS
            # =================================================

            if first_exp:

                html += f'''

<div class="metrics">

<div class="metric">

<div class="metric-label">
LIVE PRICE
</div>

<div class="metric-value green">
${current_price:.2f}
</div>

</div>

<div class="metric">

<div class="metric-label">
CALL WALL
</div>

<div class="metric-value blue">
{call_wall}
</div>

</div>

<div class="metric">

<div class="metric-label">
PUT WALL
</div>

<div class="metric-value red">
{put_wall}
</div>

</div>

<div class="metric">

<div class="metric-label">
GAMMA FLIP
</div>

<div class="metric-value yellow">
{gamma_flip}
</div>

</div>

</div>
'''

                first_exp = False

        except Exception as e:

            print(f"EXP ERROR {exp}: {e}")

    html += '''
<div class="grid">
'''

    # =====================================================
    # TABLES
    # =====================================================

    for exp_data in all_exp_data:

        exp = exp_data['exp']
        grouped = exp_data['grouped']

        exp_label = (
            pd.to_datetime(exp)
            .strftime('%m/%d/%Y')
            .lstrip('0')
            .replace('/0', '/')
        )

        max_gex = grouped['gex'].abs().max()

        html += f'''
<div class="panel">

<div class="exp-title">
{exp_label}
</div>

<div class="table-wrap">

<table>
'''

        for _, row in grouped.iterrows():

            strike = row['strike']
            gex = row['gex']

            width = min(
                abs(gex) / max_gex * 100,
                100
            )

            color = '#00ff99'

            if gex < 0:
                color = '#ff4d5a'

            extra = ''

            if row['is_gold']:

                color = '#ffe600'
                extra = 'gold'

            elif row['is_purple']:

                color = '#b026ff'
                extra = 'purple'

            elif row['is_teal']:

                color = '#19d3ff'
                extra = 'teal'

            pct_class = 'pct-green'

            if row['pct'] < 0:
                pct_class = 'pct-red'

            row_class = ''

            if row['is_current']:
                row_class = 'current'

            html += f'''
<tr class="{row_class}">

<td style="
width:95px;
font-size:18px;
">

{strike:.1f}

</td>

<td class="{pct_class}"
    style="width:90px;">

{row['pct']:.1f}%

</td>

<td>

<div
class="bar {extra}"
style="
width:{width}%;
background:{color};
">
</div>

<div style="
text-align:right;
font-size:11px;
color:#aaa;
margin-top:3px;
">

${gex/1000000:.1f}M

</div>

</td>

</tr>
'''

        html += '''
</table>

</div>

</div>
'''

    html += '''
</div>

</div>

</body>

</html>
'''

    filepath = os.path.join(
        OUTPUT_DIR,
        f"{ticker_symbol}_heatmap.html"
    )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(html)

    print(f"BUILT {ticker_symbol}")

    return filepath

# =========================================================
# MAIN LOOP
# =========================================================

opened = False

while True:

    print("Refreshing dashboards...")

    first_file = None

    for ticker_symbol in TICKERS:

        filepath = build_heatmap(
            ticker_symbol
        )

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
