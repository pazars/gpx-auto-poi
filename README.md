# gpx-auto-poi
Automatically add all kinds of nearby POIs to a GPX track.

Currently supports:

- Drinking water
- Fuel stations
- Convenience store
- RMK huts and shelters (Estonia)

Keep in mind that some POIs still might not show up because similar POIs can be labeled differently in OpenStreetMap and it is possible that current queries can miss out some of them.

## Install dependencies

```python -m pip install -r requirements.txt```

## Launch app

```panel serve path/to/app.py --show```

When finished, `CTRL+C` to stop app.

## Last README update
2023-07-19