import streamlit as st
import requests
import os
import pandas as pd
from datetime import date,timedelta,datetime
import calendar
from dateutil import parser
import time
import uuid
from posthog import Posthog

import plotly.graph_objects as go

# Used for Getting forecasting data from selected location 
from Dest_Forecasting_Data_Get import Dest_Forecastig_Data_Get 

# Function handles itinerary changes 
from poisUpdate import poisUpdate

#^ PAGE CONFIGURATION---------------------------- 
st.set_page_config(
    page_title="Start Your Travel Journey", 
    page_icon="🌍", 
    layout="wide"
)

#^ BACKGROUND STYLE AND CSS----------------------------
page_bg_img = '''
<style>
[data-testid="stAppViewContainer"] {
    background-image: url('https://images.unsplash.com/photo-1517760444937-f6397edcbbcd');
    background-size: cover;
    background-attachment: fixed;
}
[data-testid="stHeader"] {background: rgba(0,0,0,0);}
</style>'''
st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
    <style>
        .poi-recbox {
            background-color: rgba(131, 131, 131, 0.50);
            padding: 15px;
            border-radius: 15px;
            height: auto;
            font-size:25px;
        }
        .poi-disclmbox {
            background-color: rgba(131, 131, 131, 0.50);
            border-radius: 15px;
            height: auto;
            text-align: center;
            font-size:20px;
        }
        .poi-statO {
            font-size:20px;
        }
        .poi-statI {
            font-size:18px;
        }
        .scrollable-plot{
            width:100%;
            overflow-x: auto;
            overflow-y:hidden;
        }
        .scrollable-divMnthFC{
            overflow: auto;
            height: 450px;
            white-space: nowrap;
        }
        .scrollable-divLang{
            overflow-y: auto;
            height: 650px;
        }
        .stSpinner > div > div > div {
            font-size: 24px;
            color: #18c9d6;
        }
    </style>
    """, unsafe_allow_html=True)

#^ Backend Connection----------------------------
# In Docker/Heroku point this to the backend service URL
API_URL = os.environ.get("BACK_END_CONN")
if not API_URL:
    API_URL = os.getenv("API_URL", "http://localhost:8000")

with st.spinner("Connecting to service....."):
    for tr in range(5):
        try:
            res = requests.get(f"{API_URL}/Health", timeout=2.5)
            if res.status_code == 200:
                break
        except:
            time.sleep(1)
        if tr == 4:
            st.error("Backend service not avaiable at this time")
            st.stop()

#^ Setting up PostHog----------------------
# Generate an anonymous ID once per session  
if 'anon_id' not in st.session_state:  
    st.session_state['anon_id'] = str(uuid.uuid4())
PHG_API = os.environ.get("PHG_API")
if not PHG_API:
    PHG_API = st.secrets["PHG_API"]
PHG_HST = os.environ.get("PHG_HST")
if not PHG_HST:
    PHG_HST = st.secrets["PHG_HST"]
posthog = Posthog(
    project_api_key=PHG_API,
    host=PHG_HST
)
# Use the same anonymous ID for all events in this session  
posthog.capture(  
    distinct_id=st.session_state['anon_id'],  
    event='$pageview',  
    properties={  
        '$pathname': '/app',  # The page path  
    }  
) 

#^ Data convert from Backend------------------- 
def date_conv_from(df:pd.DataFrame,dates:list) -> pd.DataFrame:
    for cn in dates:
        df[cn] = pd.to_datetime(df[cn], errors="coerce").dt.date
    return df

#^ SESSION RELATED-----------------------------
# --- PRE LOADED BACKEND DATA ---
if "dfs_main" not in st.session_state and "flight_main" not in st.session_state:
    #^ Getting main data-----------------------------
    res = requests.post(f"{API_URL}/dfs_flgh_data").json()
    res = [pd.DataFrame(item) for item in res]
    st.session_state["dfs_main"] = date_conv_from(res[0],['Date'])
    st.session_state["flight_main"] = date_conv_from(res[1],['apt_time_dt_ds','apt_time_dt_dp'])
# --- HOUSING FORECAST & RECOMMEND & FLIGHT DATA ---
if 'FC_sel_Dest' not in st.session_state:
    st.session_state['FC_sel_Dest'] = pd.DataFrame()
if 'Flght_sel_Dest' not in st.session_state:
    st.session_state['Flght_sel_Dest'] = pd.DataFrame()
if 'RC_alt_Dest' not in st.session_state:
    st.session_state['RC_alt_Dest'] = pd.DataFrame()
if 'Flght_alt_Dest' not in st.session_state:
    st.session_state['Flght_alt_Dest'] = pd.DataFrame()
# --- HOUSING USER SELECTIONS ---
if 'user_sel' not in st.session_state:
    st.session_state['user_sel'] = [None,None,None,None,None,None]
# --- USER INPUT LANG
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = "English"
# ---- SESSION STATE INIT ----
for k in ["sel_att_cat","sel_att_type","sel_org","sel_Arv_dte","sel_crowd","sel_temp","sel_locN"]:
    if k not in st.session_state:
        st.session_state[k] = None
# ---- CALLBACKS ----
def update_user_sel():#Updating user_sel list to reflect new itinerary changes 
    st.session_state['user_sel'][0] = st.session_state['sel_org']
    st.session_state['user_sel'][1] = st.session_state['sel_Arv_dte']
    st.session_state['user_sel'][2] = st.session_state['sel_att_cat']
    if st.session_state['sel_att_cat'] == None:
        st.session_state['sel_att_type'] = None
    st.session_state['user_sel'][3] = st.session_state['sel_att_type']
    st.session_state['user_sel'][4] = st.session_state['sel_crowd']
    st.session_state['user_sel'][5] = st.session_state['sel_temp']

pois = poisUpdate() # used by the destination selection

#^ LAYOUT STRUCTURE---------------------------- 
O_W = 0.5
uppR = st.columns([O_W,7,O_W],gap='small')
midR = st.columns([O_W,2,5,O_W],gap='medium')
lowR = st.columns([O_W,2,2.5,2.5,O_W],gap='small')

#* ---------------------------- ROW 1: TITLE
with uppR[1]:
    TitleDis = st.columns([5],gap='small') + st.columns([7],gap='small')
    with TitleDis[0]:
        st.markdown(f"""
                <div class='poi-disclmbox'>
                    <h3>Disclaimers</h3>
                    <p>Forecast Model still needs Improvements | Currency is in CAD, converts based on Origin | Weather metrics in (TEMP C),(GUST KM/H),(PRCEP MM),(REL HUM %)</p>
                </div>
                """, unsafe_allow_html=True)
    with TitleDis[1]: 
        st.markdown("<h1 style='text-align:center; font-size:60px;'>Start Your Travel Journey</h1>", unsafe_allow_html=True)
    st.divider()
st.divider()

#* ---------------------------- ROW 2: OPTIONS & LOC EDA
with midR[1]:
    ops = st.columns([1]) + st.columns([1,1,1]) + st.columns([1,1]) + st.columns([1,1,1])
    with ops[0]:
        st.subheader("Itineraries")

    with ops[1]:
        OriginList = st.session_state["flight_main"].drop_duplicates(subset=['Country_dp','City_dp'])[['Country_dp','City_dp']]
        sel_org = st.selectbox("Choose an Orgin:",
                            OriginList.values.tolist(),
                            index=None,
                            placeholder="Select...",
                            key="sel_org"
                            ,on_change=update_user_sel)

    with ops[2]:
        user_input = st.text_input("Language Translator", help="Type in Langauge to translate Suggestions and Recommendations to, Currency will also change"
                               ,placeholder=f"Type what language to tranlate to",
                               key="user_input",
                               on_change=update_user_sel)
        if user_input.isalnum():
            user_input = ""
        if user_input == "": user_input="English"

    with ops[3]:
        sel_Arv_dte =  st.date_input(
            "Select Travel Arrival Date",
            min_value=date.today(),
            max_value=date.today() + timedelta(days=180),
            format="YYYY-MM-DD",
            key="sel_Arv_dte"
            ,on_change=update_user_sel)

    with ops[4]:
        AttCatL = st.session_state["dfs_main"]['Attraction_Category'].unique().tolist()
        sel_att_cat = st.selectbox("Choose Attraction Category:",
                                AttCatL,
                                index=None,
                                key="sel_att_cat",
                                placeholder="Select...",
                                on_change=update_user_sel)

    with ops[5]:
        att_type_list = st.session_state["dfs_main"][st.session_state["dfs_main"]['Attraction_Category'] == sel_att_cat]['Type_of_Attraction'].unique().tolist() if sel_att_cat else []
        sel_att_type = st.selectbox("Choose Attraction Type:",
                                att_type_list,
                                index=None,
                                placeholder="Select...",
                                disabled=(sel_att_cat == None),
                                key="sel_att_type"
                                ,on_change=update_user_sel)

    with ops[6]:
        sel_crowd = st.selectbox("Choose Crowd level:",
                        ['LOW','MEDIUM','HIGH'],
                        index=None,
                        placeholder="Select...",
                        key="sel_crowd"
                        ,on_change=update_user_sel)

    with ops[7]:
        sel_temp = st.selectbox("Choose Temp level:",
                        ['LOW','MEDIUM','HIGH'],
                        index=None,
                        placeholder="Select...",
                        key="sel_temp"
                        ,on_change=update_user_sel)
    
    with ops[8]:
        locNL = pois['Location_Name'].unique().tolist()
        sel_locN = st.selectbox("Choose a Destination:",
                        locNL,
                        index=None,
                        placeholder="Select...",
                        key="sel_locN")
        if sel_locN != None:
             # Capture event for anonymous user   
            posthog.capture(  
                distinct_id=st.session_state['anon_id'],  
                event='user_input_submitted',  
                properties={ 
                    'Origin': ", ".join(sel_org),
                    'Arrival_Date': sel_Arv_dte,
                    'Attraction_Category':sel_att_cat,
                    'Attraction_Type':sel_att_type,
                    'Crowd_Tolerance':sel_crowd,
                    'Temp_Preference':sel_temp,
                    'Destination':sel_locN,
                    '$process_person_profile': False , # Don't create person profile (cheaper)  
                    'environment': os.getenv('STREAMLIT_ENV', 'Development')  
                }  
            )  
            posthog.flush() # end capture before page refresh
            Dest_Forecastig_Data_Get()

with midR[2]:
    # Update figure with new data if Orgin,Avr Time,Dest have been selected
    fig = go.Figure()
    if st.session_state['sel_org'] != None and st.session_state['sel_Arv_dte'] != None and st.session_state['sel_locN'] != None:
        # Get Only the selected location, attach the storeded FC session data to historical data
        pltdata = st.session_state["dfs_main"][st.session_state["dfs_main"]['Location_Name'] == st.session_state['sel_locN']]
        pltdata = pd.concat([pltdata,st.session_state['FC_sel_Dest']],axis='index')[['Date','PedsSen_Count','Weather_Temperature','Weather_Wind_Gust','Weather_Relative_Humidity','Weather_Precipitation']]
        pltdata['Date'] = pltdata['Date'].apply(lambda x: pd.to_datetime(x.strftime('%Y-%m-%d')))

        # Resample for monthly from daily, provides a better visual of the hist + forecast data
        pltdata = pltdata.set_index('Date').resample('ME').mean().reset_index()
        pltdata = pltdata.rename(columns={
            'PedsSen_Count':'Monthly Crowd Count',
            'Weather_Temperature':'Monthly Temperature',
            'Weather_Wind_Gust':'Monthly Wind',
            'Weather_Relative_Humidity':'Monthly Realtive Humidity',
            'Weather_Precipitation':'Monthly Precipitation'
            })
        Tinfo = st.session_state["dfs_main"][['City','Country','Location_Name']].loc[st.session_state["dfs_main"]['Location_Name'] == st.session_state['sel_locN']].drop_duplicates().reset_index()
        
        fig.add_trace(go.Scatter( x=pltdata['Date'],y=pltdata['Monthly Crowd Count'],name = "Crowd Count",mode='lines',line=dict(width=3),yaxis='y'))
        fig.add_trace(go.Scatter(x=pltdata['Date'],y=pltdata['Monthly Temperature'],name = "Temperature",mode='lines',line=dict(width=3),opacity=0.7,yaxis='y2'))
        fig.add_trace(go.Scatter(x=pltdata['Date'],y=pltdata['Monthly Wind'],name = "Wind Gust",mode='lines',line=dict(width=3),opacity=0.5,yaxis='y3'))
        fig.add_trace(go.Scatter(x=pltdata['Date'],y=pltdata['Monthly Realtive Humidity'],name = "Realtive Humidity",mode='lines',line=dict(width=3),opacity=0.5,yaxis='y4'))
        fig.add_trace(go.Bar(x=pltdata['Date'],y=pltdata['Monthly Precipitation'],name = "Precipitation",marker_color="purple",opacity=0.5,yaxis='y5'))

        # Adding Forecast vertical line 
        fig.add_vline(x=parser.parse('2026-01-01').timestamp()*1000, line_width=2, line_dash="dash", line_color="red", annotation_text="Forecast Start>>", annotation_position="bottom left")

        fig.update_layout(title=f"{Tinfo['Location_Name'].loc[0]} — Monthly Trend ---- [{Tinfo['Country'].loc[0]}/{Tinfo['City'].loc[0]}]",
                      font=dict(size=24),
                      xaxis=dict(title_font_size=20,tickfont=dict(size=18),ticks="outside",automargin=True),
                      yaxis=dict(title_font_size=20,tickfont=dict(size=18),title='Crowd',side='left',ticks="outside",ticklabelposition="outside",automargin=True),
                      yaxis2=dict(title_font_size=20,tickfont=dict(size=18),title='Temp(C)',overlaying='y',side='left',ticks="outside",ticklabelposition="outside",automargin=True,anchor="free",autoshift=True,shift=1),
                      yaxis3=dict(title_font_size=20,tickfont=dict(size=18),title='Gust(KM/H)',overlaying='y',side='left',ticks="outside",ticklabelposition="outside",automargin=True,anchor="free",autoshift=True,shift=1),
                      yaxis4=dict(title_font_size=20,tickfont=dict(size=18),title='Rel Hum(%)',overlaying='y',side='left',ticks="outside",ticklabelposition="outside",automargin=True,anchor="free",autoshift=True,shift=1),
                      yaxis5=dict(title_font_size=20,tickfont=dict(size=18),title='Prcep(MM)',overlaying='y',side='left',ticks="outside",ticklabelposition="outside",automargin=True,anchor="free",autoshift=True,shift=1),
                      height=300,
                      margin=dict(l=5,r=5,t=40,b=5),
                      hovermode="x unified",
                      legend=dict(x=1,y=1,xanchor="left",yanchor="top")
        )

    else: # If user deselectes Orgin,Arv Time,Dest, then reset graph. 
        fig.add_trace(go.Scatter())
    
        fig.update_layout(title="Destination-Orgin-Time not Selected",
                        font=dict(size=24),
                        xaxis=dict(title_font_size=20,tickfont=dict(size=18)),
                        yaxis=dict(title_font_size=20,tickfont=dict(size=18)),
                        height=300, 
                        margin=dict(l=10,r=10,t=40,b=10))
        
    st.plotly_chart(fig, use_container_width=True)

#* ---------------------------- ROW 3: TRANSLATOR & SUGGESTION & RECOMMENDATION & MONTH DAILY FC RESULTS
# Below are the AI Features for Sugesting and Recommending 
with lowR[2]: # Sueggestions
    st.subheader("Suggestions")
    if st.session_state['sel_org'] != None and st.session_state['sel_Arv_dte'] != None and st.session_state['sel_locN'] != None:
        # Reterving the Forecast at User Arival Time and Flight Path at the date
        FCArv = st.session_state['FC_sel_Dest'].loc[st.session_state['FC_sel_Dest']['Date'] == st.session_state['sel_Arv_dte']].reset_index(drop=True)
        FLArv = st.session_state['Flght_sel_Dest'].loc[st.session_state['Flght_sel_Dest']['apt_time_dt_ds'] == st.session_state['sel_Arv_dte']].reset_index(drop=True)

        FClow = st.session_state['FC_sel_Dest'].loc[st.session_state['FC_sel_Dest']['PedsSen_Count'] < FCArv['PedsSen_Count'].loc[0]]
        FLlow = st.session_state['Flght_sel_Dest'].loc[st.session_state['Flght_sel_Dest']['apt_time_dt_ds'].isin(FClow['Date'].to_list())].reset_index(drop=True)

        StateBuilder = [] # Logic Statement Builder

        StateBuilder.append(f"""<p class='poi-statO'>Forecast Crowd: {int(FCArv['PedsSen_Count'].loc[0])} people<br></p>""")

        if len(FLArv) > 0: 
            OthFlArv = '<br>'.join([f'{tp['apt_name_dp']} -- {tp['apt_time_dt_dp']} --> {tp['apt_name_ds']} -- {tp['apt_time_dt_ds']}  >>> &dollar;{tp['price']}' for i,tp in FLArv.nsmallest(n=20, columns='price').iterrows()][:3])
            StateBuilder.append(
                f"""<p class='poi-statO'>Arvival Date Flight Paths <br> {OthFlArv}</p>"""
            )
        else:
            StateBuilder.append(
                """<p class='poi-statO'>No Flights Path For Arvival Date</p>"""
            )

        if len(FClow) > 0:
            OthFCLow = '<br>'.join([f'People: {int(tp['PedsSen_Count'])} -- {tp['Date']}' for i,tp in FClow.nsmallest(n=20, columns='PedsSen_Count').iterrows() if tp['Date'] > date.today()][:3]) 
            StateBuilder.append(
                f"""<p class='poi-statO'>Other Dates With Less Arvival Crowd Forecast<br> {OthFCLow}</p>"""
            ) 
        else:
            StateBuilder.append(
                """<p class='poi-statO'>No Other Dates Less than Arvival Date Crowd Forecast </p>"""
            )

        if len(FLlow) > 0:
            OthFllow = '<br>'.join([f'{tp['apt_name_dp']} -- {tp['apt_time_dt_dp']} --><br> {tp['apt_name_ds']} -- {tp['apt_time_dt_ds']} >>> &dollar;{tp['price']}' for i,tp in FLlow.nsmallest(n=20, columns='price').iterrows()][:3])
            StateBuilder.append(
                f"""<p class='poi-statO'>Other Dates Flight Paths <br> {OthFllow}</p>"""
            )
        else:
            StateBuilder.append(
                """<p class='poi-statO'>No Flights Path For Other Dates</p>\n"""
            )
        
        payload = {"content":
        "You are an HTML editor, not a chat assistant.\n"+
        "Return only the final edited raw HTML.\n"+
        "Do not explain anything before or after the HTML.\n"+
        "Do not include citations, links, source names, or notes outside the HTML.\n"+
        f"Target-Language is {st.session_state['user_input']}.\n"+
        f"Target-Country is {st.session_state['sel_org'][0]}.\n"+
        f"Target-Country has the city of {st.session_state['sel_org'][1]}.\n\n"+

        "TASKS:\n"+
        "1. Determine the Target-Country currency.\n"+
        "2. Determine the current currency exchange-rate between Canada and Target-Country.\n"+
        "3. If Target-Country not Canada then convert any currency value with &dollar; in HTML body by multiplying it with exchange-rate.\n"+
        "4. Translate only visible user-facing English text into Target-Language.\n"+
        "5. If Target-Country not Canada then append a visible line at the bottom of the HTML body showing the Target-Country currency label, and Canada to Target-Country exchange-rate.\n\n"+

        "STRICT CURRENCY RULES:\n"+
        "- Treat every visible &dollar; amount as CAD.\n"+
        "- Convert only visible monetary values in the HTML body.\n\n"+

        "STRICT HTML RULES:\n"+
        "- Preserve the HTML structure exactly.\n"+
        "- Do NOT modify tags, attributes, IDs, class names, JavaScript, CSS, or template variables.\n"+
        "- Do NOT translate text inside <script>, <style>, <meta>, <head>, or HTML comments.\n"+
        "- Translate only text visibly rendered in the browser.\n"+
        "- Maintain whitespace and formatting as much as possible.\n\n"+

        "STRICT OUTPUT RULES:\n"+
        "- Return ONLY raw HTML.\n"+
        "- Do NOT output any explanation.\n"+
        "- Do NOT output any preface.\n"+
        "- Do NOT output any summary.\n"+
        "- Do NOT output citations.\n"+
        "- Do NOT output URLs.\n"+
        "- Do NOT output source names.\n"+
        "- Do NOT say 'Here is the updated HTML'.\n"+
        "- Do NOT use markdown.\n"+
        "- Do NOT use triple backticks.\n"+
        "- The response must begin with the first HTML tag and end with the last HTML tag.\n\n"+

        "HTML TO EDIT:\n"+
        f"{''.join(StateBuilder)}"}
        with st.spinner("Connecting to OpenAI....."):
            for tr in range(5):
                try:
                    resp = requests.post(f"{API_URL}/OPENAI",json=payload, timeout=10)
                    if resp.status_code == 200:
                        break
                except:
                    time.sleep(1)
                if tr == 4:
                    st.error("OpenAI service not avaiable at this time")
                    st.stop()

        st.markdown(f"""
            <div class='poi-recbox'>
                    {resp.json()['resp']}
            </div>
            """, unsafe_allow_html=True)
        
    else: # Empty div when one of the itinerary selections is deselected
        st.markdown(f"""
            <div class='poi-recbox'>
            </div> 
            """, unsafe_allow_html=True)
        
with lowR[3]:# Recmmmendation
    st.subheader("Alternative Destination")
    if st.session_state['sel_org'] != None and st.session_state['sel_Arv_dte'] != None and st.session_state['sel_locN'] != None:
        RCArv = st.session_state['RC_alt_Dest']
        RCFl = st.session_state['Flght_alt_Dest']  
 
        StateBuilder2 = [] # Logic Satament Builder

        StateBuilder2.append(f"""<p class='poi-statO'>{RCArv['Location_Name'].loc[0]}, {RCArv['Country'].loc[0]}, {RCArv['City'].loc[0]} with past historical crowd numbers 
                            lower than current selected, one of them being {int(RCArv['PedsSen_Count'].loc[0])} people<br>You could consider traveling to here during {RCArv['Date'].loc[0].month}/{RCArv["Date"].loc[0].day}</p>""")
        payload = {"content":
        "You are an HTML editor, not a chat assistant.\n"+
        "Return only the final edited raw HTML.\n"+
        "Do not explain anything before or after the HTML.\n"+
        "Do not include citations, links, source names, or notes outside the HTML.\n"+
        f"Target-Language is {st.session_state['user_input']}.\n"+
        f"Target-Country is {st.session_state['sel_org'][0]}.\n"+
        f"Target-Country has the city of {st.session_state['sel_org'][1]}.\n\n"+

        "TASKS:\n"+
        "1. Translate only visible user-facing English text into Target-Language.\n\n"+

        "STRICT HTML RULES:\n"+
        "- Preserve the HTML structure exactly.\n"+
        "- Do NOT modify tags, attributes, IDs, class names, JavaScript, CSS, or template variables.\n"+
        "- Do NOT translate text inside <script>, <style>, <meta>, <head>, or HTML comments.\n"+
        "- Translate only text visibly rendered in the browser.\n"+
        "- Maintain whitespace and formatting as much as possible.\n\n"+

        "STRICT OUTPUT RULES:\n"+
        "- Return ONLY raw HTML.\n"+
        "- Do NOT output any explanation.\n"+
        "- Do NOT output any preface.\n"+
        "- Do NOT output any summary.\n"+
        "- Do NOT output citations.\n"+
        "- Do NOT output URLs.\n"+
        "- Do NOT output source names.\n"+
        "- Do NOT say 'Here is the updated HTML'.\n"+
        "- Do NOT use markdown.\n"+
        "- Do NOT use triple backticks.\n"+
        "- The response must begin with the first HTML tag and end with the last HTML tag.\n\n"+

        "HTML TO EDIT:\n"+
        f"{''.join(StateBuilder2)}"}
        with st.spinner("Connecting to OpenAI....."):
            for tr in range(5):
                try:
                    resp = requests.post(f"{API_URL}/OPENAI",json=payload, timeout=10)
                    if resp.status_code == 200:
                        break
                except:
                    time.sleep(1)
                if tr == 4:
                    st.error("OpenAI service not avaiable at this time")
                    st.stop()

        st.markdown(f"""
            <div class='poi-recbox'>
                    {resp.json()['resp']}
            </div>
            """, unsafe_allow_html=True)
            
    else: # Empty div when one of the itinerary selections is deselected
        st.markdown(f"""
            <div class='poi-recbox'>
            </div>
            """, unsafe_allow_html=True)
            
with lowR[1]: # 30 day Forecast Table Builder for month that user's date is in
    st.subheader("Month Forcast Numbers")
    if st.session_state['sel_org'] != None and st.session_state['sel_Arv_dte'] != None and st.session_state['sel_locN'] != None:
        dts_sel = st.session_state['sel_Arv_dte']
        num_days = calendar.monthrange(dts_sel.year, dts_sel.month)[1]
        start_dte = datetime(dts_sel.year,dts_sel.month,1).date()
        end_dte = datetime(dts_sel.year,dts_sel.month,num_days).date()
        month_fc = st.session_state['FC_sel_Dest'][(st.session_state['FC_sel_Dest']['Date'] >= start_dte) & (st.session_state['FC_sel_Dest']['Date'] <= end_dte)]
        month_fc = month_fc.drop(columns=['Is_Holiday'])
        month_fc = month_fc.rename(columns={
            'Weather_Temperature':'Temp',
            'Weather_Wind_Gust':'Gust',
            'Weather_Relative_Humidity':'Rel Hum',
            'Weather_Precipitation':'Precp',
            'PedsSen_Count':'Daily Crowd'
        })
        month_fc = month_fc.loc[:,['Date','Daily Crowd','Temp','Gust','Rel Hum','Precp']]
        st.markdown(f"""
            <div class='poi-recbox scrollable-divMnthFC'>
                {month_fc.to_html(formatters={'Daily Crowd':'{:,.0f}'.format,
                                               'Temp':'{:,.2f}'.format,
                                               'Gust':'{:,.2f}'.format,
                                               'Rel Hum':'{:,.2f}'.format,
                                               'Precp':'{:,.2f}'.format
                                            }, index=False)}
            </div>
            """, unsafe_allow_html=True)
        
    else:
        st.markdown(f"""
            <div class='poi-recbox'>
            </div>
            """, unsafe_allow_html=True)