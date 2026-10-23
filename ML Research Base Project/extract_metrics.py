import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import silhouette_score, adjusted_rand_score, davies_bouldin_score
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Load
df = pd.read_csv('global_fuel_prices_2020_2026.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['country','date']).reset_index(drop=True)
df_dates = pd.DataFrame({'date': df['date']})

# Split
SPLIT_DATE = '2025-04-01'
train_mask = (df_dates['date'] < SPLIT_DATE).to_numpy()
test_mask = ~train_mask

# Clustering features
cluster_feats = ['cross_ratio_lag1','brent_momentum_lag1']
# compute base features
df['cross_ratio'] = df['diesel_usd_liter'] / df['petrol_usd_liter']
df['brent_momentum'] = df.groupby('country')['brent_crude_usd'].pct_change(periods=4)
# lags
df['cross_ratio_lag1'] = df.groupby('country')['cross_ratio'].shift(1)
df['brent_momentum_lag1'] = df.groupby('country')['brent_momentum'].shift(1)
# drop contemporaries
#df = df.drop(columns=['cross_ratio','brent_momentum'])

# median imputation fit on TRAIN rows only
cluster_medians = df.loc[train_mask, cluster_feats].median()
cluster_data = df[cluster_feats].fillna(cluster_medians)

# StandardScaler config first (to derive ews shocks as notebook did)
scaler = StandardScaler().fit(cluster_data[train_mask])
cluster_scaled = scaler.transform(cluster_data)
cluster_scaled_train = cluster_scaled[train_mask]

# choose K=4 per notebook
CHOSEN_K = 4
km = KMeans(n_clusters=CHOSEN_K, random_state=42, n_init=10).fit(cluster_scaled_train)
raw_cluster = km.predict(cluster_scaled)
# centroids original units
centroids_orig = scaler.inverse_transform(km.cluster_centers_)
cent_df = pd.DataFrame(centroids_orig, columns=cluster_feats)
cent_df['n_rows'] = pd.Series(raw_cluster).value_counts().sort_index().values
# derive ordering
ratio_norm = cluster_data.loc[train_mask, 'cross_ratio_lag1'].median()
cent_df['ratio_extremity'] = (cent_df['cross_ratio_lag1'] - ratio_norm).abs()
order = (cent_df.sort_values(['brent_momentum_lag1','ratio_extremity']).index.tolist())
cluster_to_level = {raw_id: lvl for lvl, raw_id in enumerate(order)}

df['EWS_Alert_Level'] = pd.Series(raw_cluster, index=df.index).map(cluster_to_level)

# Phase E shocks (used as reference in cluster_cmp)
ews = pd.DataFrame({'country': df['country'].to_numpy(), 'date': df_dates['date'].to_numpy(), 'petrol': df['petrol_usd_liter'].to_numpy(), 'alert_level': df['EWS_Alert_Level'].to_numpy()})

g = ews.groupby('country')
ews['chg'] = g['petrol'].diff()
ews['sigma'] = g['chg'].transform(lambda s: s.shift(1).rolling(26, min_periods=8).std())
ews['shock'] = (ews['chg'].abs() > 2.0 * ews['sigma']) & ews['sigma'].notna()
ews['alert'] = ews['alert_level'].isin({3})

# Now cluster_cmp across configs
cd = cluster_data
X_raw = cd.to_numpy()
X_std = cluster_scaled
X_min = MinMaxScaler().fit(cd[train_mask]).transform(cd)

def log2(cd_df):
    a = cd_df.copy()
    a['cross_ratio_lag1'] = np.log1p(a['cross_ratio_lag1'].clip(lower=0))
    a['brent_momentum_lag1'] = np.sign(a['brent_momentum_lag1']) * np.log1p(np.abs(a['brent_momentum_lag1']))
    return a.to_numpy()

config_feats = {
    'Raw (no scaling)': X_raw,
    'StandardScaler (Z-Score)': X_std,
    'MinMax': X_min,
    'Log (safe)': log2(cd),
}

# references
valid_lag = df[cluster_feats].notna().all(axis=1).to_numpy()
key = pd.DataFrame({'country': df['country'].to_numpy(), 'date': df_dates['date'].to_numpy()})
shock_aligned = key.merge(ews[['country','date','shock']], on=['country','date'], how='left')['shock'].fillna(False).astype(int).to_numpy()
refs = {
    'subsidy': LabelEncoder().fit_transform(df['subsidy_level'].astype(str)),
    'income': LabelEncoder().fit_transform(df['income_level'].astype(str)),
    'region': LabelEncoder().fit_transform(df['region'].astype(str)),
    'shocks': shock_aligned,
}

from sklearn.metrics import davies_bouldin_score
rows = []
raw_km = KMeans(n_clusters=CHOSEN_K, random_state=42, n_init=10).fit(config_feats['Raw (no scaling)'][train_mask])
raw_labels_all = raw_km.predict(config_feats['Raw (no scaling)'])

for name, feats in config_feats.items():
    km2 = KMeans(n_clusters=CHOSEN_K, random_state=42, n_init=10).fit(feats[train_mask])
    labels_all = km2.predict(feats)
    tr_n = int(train_mask.sum())
    rng = np.random.RandomState(42)
    sidx = rng.choice(tr_n, size=min(5000,tr_n), replace=False)
    sil = silhouette_score(feats[train_mask][sidx], km2.predict(feats[train_mask])[sidx])
    dbi = davies_bouldin_score(feats[train_mask], km2.labels_)
    ari = {k: adjusted_rand_score(refs[k][valid_lag], labels_all[valid_lag]) for k in refs}
    ari_raw = adjusted_rand_score(raw_labels_all[valid_lag], labels_all[valid_lag])
    # stability
    labs = [KMeans(n_clusters=CHOSEN_K, random_state=s, n_init=10).fit(feats[train_mask]).predict(feats)[valid_lag] for s in range(10)]
    pair = [adjusted_rand_score(labs[i], labs[j]) for i in range(len(labs)) for j in range(i+1, len(labs))]
    rows.append((name, sil, dbi, ari['subsidy'], ari['income'], ari['region'], ari['shocks'], ari_raw, float(np.mean(pair))))

print('\nPer-configuration clustering metrics (rounded 4dp):')
print('Config | Silhouette | DaviesBouldin | ARI_subsidy | ARI_income | ARI_region | ARI_shocks | Stability_ARI')
for r in rows:
    print(f"{r[0]} | {r[1]:.4f} | {r[2]:.4f} | {r[3]:.4f} | {r[4]:.4f} | {r[5]:.4f} | {r[6]:.4f} | {r[8]:.4f}")

# Specifically print StandardScaler row
for r in rows:
    if r[0]=='StandardScaler (Z-Score)':
        std_row = r
        break
print('\nStandardScaler (Z-Score) metrics:')
print(f"Silhouette = {std_row[1]:.4f}")
print(f"ARI_subsidy = {std_row[3]:.4f}")
print(f"ARI_income = {std_row[4]:.4f}")
print(f"ARI_region = {std_row[5]:.4f}")
print(f"ARI_shocks = {std_row[6]:.4f}")
print(f"Stability_ARI = {std_row[8]:.4f}")

# Supervised models: evaluate per notebook
fuel_targets = ['diesel_usd_liter','petrol_usd_liter','lpg_usd_liter']
df_sup = df.copy()
if 'date' in df_sup.columns:
    df_sup = df_sup.drop(columns=['date'])
# add temporal from df_dates
df_sup['month'] = df_dates['date'].dt.month
df_sup['year'] = df_dates['date'].dt.year
df_sup['week_of_year'] = df_dates['date'].dt.isocalendar().week.astype(int)
# encode categorical minimally
for col in ['season','region','region_group','income_level','subsidy_level']:
    if col in df_sup.columns:
        df_sup[col] = LabelEncoder().fit_transform(df_sup[col].astype(str))
# one-hot country
df_sup = pd.get_dummies(df_sup, columns=['country'], prefix='country')

results = []
for fuel in fuel_targets:
    if fuel not in df_sup.columns:
        continue
    y = df_sup[fuel]
    ytr = y[train_mask]
    yte = y[test_mask]
    X_fuel = df_sup.drop(columns=fuel_targets, errors='ignore')
    # impute numeric columns using medians computed on TRAIN rows only (leak-safe)
    num_cols = X_fuel.select_dtypes(include=[np.number]).columns.tolist()
    medians = X_fuel.loc[train_mask, num_cols].median()
    X_fuel[num_cols] = X_fuel[num_cols].fillna(medians)
    Xtr = X_fuel[train_mask]
    Xte = X_fuel[test_mask]
    # scaling for LR and KNN
    sc = StandardScaler().fit(Xtr.astype(float))
    Xtr_s = sc.transform(Xtr.astype(float))
    Xte_s = sc.transform(Xte.astype(float))
    # Linear
    lr = LinearRegression().fit(Xtr_s, ytr)
    pred_lr = lr.predict(Xte_s)
    r2_lr = r2_score(yte, pred_lr); mae_lr = mean_absolute_error(yte, pred_lr); rmse_lr = np.sqrt(mean_squared_error(yte, pred_lr))
    results.append((fuel,'Linear Regression', r2_lr, mae_lr, rmse_lr))
    # KNN
    knn = KNeighborsRegressor(n_neighbors=5).fit(Xtr_s, ytr)
    pred_knn = knn.predict(Xte_s)
    r2_knn = r2_score(yte, pred_knn); mae_knn = mean_absolute_error(yte, pred_knn); rmse_knn = np.sqrt(mean_squared_error(yte, pred_knn))
    results.append((fuel,'KNN', r2_knn, mae_knn, rmse_knn))
    # Random Forest (raw features)
    rf = RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42).fit(Xtr, ytr)
    pred_rf = rf.predict(Xte)
    r2_rf = r2_score(yte, pred_rf); mae_rf = mean_absolute_error(yte, pred_rf); rmse_rf = np.sqrt(mean_squared_error(yte, pred_rf))
    results.append((fuel,'Random Forest', r2_rf, mae_rf, rmse_rf))
    # XGBoost (raw)
    xgb = XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.1, random_state=42, verbosity=0).fit(Xtr, ytr)
    pred_xgb = xgb.predict(Xte)
    r2_xgb = r2_score(yte, pred_xgb); mae_xgb = mean_absolute_error(yte, pred_xgb); rmse_xgb = np.sqrt(mean_squared_error(yte, pred_xgb))
    results.append((fuel,'XGBoost', r2_xgb, mae_xgb, rmse_xgb))

print('\nSupervised model results (Test set):')
print('Fuel | Model | R2 | MAE | RMSE')
for r in results:
    print(f"{r[0]} | {r[1]} | {r[2]:.4f} | {r[3]:.4f} | {r[4]:.4f}")

# Persistence baseline
print('\nPersistence baseline (per notebook):')
for fuel in fuel_targets:
    prev = df.groupby('country')[fuel].shift(1)
    y_true = df.loc[test_mask, fuel].to_numpy()
    y_pred = prev[test_mask].to_numpy()
    valid = ~np.isnan(y_pred)
    y_true, y_pred = y_true[valid], y_pred[valid]
    r2 = r2_score(y_true, y_pred); mae = mean_absolute_error(y_true, y_pred); rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"{fuel} persistence -> R2: {r2:.4f} | MAE: {mae:.4f} | RMSE: {rmse:.4f}")

print('\nDone')
