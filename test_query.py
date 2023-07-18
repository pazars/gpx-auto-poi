import overpass
import gpxpy
import pprint
import overpy

import numpy as np

from pathlib import Path
from OSMPythonTools.api import Api

gpx_path = Path("C:/Users/davis/OneDrive/Documents/gpx-auto-poi/test.gpx")

with open(gpx_path, "r") as gpx_file:
    gpx = gpxpy.parse(gpx_file)

lons = []
lats = []

for point in gpx.tracks[0].segments[0].points:
    lons += [point.longitude]
    lats += [point.latitude]

lats = np.array(lats)
lons = np.array(lons)

bbox = f"{np.min(lats), np.min(lons), np.max(lats), np.max(lons)}"

api = overpass.API()
# query = f"""(node["amenity"="drinking_water"]{bbox};way["amenity"="drinking_water"]{bbox};relation["amenity"="drinking_water"]{bbox};)"""
# way_query = f"""way(244704262)"""
fuel_query = f"""node["amenity"="fuel"]{bbox}"""
response = api.get(fuel_query)

# api2 = Api()
# response = api2.query("way/244704262")

# api3 = overpy.Overpass()
# response3 = api3.query("""way(244704262);(._;>;);out body;""")
# print((float(response3.ways[0].nodes[0].lat), float(response3.ways[0].nodes[0].lon)))

pprint.pprint(response)
# pprint.pprint(response["features"])
