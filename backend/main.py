from fastapi import FastAPI
from pydantic import BaseModel
# from Cal import Cal
from dateutil import parser
import pandas as pd
import os
import datetime

# Model Exc File
from arima_model import ARIMA_MD 
from knn_model import KNN_MD

folder1 = "./datasets"
dfs_comb = pd.DataFrame()
for df in [pd.read_csv(os.path.join(folder1,f)) for f in os.listdir(folder1) if f.endswith('daily.csv')]:
    dfs_comb = pd.concat([dfs_comb,df],axis='rows')
dfs_comb['Date'] = dfs_comb['Date'].apply(lambda x: parser.parse(x).date())#pd.to_datetime(dfs_comb["Date"]).dt.strftime("%Y-%m-%d %H:%M:%S")#dfs_comb['Date'].apply(lambda x: parser.parse(x).date())#datetime.date(YYYY, MM, DD)

folder2 = "./datasets/flight_paths.csv"
flights = pd.read_csv(folder2)
flights['apt_time_dt_ds'] = flights['apt_time_dt_ds'].apply(lambda x: parser.parse(x).date())#pd.to_datetime(flights["apt_time_dt_ds"]).dt.strftime("%Y-%m-%d %H:%M:%S")#flights['apt_time_dt_ds'].apply(lambda x: parser.parse(x).date())#datetime.date(YYYY, MM, DD)
flights['apt_time_dt_dp'] = flights['apt_time_dt_dp'].apply(lambda x: parser.parse(x).date())#pd.to_datetime(flights["apt_time_dt_dp"]).dt.strftime("%Y-%m-%d %H:%M:%S")#flights['apt_time_dt_dp'].apply(lambda x: parser.parse(x).date())

app = FastAPI()

def date_conv_to(df:pd.DataFrame,dates:list) -> list[dict]:
    df = df.copy()
    for cn in dates:
        df[cn] = pd.to_datetime(df[cn], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return df.to_dict(orient="records")

def date_conv_from(df:pd.DataFrame,dates:list) -> pd.DataFrame:
    for cn in dates:
        df[cn] = pd.to_datetime(df[cn], errors="coerce").dt.date
    return df

@app.post("/Health")
async def backend_up():
    return 

# def obtain_models():
#     return 

@app.post("/dfs_flgh_data")
async def dfs_flgh_data():
    return [date_conv_to(dfs_comb,['Date']),date_conv_to(flights,['apt_time_dt_ds','apt_time_dt_dp'])]

class FrCtReq(BaseModel):
    loc:str
    lat:float
    long:float
@app.post("/Forecasting")
async def forecasting(input:FrCtReq):
    return date_conv_to(ARIMA_MD(input.loc,input.lat,input.long),['Date'])

class RecReq(BaseModel):
    NewR:list
    main:str
    loc:str
@app.post("/Recommendation")
async def recommendation(input:RecReq):
    input.NewR[8] = datetime.date.fromisoformat(input.NewR[8])
    df = date_conv_from(pd.read_json(input.main),['Date'])
    kn = KNN_MD(input.NewR,df,input.loc)
    kn['Date'] = pd.to_datetime(kn['Date'], errors="coerce").strftime("%Y-%m-%d %H:%M:%S")
    return kn.to_dict()