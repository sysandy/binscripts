#!/usr/bin/python
##############################################################################
# Parses current observations at climo station from nws api and returns
# values delimited by ',' to be used as input for other scripts
# Andy Malato
# June 2023
##############################################################################
import sys
import urllib.request
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
import os

#############################################################################
# 
#############################################################################
def get_station_data(url):

	try:
        	urldata =  urllib.request.urlopen(url)
	except HTTPError:
        	sys.exit ("Failed to fetch station data -- possible invalid station_id specified?")

	data = json.load(urldata)	

	return(data)

#############################################################################
# 
#############################################################################
def c_to_f(temp):
	# Convert C to F
	unit = 'F'
	if temp is not None:
		temp = (temp * 1.8000) + 32
		temp = round(temp)
		temp = '{}{}' . format(temp, unit)
	return(temp)

#############################################################################
# Convert Pascals to Inches of Mercury
#############################################################################
def p_to_i(pa):
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

        sector = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]

        index = direction%360
        index = round(index / 22.5)
        compassdir = sector[index]

        return(compassdir)

#############################################################################
# main() 
#############################################################################
ME=sys.argv[0]
ME=os.path.basename(ME)

# Get arguments
if len(sys.argv) < 2:
	print ("Usage: {} station_id!" . format(ME))
	sys.exit(1)

# Define location URL based on lat and lon coordinates
# https://weather-gov.github.io/api/general-faqs
#station_id = 'KMMU'
station_id = sys.argv[1]
url = 'https://api.weather.gov/stations/{}/observations/latest' . format(station_id)
data = get_station_data(url)

#print (data)

current_timestamp = data["properties"]["timestamp"]
current_weather = data["properties"]["textDescription"]
current_temp = data["properties"]["temperature"]["value"]
current_humidity = data["properties"]["relativeHumidity"]["value"]
current_windchill = data["properties"]["windChill"]["value"]
current_heatindex = data["properties"]["heatIndex"]["value"]
current_dewpoint = data["properties"]["dewpoint"]["value"]
current_wind_direction = data["properties"]["windDirection"]["value"]
current_wind_speed = data["properties"]["windSpeed"]["value"]
current_wind_gust = data["properties"]["windGust"]["value"]
current_pressure = data["properties"]["barometricPressure"]["value"]

# convert temp to F
#current_temp = (current_temp * 1.8000) + 32
current_temp = c_to_f(current_temp)
# now round to nearest integer value
#current_temp = round(current_temp)
# Dewpoint conversion
current_dewpoint = c_to_f(current_dewpoint)
# round humidity
current_humidity = round(current_humidity)
# Wind Chill
current_windchill = c_to_f(current_windchill)
# Heat Index
current_heatindex = c_to_f(current_heatindex)
# Barametric Conversion
current_pressure = p_to_i(current_pressure)
# Wind Speed
current_wind_speed = k_to_m(current_wind_speed)
# Wind Gust
current_wind_guest = k_to_m(current_wind_gust)
# Wind Direction
current_wind_direction = angle2compass(current_wind_direction)

# Nicely format output 
print ("Current Weather: {}" . format(current_weather))
print ("Current Temperature: {}" . format(current_temp))
print ("Current Humidity: {}%" . format(current_humidity))
print ("Current Windchill: {}" . format(current_windchill))
print ("Current Heatindex: {}" . format(current_heatindex))
print ("Current Dewpoint: {}" . format(current_dewpoint))
print ("Current Wind Dir: {}" . format(current_wind_direction))
print ("Current Wind Speed: {} " . format(current_wind_speed))
print ("Current Wind Gust: {} ". format(current_wind_gust))
print ("Current Pressure: {}\n" . format(current_pressure))
print ("Last Updated: {}" . format(current_timestamp))
