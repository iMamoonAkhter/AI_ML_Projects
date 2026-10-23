# Findings — Global Fuel Price Prediction & Early Warning System (EWS)

**Dataset:** weekly fuel prices, 84 countries × 327 weeks (2020-01-06 → 2026-04-06).
**Targets:** `petrol_usd_liter`, `diesel_usd_liter`, `lpg_usd_liter`.
**Split:** chronological — train < 2025-04-01 (23,016 rows), test ≥ 2025-04-07 (4,452 rows).
**Reproducibility:** the notebook now runs top-to-bottom from a clean kernel with no
undefined variables; all imputation, label encoding and scaling are fit on training rows
only; `random_state=42` throughout.

---

## 1. The headline R² ≈ 0.999 is an autocorrelation artifact

Weekly price *levels* are ~99.95% autocorrelated, so "this week ≈ last week" already
explains almost all variance. A **naive persistence baseline** (`price[t] = price[t-1]`,
per country), scored on the same test split, achieves:

| Fuel | Persistence R² | Persistence RMSE |
|------|---------------:|-----------------:|
| diesel | 0.9991 | 0.0464 |
| petrol | 0.9991 | 0.0482 |
| lpg    | 0.9988 | 0.0423 |

Against this honest yardstick (skill = 1 − RMSE_model / RMSE_persistence):

| Fuel | Best model | RMSE | Skill | Beats persistence? |
|------|-----------|-----:|------:|:-----------------:|
| diesel | XGBoost | 0.0411 | +0.114 | yes (marginal) |
| petrol | XGBoost | 0.0411 | +0.149 | yes (marginal) |
| lpg    | XGBoost | 0.0352 | +0.167 | yes (marginal) |

**Only XGBoost beats persistence, and only by 11–17% RMSE.** Linear Regression, KNN and
Random Forest all post **negative** skill (−1.4 to −3.5) — they are *worse* than doing
nothing on every fuel. The impressive-looking R² of the level models is therefore mostly
an illusion created by autocorrelation, not genuine forecasting ability.

## 2. Forecasting the *change* is near the edge of predictability

When we instead predict the next-week **change** `Δ = price[t+h] − price[t]` (forward
shift per country; train/test split on the *target* date to prevent look-ahead) and score
skill against a **zero-change** baseline, the value of ML largely evaporates:

- Regression skill scores cluster around **zero** (≈ −0.18 to +0.09) across fuels and
  horizons h = 1, 4, 12 weeks. No model wins consistently. Linear gives small positive
  skill at h=1 (+0.03 to +0.09); tree models mostly lose at h=1–4.
- **Direction** (up/down) classification is barely above a majority-class guess; the best
  cases are diesel h=4 (skill +0.075) and lpg h=12 (skill +0.090), most others ≈ 0.

This is the central, defensible result: once the autocorrelation crutch is removed, weekly
fuel-price *movements* are close to unpredictable from these features.

## 3. The EWS clustering was degenerate; scaling + K-justification fixes it

The original K-Means ran on **unscaled** features, collapsing 96.6% of weeks into one
cluster (26536 / 698 / 175 / 59). After standardizing the clustering features
(`cross_ratio_lag1`, `brent_momentum_lag1`, scaler fit on train only) the clusters become
non-degenerate:

| Alert level | Regime (derived from centroid) | Brent momentum | diesel/petrol ratio | n rows |
|---|---|---:|---:|---:|
| 0 | Normal | −0.149 | 0.93 | 668 |
| 1 | Local Peak | −0.006 | 0.92 | 19,150 |
| 2 | Global Inflation | +0.010 | **3.23** | 127 |
| 3 | Severe Crisis | +0.062 | 0.93 | 7,523 |

- **K is justified, not assumed.** A K = 2..8 sweep shows the global silhouette maximum at
  K=2 (0.90) is **degenerate** — it merely isolates ~130 petrol-subsidy rows
  (Venezuela/Iran/Libya, petrol ≈ $0.01/L → diesel/petrol ratio 3–7×). Excluding
  degenerate solutions, silhouette is flat (~0.48–0.52), so **K=4** is chosen for an
  interpretable alert ladder.
- **Labels are derived from centroids** (ordered by Brent momentum), not assumed, and the
  centroid table is printed for audit.
- **Caveat:** the 127-row level-2 pocket is a *structural subsidy* artifact, not a market
  regime; it is labeled "Global Inflation" only because the diesel/petrol ratio is extreme.
  A cleaner design would label it "Structural/Subsidized" or drop the ratio feature.

## 4. As an alarm, the EWS gives lead time but poor precision

Defining a **price-shock event** objectively (|weekly petrol change| > 2× trailing-26-week
σ, past data only) and treating EWS level 3 as an active alert, credited if a shock follows
within 8 weeks:

| Metric | Value |
|---|---:|
| Total shocks | 1,816 |
| Total alert onsets | 2,032 |
| Precision (alert → shock) | 0.359 |
| Recall (shock with prior alert) | 0.600 |
| False-alarm rate | 0.641 |
| Avg / median lead time | 4.15 / 4.0 weeks |
| Random-alarm precision (8w) | 0.421 |
| Precision lift vs random | **0.85×** |

The EWS catches **60% of shocks with ~4 weeks of lead time**, which is operationally
attractive. **However its precision (0.36) is *below* a random alarm of the same firing
rate (0.42), and 64% of alerts are false.** The alert fires almost as often as shocks
occur (2,032 vs 1,816), so its recall comes largely from being "on" much of the time rather
than from genuine discrimination. Example country timelines (Greece, New Zealand, United
Kingdom, Nepal) in the notebook visualize this: shocks do cluster in alert bands, but many
shocks fall outside alerts and many alert bands contain no shock.

---

## Limitations & recommended framing for the thesis

1. **Report skill, not raw R².** On autocorrelated price levels, R² ≈ 0.999 is the
   baseline, not an achievement. Every model should be reported relative to persistence.
2. **The genuine forecasting task (the change) is hard.** ML adds little consistent value
   for weekly fuel-price movements with these features; this is a finding, not a failure.
3. **The EWS is an early-warning *indicator*, not a precise alarm.** It buys lead time and
   recall at the cost of many false positives; a precision-tuned threshold or richer
   features would be needed for operational use.
4. **Subsidy structure is a confounder.** The diesel/petrol ratio mostly encodes static
   subsidy regimes (a handful of countries), not market dynamics, and should be treated as
   a control rather than a stress signal.

*All numbers above were produced by a clean "Restart & Run All" of `ML EWS.ipynb`
(scikit-learn 1.9, xgboost 3.2, pandas 3.0). Figures are embedded in the notebook;
`phaseE_timelines.png` holds the example alarm timelines.*
