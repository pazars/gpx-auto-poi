import overpass
import pprint

api = overpass.API()

bbox = (36.77799, -4.3909, 37.13245, -3.69876)

query = f"""(node["amenity"="drinking_water"]{bbox};way["amenity"="drinking_water"]{bbox};relation["amenity"="drinking_water"]{bbox};)"""

response = api.get(query)

pprint.pprint(response["features"])
