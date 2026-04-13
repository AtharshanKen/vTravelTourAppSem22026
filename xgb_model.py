import pandas as pd
import numpy as np
import pickle
import os
import random

from xgboost import XGBRegressor

SEED = 42
os.environ["PYTHONHASHSEED"] = str(SEED)
np.random.seed(SEED)
random.seed(SEED)

from weather_req_holiday import Weather_Requester,Holidayer

# Applying the cyclical endoding to forecasting data frame
def add_calendar_features_future(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dow_sin"] = np.sin(2 * np.pi * df["Date"].dt.dayofweek / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["Date"].dt.dayofweek / 7)
    df["doy_sin"] = np.sin(2 * np.pi * df["Date"].dt.dayofyear / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["Date"].dt.dayofyear / 365.25)
    df["is_weekend"] = (df["Date"].dt.dayofweek >= 5).astype(int)
    return df

# Load the correct pickel file
def load_location_pickle(loc_id: str):
    with open(f"./models/{loc_id}.pkl", "rb") as f:
        bundle = pickle.load(f)
    return bundle

# We are using a sliding window, must obtain the state and alpha as each data set model can vary, no state and alpha works for more then one data set    
def _init_ewma_state(history: list[float], halflife: float) -> tuple[float, float]:
    alpha = 1.0 - np.exp(np.log(0.5) / halflife)
    if not history:
        return 0.0, alpha

    state = float(history[0])
    for v in history[1:]:
        state = alpha * float(v) + (1.0 - alpha) * state
    return state, alpha

Cabrv = {'IRDUB':'IE','NZAUK':'NZ'} # Country Codes for Holiday data
# Loads an XGB location bundle, builds future exogenous inputs (weather+holiday+calendar),
# and performs recursive forecasting using lag/rolling/EWMA features.
# Returns Date formatted as YYYY-MM-DD.
def XGB_MD(loc_id: str, lat: float, lon: float) -> pd.DataFrame:
    country_code = Cabrv.get(loc_id.split('_')[0])

    bundle = load_location_pickle(loc_id)

    features = bundle["features"]
    imputer = bundle["imputer"]
    model = bundle["model"]

    history_raw = bundle["last_history_raw"].copy().reset_index(drop=True)

    history = [float(v) for v in history_raw['PedsSen_Count'].dropna().tolist()]

    ewma60_state, alpha60 = _init_ewma_state(history, halflife=60.0)

    # Build exogenous future inputs
    wx = Weather_Requester(lat, lon)
    wx["Date"] = pd.to_datetime(wx["Date"]).dt.normalize()

    hol = Holidayer(wx,country_code)
    fut = add_calendar_features_future(hol)

    preds = []

    # Helps with bulding all lag columns
    def lag(k: int) -> float:
        if len(history) >= k:
            return float(history[-k])
        return float(history[0])

    for i in range(fut.shape[0]):
        row = fut.iloc[i]

        # Fill this new row then append to window after 
        new = pd.Series(index=features, dtype="float64")

        # Lag/rolling/EWMA features (matching training definitions)
        if "lag1" in features:
            new["lag1"] = lag(1)
        if "lag7" in features:
            new["lag7"] = lag(7)
        if "lag14" in features:
            new["lag14"] = lag(14)
        if "lag28" in features:
            new["lag28"] = lag(28)

        if "roll7" in features:
            new["roll7"] = float(np.mean(history[-7:]))
        if "roll14" in features:
            new["roll14"] = float(np.mean(history[-14:]))
        if "roll30" in features:
            new["roll30"] = float(np.mean(history[-30:]))

        if "ewma60" in features:
            new["ewma60"] = float(ewma60_state)

        # Weather
        new["Weather_Temperature"] = float(row["Weather_Temperature"])
        new["Weather_Wind_Gust"] = float(row["Weather_Wind_Gust"])
        new["Weather_Relative_Humidity"] = float(row["Weather_Relative_Humidity"])
        new["Weather_Precipitation"] = float(row["Weather_Precipitation"])

        # Holiday/calendar
        new["Is_Holiday"] = int(row["Is_Holiday"])
        new["dow_sin"] = float(row["dow_sin"])
        new["dow_cos"] = float(row["dow_cos"])
        new["doy_sin"] = float(row["doy_sin"])
        new["doy_cos"] = float(row["doy_cos"])
        new["is_weekend"] = int(row["is_weekend"])

        # Predict in log-space model, then invert with expm1
        X_one = pd.DataFrame([new], columns=features)
        X_one = imputer.transform(X_one) # ndarry with non zero values to improve ml processing speed
        pred_log = float(model.predict(X_one)[0])
        pred = float(np.clip(np.expm1(pred_log), 0.0, None))
        preds.append(pred)

        # Update recursive state with predicted value
        history.append(pred)
        ewma60_state = alpha60 * pred + (1.0 - alpha60) * ewma60_state

    out = fut.copy()
    out.insert(1, "PedsSen_Count", np.round(preds, 0))
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")

    keep_cols = [
        "Date",
        "PedsSen_Count",
        "Weather_Temperature",
        "Weather_Wind_Gust",
        "Weather_Relative_Humidity",
        "Weather_Precipitation",
        "Is_Holiday",
    ]
    return out[keep_cols]