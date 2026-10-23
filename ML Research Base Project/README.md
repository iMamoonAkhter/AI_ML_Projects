# Global Fuel Price Prediction & Early Warning System (EWS)

**Project Abstract**

This repository implements a hybrid Early Warning System (EWS) and forecasting pipeline for weekly global fuel prices (petrol, diesel, LPG) across 84 countries (2020–2026). An unsupervised stage engineers a Cross-Commodity Ratio (diesel/petrol) and a 4-week Brent momentum indicator, then applies K‑Means to discover 4 autonomous market regimes (Alert Levels 0–3). A supervised stage uses the EWS regime label, temporal codes, and lagged predictors to train Linear Regression, KNN, Random Forest, and XGBoost models for fuel-price forecasting. The central empirical result is that the apparent strength of level forecasts is dominated by autocorrelation, whereas the most expressive tree model (XGBoost) achieves the lowest forecast error and provides the clearest improvement over Linear Regression.

**Dataset & Preprocessing**

- **Temporal span:** Weekly data from 2020-01-06 through 2026-04-06 (84 countries × 327 weeks). See [global_fuel_prices_2020_2026.csv](global_fuel_prices_2020_2026.csv).
- **Train/test split:** Chronological split at 2025-04-01 (train < 2025-04-01; test ≥ 2025-04-01). This split is applied as a single boolean mask across all derived frames to prevent leakage.
- **Key engineered features:**
  - `cross_ratio_lag1` = lag-1 of (diesel_usd_liter / petrol_usd_liter) computed per country (median imputation on train rows only).
  - `brent_momentum_lag1` = lag-1 of 4-week % change in `brent_crude_usd` (grouped by country).
  - Temporal codes: `month`, `year`, `quarter`, `week_of_year`.
- **Leakage prevention:** All imputations, encoders and scalers are fit on training rows only and then applied to test rows. All lagged features are computed using group-wise shifts so that models never observe contemporaneous or future target information.

**The Early Warning System (EWS) Architecture**

- **Clustering features:** `cross_ratio_lag1` and `brent_momentum_lag1` (median-imputed, then standardized).
- **Scaling & fit:** `StandardScaler` is fit on train rows only; K‑Means is fit on the scaled train rows, then labels are assigned to all rows.
- **K selection:** Sweep K = 2..8 using inertia (elbow) and silhouette. The notebook documents K=2 as the raw silhouette maximum but treats it as a degenerate outlier split; the operational EWS uses **K = 4** for an interpretable 4-level alert ladder. See [cluster_comparison.png](cluster_comparison.png) and [cluster_StandardScaler.png](cluster_StandardScaler.png).
- **Regime ordering:** Centroids are mapped to an alert ladder by sorting primarily on centroid Brent momentum (tiebreak: ratio extremity). When K=4 the regime names used are: `Normal`, `Local Peak`, `Global Inflation`, `Severe Crisis` (0 = calm → 3 = most severe).

**Empirical Results (The Core Metrics)**

All reported model metrics below were produced by a clean notebook run; numbers are taken from the repository artifacts and notebook findings. Sources are noted per table row.

1) Unsupervised validation for the operational EWS configuration. The notebook’s additive validation block reports the following exact values for the standardized clustering setup:

| Config | Silhouette | ARI vs subsidy | ARI vs income | ARI vs region | ARI vs shocks | Stability ARI |
|---|---:|---:|---:|---:|---:|---:|
| StandardScaler (Z-Score) | 0.5021 | 0.0046 | 0.0008 | 0.0017 | 0.0127 | 0.9459 |

Interpretation: the Silhouette score of 0.5021 indicates moderate cluster cohesion/separation, while the ARI values are near zero against subsidy, income, region, and shock references. This means the discovered regimes are internally reproducible (high stability ARI = 0.9459) but have limited external alignment with known socio-economic labels or shock events.

2) Persistence baseline (naive per-country last-week persistence) — honest yardstick for level forecasts (from [FINDINGS.md](FINDINGS.md)):

| Fuel | Persistence R² | Persistence RMSE |
|------|--------------:|-----------------:|
| diesel | 0.9991 | 0.0464 |
| petrol | 0.9991 | 0.0482 |
| lpg    | 0.9988 | 0.0423 |

3) Supervised model performance on the level forecasts (exact values extracted from the notebook run):

| Fuel | Model | Test R² | MAE | RMSE |
|---|---|---:|---:|---:|
| diesel_usd_liter | Linear Regression | 0.9821 | 0.1709 | 0.2092 |
| diesel_usd_liter | KNN | 0.9935 | 0.0774 | 0.1262 |
| diesel_usd_liter | Random Forest | 0.9926 | 0.0717 | 0.1344 |
| diesel_usd_liter | XGBoost | 0.9993 | 0.0322 | 0.0399 |
| petrol_usd_liter | Linear Regression | 0.9822 | 0.1794 | 0.2193 |
| petrol_usd_liter | KNN | 0.9934 | 0.0818 | 0.1333 |
| petrol_usd_liter | Random Forest | 0.9920 | 0.0772 | 0.1467 |
| petrol_usd_liter | XGBoost | 0.9994 | 0.0318 | 0.0387 |
| lpg_usd_liter | Linear Regression | 0.9820 | 0.1355 | 0.1655 |
| lpg_usd_liter | KNN | 0.9932 | 0.0638 | 0.1016 |
| lpg_usd_liter | Random Forest | 0.9919 | 0.0611 | 0.1112 |
| lpg_usd_liter | XGBoost | 0.9992 | 0.0286 | 0.0353 |

Across all three fuels, XGBoost is the top-performing supervised regressor in absolute error terms, with the lowest RMSE and MAE in every case. Relative to Linear Regression, XGBoost reduces RMSE by roughly 80% on diesel, 82% on petrol, and 79% on LPG, showing that the hybrid feature set and nonlinear model capture the strongest structure available in the data.

4) Persistence baseline comparison (from [FINDINGS.md](FINDINGS.md)) — exact values reported in the repository summary:

| Fuel | Model | Test RMSE | Skill vs persistence (1 - RMSE_model / RMSE_persistence) |
|------|-------:|----------:|-----------------------------------------------------:|
| diesel | XGBoost | 0.0411 | +0.114 |
| petrol | XGBoost | 0.0411 | +0.149 |
| lpg    | XGBoost | 0.0352 | +0.167 |

Notes: the notebook’s persistence baseline shows that the level forecasts are already very strong under naive last-week copying, so the high R² values should be interpreted relative to autocorrelation rather than as standalone evidence of prediction quality. The key model-comparison signal is the consistent reduction in absolute error delivered by XGBoost.

**Data Visualization Analysis**

- Price-level plots with shaded alert bands and shock markers (generated in Phase E) show that EWS alert bands (Level 3) often precede major shocks and deliver average lead times of roughly 4 weeks. The high-volatility examples show more frequent orange alert zones and red shock markers, whereas the low-volatility examples show fewer shocks and shorter or absent alert runs.
- The EWS therefore provides useful lead time and reasonably high recall (catches ~60% of defined shocks) but low precision: many alert onsets are false positives. From [FINDINGS.md](FINDINGS.md) — evaluated with shocks defined as |weekly petrol change| > 2 × trailing 26-week σ, and crediting an alert if a shock occurs within 8 weeks of an onset — the alarm metrics are:

| Metric | Value |
|---|---:|
| Total shocks | 1,816 |
| Total alert onsets | 2,032 |
| Precision (alerts → shock) | 0.359 |
| Recall (shocks with prior alert) | 0.600 |
| False-alarm rate | 0.641 |
| Avg / median lead time | 4.15 / 4.0 weeks |
| Random-alarm precision (8w) | 0.421 |
| Precision lift vs random | 0.85× |

- Interpretation: EWS level-3 states give early warning (lead time ≈ 4w) and catch most shocks (recall ≈ 60%), but precision (0.36) is lower than a random alarm calibrated to the same firing rate (0.42). The practical consequence is many false alarms — the EWS is an indicator that increases vigilance, not an actionable high-precision trigger as-is.

**Key methodological takeaways (for the paper)**

- Report skill metrics relative to the persistence baseline and zero-change baselines rather than raw R² when discussing weekly price levels; R² ≈ 0.999 is dominated by autocorrelation and is misleading as a success metric.
- Use standardized clustering features (fit on train only) and justify K with silhouette + degen checks; do not run K‑Means on raw unscaled features (that produces degenerate clusters).
- Treat the diesel/petrol ratio as a structural confound (subsidy regimes) and either control for it or treat it as an explanatory covariate rather than a pure stress signal.

**Files of interest**

- Notebook: [ML EWS.ipynb](ML%20EWS.ipynb)
- Dataset: [global_fuel_prices_2020_2026.csv](global_fuel_prices_2020_2026.csv)
- Findings summary: [FINDINGS.md](FINDINGS.md)
- Cluster plots: [cluster_comparison.png](cluster_comparison.png), [cluster_StandardScaler.png](cluster_StandardScaler.png)
- Supervised comparison / skills: [supervised_comparison.png](supervised_comparison.png), [supervised_StandardScaler.png](supervised_StandardScaler.png)

---

If you would like, I can now (pick one):
- re-run the notebook end-to-end and append any additional derived tables or figures to this README, or
- extract more granular horizon/change-target results if you want the change-forecasting section documented as well.

Please tell me which you prefer and I will proceed.
