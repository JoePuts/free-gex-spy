import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import webbrowser
import os
import time

print("Starting FULL-SCREEN LIVE Gamma Exposure Heatmap...")
print("→ Dates now stick when scrolling down")
print("→ Auto-updates every 20 seconds")
print("→ Press F5 in browser to refresh\n")

TICKER = "SPY"
html_file = "gex_heatmap_final.html"

def build_heatmap():
    ticker = yf.Ticker(TICKER)
    current_price = ticker.history(period="1d")['Close'].iloc[-1]
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    expirations = ticker.options[:4]

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LIVE SPX/SPY Gamma Exposure Heatmap</title>
    <style>
        body {{ background: #0f0f0f; color: #fff; font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        h2 {{ text-align: center; color: #0f0; margin: 20px 0 10px; font-size: 28px; }}
        .timestamp {{ text-align: center; color: #666; font-size: 16px; margin-bottom: 25px; }}
        .container {{ display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }}
        .day-section {{ flex: 1; min-width: 360px; max-width: 420px; position: relative; }} /* ← tad wider for better screen fit */
        h3 {{ 
            text-align: center; 
            color: #aaa; 
            margin: 0 0 8px 0; 
            font-size: 20px; 
            background: #1a1a1a; 
            padding: 12px; 
            position: sticky; 
            top: 0; 
            z-index: 10; 
            border-bottom: 2px solid #333;
        }}
        table {{ width: 100%; border-collapse: collapse; background: #111; }}
        th, td {{ padding: 12px 14px; text-align: right; border-bottom: 1px solid #333; font-size: 15px; }}
        th {{ background: #1a1a1a; font-weight: bold; }}
        .strike {{ text-align: right; font-weight: bold; width: 90px; background: #000; }}
        .pct {{ text-align: center; font-weight: bold; width: 85px; }}
        .bar-cell {{ text-align: left; padding-left: 12px; }}
        .dollar {{ text-align: right; font-weight: bold; width: 130px; }}
        .current {{ background: #222 !important; position: relative; }}
        .current::after {{ content: "→"; position: absolute; left: -28px; top: 50%; transform: translateY(-50%); font-size: 26px; color: white; }}
        .bar {{ 
            height: 34px; 
            border-radius: 6px; 
        }}

        /* === ULTRA COOL GLOW ANIMATIONS === */
        @keyframes goldGlow {{
            0%   {{ box-shadow: 0 0 8px #FFD700, 0 0 16px #FFEA80, 0 0 24px #FFE700; }}
            100% {{ box-shadow: 0 0 20px #FFD700, 0 0 40px #FFAA00, 0 0 60px #FFEA00; }}
        }}
        @keyframes purpleGlow {{
            0%   {{ box-shadow: 0 0 8px #8B00FF, 0 0 16px #BB44FF, 0 0 24px #CC77FF; }}
            100% {{ box-shadow: 0 0 20px #8B00FF, 0 0 40px #AA00FF, 0 0 60px #CC00FF; }}
        }}

        .kingpin {{ 
            animation: goldGlow 1.4s ease-in-out infinite alternate; 
        }}
        .purple-bar {{ 
            animation: purpleGlow 1.4s ease-in-out infinite alternate; 
        }}
    </style>
</head>
<body>
    <h2>LIVE SPX/SPY Gamma Exposure Heatmap</h2>
    <p class="timestamp">Current Price: <b>{current_price:,.2f}</b> • Last updated: {now_str} (press F5 to refresh)</p>
    <div class="container">
"""

    for exp in expirations:
        exp_date = pd.to_datetime(exp).strftime('%m/%d/%Y').lstrip('0').replace('/0', '/')
        
        try:
            opt = ticker.option_chain(exp)
            calls = opt.calls.copy()
            puts = opt.puts.copy()
            calls['type'] = 'call'
            puts['type'] = 'put'
            df_exp = pd.concat([calls, puts], ignore_index=True)
        except:
            continue

        spot = current_price
        df_exp['flow'] = df_exp['openInterest'] * 100 * spot * np.where(df_exp['type'] == 'call', 1, -1)

        heatmap_df = df_exp.groupby('strike')['flow'].sum().reset_index()
        heatmap_df = heatmap_df.sort_values('strike')

        heatmap_df['pct'] = ((heatmap_df['strike'] - spot) / spot * 100).round(1)
        heatmap_df['pct_str'] = heatmap_df['pct'].astype(str) + '%'

        max_flow = heatmap_df['flow'].abs().max()
        if max_flow > 0:
            scale = 400_000_000 / max_flow
            heatmap_df['flow'] = heatmap_df['flow'] * scale

        heatmap_df['flow_m'] = (heatmap_df['flow'] / 1_000_000).round(1)
        heatmap_df['dollar_str'] = heatmap_df['flow_m'].apply(lambda x: f"${x:,.1f}M" if x >= 0 else f"-${abs(x):,.1f}M")

        heatmap_df = heatmap_df[(heatmap_df['strike'] >= current_price * 0.88) & (heatmap_df['strike'] <= current_price * 1.12)]

        # ====================== SINGLE KINGPIN + SINGLE PURPLE ======================
        max_abs_idx = heatmap_df['flow'].abs().idxmax()
        min_idx = heatmap_df['flow'].idxmin()

        heatmap_df['is_king'] = False
        heatmap_df['is_purple'] = False

        heatmap_df.loc[max_abs_idx, 'is_king'] = True
        if not heatmap_df.empty:
            heatmap_df.loc[min_idx, 'is_purple'] = True

        def get_bar_color(flow, is_king, is_purple):
            if is_king: 
                return "#FFD700"          # Gold kingpin
            if is_purple: 
                return "#8B00FF"          # Single purple = biggest dealer loss
            if flow < 0:      
                return "#FF4444"          # Regular negative = red
            if flow > 40000:  
                return "#00FF88"
            if flow > 0:      
                return "#00CC66"
            return "#FFCC00"

        heatmap_df['bar_color'] = heatmap_df.apply(
            lambda row: get_bar_color(row['flow'], row['is_king'], row['is_purple']), axis=1
        )

        html += f'<div class="day-section"><h3>{exp_date}</h3>'
        html += """
        <table>
            <tr>
                <th class="strike">Strike</th>
                <th class="pct">% Change</th>
                <th>Net Exposure</th>
                <th class="dollar">Value</th>
            </tr>
        """

        for _, row in heatmap_df.iterrows():
            is_current = abs(row['strike'] - current_price) < 2
            row_class = 'current' if is_current else ''
            pct_color = "#00ff00" if row['pct'] > 0 else "#ff4444"
            pct_bg = "#006400" if row['pct'] > 0 else "#8B0000"
            
            bar_width = min(98, abs(row['flow_m']) * 1.5)
            if row['is_king'] or row['is_purple']:
                bar_width = 100

            extra_class = " kingpin" if row['is_king'] else " purple-bar" if row['is_purple'] else ""
            
            html += f"""
                <tr class="{row_class}">
                    <td class="strike">{int(row['strike'])}</td>
                    <td class="pct" style="background:{pct_bg}; color:{pct_color};">{row['pct_str']}</td>
                    <td class="bar-cell">
                        <div class="bar{extra_class}" style="background: {row['bar_color']}; width: {bar_width}%;"></div>
                    </td>
                    <td class="dollar">{row['dollar_str']}</td>
                </tr>
            """
        html += "</table></div>"

    html += "</div></body></html>"
    return html

# =============== LIVE UPDATE ===============
with open(html_file, "w", encoding="utf-8") as f:
    f.write(build_heatmap())

webbrowser.open('file://' + os.path.realpath(html_file))

print(f"✅ Full-screen version opened: {html_file}")
print("→ Golden kingpin + purple node now have INSANE flashing neon glows")
print("→ Both look REALLY COOL and pop hard")
print("→ Heatmap made a tad wider to better fit your screen")
print("→ Dates stay visible when scrolling down.")
print("Just press F5 in the browser to see latest flow.\n")

try:
    while True:
        time.sleep(20)
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(build_heatmap())
        print(f"Updated at {datetime.now().strftime('%H:%M:%S')}")
except KeyboardInterrupt:
    print("\nStopped.")