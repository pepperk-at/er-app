"""Download Ottawa boundaries from Statistics Canada (2021 Census cartographic boundary files, ArcGIS REST service,
Open Government Licence - Canada) and save them, simplified, as GeoJSON for the City & Events map.

- data/ottawa_da.geojson: the 1,392 dissemination areas (DA) of the City of Ottawa (DAUID starts with 3506)
- data/ottawa_city.geojson: the City of Ottawa municipal boundary (census subdivision 3506008)

Run once: python app_v3/tools/ottawa_boundaries.py   (standard library only)
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer"
DATA = Path(__file__).parent.parent / "data"


def query(layer, where, fields):
    params = {"where": where, "outFields": fields, "outSR": 4326, "f": "geojson",
              "maxAllowableOffset": 0.0002, "geometryPrecision": 5}  # ~20 m simplification, ~1 m precision
    url = f"{BASE}/{layer}/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


for name, layer, where, fields in [("ottawa_da", 12, "DAUID LIKE '3506%'", "DAUID,LANDAREA"),
                                   ("ottawa_city", 9, "CSDUID='3506008'", "CSDUID,CSDNAME")]:
    gj = query(layer, where, fields)
    out = DATA / f"{name}.geojson"
    out.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    print(f"{out.name}: {len(gj['features'])} features, {out.stat().st_size / 1e6:.2f} MB")
