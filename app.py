import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta, date

st.set_page_config(page_title="Temperature Chart", layout="wide")

# Force dark theme via CSS since config.toml is not used
st.markdown("""
<style>
  .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
      background-color: #0e1117;
      color: #fafafa;
  }
  [data-testid="stSidebar"] { background-color: #161a25; }
  .stDataFrame, [data-testid="stDataFrame"] { color: #fafafa; }
  h1, h2, h3, label, p { color: #fafafa !important; }
  [data-testid="stSlider"] label { color: #fafafa !important; }
</style>
""", unsafe_allow_html=True)

st.title("Max Temperature (°F)")

# ─── Load data from secrets ────────────────────────────────────────────────────
records = st.secrets["data"]["records"]
dates = pd.to_datetime([r["date"] for r in records])
temps = [float(r["temperature"]) for r in records]

df = pd.DataFrame({"date": dates, "temp": temps})
df = df.sort_values("date").reset_index(drop=True)

# ─── Moving average ────────────────────────────────────────────────────────────
MA_WINDOW = 10
df["moving_avg"] = df["temp"].rolling(window=MA_WINDOW, center=True, min_periods=1).mean()

# ─── Annotation config from secrets ──────────────────────────────────────────
SHADED_REGIONS = [
    (r["start"], r["end"], r["color"], float(r["alpha"]), r["label"])
    for r in st.secrets["data"]["shaded_regions"]
]
POINT_ANNOTATIONS = [
    (r["date"], r["text"], int(r["dx"]), float(r["dy"]))
    for r in st.secrets["data"]["point_annotations"]
]
VERTICAL_ANNOTATIONS = [
    (r["date"], r["label"], r["color"], r["style"])
    for r in st.secrets["data"]["vertical_annotations"]
]

Y_MIN        = 94
Y_MAX        = 106
Y_DRUG_LABEL = 105.5
Y_CRP_HIGH   = 95.2
Y_CRP_LOW    = 96.2

# ─── Date-range slider in main area ───────────────────────────────────────────
date_max = df["date"].max().date()
CHART_START = date(2025, 12, 6)

date_range = st.slider(
    "Date range",
    min_value=CHART_START,
    max_value=date_max,
    value=(CHART_START, date_max),
    format="DD MMM YYYY",
)
start_date = pd.Timestamp(date_range[0])
end_date   = pd.Timestamp(date_range[1])

# ─── Build Plotly figure ───────────────────────────────────────────────────────
fig = go.Figure()

# Shaded drug regions
for start, end, color, alpha, label in SHADED_REGIONS:
    x0 = pd.to_datetime(start)
    x1 = pd.to_datetime(end)
    fig.add_vrect(
        x0=x0.isoformat(), x1=x1.isoformat(),
        fillcolor=color, opacity=alpha,
        layer="below", line_width=0,
    )
    mid = x0 + (x1 - x0) / 2
    fig.add_annotation(
        x=mid.isoformat(), y=Y_DRUG_LABEL,
        text=label, showarrow=False,
        font=dict(size=12, color="black"),
        bgcolor=color, opacity=0.85, borderpad=3,
    )

# Vertical lines + alternating CRP labels + triangle markers
vline_xs, vline_colors = [], []
for i, (date_str, label, lcolor, lstyle) in enumerate(VERTICAL_ANNOTATIONS):
    xdate = pd.to_datetime(date_str)
    fig.add_vline(
        x=xdate.isoformat(),
        line_color=lcolor, line_width=1.2,
        line_dash=lstyle, opacity=0.85,
    )
    y_label = Y_CRP_HIGH if i % 2 == 0 else Y_CRP_LOW
    fig.add_annotation(
        x=xdate.isoformat(), y=y_label,
        text=label, showarrow=False,
        font=dict(size=11, color=lcolor),
        bgcolor="white", bordercolor=lcolor,
        borderwidth=0.9, borderpad=3, opacity=0.9,
    )
    vline_xs.append(xdate)
    vline_colors.append(lcolor)

# Triangle markers at y-axis bottom for vertical lines
fig.add_trace(go.Scatter(
    x=vline_xs,
    y=[Y_MIN] * len(vline_xs),
    mode="markers",
    marker=dict(symbol="triangle-down", size=7, color=vline_colors),
    showlegend=False,
    hoverinfo="skip",
))

# Temperature line
fig.add_trace(go.Scatter(
    x=df["date"], y=df["temp"],
    mode="lines+markers",
    name="Daily Max Temp",
    line=dict(color="#4C9BE8", width=1.4),
    marker=dict(size=4, color="#4C9BE8"),
))

# Moving average
fig.add_trace(go.Scatter(
    x=df["date"], y=df["moving_avg"],
    mode="lines",
    name=f"{MA_WINDOW}-Day Moving Avg",
    line=dict(color="#E05C2A", width=1.8, dash="dash"),
))

# Point annotations with arrows
for date_str, text, dx, dy in POINT_ANNOTATIONS:
    xpt = pd.to_datetime(date_str)
    idx = (df["date"] - xpt).abs().idxmin()
    ypt = float(df.loc[idx, "temp"])
    xtip = (xpt + timedelta(days=dx)).isoformat()
    fig.add_annotation(
        x=xtip, y=ypt + dy,
        ax=xpt.isoformat(), ay=ypt,
        xref="x", yref="y",
        axref="x", ayref="y",
        text=text, showarrow=True,
        arrowhead=2, arrowcolor="gray", arrowwidth=1,
        font=dict(size=11, color="black"),
        bgcolor="white", bordercolor="steelblue",
        borderwidth=0.8, borderpad=3,
    )

# Layout
fig.update_layout(
    template="plotly_dark",
    xaxis=dict(
        range=[start_date.isoformat(), end_date.isoformat()],
        tickformat="%d-%b",
        tickangle=-90,
        tickfont=dict(size=16, color="white"),
        title=dict(text="Date", font=dict(size=16, color="white")),
        showgrid=True,
        gridcolor="rgba(0,0,0,0.1)",
        gridwidth=0.4,
        linecolor="#aaaaaa",
    ),
    yaxis=dict(
        range=[Y_MIN, Y_MAX],
        title=dict(text="Temperature (°F)", font=dict(size=16, color="white")),
        tickfont=dict(size=16, color="white"),
        showgrid=True,
        gridcolor="rgba(0,0,0,0.15)",
        gridwidth=0.5,
        dtick=1,
        linecolor="#aaaaaa",
    ),
    height=620,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=16, color="white"),
    ),
    paper_bgcolor="#0e1117",
    plot_bgcolor="white",
    margin=dict(l=60, r=20, t=60, b=130),
)

st.plotly_chart(fig, use_container_width=True)

# Three summary tables in one row
col_crp, col_chills, col_meds = st.columns(3)

with col_crp:
    st.subheader("CRP Values")
    crp_rows = [
        {"Date": pd.to_datetime(d).strftime("%d %b %Y"), "CRP": int(lbl.split("<br>")[1].strip())}
        for d, lbl, _, _ in VERTICAL_ANNOTATIONS
        if lbl.startswith("CRP")
    ]
    st.dataframe(pd.DataFrame(crp_rows), hide_index=True, use_container_width=True)

with col_chills:
    st.subheader("Chills Episodes")
    chills_rows = [
        {"Date": pd.to_datetime(d).strftime("%d %b %Y"), "Note": text.strip()}
        for d, text, _, _ in POINT_ANNOTATIONS
    ]
    st.dataframe(pd.DataFrame(chills_rows), hide_index=True, use_container_width=True)

with col_meds:
    st.subheader("Medications")
    meds_rows = [
        {
            "From": pd.to_datetime(s).strftime("%d %b %Y"),
            "To":   pd.to_datetime(e).strftime("%d %b %Y"),
            "Medication": lbl,
        }
        for s, e, _, _, lbl in SHADED_REGIONS
    ]
    st.dataframe(pd.DataFrame(meds_rows), hide_index=True, use_container_width=True)
