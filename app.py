import numpy as np
import panel as pn

import gpxpy
import overpass
import geopy.distance
import pprint
import folium
import overpy
import copy
import param

from pathlib import Path

MIN_N_ROUTE_SPLITS = 10
DISTANCE_THRESHOLD_KM = 3


class MultipleSwitches(pn.widgets.base.CompositeWidget):
    num_switches = 5
    value = param.List(default=[False] * num_switches, item_type=bool)

    _composite_type = pn.Column

    def __init__(self, **params):
        # Water
        self._first_switch = pn.widgets.Switch()
        # Fuel stations
        self._second_switch = pn.widgets.Switch()
        # Convenience stores
        self._third_switch = pn.widgets.Switch()
        # RMK huts and shelters (Estonia)
        self._fourth_switch = pn.widgets.Switch()
        # Placeholder
        self._fifth_switch = pn.widgets.Switch()

        super().__init__(**params)

        self._composite[:] = [
            self._first_switch,
            self._second_switch,
            self._third_switch,
            self._fourth_switch,
            self._fifth_switch,
        ]

        self._sync_widgets()

    @param.depends("value", watch=True)
    def _sync_widgets(self):
        self._first_switch.value = self.value[0]
        self._second_switch.value = self.value[1]
        self._third_switch.value = self.value[2]
        self._fourth_switch.value = self.value[3]
        self._fifth_switch.value = self.value[4]

    @param.depends(
        "_first_switch.value",
        "_second_switch.value",
        "_third_switch.value",
        "_fourth_switch.value",
        "_fifth_switch.value",
        watch=True,
    )
    def _sync_params(self):
        self.value = [
            self._first_switch.value,
            self._second_switch.value,
            self._third_switch.value,
            self._fourth_switch.value,
            self._fifth_switch.value,
        ]


def get_bbox(gpx):
    lons = []
    lats = []

    for point in gpx.tracks[0].segments[0].points:
        lons += [point.longitude]
        lats += [point.latitude]

    return f"{min(lats), min(lons), max(lats), max(lons)}"


def get_num_splits(n):
    if n <= 0:
        return []
    divisors = [1, n]
    for div in range(1, int(n**0.5 + 1)):
        if n % div == 0:
            divisors.extend([n // div, div])
    unique_divs = np.array(list(set(divisors)))
    return int(np.where(unique_divs >= MIN_N_ROUTE_SPLITS, unique_divs, np.inf).min())


def find_closest_to_point(response, lat, lon):
    dists = []
    qlocs = []

    for feature in response["features"]:
        qlon, qlat = feature["geometry"]["coordinates"]
        # Distance between (#lat, lon)
        lon, lat = lons[len(lons) // 2], lats[len(lats) // 2]
        dists += [geopy.distance.distance((lat, lon), (qlat, qlon))]
        qlocs += [(qlat, qlon)]

    dists = np.array(dists)

    min_dist = np.min(dists)
    min_dist_idx = np.argmin(dists)
    min_lat, min_lon = qlocs[min_dist_idx]

    return (min_lat, min_lon, min_dist)


def closest_in_split(flat, flon, split_lats, split_lons):
    min_dist = DISTANCE_THRESHOLD_KM
    min_lat, min_lon = None, None
    # Check every third coordinate to make faster
    for n in range(0, len(split_lats), 3):
        lat, lon = split_lats[n], split_lons[n]
        dist = geopy.distance.distance((lat, lon), (flat, flon))
        if dist.kilometers < min_dist:
            min_dist = dist.kilometers
            min_lat, min_lon = lat, lon

    if min_lat:
        return (min_lat, min_lon, min_dist)
    return None


def _display_start_finish(route_map, gpx):
    course = gpx.tracks[0].segments[0]

    start_lat = course.points[0].latitude
    start_lon = course.points[0].longitude

    fin_lat = course.points[-1].latitude
    fin_lon = course.points[-1].longitude

    # Start position marker
    folium.Marker(
        [start_lat, start_lon],
        icon=folium.Icon(icon="play", prefix="fa", color="green"),
    ).add_to(route_map)

    # Finish position marker
    folium.Marker(
        [fin_lat, fin_lon],
        icon=folium.Icon(icon="flag-checkered", prefix="fa", color="red"),
    ).add_to(route_map)


def display_gpx_on_map(gpx_input):
    # Default map
    route_map = folium.Map(
        location=[56.945695, 24.120704],
        zoom_start=13,
        # tiles="https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}{r}.png",
        # attr='<a href="https://stadiamaps.com/">Stadia Maps</a',
    )

    if not gpx_input:
        return route_map

    # Parse input .gpx file
    gpx = gpxpy.parse(gpx_input)

    # Display gpx track on map
    coordinates = [
        (point.latitude, point.longitude) for point in gpx.tracks[0].segments[0].points
    ]

    folium.PolyLine(coordinates, weight=6).add_to(route_map)

    # Center the map on the track
    route_map.fit_bounds(route_map.get_bounds(), padding=(30, 30))

    # Display start and finish location markers
    _display_start_finish(route_map, gpx)

    return route_map


def display_pois_on_map(query, icon_key, route_map, gpx):
    pois = _get_poi_info(query, gpx)

    for poi in pois:
        poi_lat, poi_lon = poi["feature_coords"]

        # For some reason the icons can't be re-used
        # Need to create again every single time
        # Icons: https://fontawesome.com/icons?d=gallery
        if icon_key == "water":
            icon = folium.Icon(icon="faucet-drip", prefix="fa", color="blue")
        elif icon_key == "fuel":
            icon = folium.Icon(icon="gas-pump", prefix="fa", color="orange")
        elif icon_key == "store":
            icon = folium.Icon(icon="cart-shopping", prefix="fa", color="beige")
        elif icon_key == "rmk":
            icon = folium.Icon(icon="person-shelter", prefix="fa", color="green")
        else:
            icon = None

        folium.Marker(
            [poi_lat, poi_lon],
            icon=icon,
        ).add_to(route_map)

    return route_map


def _get_poi_info(query, gpx):
    # Split route into sections and get gpx bounding box coordinates

    lons = []
    lats = []

    for point in gpx.tracks[0].segments[0].points:
        lons += [point.longitude]
        lats += [point.latitude]

    lats = np.array(lats)
    lons = np.array(lons)

    num_coords = len(lons)
    num_splits = get_num_splits(len(lons))

    split_lons = np.reshape(lons, (num_splits, -1))
    split_lats = np.reshape(lats, (num_splits, -1))

    bbox = f"{np.min(lats), np.min(lons), np.max(lats), np.max(lons)}"

    # Perform query

    api = overpass.API()
    response = api.get(query)

    # Find closest split
    pois = []
    for feature in response["features"]:
        if feature["geometry"]["type"] == "LineString":
            # In some cases when the feature is a box instead of a node,
            # the easiest-to-use API fails to get coordinates,
            # so we try a different API
            feature_id = feature["id"]
            try:
                api2 = overpy.Overpass()
                # So far encountered this only for way types
                response2 = api2.query(f"way({feature_id});(._;>;);out body;")
                qlat = float(response2.ways[0].nodes[0].lat)
                qlon = float(response2.ways[0].nodes[0].lon)
            except:
                print("Failed to parse feature.")
                continue
        else:
            qlon, qlat = feature["geometry"]["coordinates"]

        closest_dist = geopy.distance.Distance(10)  # km
        feature_split_idx = 0

        for idx in range(num_splits):
            flon = split_lons[idx][num_coords // num_splits // 2]
            flat = split_lats[idx][num_coords // num_splits // 2]
            dist = geopy.distance.distance((flat, flon), (qlat, qlon))
            if dist < closest_dist:
                closest_dist = dist
                feature_split_idx = idx

        min_info = closest_in_split(
            qlat,
            qlon,
            split_lats[feature_split_idx],
            split_lons[feature_split_idx],
        )

        if not min_info:
            continue

        poi_info = {
            "feature_coords": (qlat, qlon),
            "distance_km": min_info[2],
        }

        pois.append(poi_info)

    return pois


def map_handler(switch_values, route_map, gpx_input):
    if not gpx_input:
        return route_map

    if True in switch_values:
        gpx = gpxpy.parse(gpx_input)
        bbox = get_bbox(gpx)
    else:
        # No switches turned on
        return display_gpx_on_map(gpx_input)

    if switch_values[0]:
        # Water switch turned on
        query = f"""(
        node["amenity"="drinking_water"]{bbox};
        way["amenity"="drinking_water"]{bbox};
        )"""

        route_map = display_pois_on_map(query, "water", route_map, gpx)

    if switch_values[1]:
        # Fuel switch turned on
        query = f"""(
        node["amenity"="fuel"]{bbox};
        )"""

        route_map = display_pois_on_map(query, "fuel", route_map, gpx)

    if switch_values[2]:
        # Convenience store switch turned on
        query = f"""(
        node["shop"="convenience"]{bbox};
        way["shop"="convenience"]{bbox};
        )"""

        route_map = display_pois_on_map(query, "store", route_map, gpx)

    if switch_values[3]:
        # RMK huts and shelters turned on
        query = f"""(
        node["tourism"="wilderness_hut"]["operator"="RMK"]["fee" != "yes"]{bbox};
        way["tourism"="wilderness_hut"]["operator"="RMK"]["fee" != "yes"]{bbox};

        node["tourism"="alpine_hut"]["operator"="RMK"]{bbox};
        way["tourism"="alpine_hut"]["operator"="RMK"]{bbox};

        node["building"="hut"]["operator"="RMK"]{bbox};
        way["building"="hut"]["operator"="RMK"]{bbox};

        node["building"="yes"]["operator"="RMK"]{bbox};
        way["building"="yes"]["operator"="RMK"]{bbox};

        node["building"="hut"]["operator"="RMK"]{bbox};
        way["building"="hut"]["operator"="RMK"]{bbox};

        node["amenity"="shelter"]["operator"="RMK"]{bbox};
        way["amenity"="shelter"]["operator"="RMK"]{bbox};
        )"""

        route_map = display_pois_on_map(query, "rmk", route_map, gpx)

    if switch_values[4]:
        pass

    return route_map


gpx_input = pn.widgets.FileInput(accept=".gpx", multiple=False)
switches = MultipleSwitches(name="Switches")

switch_names = pn.Column(
    pn.widgets.StaticText(name="", value="Drinking water"),
    pn.widgets.StaticText(name="", value="Fuel station"),
    pn.widgets.StaticText(name="", value="Convenience store"),
    pn.widgets.StaticText(name="", value="RMK huts"),
    pn.widgets.StaticText(name="", value="Placeholder"),
)

route_map = pn.bind(display_gpx_on_map, gpx_input)

gspec = pn.GridSpec(sizing_mode="stretch_both", min_height=650)

gspec[:2, :15] = gpx_input
gspec[3:5, :15] = pn.widgets.StaticText(
    name="", value="Select features on route", styles={"font-size": "medium"}
)

gspec[5:, :10] = switch_names
gspec[5:, 10:15] = switches
gspec[:50, 15:100] = pn.bind(map_handler, switches, route_map, gpx_input)

gspec.servable()
