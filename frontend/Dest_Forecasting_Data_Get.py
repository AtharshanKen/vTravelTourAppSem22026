import streamlit as st
import pandas as pd
from datetime import date
import requests
import os

API_URL = os.environ.get("BACK_END_CONN")
if not API_URL:
    API_URL = os.getenv("API_URL", "http://localhost:8000")
# # Model Exc File
# from arima_model import ARIMA_MD 
# from knn_model import KNN_MD
def date_conv_to(df:pd.DataFrame,dates:list) -> list[dict]:
    df = df.copy()
    for cn in dates:
        df[cn] = pd.to_datetime(df[cn], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return df.to_json(orient="records")

def date_conv_from(df:pd.DataFrame,dates:list) -> pd.DataFrame:
    for cn in dates:
        df[cn] = pd.to_datetime(df[cn], errors="coerce").dt.date
    return df

def Dest_Forecastig_Data_Get(): # Get users destination data once orgin and data have been specified
    if st.session_state['sel_org'] != None and st.session_state['sel_Arv_dte'] != None:
        dfs_comb = st.session_state['dfs_main'].copy()
        flights = st.session_state['flight_main'].copy()

        # Grab Past Location Data from Data Set
        LocData = dfs_comb[dfs_comb['Location_Name'] == st.session_state['sel_locN']]
        
        # Building Meta data used for KNN and ARIMA models 
        MetaData = LocData[['Country','City','Location_ID','Location_Name','Type_of_Attraction','Attraction_Category','Latitude','Longitude']].loc[LocData.first_valid_index()]
        
        # Get Forcast data for th enext 180 day from trim point Sept 30 2025 to 180 days later from today
        # FC = ARIMA_MD(MetaData['Location_ID'],MetaData['Latitude'],MetaData['Longitude']) # Get Forecast for POI
        FC = requests.post(f"{API_URL}/Forecasting",json={"loc":MetaData['Location_ID'],"lat":MetaData['Latitude'],"long":MetaData['Longitude']}).json()
        FC = date_conv_from(pd.DataFrame(FC),['Date'])
        FC['Date'] = FC['Date'].apply(lambda x : pd.Timestamp(x).date())#datetime.date(YYYY, MM, DD)
        
        st.session_state['FC_sel_Dest'] = FC # save to sesssion state]
        
        # Filter fligth paths with FC in mind     
        flgData1 = flights[(flights['City_dp'] == st.session_state['sel_org']) & 
                          (flights['City_ds'] == MetaData['City']) & 
                          (flights['apt_time_dt_ds'] >= date.today()) & 
                          (flights['apt_time_dt_ds'] <= FC['Date'].loc[len(FC)-1])]
        st.session_state['Flght_sel_Dest'] = flgData1 # save to sesssion state
        
        #Buidling the new row for KNN model, needed for building input
        FCr = FC.loc[FC['Date'] == st.session_state['sel_Arv_dte']]
        NEwR = [MetaData['Country'],
                MetaData['City'],
                '-', # What we are predicting for recommending
                MetaData['Location_Name'],
                MetaData['Type_of_Attraction'],
                MetaData['Attraction_Category'],
                MetaData['Latitude'],
                MetaData['Longitude'],
                st.session_state['sel_Arv_dte'].isoformat(),
                FCr['PedsSen_Count'].iloc[0].item(),
                FCr['Weather_Temperature'].iloc[0].item(),
                FCr['Weather_Wind_Gust'].iloc[0].item(),
                FCr['Weather_Relative_Humidity'].iloc[0].item(),
                FCr['Weather_Precipitation'].iloc[0].item(),
                FCr['Is_Holiday'].iloc[0].item()]
        # for item in NEwR: print(item,type(item))
        # RC = KNN_MD(NEwR,dfs_comb,MetaData['Location_ID']) # Get recommended areas with less crowd
        RC = requests.post(f"{API_URL}/Recommendation",json ={
            "NewR":NEwR,
            # "main":date_conv_to(dfs_comb,['Date']),
            "loc":MetaData['Location_ID']
        }).json()
        RC = pd.DataFrame([RC])
        RC['Date'] = pd.to_datetime(RC['Date']).dt.date
        st.session_state['RC_alt_Dest'] = RC # save to sesssion state

        # Filter fligth paths with RC in mind
        flgData2 = flights[(flights['City_dp'] == st.session_state['sel_org']) & 
                          (flights['City_ds'] == RC['City'].loc[0]) & 
                          (flights['apt_time_dt_ds'] >= date.today()) & 
                          (flights['apt_time_dt_ds'] <= RC['Date'].loc[0])]
        st.session_state['Flght_alt_Dest'] = flgData2 # save to session state
    else: # If user deselects one of the options reset save states 
        st.session_state['FC_sel_Dest'] = pd.DataFrame()
        st.session_state['Flght_sel_Dest'] = pd.DataFrame()
        st.session_state['RC_alt_Dest'] = pd.DataFrame()
        st.session_state['Flght_alt_Dest'] = pd.DataFrame()