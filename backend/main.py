from fastapi import FastAPI , HTTPException
from typing import Literal
from pydantic import BaseModel, Field
from pydantic.v1 import BaseSettings
from pathlib import Path
from dateutil import parser
import pandas as pd
import os
import datetime

#Adding env for open ai key, maps to .env for use for local work if no container env key
from openai import AsyncOpenAI
class Settings(BaseSettings):
    openai_api_key: str
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()

api = os.environ.get("OPENAI_API_KEY")
if api is None:
    api = settings.openai_api_key
client = AsyncOpenAI(api_key=api)

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

@app.get("/")
def root():
    return {"message":"Hello"}

@app.get("/Health")
def backend_up():
    return {"status": "alive"}

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
    fc = ARIMA_MD(input.loc,input.lat,input.long)
    for _,c in dfs_comb[(dfs_comb['Location_ID'] == input.loc)&(pd.to_datetime(dfs_comb['Date'],format="%Y-%m-%d").dt.year >= 2025)].reset_index(drop=True).loc[0:365,['Date','PedsSen_Count']].iterrows():
        indx = fc.index[fc['Date']==pd.Timestamp(c['Date'])].tolist()[0]
        fc.loc[indx,'PedsSen_Count'] = c['PedsSen_Count']
    return date_conv_to(fc,['Date'])

class RecReq(BaseModel):
    NewR:list
    # main:str
    loc:str
@app.post("/Recommendation")
async def recommendation(input:RecReq):
    input.NewR[8] = datetime.date.fromisoformat(input.NewR[8])
    # df = date_conv_from(pd.read_json(input.main),['Date'])
    kn = KNN_MD(input.NewR,dfs_comb,input.loc)
    kn['Date'] = pd.to_datetime(kn['Date'], errors="coerce").strftime("%Y-%m-%d %H:%M:%S")
    return kn.to_dict()


class open_AI(BaseModel):
    content:str 
@app.post("/OPENAI")
async def openai_api(input:open_AI):
    try:
        resp =  await client.responses.create(
                model="gpt-4o-mini",
                input = input.content,
                # messages=[{
                #     "role":input.role,
                #     "content":input.content
                # }],
                temperature=0.2,
                tools=[{"type": "web_search"}]
        )
        return {"resp":resp.output_text}
    except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))