import xml.etree.ElementTree as ET
from xml.dom import minidom
from shutil import copyfile
from urllib.parse import unquote
from tcx2gpx.tcx2gpx import TCX2GPX
import pandas as pd
import gpxpy
import os
import datetime
from geopy import distance
from math import sqrt, floor
#import numpy as np
import haversine
import dateutil.parser

def getTextFromXmlNodeList(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def getFilename(node):
    return unquote(getTextFromXmlNodeList(node.getElementsByTagName("name")[0].childNodes))

def formatDuration(totalSeconds):
    days = floor(totalSeconds/SECONDS_PER_DAY)
    remainingTime = totalSeconds - (days * SECONDS_PER_DAY)
    hours = floor(remainingTime/SECONDS_PER_HOUR)
    remainingTime = remainingTime - (hours * SECONDS_PER_HOUR)
    minutes = floor(remainingTime/SECONDS_PER_MINUTE)
    seconds = remainingTime - (minutes * SECONDS_PER_MINUTE)
    result = ""
    if days > 0:
        result = f"{days} days"
    if hours > 0:
        if result:
            result = result + ", "
        result = result + f"{hours} hours"
    if minutes > 0:
        if result:
            result = result + ", "
        result = result + f"{minutes} minutes"
    if result:
        result = result + " and "
    result += f"{seconds} seconds"
    return result

SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR 
SECONDS_PER_DAY = SECONDS_PER_HOUR * HOURS_PER_DAY

totalDistance = 0
longestDistance = 0
shortestDistance = 10000 # not huge, but I know there's shorter
totalTime = 0
longestDuration = 0
shortestDuration = SECONDS_PER_DAY
fastestSpeed = 0
slowestSpeed = 13 # meters per second
oldest = datetime.date(3000,12,31)
months = {}

# xstate.xml schema
# <xml>
# <file><name>file name 0</name><other></other></file>
# </xml>
xstate = minidom.parse('./public/xstate.xml')
files = xstate.getElementsByTagName("file")
for file in files:
    name = getFilename(file)
    if name.endswith(".gpx"):
        # gpx = minidom.parse(os.path.join('./public/runs', name))
        with open(os.path.join('./public/runs', name), 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)        
    elif name.endswith(".tcx"):
        gps_object = TCX2GPX(tcx_path=os.path.join('./public/runs', name))
        gps_object.read_tcx()
        gps_object.extract_track_points()
        gps_object.create_gpx()
        # gpx = minidom.parseString(gps_object.gpx.to_xml())
        gpx = gps_object.gpx
    else:
        raise ValueError('unexpected file extension for %r' % name)

    #print(f'{name} - tracks: {len(gpx.tracks)}, segments: {len(gpx.tracks[0].segments)}, points: {len(gpx.tracks[0].segments[0].points)}')

    data = gpx.tracks[0].segments[0].points
    #df = pd.DataFrame(columns=['lon', 'lat', 'alt', 'time'])
    #for point in data:
    #    df = df.append({'lon': point.longitude, 'lat' : point.latitude, 'alt' : point.elevation, 'time' : point.time}, ignore_index=True)
    #print(df)

    # Compute distance and time
    # See https://towardsdatascience.com/how-tracking-apps-analyse-your-gps-data-a-hands-on-tutorial-in-python-756d4db6715d
    alt_dif = [0]
    time_dif = [0]
    dist_vin = [0]
    dist_hav = [0]
    dist_vin_no_alt = [0]
    dist_hav_no_alt = [0]
    dist_dif_hav_2d = [0]
    dist_dif_vin_2d = [0]
    haveTime = True
    haveAlt = True
    for index in range(len(data)):
        if index == 0:
            minLat = data[index].latitude
            maxLat = minLat
            minLng = data[index].longitude
            maxLng = minLng
            continue

        start = data[index-1]
        stop = data[index]

        if stop.latitude < minLat:
            minLat = stop.latitude
        if stop.latitude > maxLat:
            maxLat = stop.latitude
        if stop.longitude < minLng:
            minLng = stop.longitude
        if stop.longitude > maxLng:
            maxLng = stop.longitude
        
        #distance_vin_2d = distance.vincenty((start.latitude, start.longitude), (stop.latitude, stop.longitude)).m
        distance_vin_2d = distance.distance((start.latitude, start.longitude), (stop.latitude, stop.longitude)).m
        dist_dif_vin_2d.append(distance_vin_2d)
        distance_hav_2d = haversine.haversine((start.latitude, start.longitude), (stop.latitude, stop.longitude))*1000
        dist_dif_hav_2d.append(distance_hav_2d)
        dist_vin_no_alt.append(dist_vin_no_alt[-1] + distance_vin_2d)
        dist_hav_no_alt.append(dist_hav_no_alt[-1] + distance_hav_2d)
        if pd.isna(start.elevation) or pd.isna(stop.elevation):
            haveAlt = False
        if haveAlt:
            alt_d = start.elevation - stop.elevation
            alt_dif.append(alt_d)
            distance_vin_3d = sqrt(distance_vin_2d**2 + (alt_d)**2)
            distance_hav_3d = sqrt(distance_hav_2d**2 + (alt_d)**2)
        if pd.isna(start.time) or pd.isna(stop.time):
            haveTime = False
        if haveTime:
            time_delta = (stop.time - start.time).total_seconds()
        time_dif.append(time_delta)
        dist_vin.append(dist_vin[-1] + distance_vin_3d)
        dist_hav.append(dist_hav[-1] + distance_hav_3d)

    # Add computed data to data frame
    #df['dis_vin_2d'] = dist_vin_no_alt 
    #df['dist_hav_2d'] = dist_hav_no_alt
    #df['dis_vin_3d'] = dist_vin
    #df['dis_hav_3d'] = dist_hav
    #if haveAlt:
    #    df['alt_dif'] = alt_dif
    #if haveTime:
    #    df['time_dif'] = time_dif
    #df['dis_dif_hav_2d'] = dist_dif_hav_2d
    #df['dis_dif_vin_2d'] = dist_dif_vin_2d        

    #print('Vincenty 2D : ', dist_vin_no_alt[-1])
    #print('Haversine 2D : ', dist_hav_no_alt[-1])
    #print('Vincenty 3D : ', dist_vin[-1])
    #print('Haversine 3D : ', dist_hav[-1])
    #print('Total Time : ', floor(sum(time_dif)/60),' min ', int(sum(time_dif)%60),' sec ')

    # Of the 4 distance estimates, find the min and max to use for various stats
    minDistCalc = dist_vin_no_alt[-1]
    maxDistCalc = dist_vin_no_alt[-1]
    if dist_hav_no_alt[-1] < minDistCalc:
        minDistCalc = dist_hav_no_alt[-1]
    if dist_hav_no_alt[-1] > maxDistCalc:
        maxDistCalc = dist_hav_no_alt[-1]
    if haveAlt:
        if dist_hav[-1] < minDistCalc:
            minDistCalc = dist_hav[-1]
        if dist_hav[-1] > maxDistCalc:
            maxDistCalc = dist_hav[-1]

    totalDistance = totalDistance + maxDistCalc
    if maxDistCalc > longestDistance:
        longestDistance = maxDistCalc
        longestDistanceRun = file
    if minDistCalc < shortestDistance:
        shortestDistance = minDistCalc
        shortestDistanceRun = file
    if haveTime:
        runTime = sum(time_dif)
    else:
        runTime = 0
    if haveTime:
        totalTime = totalTime + runTime 
        if runTime > longestDuration:
            longestDuration = runTime
            longestDurationRun = file
        if runTime < shortestDuration:
            shortestDuration = runTime
            shortestDurationRun = file
        fastSpeedCalc = minDistCalc / runTime
        if fastSpeedCalc > fastestSpeed:
            fastestSpeed = fastSpeedCalc
            fastestSpeedRun = file
        slowSpeedCalc = maxDistCalc / runTime
        if slowSpeedCalc < slowestSpeed:
            slowestSpeed = slowSpeedCalc
            slowestSpeedRun = file
    if haveTime:            
        date = data[0].time.date()
    else:
        xml = minidom.parse(os.path.join('./public/runs', name))        
        dateString = getTextFromXmlNodeList(xml.getElementsByTagName("time")[0].childNodes)
        data = dateutil.parser.parse(dateString).date()
        # gpx.has_elevations and gpx.has_times could have been used instead of my haveTime and haveAlt
    if date < oldest:
        oldest = date
        oldestRun = file
    month = date.strftime("%y %m")
    if month in months:
        months[month]["distance"] = months[month]["distance"] + maxDistCalc
        months[month]["time"] = months[month]["time"] + runTime
        months[month]["runs"] = months[month]["runs"] + 1
    else:
        months[month] = {"distance":maxDistCalc, "time":runTime, "runs":1}

    # Log the detail data for this run
    distanceEstimate = (maxDistCalc + minDistCalc) / 2
    if runTime:
        timeString = round(runTime/3600, 2)
    else:
        timeString = '?'
    centerLat = (minLat + maxLat) / 2
    centerLng = (minLng + maxLng) / 2
    print(f'<tr>' + \
          f'<td>{date.strftime("%B %d, %Y")}</td>' + \
          f'<td>{round(distanceEstimate/1000,1)} km ({round(distanceEstimate * 0.000621371,1)} miles)</td>' + \
          f'<td>{timeString} hours</td>' + \
          f'<td><a href="onerun.html?run={getFilename(file)}&lat={centerLat}&lng={centerLng}&zoom=11">map</a></td>' + \
          # f'<td>{round(maxLat-minLat,2)}</td><td>{round(maxLng-minLng,2)}</td>' + \
          f'</tr>')

#Report
print(f'{files.length} runs')
print(f"Total distance: {totalDistance/1000.0} km")
print(f"Total time: {formatDuration(totalTime)}")
print(f"First run {oldest} = {getFilename(oldestRun)}")
print(f"Longest distance single run {longestDistance/1000.0} km - {getFilename(longestDistanceRun)}")
print(f"Shortest distance single run {shortestDistance/1000.0} km - {getFilename(shortestDistanceRun)}")
print(f"Longest duration single run {formatDuration(longestDuration)} - {getFilename(longestDurationRun)}")
print(f"Shortest duration single run {formatDuration(shortestDuration)} - {getFilename(shortestDurationRun)}")
print(f"Fastest run {fastestSpeed * 2.23694} mph -  {getFilename(fastestSpeedRun)}")
print(f"Slowest run {slowestSpeed * 2.23694} mph -  {getFilename(slowestSpeedRun)}")
print("By month")
for month in months:
    print(f'{month} {months[month]["runs"]} runs distance {months[month]["distance"]/1000.0} km time: {formatDuration(months[month]["time"])}')
print("By month in hours")
for month in months:
    print(f'{month} {months[month]["runs"]} runs distance {months[month]["distance"]/1000.0} km time: {months[month]["time"]/SECONDS_PER_HOUR} hours')

# Duplicates
# <file><name>RK_gpx%20_2012-07-21_1122.gpx</name><aabb>[[47.580197,-122.407966],[47.595260,-122.382229]]</aabb><line>[[47.580197,-122.407966],[47.593204,-122.382234]]</line></file>
# <file><name>CardioTrainer_2012-08-01T15_15_25Z.gpx</name><aabb>[[47.577186,-122.148265],[47.593037,-122.119193]]</aabb><line>[[47.593037,-122.148063],[47.579663,-122.119501]]</line></file>
# <file><name>CardioTrainer_2012-08-04T17_29_49Z.gpx</name><aabb>[[47.571028,-122.382040],[47.599485,-122.330758]]</aabb><line>[[47.591117,-122.382040],[47.592629,-122.330758]]</line></file>
# <file><name>CardioTrainer_2012-07-21T18_20_22Z.gpx</name><aabb>[[47.580206,-122.407967],[47.595260,-122.382222]]</aabb><line>[[47.580230,-122.407967],[47.593222,-122.382246]]</line></file>
# <file><name>CardioTrainer_2012-08-15T15_40_12Z.gpx</name><aabb>[[47.574717,-122.168727],[47.581165,-122.139345]]</aabb><line>[[47.580632,-122.168727],[47.576092,-122.139345]]</line></file>
# <file><name>CardioTrainer_2012-08-18T16_47_20Z.gpx</name><aabb>[[47.589450,-122.326769],[47.598607,-122.247746]]</aabb><line>[[47.596980,-122.326769],[47.591156,-122.247746]]</line></file>
# <file><name>CardioTrainer_2012-08-22T14_41_15Z.gpx</name><aabb>[[47.578333,-122.248947],[47.592517,-122.195022]]</aabb><line>[[47.590532,-122.248947],[47.580414,-122.195022]]</line></file>
# <file><name>RK_gpx%20_2012-08-27_0812.gpx</name><aabb>[[47.569887,-122.136267],[47.578330,-122.107629]]</aabb><line>[[47.569887,-122.107629],[47.577439,-122.136267]]</line></file>
