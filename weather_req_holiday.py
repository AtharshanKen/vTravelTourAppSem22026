import pandas as pd
import numpy as np
from datetime import datetime,timedelta,date
from dateutil import parser
import holidays as hl
import time

import openmeteo_requests
import requests_cache
from retry_requests import retry
# trim_date = parser.parse('2026-01-01').date()

# Setup the Open-Meteo API client with cache and retry on error # <--- this is from Open Meteo Api Docs
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def Weather_Requester(lat:float,lon:float) -> pd.DataFrame:
    """
    Returns a DataFrame with:
      Date,
      Weather_Temperature,
      Weather_Wind_Gust,
      Weather_Relative_Humidity,
      Weather_Precipitation
    """
    HsRg = (date.today() - date(date.today().year, 1, 1)).days
    FcRg = 217
    plength = HsRg + FcRg
    dates = pd.date_range(pd.Timestamp(datetime(date.today().year, 1, 1, 0, 0, 0)), periods=plength, freq="D")

    # Past (archive)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": dates[0].strftime("%Y-%m-%d"),
        "end_date": dates[HsRg-1].strftime("%Y-%m-%d"),
        "daily": ["temperature_2m_mean", "wind_gusts_10m_mean", "relative_humidity_2m_mean", "precipitation_sum"],
        "timezone": "auto",
    }
    while True:
        try:
            responses = openmeteo.weather_api(url, params=params)
            break
        except Exception as e:
            print(f"Openmeto retry Past {e}", end="", flush=True)
            time.sleep(60)
            print("", end="", flush=True)

    dly = responses[0].Daily()
    T1 = dly.Variables(0).ValuesAsNumpy()
    W1 = dly.Variables(1).ValuesAsNumpy()
    R1 = dly.Variables(2).ValuesAsNumpy()
    P1 = dly.Variables(3).ValuesAsNumpy()

    # Future (seasonal)
    url = "https://seasonal-api.open-meteo.com/v1/seasonal"
    params = {
        "latitude": lat,
        "longitude": lon,
        "forecast_days": FcRg,
        "timezone": "auto",
        "daily": ["temperature_2m_mean", "wind_gusts_10m_mean", "relative_humidity_2m_mean", "precipitation_sum"],
    }
    while True:
        try:
            responses = openmeteo.weather_api(url, params=params)
            break
        except Exception as e:
            print(f"Openmeto retry Future {e}", end="", flush=True)
            time.sleep(60)
            print("", end="", flush=True)

    dly = responses[0].Daily()
    T2 = dly.Variables(0).ValuesAsNumpy()
    W2 = dly.Variables(1).ValuesAsNumpy()
    R2 = dly.Variables(2).ValuesAsNumpy()
    P2 = dly.Variables(3).ValuesAsNumpy()

    T = np.concatenate((T1, T2)).T
    W = np.concatenate((W1, W2)).T
    R = np.concatenate((R1, R2)).T
    P = np.concatenate((P1, P2)).T

    df =  pd.DataFrame(
        {
            "Date": dates,
            "Weather_Temperature": T,
            "Weather_Wind_Gust": W,
            "Weather_Relative_Humidity": R,  
            "Weather_Precipitation": P,      
        }
    )

    df = df.dropna(how='any', axis='index') # can go up to max fc but results with NaN, will drop them
    return df

def Holidayer(df:pd.DataFrame,CCode:str) -> pd.DataFrame:
    cal = hl.country_holidays(country=CCode)
    df['Is_Holiday'] = df['Date'].apply(lambda x: 1 if cal.get(x) != None else 0)
    return df
