# Turbofan Engine Predictive Maintenance (NASA CMAPSS)

Predicting Remaining Useful Life (RUL) of turbofan jet engines using sensor time-series data and gradient boosting, to enable condition-based maintenance instead of fixed-schedule maintenance.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![LightGBM](https://img.shields.io/badge/Model-LightGBM-green)
![Status](https://img.shields.io/badge/Status-In%20Progress-yellow)

---

## 🎯 Objective

Predict how many operational cycles remain before a turbofan engine fails, using multivariate sensor readings (temperature, pressure, rotational speed, etc.). This kind of model allows maintenance teams to move from **time-based maintenance** (fixed schedules, regardless of actual engine condition) to **condition-based maintenance** (servicing equipment only when sensor data indicates it's actually needed).

## ❓ Problem Statement

In industries like aviation and manufacturing, heavy machinery is typically maintained on a fixed schedule. This leads to two costly failure modes:

- **Unnecessary maintenance** — servicing equipment that is still healthy, wasting time and cost.
- **Unexpected failure** — equipment failing before its scheduled maintenance, causing downtime, safety risk, and lost production.

The NASA CMAPSS (Commercial Modular Aero-Propulsion System Simulation) dataset simulates multiple turbofan engines, each run-to-failure under different operating conditions, with 21 sensor channels recorded per cycle. The goal is to learn degradation patterns from this sensor data and predict, at any given cycle, how many cycles of useful life remain (RUL).

## 🧩 Approach

### 1. RUL Labeling
For each engine in the training set, the maximum cycle it reached (failure point) is identified. RUL for every row is then computed as:

```
RUL = max_cycle_of_engine − current_cycle
```

### 2. Exploratory Data Analysis
Sensor readings were plotted per engine against cycle number to visually identify which sensors show a clear degradation trend versus which remain flat throughout the engine's life.

### 3. Feature Selection — Removing Flat Sensors
Several sensors (e.g. `setting3`, `P2`, `T2`, `Nf_dmd`) showed near-zero variance across the entire dataset — meaning they carry no useful signal for the model — and were dropped.

### 4. Feature Engineering
Raw sensor values alone were noisy and insufficient. Two engineered feature sets were added per sensor, computed within each engine (`groupby('unit_nr')`):

- **Rolling mean (window = 5 cycles):** smooths out noise and reveals the underlying degradation trend.
- **Rate of change (cycle-to-cycle diff):** captures how quickly a sensor is drifting, i.e. the *speed* of degradation.

### 5. Engine-wise Train/Validation Split
Rather than a random row-level split (which would cause data leakage, since the model could see other cycles of the same engine at train time), the split was done at the **engine level** — 80% of engines for training, 20% held out for validation. This ensures the model is evaluated on engines it has genuinely never seen.

### 6. RUL Capping (Key Modeling Decision)
Early in an engine's life (high RUL, e.g. 200–350 cycles remaining), sensor readings look essentially healthy and carry no meaningful degradation signal — yet the model was still being asked to predict exact large RUL values from this flat data. This confused the model and inflated error significantly.

**Fix:** RUL values were capped at 125. Any true RUL above 125 is treated as 125 during training. This lets the model focus its capacity on the region where sensors actually carry predictive signal — the near-failure zone — which is also the region that matters most for real maintenance decisions.

**Impact of capping:**

| Setup | MAE | RMSE |
|---|---|---|
| Without capping | 32.53 | 44.91 |
| With capping (125) | **13.99** | **20.22** |

~60% reduction in error from this single change.

### 7. Model
A **LightGBM Regressor** was trained on the engineered feature set (raw sensors + rolling means + rate-of-change features) to predict capped RUL.

### 8. Feature Importance
Feature importance analysis showed that rolling-mean features dominate the top predictors — particularly corrected/physical core speed (`NRc`, `Nc`), bypass ratio (`BPR`), and key temperature/pressure sensors (`T24`, `T30`, `T50`, `Ps30`). This aligns with the underlying physics of turbofan degradation, where rotational speeds and internal pressures are among the first parameters to drift as an engine wears.

### 9. Final Evaluation on Held-Out Test Set
The official CMAPSS test split (`test_FD001.csv` + `RUL_FD001.csv`) was used for final evaluation. Unlike the training data, test engines are truncated mid-life (simulating a "right now" snapshot), with the true RUL at that cutoff point provided separately. The same preprocessing pipeline was applied, the last available cycle per engine was extracted, and RUL was predicted.

## ✅ Results

| Metric | Validation | Test (fully unseen) |
|---|---|---|
| MAE | 13.99 | **12.94** |
| RMSE | 20.22 | **17.95** |

Test error is on par with (even slightly better than) validation error, indicating the model generalizes well rather than overfitting to the training split. This MAE range is consistent with published benchmarks on the CMAPSS FD001 subset.

## 🛠️ Tech Stack

- **Language:** Python
- **Data handling:** Pandas, NumPy
- **Visualization:** Matplotlib, Seaborn
- **Modeling:** LightGBM, Scikit-learn
- **Environment:** Google Colab

## 📊 Dataset

NASA CMAPSS (Commercial Modular Aero-Propulsion System Simulation) — FD001 subset. This subset simulates a single operating condition and single fault mode.

> The dataset is not included in this repository due to size. Download it from the [NASA Prognostics Data Repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) and place the files in a `data/` folder.

## 🚧 Project Status / Next Steps

- [x] Data preprocessing and RUL labeling
- [x] Feature engineering (rolling mean, rate of change)
- [x] Baseline LightGBM model with RUL capping
- [x] Evaluation on official held-out test set
- [ ] Hyperparameter tuning
- [ ] Streamlit app — interactive dashboard to select an engine, view sensor trends, and see predicted RUL with a health status indicator (safe / monitor / critical)

## 📁 Repository Structure

```
predictive-maintenance-cmapss/
├── README.md
├── notebook/
│   └── rul_prediction.ipynb
├── requirements.txt
└── app.py                  # Streamlit app (upcoming)
```
