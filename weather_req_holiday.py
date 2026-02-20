import pandas as pd
import numpy as np
from datetime import timedelta,date
from dateutil import parser
import holidays as hl

import openmeteo_requests
import requests_cache
from retry_requests import retry
# trim_date = parser.parse('2026-01-01').date()

# Setup the Open-Meteo API client with cache and retry on error # <--- this is from Open Meteo Api Docs
cache_session = requests_cache.CachedSession('.amriacache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def Weather_Requester(lat:float,long:float) -> pd.DataFrame:
    # FwdD = 30 + (ArvDate - date.today()).days
    url = "https://archive-api.open-meteo.com/v1/archive"# Histroical Data
    params = {
        "latitude": lat,
        "longitude": long,
        "start_date": '2024-12-31',
        "end_date": (date.today()-timedelta(days=1)).strftime('%Y-%m-%d'),
        "daily": ["temperature_2m_mean", "wind_gusts_10m_mean", "relative_humidity_2m_mean", "precipitation_sum"],
        "timezone": "auto"
    }
    response = openmeteo.weather_api(url,params=params)
    # Basically getting the data for the beginning of the trim point of Sep 30 2025 of the dataset to 1 day - current day   
    dly = response[0].Daily()

    T1 = dly.Variables(0).ValuesAsNumpy() # Np array's 
    W1 = dly.Variables(1).ValuesAsNumpy()
    R1 = dly.Variables(2).ValuesAsNumpy()
    P1 = dly.Variables(3).ValuesAsNumpy()

    url = "https://seasonal-api.open-meteo.com/v1/seasonal"# Future Data
    params = {
        "latitude": lat,
        "longitude": long,
        "forecast_days": 217,
        "timezone": "auto",
        "daily": ["temperature_2m_mean", "wind_gusts_10m_mean", "relative_humidity_2m_mean", "precipitation_sum"]
    }
    
    response = openmeteo.weather_api(url,params=params)
    dly = response[0].Daily()

    T2 = dly.Variables(0).ValuesAsNumpy()
    W2 = dly.Variables(1).ValuesAsNumpy()
    R2 = dly.Variables(2).ValuesAsNumpy()
    P2 = dly.Variables(3).ValuesAsNumpy()

    T = np.concatenate((T1,T2))
    W = np.concatenate((W1,W2))
    P = np.concatenate((P1,P2))
    R = np.concatenate((R1,R2))
    
    # Build the final indep array, holiday and time will be added later
    vstk = pd.DataFrame(data = np.vstack((T,W,R,P)).T,
                        columns=['Weather_Temperature',
                                 'Weather_Wind_Gust',
                                 'Weather_Relative_Humidity',
                                 'Weather_Precipitation'])

    return vstk

def Holidayer(df:pd.DataFrame,CCode:str) -> pd.DataFrame:
    df['Is_Holiday'] = df['Date'].apply(lambda x: 1 if hl.country_holidays(country=CCode).get(x) != None else 0)
    return df
