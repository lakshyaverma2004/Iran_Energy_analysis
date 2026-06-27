import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR = PROJECT_ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Colour palette ──────────────────────────────────────────────────────────

BRENT_COLOR = "#185FA5"
WTI_COLOR   = "#0F6E56"
NATGAS_COLOR = "#854F0B"
EVENT_E1    = "#E24B4A"
EVENT_E2    = "#3B6D11"
EVENT_E3    = "#BA7517"
SHADING     = "#E24B4A"
BACKGROUND  = "#FAFAF8"
GRID        = "#E5E3DD"

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.facecolor"] = BACKGROUND
plt.rcParams["figure.facecolor"] = BACKGROUND
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.color"] = GRID
plt.rcParams["grid.linewidth"] = 0.6
sns.set_theme(style="whitegrid")
# Re-apply after seaborn overrides
plt.rcParams["axes.facecolor"] = BACKGROUND
plt.rcParams["figure.facecolor"] = BACKGROUND
plt.rcParams["grid.color"] = GRID
plt.rcParams["grid.linewidth"] = 0.6

SAVE_KW = dict(dpi=150, bbox_inches="tight", facecolor=BACKGROUND)

EVENTS_INFO = {
    "E1": ("2026-02-28", EVENT_E1, "--", "US-Israel Strikes Begin"),
    "E2": ("2026-06-17", EVENT_E2, "--", "US-Iran MoU Signed"),
    "E3": ("2026-06-18", EVENT_E3, ":",  "Swiss Talks Postponed"),
}

BASELINE_START = "2026-01-02"
BASELINE_END   = "2026-02-27"

# ── Load data ───────────────────────────────────────────────────────────────

prices = pd.read_csv(PROC_DIR / "prices.csv", index_col="Date", parse_dates=True)
prices = prices.loc["2026-01-02":]

returns = pd.read_csv(PROC_DIR / "returns.csv", index_col="Date", parse_dates=True)
volatility = pd.read_csv(PROC_DIR / "volatility.csv", index_col="Date", parse_dates=True)
corr_pre = pd.read_csv(PROC_DIR / "corr_pre_conflict.csv", index_col=0)
corr_con = pd.read_csv(PROC_DIR / "corr_conflict.csv", index_col=0)


def add_event_lines(ax, ypos_frac=0.95):
    """Add vertical event lines and labels to an axes."""
    for tag, (date_str, color, ls, label) in EVENTS_INFO.items():
        dt = pd.Timestamp(date_str)
        ax.axvline(dt, color=color, linestyle=ls, linewidth=1.2, zorder=3)
        ylim = ax.get_ylim()
        ypos = ylim[0] + ypos_frac * (ylim[1] - ylim[0])
        ax.text(dt, ypos, f" {tag}: {label}", rotation=90, va="top",
                ha="right", fontsize=8, color=color, alpha=0.9)


def add_conflict_shading(ax):
    ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-17"),
               color=SHADING, alpha=0.06, zorder=0)
    mid = pd.Timestamp("2026-04-22")
    ylim = ax.get_ylim()
    ypos = ylim[0] + 0.92 * (ylim[1] - ylim[0])
    ax.text(mid, ypos, "Conflict Window", ha="center", fontsize=10,
            color="#999999", fontstyle="italic", alpha=0.7)


# ═════════════════════════════════════════════════════════════════════════════
# CHART 1 — Price timeline with event markers
# ═════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("CHART 1 — Price timeline")
print("=" * 60)

fig, ax1 = plt.subplots(figsize=(14, 7))
ax2 = ax1.twinx()

ax1.plot(prices.index, prices["Brent_Crude"], color=BRENT_COLOR,
         linewidth=2, label="Brent Crude (LHS)")
ax1.plot(prices.index, prices["WTI_Crude"], color=WTI_COLOR,
         linewidth=1.5, linestyle="--", label="WTI Crude (LHS)")
ax2.plot(prices.index, prices["Natural_Gas"], color=NATGAS_COLOR,
         linewidth=1.5, alpha=0.85, label="Natural Gas (RHS)")

ax1.set_ylabel("Price (USD / barrel)", fontsize=12)
ax2.set_ylabel("Price (USD / MMBtu)", fontsize=12)
ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

# Event lines + shading (draw on ax1 so they sit behind data)
for tag, (date_str, color, ls, _label) in EVENTS_INFO.items():
    dt = pd.Timestamp(date_str)
    ax1.axvline(dt, color=color, linestyle=ls, linewidth=1.2, zorder=3)
ax1.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-17"),
            color=SHADING, alpha=0.06, zorder=0)

# Annotations — place after setting data limits
ylim1 = ax1.get_ylim()
for tag, (date_str, color, ls, label) in EVENTS_INFO.items():
    dt = pd.Timestamp(date_str)
    ypos = ylim1[0] + 0.93 * (ylim1[1] - ylim1[0])
    ax1.text(dt, ypos, f" {tag}: {label}", rotation=90, va="top",
             ha="right", fontsize=9, color=color, alpha=0.9)

mid = pd.Timestamp("2026-04-22")
ypos_cw = ylim1[0] + 0.85 * (ylim1[1] - ylim1[0])
ax1.text(mid, ypos_cw, "Conflict Window", ha="center", fontsize=10,
         color="#999999", fontstyle="italic", alpha=0.7)

# Legend — combine both axes
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=10, framealpha=0.9)

fig.suptitle("Oil & Gas Prices — 2026 US–Iran Conflict",
             fontsize=16, fontweight="bold", y=0.97)
fig.text(0.5, 0.91,
         "Brent, WTI crude and Henry Hub Natural Gas spot prices, Jan–Jun 2026",
         ha="center", fontsize=11, color="#666666")

ax2.grid(False)

path1 = OUT_DIR / "price_timeline.png"
fig.savefig(path1, **SAVE_KW)
plt.close(fig)
print(f"Saved {path1.name}")


# ═════════════════════════════════════════════════════════════════════════════
# CHART 2 — Cumulative Abnormal Returns (3 subplots)
# ═════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("CHART 2 — Cumulative Abnormal Returns")
print("=" * 60)

PRIMARY = ["Brent_Crude", "WTI_Crude", "Natural_Gas"]
COLORS = {"Brent_Crude": BRENT_COLOR, "WTI_Crude": WTI_COLOR, "Natural_Gas": NATGAS_COLOR}
LABELS = {"Brent_Crude": "Brent Crude", "WTI_Crude": "WTI Crude", "Natural_Gas": "Natural Gas"}

baseline_ret = returns.loc[BASELINE_START:BASELINE_END, PRIMARY]
expected_returns = baseline_ret.mean().to_dict()


def get_event_window(returns_df, event_date_str, window=10):
    event_date = pd.Timestamp(event_date_str)
    available = returns_df.index
    if event_date not in available:
        future = available[available >= event_date]
        if len(future) == 0:
            raise ValueError(f"No trading days on or after {event_date_str}")
        event_date = future[0]
    loc = available.get_loc(event_date)
    start = max(loc - window, 0)
    end = min(loc + window + 1, len(available))
    return returns_df.iloc[start:end], event_date


chart2_events = [
    ("E1 — US Strikes Begin (Feb 28)", "2026-02-28"),
    ("E2 — US–Iran MoU Signed (Jun 17)", "2026-06-17"),
    ("E3 — Swiss Talks Postponed (Jun 18)", "2026-06-18"),
]

fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=False)
fig.subplots_adjust(wspace=0.3)

for idx, (title, event_date_str) in enumerate(chart2_events):
    ax = axes[idx]
    window_df, actual_date = get_event_window(returns, event_date_str, window=10)
    loc = window_df.index.get_loc(actual_date)

    for asset in PRIMARY:
        ar = window_df[asset].values - expected_returns[asset]
        car_raw = np.cumsum(ar)
        rel_days = np.arange(-loc, len(ar) - loc)
        # Normalise: zero at day -1
        car_at_m1 = car_raw[loc - 1] if loc >= 1 else 0.0
        car_norm = (car_raw - car_at_m1) * 100

        ax.plot(rel_days, car_norm, color=COLORS[asset], linewidth=1.8,
                label=LABELS[asset] if idx == 0 else None)

    ax.axvline(0, color="black", linewidth=1, linestyle="--", alpha=0.7)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xlabel("Trading days relative to event", fontsize=9)
    if idx == 0:
        ax.set_ylabel("Cumulative Abnormal Return (%)", fontsize=10)
    ax.tick_params(labelsize=9)

axes[0].legend(fontsize=9, loc="upper left", framealpha=0.9)

fig.suptitle("Cumulative Abnormal Returns Around Key Conflict Events",
             fontsize=14, fontweight="bold", y=1.02)

path2 = OUT_DIR / "abnormal_returns.png"
fig.savefig(path2, **SAVE_KW)
plt.close(fig)
print(f"Saved {path2.name}")


# ═════════════════════════════════════════════════════════════════════════════
# CHART 3 — Rolling Volatility
# ═════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("CHART 3 — Rolling Volatility")
print("=" * 60)

fig, ax = plt.subplots(figsize=(14, 6))

for asset, color, lbl in [
    ("Brent_Crude", BRENT_COLOR, "Brent Crude"),
    ("WTI_Crude",   WTI_COLOR,   "WTI Crude"),
    ("Natural_Gas", NATGAS_COLOR, "Natural Gas"),
]:
    ax.plot(volatility.index, volatility[asset], color=color, linewidth=1.8, label=lbl)

# Event lines + shading
for tag, (date_str, color, ls, _label) in EVENTS_INFO.items():
    ax.axvline(pd.Timestamp(date_str), color=color, linestyle=ls, linewidth=1.2, zorder=3)
ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-17"),
           color=SHADING, alpha=0.06, zorder=0)

# Pre-conflict average reference line
pre_brent_vol = volatility.loc[BASELINE_START:BASELINE_END, "Brent_Crude"].dropna().mean()
ax.axhline(pre_brent_vol, color="grey", linewidth=1, linestyle="--", alpha=0.7)
ax.text(volatility.index[-1], pre_brent_vol + 1.5,
        f"Pre-conflict avg: {pre_brent_vol:.0f}%",
        ha="right", fontsize=9, color="grey")

# Event annotations
ylim = ax.get_ylim()
for tag, (date_str, color, ls, label) in EVENTS_INFO.items():
    dt = pd.Timestamp(date_str)
    ypos = ylim[0] + 0.93 * (ylim[1] - ylim[0])
    ax.text(dt, ypos, f" {tag}: {label}", rotation=90, va="top",
            ha="right", fontsize=8, color=color, alpha=0.9)

mid = pd.Timestamp("2026-04-22")
ypos_cw = ylim[0] + 0.85 * (ylim[1] - ylim[0])
ax.text(mid, ypos_cw, "Conflict Window", ha="center", fontsize=10,
        color="#999999", fontstyle="italic", alpha=0.7)

ax.set_ylabel("Annualised Volatility (%)", fontsize=12)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
ax.legend(loc="upper left", fontsize=10, framealpha=0.9)

fig.suptitle("Realised Volatility (20-day Rolling, Annualised) — 2026 US–Iran Conflict",
             fontsize=14, fontweight="bold", y=0.97)
fig.text(0.5, 0.91, "Higher values = more uncertain markets",
         ha="center", fontsize=11, color="#666666")

path3 = OUT_DIR / "volatility_chart.png"
fig.savefig(path3, **SAVE_KW)
plt.close(fig)
print(f"Saved {path3.name}")


# ═════════════════════════════════════════════════════════════════════════════
# CHART 4 — Correlation heatmap (side-by-side)
# ═════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("CHART 4 — Correlation Heatmaps")
print("=" * 60)

ASSET_ORDER = [
    "Brent_Crude", "WTI_Crude", "Natural_Gas", "USD_Index",
    "ExxonMobil", "Halliburton", "United_Airlines", "Lockheed_Martin",
]

corr_pre_ord = corr_pre.loc[ASSET_ORDER, ASSET_ORDER]
corr_con_ord = corr_con.loc[ASSET_ORDER, ASSET_ORDER]

fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(16, 6))
fig.subplots_adjust(wspace=0.35)

hm_kw = dict(cmap="RdYlGn", vmin=-1, vmax=1, annot=True, fmt=".2f",
             square=True, linewidths=0.5, annot_kws={"size": 9},
             cbar=False)

sns.heatmap(corr_pre_ord, ax=ax_l, **hm_kw)
ax_l.set_title("Correlations — Pre-Conflict\n(Jan–Feb 2026)", fontsize=11, fontweight="bold")
ax_l.tick_params(labelsize=8)

sns.heatmap(corr_con_ord, ax=ax_r, **hm_kw)
ax_r.set_title("Correlations — Conflict Window\n(Mar–Jun 2026)", fontsize=11, fontweight="bold")
ax_r.tick_params(labelsize=8)

# Shared colour bar
sm = plt.cm.ScalarMappable(cmap="RdYlGn", norm=plt.Normalize(vmin=-1, vmax=1))
sm.set_array([])
cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
fig.colorbar(sm, cax=cbar_ax)

brent_air_pre = corr_pre.loc["Brent_Crude", "United_Airlines"]
brent_air_con = corr_con.loc["Brent_Crude", "United_Airlines"]

fig.suptitle("How Asset Correlations Shifted During the Iran Conflict",
             fontsize=14, fontweight="bold", y=1.02)
fig.text(0.5, -0.02,
         f"Note: Brent–Airlines correlation shifted from {brent_air_pre:+.2f} to "
         f"{brent_air_con:+.2f}, confirming oil-price headwind for aviation sector.",
         ha="center", fontsize=10, color="#555555", fontstyle="italic")

path4 = OUT_DIR / "correlation_heatmap.png"
fig.savefig(path4, **SAVE_KW)
plt.close(fig)
print(f"Saved {path4.name}")


# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("ALL CHARTS COMPLETE")
print("=" * 60)

for p in [path1, path2, path3, path4]:
    size_kb = p.stat().st_size / 1024
    from PIL import Image
    img = Image.open(p)
    print(f"  {p.name:<30s}  {size_kb:>7.1f} KB   {img.size[0]}x{img.size[1]} px   "
          f"DPI hint: {img.info.get('dpi', 'n/a')}")
    img.close()
