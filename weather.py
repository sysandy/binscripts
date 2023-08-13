#!/usr/bin/python3
# vim set noexpandtab copyindent preserveindent softtabstop=0 shiftwidth=4 tabstop=4
##############################################################################
# Parses current observations at climo station from nws api and returns
# values delimited by ',' to be used as input for other scripts
# Andy Malato
# June 2023
##############################################################################
import sys,os,argparse
import requests
import json
import datetime 
import pytz

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
# 
#############################################################################
def clean_timestamp(utc_timestamp_str):
	utc_timestamp = datetime.datetime.strptime(utc_timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
	# Get localtime
	#local_timezone = pytz.timezone(pytz.country_timezones["US"][0])		
	local_timezone = datetime.datetime.now(pytz.timezone('UTC')).astimezone().tzinfo
	local_timestamp = utc_timestamp.astimezone(local_timezone)
	local_timestamp_str = local_timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")

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
			unit = 'F'
		else:
			unit = 'C'
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
# Get WX Station Information -- returns ID and Name
#############################################################################
def get_wx_station_info(station_url):
	
	station_data = urlreq(station_url)
	# Get Station Specific Data
	stationID = station_data["properties"]["stationIdentifier"]
	stationName = station_data["properties"]["name"]

	return(stationID, stationName)

#############################################################################
# Print Weather Data to screen based on options
#############################################################################
def display_weather_data(station_id, options):
	
	weather_display_list = []

	if (options['display_metric']):
		metricflag = True
	else:
		metricflag = False

	api_url = 'https://api.weather.gov'
	# Get Station Information
	station_url = '{}/stations/{}' . format(api_url, station_id)
	stationID,stationName = get_wx_station_info(station_url)
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

    ####################################################################
    # Display Weather Station Header Information
    ####################################################################
	if (options['display_headers']):
		current_timestamp = clean_timestamp(current_timestamp)
		print ("=" * 60)	
		print ("Station: {:<10}{}" . format(stationID, stationName))
		print ("Timestamp: {}" . format(current_timestamp))
		print ("=" * 60)	
	# Display values based on options
    ####################################################################
    # Display Weather Conditions
    ####################################################################
	if (options['display_weather']):
		current_weather = data["properties"]["textDescription"]
		#title = "Current Weather: "
		title = titles_dict['weather']
		weather_display_format = "{}{}" . format(title,current_weather)
		weather_display_list.append(weather_display_format)
		#print('{} {}' . format(title,current_weather))

    ####################################################################
    # Display Temperature
    ####################################################################
	if (options['display_temp']):
		current_temp = data["properties"]["temperature"]["value"]
		current_temp,unit=calc_temp(current_temp,metricflag)
		title = titles_dict['temperature']
		temp_display_format = "{}{}{}" . format(title,current_temp,unit)
		weather_display_list.append(temp_display_format)
		#print('{} {}{}' . format(title,current_temp,unit))

    ####################################################################
    # Display Humidity
    ####################################################################
	if (options['display_humidity']):
		current_humidity = data["properties"]["relativeHumidity"]["value"]
		if current_humidity is not None:
			current_humidity = round(current_humidity)
			unit = '%'
		#title = "Current Humidity: "
		title = titles_dict['humidity']
		humidity_display_format = "{}{}{}" . format(title,current_humidity,unit)
		weather_display_list.append(humidity_display_format)
		#print ('{} {}{}' . format(title,current_humidity,unit))

    ####################################################################
    # Display dewpoint
    ####################################################################
	if (options['display_dewpoint']):
		current_dewpoint = data["properties"]["dewpoint"]["value"]
		current_dewpoint,unit = calc_temp(current_dewpoint,metricflag)
		#title = "Current Dewpoint: "
		title = titles_dict['dewpoint']
		dewpoint_display_format = "{}{}{}" . format(title,current_dewpoint,unit)
		weather_display_list.append(dewpoint_display_format)
		#print('{} {}{}' . format(title,current_dewpoint,unit))

    ####################################################################
    # Display Barametric Pressure
    ####################################################################
	if (options['display_pressure']):
		current_pressure = data["properties"]["barometricPressure"]["value"]
		#title = "Current Pressure: "
		title = titles_dict['pressure']
		current_pressure = p_to_i(current_pressure)
		pressure_display_format = "{}{}" . format(title,current_pressure,unit)
		weather_display_list.append(pressure_display_format)
		#print ('{} {}' . format(title,current_pressure,unit))

    ####################################################################
    # Display Windchill 
    ####################################################################
	if (options['display_windchill']):
		current_windchill = data["properties"]["windChill"]["value"]
		current_windchill,unit = calc_temp(current_windchill,metricflag)
		#title = "Current Windchill: "
		title = titles_dict['windchill']
		windchill_display_format = "{}{}{}" . format(title,current_windchill,unit)
		weather_display_list.append(windchill_display_format)
		#print('{} {}{}' . format(title,current_windchill,unit))

    ####################################################################
    # Display Heat Index
    ####################################################################
	if (options['display_heatindex']):
		current_heatindex = data["properties"]["heatIndex"]["value"]
		current_heatindex,unit = calc_temp(current_heatindex,metricflag)
		#title = "Current Heatindex: "
		title = titles_dict['heatindex']
		heatindex_display_format = "{}{}{}" . format(title,current_heatindex,unit)
		weather_display_list.append(heatindex_display_format)
		#print('{} {}{}' . format(title,current_heatindex,unit))
	
    ####################################################################
    # Display Wind
    ####################################################################
	if (options['display_windspeed']):
		current_wind_speed = data["properties"]["windSpeed"]["value"]
		current_wind_speed,unit = calc_wind(current_wind_speed,metricflag)
		if current_wind_speed == 0:
			current_wind_speed = "Calm"
			unit = ''
		#title = "Current Wind: "
		title = titles_dict['wind']
		wind_display_format = "{}{}{}" . format(title,current_wind_speed,unit)
		weather_display_list.append(wind_display_format)
		#print('{} {}{}' . format(title,current_wind_speed,unit))

    ####################################################################
    # Display Wind Gust
    ####################################################################
	if (options['display_windgust']):
		current_wind_gust = data["properties"]["windGust"]["value"]
		current_wind_gust,unit = calc_wind(current_wind_gust,metricflag)
		#title = "Current Wind Gust: "
		title = titles_dict['windgust']
		windgust_display_format = "{}{}{}" . format(title,current_wind_gust,unit)
		weather_display_list.append(windgust_display_format)
		#print('{} {}{}' . format(title,current_wind_gust,unit))

    ####################################################################
    # Display Wind Direction
    ####################################################################
	if (options['display_winddirection']):
		current_wind_direction = data["properties"]["windDirection"]["value"]
		#title = "Current Wind Direction: "
		title = titles_dict['winddir']
		current_wind_direction = angle2compass(current_wind_direction)
		if current_wind_direction == 0:
			current_wind_direction = 'N/A'
		wind_direction_display_format = "{}{}" . format(title,current_wind_direction)
		weather_display_list.append(wind_direction_display_format)
		#print ('{} {}' . format(title,current_wind_direction))

    # return list of data to caller
	return(weather_display_list)
#############################################################################
# main() 
#############################################################################
ME=sys.argv[0]
ME=os.path.basename(ME)

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
parser.add_argument("--script", help="Print all data formated on a single line for parsing by external script", action="store_true")
parser.add_argument("--metric", help="Print all data in metric units", action="store_true")
parser.add_argument("--valuesonly", help="Display on data values, no titles", action="store_true")
parser.add_argument("--noheaders", help="Don't display header with station info", action="store_true")
parser.add_argument("--allvalues", help="Dislay all data values", action="store_true")

args = parser.parse_args()


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


display_options = { 'display_weather':display_weather, 'display_temp':display_temp, 'display_humidity':display_humidity, 'display_windchill':display_windchill, 
                    'display_heatindex':display_heatindex, 'display_dewpoint': display_dewpoint, 'display_winddirection':display_winddirection, 'display_windspeed':display_windspeed,
			        'display_windgust':display_windgust, 'display_pressure':display_pressure, 'display_metric':display_metric, 'display_notitles':display_notitles, 'display_headers':display_headers}

station_id = args.stationID

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
