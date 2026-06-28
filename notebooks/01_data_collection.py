import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import numpy as np
from fredapi import Fred

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT.parent / ".env"
load_dotenv(ENV_PATH)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROC_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)


START = "2025-12-01"
END = "2026-06-20"

TICKERS = {
    "BZ=F":     "Brent_Crude",
    "CL=F":     "WTI_Crude",
    "NG=F":     "Natural_Gas",
    "DX-Y.NYB": "USD_Index",
    "XOM":      "ExxonMobil",
    "HAL":      "Halliburton",
    "UAL":      "United_Airlines",
    "LMT":      "Lockheed_Martin",
    "RTX":      "Raytheon",
    "FDX":      "FedEx",
}

print("=" * 70)
print("PART A — Downloading yfinance price data")
print("=" * 70)

raw = yf.download(list(TICKERS.keys()), start=START, end=END, group_by="ticker", auto_adjust=True)

frames = []
for yf_ticker, friendly in TICKERS.items():
    try:
        col = raw[yf_ticker]["Close"]
        col = col.rename(friendly)
        frames.append(col)
    except KeyError:
        print(f"  WARNING: {yf_ticker} ({friendly}) — no data returned")

prices = pd.concat(frames, axis=1)
prices.index.name = "Date"

prices_raw = prices.copy()
prices_raw.to_csv(RAW_DIR / "prices_raw.csv")
print(f"\nSaved prices_raw.csv  → {prices_raw.shape[0]} rows × {prices_raw.shape[1]} cols")
print(f"  Date range: {prices_raw.index.min().date()} to {prices_raw.index.max().date()}")

prices = prices.loc["2026-01-02":]
prices = prices.ffill(limit=2)
prices = prices.dropna(how="all")

prices.to_csv(PROC_DIR / "prices.csv")
print(f"\nSaved prices.csv      → {prices.shape[0]} rows × {prices.shape[1]} cols")
print(f"  Date range: {prices.index.min().date()} to {prices.index.max().date()}")
print(f"  NaN count per column:")
for col in prices.columns:
    n = prices[col].isna().sum()
    print(f"    {col:20s} {n:>4d}")



print("\n" + "=" * 70)
print("PART B — Downloading FRED macro data")
print("=" * 70)

FRED_KEY = os.getenv("FRED_API_KEY")
if not FRED_KEY:
    print("ERROR: FRED_API_KEY not found in .env — skipping Part B")
    sys.exit(1)

fred = Fred(api_key=FRED_KEY)

FRED_SERIES = {
    "DCOILWTICO":  "WTI_Spot",
    "DCOILBRENTEU": "Brent_Spot",
    "GASREGCOVW":  "US_Gas_Retail",
    "CPIAUCSL":    "CPI",
}

FRED_START = "2026-01-01"
FRED_END = "2026-06-20"

macro_frames = []
for series_id, friendly in FRED_SERIES.items():
    try:
        s = fred.get_series(series_id, observation_start=FRED_START, observation_end=FRED_END)
        s.name = friendly
        macro_frames.append(s)
        print(f"  {series_id:16s} → {friendly:16s}  {len(s)} observations")
    except Exception as e:
        print(f"  WARNING: {series_id} failed — {e}")

macro = pd.concat(macro_frames, axis=1)
macro.index.name = "Date"

macro_raw = macro.copy()
macro_raw.to_csv(RAW_DIR / "macro_raw.csv")
print(f"\nSaved macro_raw.csv   → {macro_raw.shape[0]} rows × {macro_raw.shape[1]} cols")

macro = macro.ffill()
macro.to_csv(PROC_DIR / "macro.csv")
print(f"Saved macro.csv       → {macro.shape[0]} rows × {macro.shape[1]} cols")
print(f"  Date range: {macro.index.min().date()} to {macro.index.max().date()}")



print("\n" + "=" * 70)
print("PART C — Data Quality Report")
print("=" * 70)

print(f"\n{'prices.csv':=^60}")
print(f"  Shape: {prices.shape}")
print(f"  Date range: {prices.index.min().date()} → {prices.index.max().date()}")
print(f"\n  {'Column':<20s} {'Missing%':>8s}  {'Min':>10s}  {'Max':>10s}")
print(f"  {'-'*20} {'-'*8}  {'-'*10}  {'-'*10}")
for col in prices.columns:
    pct = 100 * prices[col].isna().sum() / len(prices)
    lo = prices[col].min()
    hi = prices[col].max()
    print(f"  {col:<20s} {pct:>7.1f}%  {lo:>10.2f}  {hi:>10.2f}")

print(f"\n{'macro.csv':=^60}")
print(f"  Shape: {macro.shape}")
print(f"  Date range: {macro.index.min().date()} → {macro.index.max().date()}")
print(f"\n  {'Column':<20s} {'Missing%':>8s}")
print(f"  {'-'*20} {'-'*8}")
for col in macro.columns:
    pct = 100 * macro[col].isna().sum() / len(macro)
    print(f"  {col:<20s} {pct:>7.1f}%")

brent_ok = "Brent_Crude" in prices.columns and prices["Brent_Crude"].first_valid_index().date() <= pd.Timestamp("2026-01-03").date()
wti_ok = "WTI_Crude" in prices.columns and prices["WTI_Crude"].first_valid_index().date() <= pd.Timestamp("2026-01-03").date()
print(f"\n  Brent_Crude data from 2026-01-02: {'✓' if brent_ok else '✗'}")
print(f"  WTI_Crude   data from 2026-01-02: {'✓' if wti_ok else '✗'}")
print("\nDone.")
