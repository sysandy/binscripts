#!/usr/bin/python3
# vim set noexpandtab copyindent preserveindent softtabstop=0 shiftwidth=4 tabstop=4
##############################################################################
# Parses current observations at climo station from nws api and returns
# values delimited by ',' to be used as input for other scripts
# Andy Malato
# June 2023
# Updated May 31 2024 (Almost a year from initial code)
#   Removed dependacy on pytz and also added icon from seperated weather for script
#   output.  Additional cleanup of unneeded comments in code
# Updated May 11 2025
#   Fixed bug with sunrise/sunset times that preventing "Night" Icons from
#   Displaying during the day.
# Updated June 12 2025
#   Added --forecast option to display forecast for given stationID
##############################################################################
import sys,os,argparse
import requests
import json
import datetime 
from datetime import datetime as dt
import dateutil.parser as dp
import time
import zoneinfo
import ephem
import shutil

#############################################################################
# 
#############################################################################
def urlreq(api_endpoint, method='get', headers=None, payload=None):
        if method == "post":
            if headers == None:
                response = requests.post(api_endpoint, json=payload)
            elif payload == None:
                response = requests.post(api_endpoint, headers=headers)
            else:
                response = requests.post(api_endpoint, json=payload, headers=headers)

        if method == "get":
                headers = {"Content-Type": "application/json", "User-Agent": "weather.py, weather_py@malato.org"}
                response = requests.get(api_endpoint, headers=headers)
        # Check various status return codes
        if response.status_code == 401:
                print ("Authorization denied -- Did our token expire ?")
                sys.exit(1)
        elif response.status_code == 422:
                print ("Unable to process request -- bad secret ?")
                sys.exit(1)
        elif response.status_code == 204:
                # this means no content success which is what gets returned after some put requests
                # We just return here
                return()
        elif response.status_code == 202:
                print ("The request has been accepted for processing")
        elif response.status_code != 200:
                print ("Unable to process request, an error occured: [{}]" . format(response.status_code))
                #sys.exit ("Failed to fetch station data -- possible invalid station_id specified?")
                sys.exit(1)
        if response.content == None:
                data = None
        else:
                responsemsg = response.content
                responsemsg = responsemsg.decode('utf-8')
                if responsemsg == "Request needs authentication!":
                        print("Cannot authenticate with TOKEN, headers passed were[{}]" . format(headers))
                        sys.exit(1)
                data = response.json()
        return(data)
#############################################################################
# Convert ISO 8601 UTC Timestamp to Local Time
#############################################################################
def clean_timestamp(utc_timestamp_str):
    iso8601_timestamp = "%Y-%m-%dT%H:%M:%S%z"
    utc_timestamp = dt.strptime(utc_timestamp_str, iso8601_timestamp)
    # Get localtime
    local_timezone = dt.now(zoneinfo.ZoneInfo('UTC')).astimezone().tzinfo
    local_timestamp = utc_timestamp.astimezone(local_timezone)
    local_timefmt = "%Y-%m-%d %H:%M:%S %Z"
    local_timefmt = "%m/%d/%Y %H:%M:%S %Z"
    local_timestamp_str = local_timestamp.strftime(local_timefmt)

    return(local_timestamp_str)

#############################################################################
# 
#############################################################################
def calc_temp(temp,metricflag=False):
    unit = ''
    if temp is not None:
        if not metricflag:
            # Convert C to F
            temp = (temp * 1.8000) + 32
            unit = '°F'
        else:
            unit = '°C'
        temp = round(temp)
    return(temp,unit)

#############################################################################
# 
#############################################################################
def calc_wind(wind,metricflag=False):
    unit = ''
    if wind is not None:
        if not metricflag:
            # Convert to mph
            wind = wind * 0.62137
            unit = 'mph'
        else:
            unit = 'km/h'
        wind = round(wind)
    return(wind,unit)

#############################################################################
# 
#############################################################################
def c_to_f(temp):
    # Convert C to F
    unit = 'F'
    if temp is not None:
        temp = (temp * 1.8000) + 32
        temp = round(temp)
    return(temp)

#############################################################################
# Convert Pascals to Inches of Mercury
#############################################################################
def p_to_i(pa):
    unit = ''
    i = None
    if pa is not None:
        unit = 'in'
        i = pa * 0.00029530
        i = round(i,2)
        i = '{}{}' . format(i, unit)
    unit = 'in'
    i = pa * 0.00029530
    i = round(i,2)
    i = '{}{}' . format(i, unit)
    return(i)

#############################################################################
# Convert km/h to mi/h
#############################################################################
def k_to_m(km):
    unit = 'mph'
    if km is not None:
        km = km * 0.62137
        km = round(km)
        km = '{}{}' . format(km, unit)
    return(km)

#############################################################################
# Convert Wind angle to compass direction
#############################################################################
def angle2compass(direction):
    if direction:
        sector = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
        index = direction%360
        index = round(index / 22.5)
        compassdir = sector[index]
        return(compassdir)
    else:
        return(direction)

#############################################################################
# Get Sunrise and Sunset times based on station coordinates
#############################################################################
def get_sunrise_sunset(latitude, longitude):
    date = datetime.date.today()
    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.long = str(longitude)
    observer.date = date

    sunrise = observer.next_rising(ephem.Sun())
    sunset = observer.next_setting(ephem.Sun())

    # return in localtime
    sunrise = ephem.Date(sunrise)
    sunrise = ephem.localtime(sunrise)
    sunrise = sunrise.strftime("%m/%d/%Y %H:%M:%S")

    sunset = ephem.Date(sunset)
    sunset = ephem.localtime(sunset)
    sunset = sunset.strftime("%m/%d/%Y %H:%M:%S")

    return (sunrise, sunset)

#############################################################################
# Get WX Station Information -- returns ID and Name
#############################################################################
def get_wx_station_info(station_id):
    
    # URL Stuff
    #api_url = 'https://api.weather.gov'
    api_url = API_URL
    station_url = '{}/stations/{}' . format(api_url, station_id)

    station_data = urlreq(station_url)
    # Get Station Specific Data
    stationID = station_data["properties"]["stationIdentifier"]
    stationName = station_data["properties"]["name"]
    # Get Lon and Lat coordinatents of station used for calc sunrise and sunset
    stationLON = station_data["geometry"]["coordinates"][0]
    stationLAT = station_data["geometry"]["coordinates"][1]

    return(stationID,stationName,stationLON,stationLAT)

#############################################################################
# Determine if we need to use NT icons or regular day icons 
#############################################################################
def get_icon_type(sunrise,sunset):
    iconset=()
    ct = dt.now()
    AMorPM = ct.strftime("%p")

    #print(sunrise)
    #print(sunset)

    # Get current time in unix format 
    current_time = round(time.time())
    sunset_time = dp.parse(sunset)
    sunset_time = round(sunset_time.timestamp())
    sunset_time = sunset_time + 86400 # need to adjust for one day
    sunrise_time = dp.parse(sunrise)
    sunrise_time = round(sunrise_time.timestamp())
    #print("Current Time: {}" . format(current_time))
    #print("Sunrise Time: {}" . format(sunrise_time))
    #print("Sunset Time: {}" . format(sunset_time))

    if AMorPM == "PM":
        #sunset_time = dp.parse(sunset)
        #sunset_time = round(sunset_time.timestamp())
        #if current_time - sunset_time > 0:
        if current_time > sunset_time:
            iconset = "night"
        else:
            iconset = "day"
    elif AMorPM == "AM":
        #sunrise_time = dp.parse(sunrise)
        #sunrise_time = round(sunrise_time.timestamp())

        #if current_time - sunrise_time < 0:
        if current_time < sunrise_time:
            iconset = "night"
        else:
            iconset = "day"

    return(iconset)

#############################################################################
# Define Dictionary to hold weather emoji for each weather type
#############################################################################
def get_wx_emoji(weather,sunrise,sunset):
    
    ##############################################################################
    # Define Sky Conditions that match specific emoji
    # Taken from:
    # https://symbl.cc/en/emoji/travel-and-places/sky-and-weather/
    ##############################################################################
    # These Icons differ based on whether it is "NIGHT" or "DAY" which is 
    # defined by whether the sun has risen or set.
    # Determine what iconset to use based on return value from function
    iconset=get_icon_type(sunrise,sunset)

    if iconset == "day":
        Clear = '🌞'
        Mostly_Clear = '☀️'
        Partly_Cloudy = '🌤️'
        Variable_Cloudy = '⛅'
        Mostly_Cloudy = '🌥️'
        Showers = '🌦️'

    elif iconset == "night":
        Clear = '🌛'
        Mostly_Clear = '🌛'
        Partly_Cloudy = '☾'
        Variable_Cloudy = '☁'
        Mostly_Cloudy = '☁️'
        Showers = '🌧️'

    # These icons can be used day or night
    Cloudy ='☁️'
    Rainy = '🌧️'
    Tstorms = '⛈️'
    ThunderStorm = '⚡'
    LightThunder = '🌩️'
    Snowy = '🌨️'
    Snow = '❄️'
    SnowRain = "❄"
    Ice = '🧊'
    Windy = '🌬️'
    Foggy = '🌫️'
    Coastal_Storm = '🌊'
    Haze = '🌫️'
    Smog = '🌁'
    Tornado = '🌪️'
    Hurricane = '🌀'

    # Define dictionary for weather conditions
    # Definitions from weather.gov/forecast-icons
    weather_conditions = {
        "fair": Clear,
        "clear": Clear,
        "fair with haze": Mostly_Clear,
        "clear with haze": Mostly_Clear,
        "fair and breezy": Clear,
        "clear breezy": Clear,
        "a few clouds": Partly_Cloudy,
        "a few clouds with haze": Variable_Cloudy,
        "a few clouds and breezy": Partly_Cloudy,
        "mostly clear": Mostly_Clear,
        "partly cloudy": Partly_Cloudy,
        "partly cloudy with hazy": Partly_Cloudy,
        "partly cloudy and breezy": Partly_Cloudy,
        "mostly cloudy": Mostly_Cloudy,
        "mostly cloudy with haze": Mostly_Cloudy,
        "mostly cloudy and breezy": Mostly_Cloudy,
        "fog/mist": Foggy,
        "shallow fog": Foggy,
        "cloudy": Cloudy,
        "overcast": Cloudy,
        "overcast with hazy": Haze,
        "overcast and breezy": Cloudy,
        "light rain": Rainy,
        "drizzle": Rainy,
        "light drizzle": Rainy,
        "heavy drizzle": Rainy,
        "light rain fog/mist": Rainy,
        "light rain and fog/mist": Rainy,
        "fog/mist and light rain": Rainy,
        "drizzle fog/mist": Rainy,
        "light drizzle fog/mist": Rainy,
        "light drizzle and fog/mist": Rainy,
        "heavy drizzle fog/mist": Rainy,
        "light rain fog": Rainy,
        "drizzle fog": Rainy,
        "light drizzle fog": Rainy,
        "heavy drizzle fog": Rainy,
        "rain": Rainy,
        "heavy rain": Rainy,
        "rain fog/mist": Rainy,
        "rain and fog/mist": Rainy,
        "heavy rain fog/mist": Rainy,
        "heavy rain and fog/mist": Rainy,
        "rain fog": Rainy,
        "heavy rain fog": Rainy,
        "thunderstorm in vicinity hail haze": ThunderStorm,
        "thunderstorm haze in vicinity hail": ThunderStorm,
        "thunderstorm light rain hail haze": ThunderStorm,
        "thunderstorm heavy rain hail haze": ThunderStorm,
        "thunderstorm hail fog": ThunderStorm,
        "thunderstorm light rain hail fog": ThunderStorm,
        "thunderstorm heavy rain hail fog": ThunderStorm,
        "thunderstorm small hail/snow pellets": ThunderStorm,
        "thunderstorm rain small hail/snow pellets": ThunderStorm,
        "light thunderstorm rain small hail/snow pellets": LightThunder,
        "heavy thunderstorm rain small hail/snow pellets": LightThunder,
        "thunderstorm": Tstorms,
        "thunderstorm rain": Tstorms,
        "light thunderstorm rain": LightThunder,
        "heavy thunderstorm rain": Tstorms,
        "thunderstorm rain fog/mist": LightThunder,
        "light thunderstorm rain fog/mist": LightThunder,
        "light thunderstorms and light rain and fog/mist": LightThunder,
        "heavy thunderstorm rain fog and windy": LightThunder,
        "heavy thunderstorm rain fog/mist": LightThunder,
        "heavy thunderstorms and heavy rain and fog/mist": LightThunder,
        "thunderstorm showers in vicinity": LightThunder,
        "light thunderstorm rain haze": LightThunder,
        "heavy thunderstorm rain haze": LightThunder,
        "thunderstorm fog": LightThunder,
        "light thunderstorm rain fog": LightThunder,
        "heavy thunderstorm rain fog": LightThunder,
        "thunderstorm light rain": LightThunder,
        "thunderstorm heavy rain": LightThunder,
        "thunderstorm rain fog/mist": LightThunder,
        "thunderstorm light rain fog/mist": LightThunder,
        "thunderstorm heavy rain fog/mist": LightThunder,
        "thunderstorm in vicinity fog/mist": ThunderStorm,
        "thunderstorm in vicinity fog": ThunderStorm,
        "thunderstorm showers in vicinity": Tstorms,
        "thunderstorm in vicinity haze": ThunderStorm,
        "thunderstorm haze in vicinity": ThunderStorm,
        "thunderstorm light rain haze":  LightThunder,
        "thunderstorm heavy rain haze": LightThunder,
        "thunderstorm fog": ThunderStorm,
        "thunderstorm light rain fog": Tstorms,
        "thunderstorm heavy rain fog": LightThunder,
        "thunderstorm hail": ThunderStorm,
        "light thunderstorm rain hail": ThunderStorm,
        "heavy thunderstorm rain hail": ThunderStorm,
        "thunderstorm rain hail fog/mist": LightThunder,
        "light thunderstorm rain hail fog/mist": LightThunder,
        "heavy thunderstorm rain hail fog/hail": LightThunder,
        "thunderstorm showers in vicinity hail": LightThunder,
        "light thunderstorm rain hail haze": LightThunder,
        "heavy thunderstorm rain hail haze": LightThunder,
        "thunderstorm hail fog": ThunderStorm,
        "light thunderstorm rain hail fog": LightThunder,
        "heavy thunderstorm rain hail fog":LightThunder,
        "heavy thunderstorms and heavy rain": LightThunder,
        "thunderstorms and rain": LightThunder,
        "thunderstorms and rain and fog/mist": LightThunder,
        "thunderstorm light rain hail":LightThunder,
        "thunderstorm heavy rain hail": Tstorms,
        "thunderstorm rain hail fog/mist": Tstorms,
        "thunderstorm light rain hail fog/mist": Tstorms,
        "thunderstorm heavy rain hail fog/mist": Tstorms,
        "thunderstorm in vicinity hail": ThunderStorm,
        "thunderstorm in vicinity hail haze": ThunderStorm,
        "thunderstorm haze in vicinity hail": ThunderStorm,
        "thunderstorm light rain hail haze": LightThunder,
        "thunderstorm heavy rain hail haze": LightThunder,
        "thunderstorm hail fog": ThunderStorm,
        "thunderstorm light rain hail fog": Tstorms,
        "thunderstorm heavy rain hail fog": Tstorms,
        "thunderstorm small hail/snow pellets": Tstorms,
        "thunderstorm rain small hail/snow pellets": Tstorms,
        "thunderstorms": Tstorms,
        "light thunderstorm rain small hail/snow pellets": Tstorms,
        "heavy thunderstorm rain small hail/snow pellets": Tstorms,
        "rain ice pellets": SnowRain,
        "light rain ice pellets": SnowRain,
        "heavy rain ice pellets": SnowRain,
        "Drizzle Ice Pellets": SnowRain,
        "light drizzle ice pellets": SnowRain,
        "heavy drizzle ice pellets": SnowRain,
        "ice pellets rain": SnowRain,
        "light ice pellets rain": SnowRain,
        "heavy ice pellets rain": SnowRain,
        "ice pellets drizzle": SnowRain,
        "light ice pellets drizzle": SnowRain,
        "heavy ice pellets drizzle": SnowRain,
        "freezing rain": SnowRain,
        "freezing drizzle": SnowRain,
        "light freezing rain": SnowRain,
        "light freezing drizzle": SnowRain,
        "heavy freezing rain": SnowRain,
        "heavy freezing drizzle": SnowRain,
        "freezing rain in vicinity": SnowRain,
        "freezing drizzle in vicinity": SnowRain,
        "freezing rain rain": SnowRain,
        "light freezing rain rain": SnowRain,
        "heavy freezing rain rain": SnowRain,
        "rain freezing rain": SnowRain,
        "light rain freezing rain": SnowRain,
        "heavy rain freezing rain": SnowRain,
        "freezing drizzle rain": SnowRain,
        "light freezing drizzle rain": SnowRain,
        "heavy freezing drizzle rain": SnowRain,
        "rain freezing drizzle": SnowRain,
        "light rain freezing drizzle": SnowRain,
        "heavy rain freezing drizzle": SnowRain,
        "freezing rain snow": SnowRain,
        "light freezing rain snow": SnowRain,
        "heavy freezing rain snow": SnowRain,
        "freezing drizzle snow": SnowRain,
        "light freezing drizzle snow": SnowRain,
        "heavy freezing drizzle snow": SnowRain,
        "snow freezing rain": SnowRain,
        "light snow freezing rain": SnowRain,
        "heavy snow freezing rain": SnowRain,
        "snow freezing drizzle": SnowRain,
        "light snow freezing drizzle": SnowRain,
        "heavy snow freezing drizzle": SnowRain,
        "ice pellets": Ice,
        "light ice pellets": Ice,
        "heavy ice pellets": Ice,
        "ice pellets in vicinity": Ice,
        "showers ice pellets": Ice,
        "thunderstorm ice pellets": Ice,
        "ice crystals": Ice,
        "hail": Ice,
        "small hail/snow pellets": Ice,
        "light small hail/snow pellets": Ice,
        "heavy small hail/snow pellets": Ice,
        "showers hail": Ice,
        "hail showers": Ice,
        "snow ice pellets": Ice,
        "rain snow": SnowRain,
        "light rain snow": SnowRain,
        "heavy rain snow": SnowRain,
        "snow rain": SnowRain,
        "light snow rain": SnowRain,
        "heavy snow rain": SnowRain,
        "drizzle snow": SnowRain,
        "light drizzle snow": SnowRain,
        "heavy drizzle snow": SnowRain,
        "snow drizzle": SnowRain,
        "light snow drizzle": SnowRain,
        "heavy drizzle snow": SnowRain,
        "snow": Snow,
        "light snow": Snow,
        "heavy snow": Snow,
        "snow showers": Snow,
        "light snow showers": Snow,
        "heavy snow showers": Snow,
        "showers snow": Snow,
        "light showers snow": Snow,
        "heavy showers snow": Snow,
        "snow fog/mist": Snow,
        "light snow fog/mist": Snow,
        "light snow and fog/mist": Snow,
        "heavy snow fog/mist": Snow,
        "snow showers fog/mist": Snow,
        "light snow showers fog/mist": Snow,
        "heavy snow showers fog/mist": Snow,
        "showers snow fog/mist": Snow,
        "light showers snow fog/mist": Snow,
        "heavy showers snow fog/mist": Snow,
        "snow fog": Snow,
        "light snow fog": Snow,
        "heavy snow fog": Snow,
        "snow showers fog": Snow,
        "light showers snow fog/mist": Snow,
        "heavy showers snow fog/mist": Snow,
        "snow fog": Snow,
        "light snow fog": Snow,
        "heavy snow fog": Snow,
        "snow showers fog": Snow,
        "light snow showers fOg": Snow,
        "heavy snow showers fog": Snow,
        "showers in vicinity snow": Snow,
        "snow showers in vicinity": Snow,
        "snow showers in vicinity fog/mist": Snow,
        "snow showers in vicinity fog": Snow,
        "low drifting snow": Snow,
        "blowing snow": Snow,
        "snow low drifting snow": Snow,
        "snow blowing snow": Snow,
        "light snow low drifting snow": Snow,
        "light snow blowing snow": Snow,
        "light snow blowing snow fog/mist": Snow,
        "heavy snow low drifting snow": Snow,
        "heavy snow blowing snow": Snow,
        "thunderstorm snow": Snow,
        "light thunderstorm snow": Snow,
        "heavy thunderstorm snow": Snow,
        "snow grains": Snow,
        "light snow grains": Snow,
        "heavy snow grains": Snow,
        "heavy blowing snow": Snow,
        "blowing snow in vicinity": Snow,
        "funnel cloud": Tornado,
        "funnel cloud in vicinity": Tornado,
        "tornado/water spout": Tornado,
        "tornado": Tornado,
        "hurricane warming": Hurricane,
        "hurricane watch": Hurricane,
        "tropical storm warning": Coastal_Storm,
        "tropical storm watch": Coastal_Storm,
        "tropical storm conditions presently exist w/hurricane warning in effect": Coastal_Storm,
        "windy": Windy,
        "breezy": Windy,
        "fair and windy": Windy,
        "a few clouds and windy": Windy,
        "partly cloudy and windy": Windy,
        "mostly cloudy and windy": Windy,
        "overcast and windy": Windy,
        "smoke": Smog,
        "haze": Haze,
        "hot": Mostly_Clear,
        "cold": Ice,
        "blizzard": Snow,
        "freezing fog": Foggy,
        "partial fog": Foggy,
        "patches of fog": Foggy,
        "fog in vicinity": Foggy,
        "freezing fog in vicinity": Foggy,
        "shallow fog in vincinity": Foggy,
        "partial fog in vincinity": Foggy,
        "patches of fog in vicinity": Foggy,
        "showers in vicinity fog": Foggy,
        "light freezing fog": Foggy,
        "heavy freezing fog": Foggy
    }

    # Return UNICODE value for emoji
    return(weather_conditions.get(weather.lower(), "❓"))
#############################################################################
# Print Weather Forecast to screen 
#############################################################################
def display_weather_forecast(station_id):

    # This function "prints" the forecast for given stationID.  It really should
    # just return a data structure but for now this does the job.
    
    stationID,stationName,stationLON,stationLAT = get_wx_station_info(station_id)

    # Get Station Forecast Information
    station_forecast_url = '{}/points/{},{}' . format(API_URL, stationLAT, stationLON)
    forecast_station_data = urlreq(station_forecast_url)

    #pretty_json = json.dumps(forecast_station_data, indent=4)
    #print (pretty_json)

    # This is the URL we parse for forecast data
    forecast_url = forecast_station_data["properties"]["forecast"]
    forecast_grid_data = urlreq(forecast_url)

    # Print Header
    header = 'Forecast Information for {}({})' . format(stationName, stationID)
    print(header)
    print('')
    # Print the Forecast 
    for period in forecast_grid_data["properties"]["periods"]:
        DashNumber = len(period['name'])
	# Get column width of terminal
        cwidth = shutil.get_terminal_size().columns
        PeriodName=period['name']
        centered_PeriodName = PeriodName.center(cwidth)
        seperator = "-" * DashNumber
        centered_seperator = seperator.center(cwidth)
        #print (period['name'])
        print (centered_PeriodName)
        print (centered_seperator)
        #print ("-" * DashNumber)
        print (period['detailedForecast'])
        print ("*" * cwidth)

    return()
    
#############################################################################
# Print Weather Data to screen based on options
#############################################################################
def display_weather_data(station_id, options):
    
    weather_display_list = []

    if (options['display_metric']):
        metricflag = True
    else:
        metricflag = False

    #api_url = 'https://api.weather.gov'
    api_url = API_URL
    # Get Station Information
    #station_url = '{}/stations/{}' . format(api_url, station_id)

    stationID,stationName,stationLON,stationLAT = get_wx_station_info(station_id)

    # Get Station Data Information
    station_data_url = '{}/stations/{}/observations/latest' . format(api_url, station_id)
    data = urlreq(station_data_url)

    # Values from station data
    current_timestamp = data["properties"]["timestamp"]

    # Create dictionary used for titles:
    titles_dict = {'weather':'Current Weather: ', 'temperature':'Current Temperature: ', 'humidity': 'Current Humidity: ',
                   'dewpoint':'Current Dewpoint: ', 'pressure':'Current Pressure: ', 'windchill':'Current windchill: ',
                   'heatindex':'Current Heatindex: ', 'wind':'Current Wind: ', 'windgust':'Current Wind Gust: ', 'winddir':'Current Wind Direction: ' 
                  }

    if (options['display_notitles']):
        # zero out all values in titles_dict
        for key in titles_dict:
            titles_dict[key] = ''

    # Get sunrise and sunset times of station for current date
    sunrise,sunset = get_sunrise_sunset(stationLAT,stationLON)

    ####################################################################
    # Display Weather Station Header Information
    ####################################################################
    if (options['display_headers']):
        current_timestamp = clean_timestamp(current_timestamp)
        print ("=" * 60)    
        print ("Station: {:<10}{}" . format(stationID, stationName))
        print ("Timestamp: {}" . format(current_timestamp))
        print ("Coordinates: LON[{}], LAT[{}]" . format(stationLON, stationLAT))
        print ("Sunrise: {}, Sunset: {}" . format(sunrise, sunset))
        print ("=" * 60)    
    # Display values based on options
    ####################################################################
    # Display Weather Conditions
    ####################################################################
    if (options['display_weather']):
        current_weather = data["properties"]["textDescription"]
        title = titles_dict['weather']
        if display_icon:
            weather_icon = get_wx_emoji(current_weather,sunrise,sunset)
            if not icononly:
                if scriptFlag:
                    weather_display_icon = "{}{}" . format(title,weather_icon)
                    weather_display_format = "{}{}" . format(title,current_weather)
                else:
                    weather_display_format = "{}{}{}" . format(title,current_weather,weather_icon)
            else:
                weather_display_format = "{}{}" . format(title,weather_icon)
        else:
             weather_display_format = "{}{}" . format(title,current_weather)

        weather_display_list.append(weather_display_format)
        if display_icon:
            if scriptFlag:
                if not icononly:
                    weather_display_list.append(weather_display_icon)
        
    ####################################################################
    # Display Temperature
    ####################################################################
    if (options['display_temp']):
        current_temp = data["properties"]["temperature"]["value"]
        current_temp,unit=calc_temp(current_temp,metricflag)
        title = titles_dict['temperature']
        temp_display_format = "{}{}{}" . format(title,current_temp,unit)
        weather_display_list.append(temp_display_format)

    ####################################################################
    # Display Humidity
    ####################################################################
    if (options['display_humidity']):
        current_humidity = data["properties"]["relativeHumidity"]["value"]
        if current_humidity is not None:
            current_humidity = round(current_humidity)
            unit = '%'
        title = titles_dict['humidity']
        humidity_display_format = "{}{}{}" . format(title,current_humidity,unit)
        weather_display_list.append(humidity_display_format)

    ####################################################################
    # Display dewpoint
    ####################################################################
    if (options['display_dewpoint']):
        current_dewpoint = data["properties"]["dewpoint"]["value"]
        current_dewpoint,unit = calc_temp(current_dewpoint,metricflag)
        title = titles_dict['dewpoint']
        dewpoint_display_format = "{}{}{}" . format(title,current_dewpoint,unit)
        weather_display_list.append(dewpoint_display_format)

    ####################################################################
    # Display Barametric Pressure
    ####################################################################
    if (options['display_pressure']):
        current_pressure = data["properties"]["barometricPressure"]["value"]
        title = titles_dict['pressure']
        current_pressure = p_to_i(current_pressure)
        pressure_display_format = "{}{}" . format(title,current_pressure,unit)
        weather_display_list.append(pressure_display_format)

    ####################################################################
    # Display Windchill 
    ####################################################################
    if (options['display_windchill']):
        current_windchill = data["properties"]["windChill"]["value"]
        current_windchill,unit = calc_temp(current_windchill,metricflag)
        title = titles_dict['windchill']
        windchill_display_format = "{}{}{}" . format(title,current_windchill,unit)
        weather_display_list.append(windchill_display_format)

    ####################################################################
    # Display Heat Index
    ####################################################################
    if (options['display_heatindex']):
        current_heatindex = data["properties"]["heatIndex"]["value"]
        current_heatindex,unit = calc_temp(current_heatindex,metricflag)
        title = titles_dict['heatindex']
        heatindex_display_format = "{}{}{}" . format(title,current_heatindex,unit)
        weather_display_list.append(heatindex_display_format)
    
    ####################################################################
    # Display Wind
    ####################################################################
    if (options['display_windspeed']):
        current_wind_speed = data["properties"]["windSpeed"]["value"]
        current_wind_speed,unit = calc_wind(current_wind_speed,metricflag)
        if current_wind_speed == 0:
            current_wind_speed = "Calm"
            unit = ''
        title = titles_dict['wind']
        wind_display_format = "{}{}{}" . format(title,current_wind_speed,unit)
        weather_display_list.append(wind_display_format)

    ####################################################################
    # Display Wind Gust
    ####################################################################
    if (options['display_windgust']):
        current_wind_gust = data["properties"]["windGust"]["value"]
        current_wind_gust,unit = calc_wind(current_wind_gust,metricflag)
        title = titles_dict['windgust']
        windgust_display_format = "{}{}{}" . format(title,current_wind_gust,unit)
        weather_display_list.append(windgust_display_format)

    ####################################################################
    # Display Wind Direction
    ####################################################################
    if (options['display_winddirection']):
        current_wind_direction = data["properties"]["windDirection"]["value"]
        title = titles_dict['winddir']
        current_wind_direction = angle2compass(current_wind_direction)
        if current_wind_direction == 0:
            current_wind_direction = 'N/A'
        wind_direction_display_format = "{}{}" . format(title,current_wind_direction)
        weather_display_list.append(wind_direction_display_format)

    # return list of data to caller
    return(weather_display_list)
#############################################################################
# main() 
#############################################################################
ME=sys.argv[0]
ME=os.path.basename(ME)
API_URL = 'https://api.weather.gov'

parser = argparse.ArgumentParser(usage='%(prog)s [options] StationID',description='Utlilty for printing weather conditions')
parser.add_argument("stationID", metavar="StationID", type=str, help="The name of the wx station ID to get condition from")
parser.add_argument("-t", "--temp", help="Print temparature for given stationID", action="store_true", default=False)
parser.add_argument("-H", "--humidity", help="Print humidity for given stationID", action="store_true", default=False)
parser.add_argument("-d", "--dewpoint", help="Print dewpoint for given stationID", action="store_true", default=False)
parser.add_argument("-w", "--weather", help="Print weather for given stationID", action="store_true", default=False)
parser.add_argument("-p", "--pressure", help="Print barametric pressure for given stationID", action="store_true", default=False)
parser.add_argument("-W", "--windchill", help="Print windchill for given stationID", action="store_true", default=False)
parser.add_argument("-i", "--heatindex", help="Print heatindex for given stationID", action="store_true", default=False)
parser.add_argument("-c", "--winddirection", help="Print wind direction for given stationID", action="store_true", default=False)
parser.add_argument("-g", "--windgust", help="Print wind gust for given stationID", action="store_true", default=False)
parser.add_argument("-s", "--windspeed", help="Print wind speed for given stationID", action="store_true", default=False)
parser.add_argument("--forecast", help="Print Forecast for given StationID", action="store_true", default=False)
parser.add_argument("--script", help="Print all data formated on a single line for parsing by external script", action="store_true")
parser.add_argument("--metric", help="Print all data in metric units", action="store_true")
parser.add_argument("--valuesonly", help="Display on data values, no titles", action="store_true")
parser.add_argument("--noheaders", help="Don't display header with station info", action="store_true")
parser.add_argument("--allvalues", help="Dislay all data values", action="store_true")
parser.add_argument("--icon", help="Display weather icon for weather value", action="store_true")
parser.add_argument("--icononly", help="only display icons for weather value", action="store_true")


# check for arguments passed
if len(sys.argv) == 1:
   parser.print_help()
   sys.exit(1)

args = parser.parse_args()

if args.forecast:
    display_forecast = True
else:
    display_forecast = False
# define options to pass to display_weather_data() based on command line options
if args.weather:
    display_weather = True
else:
    display_weather = False
if args.temp:
    display_temp = True
else:
    display_temp = False
if args.humidity:
    display_humidity = True
else:
    display_humidity = False
if args.windchill:
    display_windchill = True
else:
    display_windchill = False
if args.heatindex:
    display_heatindex = True
else:
    display_heatindex = False
if args.dewpoint:
    display_dewpoint = True
else:
    display_dewpoint = False
if args.winddirection:
    display_winddirection = True
else:
    display_winddirection = False
if args.windspeed:
    display_windspeed = True
else:
    display_windspeed = False
if args.windgust: 
    display_windgust = True
else:
    display_windgust = False
if args.pressure:
    display_pressure = True
else:
    display_pressure = False

if args.metric:
    display_metric = True
else:
    display_metric = False

if args.valuesonly or args.script:
    display_notitles = True
else:
    display_notitles = False

if args.noheaders or args.script:
    display_headers = False
else:
    display_headers = True

if args.script:
    scriptFlag = True
else:
    scriptFlag = False

if args.icon:
    display_icon = True
else:
    display_icon = False

if args.icononly:
    display_icon = True
    icononly = True
    display_headers = False
    display_notitles = True
else:
    icononly = False

display_options = { 'display_weather':display_weather, 'display_temp':display_temp, 'display_humidity':display_humidity, 'display_windchill':display_windchill, 
                    'display_heatindex':display_heatindex, 'display_dewpoint': display_dewpoint, 'display_winddirection':display_winddirection, 'display_windspeed':display_windspeed,
                    'display_windgust':display_windgust, 'display_pressure':display_pressure, 'display_metric':display_metric, 'display_notitles':display_notitles, 'display_headers':display_headers, 'display_icon':display_icon}


station_id = args.stationID

if display_forecast:
   weather_forecast_list = display_weather_forecast(station_id)
   sys.exit(0)

# Display all data values if --allvalues flag is set
if args.allvalues:
    for key in display_options:
        # we don't turn these flags on because they are not data related
        if key == "display_metric" or key == "display_notitles" or key == "display_headers":
            next
        else:
            display_options[key] = True

# Populate list with weather data
weather_display_list = display_weather_data(station_id, display_options)

if args.script:
    listsize = len(weather_display_list)
    counter=0
    for item in weather_display_list:
        if counter < listsize -1:
            print (item, end="|")
            counter = counter+1
        else:
            print (item)
else:
    for item in weather_display_list:
        print(item)

sys.exit()
