# TravelTourApp Sem 2 2026
Capstone Project for solving over tourism 
- Created By: 
  -  Atharshan Kennedy
  -  Uzer Hamza Khan
  -  Caroline Kaurungai
  -  Anantdeep Kaur
  -  Pratik Patel

Project is an application that will guide users to lower crowded areas.

Website built with Stream Lit, FastAPI, Docker, and Deployed through Heroku & Google Cloud Run and can be accessed through here:
https://vtt-capstonesem2026-frontend-5222691be1f6.herokuapp.com/
Incropates a CI/CD workflow for updating the frontend & backend banches automatically, allowfor updated versions to be live for Heroku & GCR.
Main docker compose file for local deployment that runs backend then frontend.  
To run locally either fork then pull to remote or just download project:
  - Then right click in the folder within main directory of project click Git Bash
  - Use 'docker-compose build'
  - Use 'docker-compse up'
  - Access Backend 'http://localhost:8000/docs'
  - Access Frontend 'http://localhost:8501/'
  - If no Docker and/or Git Bash installed use terminal in CMD
    - Open a CMD in the Backend folder type in 'uv run fastapi dev main.py'
    - Open a CMD in the Frontend folder type in 'python -m streamlit run app.py'
    - Use the same links as before

Provides:
  -  Suggestions for different travel days to a location
  -  Recommendations to another location with lower crowd levels
  -  Translate suggestions and recommendations to user specified language
  -  Converts currency to user's origin
  -  A crowd forecast/historical window of the selected location
  -  Itineraries/filter options for fine tuning location options
  -  A month view forecast that encompasses the user's desired arrival date

Currently only two city's that being NewZealand Auckland & Ireland Dublin are available.

Data sources and API's:
  - Uses data from SerpAPI for future fligth paths and prices
  - Uses weather data from Open Meto Weather API for forecasting model
  - Uses OpenAI API for translating the suggestions and recommendations to specified language and currency exchanges
  - Support data manually created:
    - Used for location data of POI's
    - Used for Airport data for creating the flight data set  
  - Main data sets for NewZealand Auckland & Ireland Dublin government websites for crowd data
    - https://www.hotcity.co.nz/city-centre/results-and-statistics/pedestrian-counts
    - https://data.smartdublin.ie/dataset/dublin-city-centre-footfall-counters
    - All data sets here have similar structure to them, any future data will need same or similar structure to them
