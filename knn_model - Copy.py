import pandas as pd
import numpy as np
import pickle

from sklearn.preprocessing import LabelEncoder,StandardScaler

def KNN_MD(NewRCat:list,dfscomb:pd.DataFrame,loc_id:str)->pd.DataFrame:
    with open(f"./models/loc_knn.pkl", "rb") as f:
        knn_model = pickle.load(f) # grab right pickel file
    
    df = dfscomb.copy()
    df.loc[len(df)] = NewRCat # Adding to the end for label encoding
    df = df.reset_index(drop=True)
    # df = df[df['Location_ID'] != loc_id].reset_index(drop=True) # don't want to predict our self
    df1 = df.copy()

    # Encode categorical columns (except target)
    label_encoders = {}
    for col in df1.select_dtypes(include=['object']).columns:
        if col != 'Location_ID' and col != 'Date':
            le = LabelEncoder()
            df1[col] = le.fit_transform(df1[col].astype(str))
            label_encoders[col] = le
 
    # Performing Cyclical Encoding
    df1['Month_Sin'] = df1['Date'].apply(lambda x: np.sin(2 * np.pi * x.month / 12))
    df1['Month_Cos'] = df1['Date'].apply(lambda x: np.cos(2 * np.pi * x.month / 12))
    df1['Day_Sin']   = df1['Date'].apply(lambda x: np.sin(2 * np.pi * (x.weekday()+1)/ 7))
    df1['Day_Cos']   = df1['Date'].apply(lambda x: np.cos(2 * np.pi * (x.weekday()+1)/ 7))

    cols_to_use = [ # Not to be used but to tell what columns are being used
        'PedsSen_Count',
        'Weather_Temperature',
        'Weather_Wind_Gust',
        'Weather_Relative_Humidity',
        'Weather_Precipitation',
        'Month_Sin',
        'Month_Cos',
        'Day_Sin',
        'Day_Cos',
        'Latitude',
        'Longitude','Attraction_Category'
        ]

    X = df1.drop(columns=['Location_ID',
                        'Country',
                        'City','Is_Holiday',
                        'Type_of_Attraction',
                        'Location_Name',
                        'Date'])
    scaler = StandardScaler() 
    X = scaler.fit_transform(X)[-1] # Takes the last row that was added
    
    # Predict and get all locations not the selected location, store as [rows in dfscomb] in Found
    yPD,yPI = knn_model.kneighbors([X])
    Found = pd.DataFrame(columns=df.columns)

    for i in range(len(yPI[0])):
        idx = yPI[0,i]
        if df['Location_ID'].loc[idx] != loc_id:
            Found.loc[len(Found)] = df.loc[idx]
    
    # Keep the row found with lowest crowd
    Found = Found.sort_values(by=['PedsSen_Count']).reset_index(drop=True)
    return Found.loc[0]
