import xml.etree.ElementTree as ET
from xml.dom import minidom
import urllib2
import os

# https://en.wikibooks.org/wiki/Algorithm_Implementation/Geometry/Convex_hull/Monotone_chain
def convex_hull(points):
    """Computes the convex hull of a set of 2D points.

    Input: an iterable sequence of (x, y) pairs representing the points.
    Output: a list of vertices of the convex hull in counter-clockwise order,
      starting from the vertex with the lexicographically smallest coordinates.
    Implements Andrew's monotone chain algorithm. O(n log n) complexity.
    """

    # Sort the points lexicographically (tuples are compared lexicographically).
    # Remove duplicates to detect the case we have just one unique point.
    points = sorted(set(points))

    # Boring case: no points or a single point, possibly repeated multiple times.
    if len(points) <= 1:
        return points

    # 2D cross product of OA and OB vectors, i.e. z-component of their 3D cross product.
    # Returns a positive value, if OAB makes a counter-clockwise turn,
    # negative for clockwise turn, and zero if the points are collinear.
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # Build lower hull 
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # Build upper hull
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Concatenation of the lower and upper hulls gives the convex hull.
    # Last point of each list is omitted because it is repeated at the beginning of the other list. 
    return lower[:-1] + upper[:-1]

 
tree = ET.parse('./allruns.xml')
root = tree.getroot()

for osroot, dirs, files in os.walk('./newruns'):
    for file in files:
        if file.startswith('.'):
            continue
        print(file)
        doc = minidom.parse(os.path.join(osroot,file))
        tcxFormat =  doc.getElementsByTagName('Trackpoint').length
        points = doc.getElementsByTagName('trkpt') + doc.getElementsByTagName('Trackpoint')
        minLat = 1000
        minLng = 1000
        maxLat = -1000
        maxLng = -1000
        pointArray = []
        for point in points:
            lat = 0
            lng = 0
            if tcxFormat:
                for node in point.getElementsByTagName('LatitudeDegrees'):
                    lat = float(node.firstChild.nodeValue) 
                for node in point.getElementsByTagName('LongitudeDegrees'):
                    lng = float(node.firstChild.nodeValue)
            else:
                lat = float(point.getAttribute("lat"))
                lng = float(point.getAttribute("lon"))
            if lat == 0 or lng == 0:
                continue
            pointArray.append((lat,lng))
            if  lat < minLat:
                minLat = lat
            if lat > maxLat:
                maxLat = lat
            if lng < minLng:
                minLng = lng
            if lng > maxLng:
                maxLng = lng
        hull = convex_hull(pointArray)
        maxDistanceSq = 0
        furthestPoints = []

        pointCount = len(hull)
        for i in range(pointCount):
            for j in range(pointCount):
                if i == j:
                    continue
                d0 = hull[i][0] - hull[j][0]
                d1 = hull[i][1] - hull[j][1]
                distanceSq = d0*d0 + d1*d1
                if distanceSq > maxDistanceSq:
                    maxDistanceSq = distanceSq
                    furthestPoints = [i,j]

        print("AABB: (%.2f,%.2f)-(%.2f,%.2f), furthest points: (%.2f,%.2f)-(%.2f,%.2f)" % (
            minLat, minLng, maxLat, maxLng, 
            hull[furthestPoints[0]][0], hull[furthestPoints[0]][1],
            hull[furthestPoints[1]][0], hull[furthestPoints[1]][1]))
        run = ET.SubElement(root, "file")
        ET.SubElement(run, "name").text = urllib2.quote(file)
        ET.SubElement(run, "aabb").text = "[[%f,%f],[%f,%f]]" % (minLat, minLng, maxLat, maxLng)
        ET.SubElement(run, "line").text = "[[%f,%f],[%f,%f]]" % (hull[furthestPoints[0]][0], hull[furthestPoints[0]][1], hull[furthestPoints[1]][0], hull[furthestPoints[1]][1])    
        
tree.write("newallruns.xml")
