"""City of Ottawa view for the V3 app: the 5 EDs, events, and "what if" incident scenarios.

How the numbers are made (all estimates, see app_v3/README.md):
- Only one ED has data files (forecast, schedule, waiting room, spaces). That ED is HOME_ED.
  Every other ED gets the same hourly pattern, scaled by its annual ED visits (hospitals.csv).
- Incident patients = attendance x share exposed x attack rate x share who go to an ED.
- When they arrive: onset time after the event starts (a lognormal curve per incident type)
  plus the drive time to the hospital.
- Which hospital: nearest ED first. When its surge capacity is used up the rest go to the next
  nearest. Under-18s go to CHEO first. Patients beyond every ED's capacity are shared by size.
- Surge capacity = treatment spaces free now + spaces estimated to finish within 4 h
  (Gulchaman's rules on the home ED's spaces.csv, scaled for the other EDs).
"""
import json
import math
import os
import urllib.parse

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

import utils_v3 as utils

HOME_ED = "civic"  # the ED that the sample data files describe

# Incident types. Defaults are starting points for the sliders on the City page.
#   exposed: share of attendees exposed     attack: share of exposed who get sick or hurt
#   to_ed: share of those who go to an ED    onset: hours after the event starts (median, spread)
#   ctas: share of ED patients at each level
INCIDENTS = {
    "Food poisoning (toxin, e.g. Staph. aureus)": {
        "exposed": 0.05, "attack": 0.75, "to_ed": 0.25, "onset_median_h": 2.5, "onset_sigma": 0.6,
        "ctas": {1: 0.0, 2: 0.05, 3: 0.45, 4: 0.40, 5: 0.10},
        "source": "Onset 30 min to 8 h after eating (CDC MMWR, Staph. aureus outbreak). Attack rate 77.7% "
                  "in a catering outbreak (India). Share exposed, share going to an ED and the CTAS mix are "
                  "assumptions.",
    },
    "Crowd injury (crush, fall, panic)": {
        "exposed": 0.005, "attack": 1.0, "to_ed": 0.6, "onset_median_h": 0.6, "onset_sigma": 0.7,
        "ctas": {1: 0.03, 2: 0.17, 3: 0.40, 4: 0.30, 5: 0.10},
        "source": "PLACEHOLDER values with no source yet. Shows a fast, more severe surge.",
    },
    "Normal event (no incident)": {
        "exposed": 1.0, "attack": 0.001, "to_ed": 0.027, "onset_median_h": 1.5, "onset_sigma": 0.6,
        "ctas": {1: 0.02, 2: 0.18, 3: 0.40, 4: 0.30, 5: 0.10},
        "source": "Mass gatherings: about 1 patient per 1,000 attendees treated on site and 0.027 per 1,000 "
                  "taken to hospital (pooled Canadian/Australian events, Prehospital and Disaster Medicine). "
                  "CTAS mix is an assumption.",
    },
}

ROAD_FACTOR = 1.4  # road distance is about 1.4 x straight-line distance in a city (assumption)
DRIVE_KMH = 40     # average city driving speed, ambulance or car (assumption)
SCENARIO_HOURS = 12  # how long after the event start patients are counted

# Known venues, for live events that have no attendance. Capacities are approximate.
VENUE_CAPACITY = {
    "canadian tire centre": 18600,
    "td place stadium": 24000,
    "arena at td place": 8585,
    "td place": 8585,
    "southam hall": 2065,
    "fourth stage": 150,
    "national arts centre": 2065,
    "hard rock": 2000,
    "bronson centre": 900,
    "meridian theatres": 1500,
}
DEFAULT_ATTENDANCE = 500  # unknown venue


# ---------------------------------------------------------------- hospitals

@st.cache_data
def load_hospitals():
    h = pd.read_csv(utils.DATA / "hospitals.csv")
    h["pediatric_only"] = h["pediatric_only"].str.lower().eq("yes")
    home_visits = h.loc[h["hospital_id"] == HOME_ED, "annual_ed_visits"].iloc[0]
    h["scale"] = h["annual_ed_visits"] / home_visits  # size compared with the home ED
    return h


def hospital_name(hospital_id):
    h = load_hospitals().set_index("hospital_id")
    return h.loc[hospital_id, "name"]


def scale(hospital_id):
    return float(load_hospitals().set_index("hospital_id").loc[hospital_id, "scale"])


def surge_capacity():
    """Spaces each ED could give incident patients: free now + estimated to finish within 4 h.
    Home ED from spaces.csv; the others scaled by size. 0 if the spaces data is invalid."""
    try:
        s = utils.spaces_summary(utils.spaces_table())
        home = s["free"] + s["within_4h"]
    except utils.SpacesDataError:
        home = 0
    h = load_hospitals()
    return dict(zip(h["hospital_id"], (h["scale"] * home).round().astype(int)))


# ---------------------------------------------------------------- events

@st.cache_data
def load_event_file():
    ev = pd.read_csv(utils.DATA / "events.csv", dtype={"source_url": str, "notes": str})
    return ev.fillna({"source_url": "", "notes": ""})


def ticketmaster_key():
    """Free key from developer.ticketmaster.com, saved as TICKETMASTER_API_KEY in Streamlit secrets
    (.streamlit/secrets.toml locally, or the app's Settings > Secrets online) or as an environment variable.
    A key pasted on the City & Events page (this browser session only) wins over both."""
    if st.session_state.get("tm_key"):
        return st.session_state["tm_key"]
    try:
        key = st.secrets.get("TICKETMASTER_API_KEY")
    except Exception:  # no secrets file at all
        key = None
    return key or os.environ.get("TICKETMASTER_API_KEY")


def venue_attendance(venue):
    v = (venue or "").lower()
    for name, cap in VENUE_CAPACITY.items():
        if name in v:
            return cap, f"Attendance = capacity of {venue} (approximate)"
    return DEFAULT_ATTENDANCE, f"Unknown venue: attendance guessed at {DEFAULT_ATTENDANCE}"


def parse_ticketmaster(payload):
    """Ticketmaster Discovery API response -> rows with the same columns as events.csv."""
    rows = []
    for e in payload.get("_embedded", {}).get("events", []):
        venue = (e.get("_embedded", {}).get("venues") or [{}])[0]
        loc = venue.get("location") or {}
        start = e.get("dates", {}).get("start", {})
        if "latitude" not in loc or "localDate" not in start:
            continue
        cls = (e.get("classifications") or [{}])[0]
        attendance, note = venue_attendance(venue.get("name"))
        rows.append({
            "event_id": f"TM-{e.get('id', '')}", "name": e.get("name", "Unnamed event"),
            "venue": venue.get("name", ""), "date": start["localDate"],
            "start_time": (start.get("localTime") or "19:00:00")[:5],
            "category": cls.get("segment", {}).get("name", "Event"), "expected_attendance": attendance,
            "lat": float(loc["latitude"]), "lon": float(loc["longitude"]),
            "source": "Ticketmaster (live)", "source_url": e.get("url", ""),
            "notes": note + ("" if start.get("localTime") else ". Start time not listed, 19:00 assumed"),
        })
    return pd.DataFrame(rows, columns=load_event_file().columns)


@st.cache_data(ttl=3 * 3600, show_spinner="Getting live events from Ticketmaster...")
def live_events(api_key, start, end):
    r = requests.get("https://app.ticketmaster.com/discovery/v2/events.json", timeout=10, params={
        "apikey": api_key, "city": "Ottawa", "countryCode": "CA", "size": 100, "sort": "date,asc",
        "startDateTime": f"{start:%Y-%m-%d}T00:00:00Z", "endDateTime": f"{end:%Y-%m-%d}T23:59:59Z"})
    r.raise_for_status()
    return parse_ticketmaster(r.json())


def load_events():
    """events.csv plus live Ticketmaster events (if a key is set). Returns (events, status text)."""
    ev = load_event_file()
    key = ticketmaster_key()
    if not key:
        return ev, "Using events.csv (hand-made list). Live Ticketmaster events will be added once a key is set."
    try:
        start = utils.DEMO_NOW - pd.Timedelta(days=1)
        live = live_events(key, start, start + pd.Timedelta(days=14))
    except Exception as err:  # network down, bad key, rate limit: the demo still works on events.csv
        return ev, f"Live events unavailable ({type(err).__name__}). Showing events.csv only."
    ev = pd.concat([ev, live], ignore_index=True)
    return ev, f"Live events on: {len(live)} Ticketmaster events added to events.csv."


# ---------------------------------------------------------------- incident scenario

def km_between(lat1, lon1, lat2, lon2):
    """Straight-line distance in km (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def onset_cdf(hours, median, sigma):
    """Share of patients whose symptoms started by `hours` after the event start (lognormal)."""
    if hours <= 0:
        return 0.0
    return 0.5 * (1 + math.erf((math.log(hours) - math.log(median)) / (sigma * math.sqrt(2))))


def _share_by_size(n, ids, weights):
    """Split n whole patients in proportion to weights (largest remainder)."""
    raw = [n * w / sum(weights) for w in weights]
    out = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[: n - sum(out)]:
        out[i] += 1
    return dict(zip(ids, out))


@st.cache_data
def incident_plan(params):
    """params (a dict, see the City page): event, venue lat/lon, attendance, start, incident type, shares.
    Returns {"patients": int, "hospitals": DataFrame, "hourly": DataFrame}."""
    kind = INCIDENTS[params["incident"]]
    n = round(params["attendance"] * params["exposed"] * params["attack"] * params["to_ed"])
    kids = round(n * params["under18"])

    h = load_hospitals().copy()
    h["km"] = [ROAD_FACTOR * km_between(params["lat"], params["lon"], a, b) for a, b in zip(h["lat"], h["lon"])]
    h["drive_min"] = (h["km"] / DRIVE_KMH * 60).round().astype(int)
    h["capacity"] = h["hospital_id"].map(surge_capacity())
    h = h.sort_values("km", ignore_index=True)
    taken = dict.fromkeys(h["hospital_id"], 0)
    cap = dict(zip(h["hospital_id"], h["capacity"]))

    def fill(count, order):
        for hid in order:
            take = min(count, cap[hid] - taken[hid])
            if take > 0:
                taken[hid] += take
                count -= take
        return count

    adult_eds = h.loc[~h["pediatric_only"], "hospital_id"].tolist()
    kids_left = fill(kids, h.loc[h["pediatric_only"], "hospital_id"])
    left = fill(n - kids + kids_left, adult_eds)
    # Every ED is full: the rest still need care, shared by size among the adult EDs.
    adult = h[~h["pediatric_only"]]
    for hid, extra in _share_by_size(left, adult["hospital_id"].tolist(), adult["scale"].tolist()).items():
        taken[hid] += extra

    h["patients"] = h["hospital_id"].map(taken)
    h["over_capacity"] = (h["patients"] - h["capacity"]).clip(lower=0)
    for level, share in kind["ctas"].items():
        h[f"ctas_{level}"] = (h["patients"] * share).round(1)

    # Arrivals per clock hour at each ED: onset after the event start + drive time.
    start = pd.Timestamp(params["start"])
    rows = []
    for r in h.itertuples():
        if not r.patients:
            continue
        for k in range(SCENARIO_HOURS + 1):
            slot = start.floor("h") + pd.Timedelta(hours=k)
            a = (slot - start).total_seconds() / 3600 - r.drive_min / 60
            share = (onset_cdf(a + 1, kind["onset_median_h"], kind["onset_sigma"])
                     - onset_cdf(a, kind["onset_median_h"], kind["onset_sigma"]))
            rows.append({"timestamp": slot, "hospital_id": r.hospital_id, "short_name": r.short_name,
                         "extra_arrivals": round(r.patients * share, 1)})
    hourly = pd.DataFrame(rows, columns=["timestamp", "hospital_id", "short_name", "extra_arrivals"])
    return {"patients": n, "children": kids, "hospitals": h, "hourly": hourly}


def route_table(plan):
    """Where the patients go, one row per ED in drive-time order, with the reason (plain words)."""
    h = plan["hospitals"]
    rows, first_adult = [], True
    for r in h.itertuples():
        if plan["patients"] == 0:
            why = "No patients expected"
        elif r.pediatric_only:
            if not r.patients:
                why = "No children expected"
            elif plan.get("children", 0) > r.capacity:
                why = "Full: the other children go to the adult EDs"
            else:
                why = "Children (18 and under) go here first"
        elif r.patients == 0:
            why = "Not needed: nearer EDs had space"
        elif r.over_capacity:
            why = "Full: gets a share of the overflow (by ED size)"
        elif first_adult:
            why = "Nearest adult ED"
        else:
            why = "Next nearest: the nearer EDs were full"
        if not r.pediatric_only:
            first_adult = False
        rows.append({"Hospital": MAP_LABELS.get(r.hospital_id, r.short_name), "Drive (min)": r.drive_min,
                     "Road km (est.)": round(r.km, 2), "Patients": int(r.patients),
                     "Surge capacity": int(r.capacity), "Why": why})
    return pd.DataFrame(rows)


def active_plan():
    """The plan for the scenario switched on in the City page, or None."""
    params = st.session_state.get("incident")
    return incident_plan(params) if params else None


def extra_arrivals(hospital_id):
    """Incident arrivals per hour at one ED (Series indexed by timestamp). Empty if no scenario."""
    plan = active_plan()
    if plan is None:
        return pd.Series(dtype=float)
    hourly = plan["hourly"]
    return hourly[hourly["hospital_id"] == hospital_id].set_index("timestamp")["extra_arrivals"]


def incident_banner(hospital_id):
    """One line for the other pages: what the active scenario means for this ED."""
    params = st.session_state.get("incident")
    if not params:
        return
    plan = incident_plan(params)
    row = plan["hospitals"].set_index("hospital_id").loc[hospital_id]
    start = pd.Timestamp(params["start"])
    text = (f"Incident scenario: {params['incident'].split(' (')[0].lower()} at {params['event']} "
            f"({start:%a %H:%M}). {plan['patients']} patients expected across Ottawa EDs; "
            f"{int(row['patients'])} to {row['short_name']}")
    if row["over_capacity"]:
        st.error(text + f", {int(row['over_capacity'])} more than its surge capacity. See City & Events.")
    elif row["patients"]:
        st.warning(text + ". See City & Events.")
    else:
        st.info(text + ". See City & Events.")


# ---------------------------------------------------------------- map

STATUS_COLORS = {  # RGB, matching the app's alert colours
    "Over capacity": [214, 39, 40], "Receiving patients": [242, 142, 43],
    "No incident patients": [44, 160, 44], "Hospital": [76, 155, 232],
}
EVENT_COLORS = {"Event (events.csv)": [188, 145, 235], "Event (live, Ticketmaster)": [23, 190, 207]}
VENUE_COLOR = [255, 215, 0]  # the incident venue (gold star)
# One colour per ED for its 10 km buffer (light fill) and drive-time rings.
BUFFER_KM = 10
BUFFER_ALPHA = 30  # out of 255, about 12% (5 overlapping buffers stay see-through)
# Drive-time rings use the same rule as the patient routing: straight line x ROAD_FACTOR at DRIVE_KMH.
# They are circles, not real road travel times.
DRIVE_ZONES_MIN = (5, 10, 15)


def zone_km(minutes):
    """Straight-line radius (km) reached in `minutes` under the app's drive-time rule."""
    return minutes / 60 * DRIVE_KMH / ROAD_FACTOR



BUFFER_COLORS = {"civic": [31, 119, 180], "general": [255, 127, 14], "qch": [44, 160, 44],
                 "montfort": [214, 39, 40], "cheo": [148, 103, 189]}
# Map labels: clearer than the short names used in tables and charts.
MAP_LABELS = {"civic": "Ottawa Hospital - Civic", "general": "Ottawa Hospital - General",
              "qch": "Queensway Carleton", "montfort": "Montfort", "cheo": "CHEO (children)"}
# Free Carto dark map, no key: light grey road names, neighbourhoods, parks and water labels.
DARK_MAP = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
LABEL_GREY = [215, 215, 215]
TOOLTIP_STYLE = {"backgroundColor": "#1e1e1e", "color": "#dcdcdc", "fontSize": "13px", "maxWidth": "360px",
                 "border": "1px solid #555", "borderRadius": "6px", "boxShadow": "0 2px 8px rgba(0,0,0,0.6)",
                 "padding": "8px 10px", "whiteSpace": "pre-line", "zIndex": "1000",
                 # Streamlit 1.65 places the hover box one map-height above the mouse; top: 100% (of the
                 # map-sized box it sits in) cancels that, also in fullscreen.
                 "top": "100%", "marginTop": "12px", "marginLeft": "12px"}
# Five-point star icon. mask=True lets deck.gl colour it with get_color.
_STAR_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24">'
             '<path fill="white" d="M12 1.5l3.1 6.6 7.2.9-5.3 5 1.4 7.1L12 17.6l-6.4 3.5 1.4-7.1-5.3-5 7.2-.9z"/></svg>')
STAR_ICON = {"url": "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(_STAR_SVG),
             "width": 64, "height": 64, "anchorY": 32, "mask": True}


def _plain(tip):
    """Streamlit escapes HTML inside hover values, so tips are shown as plain text with line breaks."""
    return str(tip).replace("<br/>", "\n").replace("<b>", "").replace("</b>", "")


def _venue_tips(events):
    """One row per venue, with a hover text listing its events (soonest first)."""
    ev = events.assign(live=events["source"].str.contains("live", case=False, na=False))
    ev = ev.assign(when=pd.to_datetime(ev["date"] + " " + ev["start_time"])).sort_values("when")
    rows = []
    for (venue, lat, lon), g in ev.groupby(["venue", "lat", "lon"], sort=False):
        lines = [f"{r.when:%a %b %d %H:%M} · {r.name} · about {int(r.expected_attendance):,}"
                 + (" (live)" if r.live else "") for r in g.head(6).itertuples()]
        more = f"<br/>... and {len(g) - 6} more" if len(g) > 6 else ""
        kind = "Event (live, Ticketmaster)" if g["live"].all() else "Event (events.csv)"
        rows.append({"venue": venue, "lat": lat, "lon": lon, "color": EVENT_COLORS[kind],
                     "tip": f"<b>{venue}</b><br/>{len(g)} event(s):<br/>" + "<br/>".join(lines) + more})
    return pd.DataFrame(rows, columns=["venue", "lat", "lon", "color", "tip"])


@st.cache_data
def load_boundaries():
    """Ottawa dissemination areas and the city boundary (Statistics Canada 2021, see tools/ottawa_boundaries.py).
    Returns (da, city) GeoJSON dicts, or (None, None) if the files are missing."""
    try:
        da = json.loads((utils.DATA / "ottawa_da.geojson").read_text(encoding="utf-8"))
        city = json.loads((utils.DATA / "ottawa_city.geojson").read_text(encoding="utf-8"))
        return da, city
    except FileNotFoundError:
        return None, None


def map_legend(plan=None, buffers=True, areas=True, focus=None):
    """HTML legend for city_map (pydeck has no built-in legend)."""
    def rgb(c, a=1):
        return f"rgba({c[0]},{c[1]},{c[2]},{a})"

    def item(swatch, label):
        return (f'<span style="display:inline-flex;align-items:center;margin-right:18px;white-space:nowrap">'
                f'{swatch}<span style="margin-left:6px">{label}</span></span>')

    def dot(c):
        return f'<span style="width:12px;height:12px;border-radius:50%;border:1px solid #333;background:{rgb(c)}"></span>'

    def star(c, size=16):
        return f'<span style="color:{rgb(c)};font-size:{size}px;line-height:1">&#9733;</span>'

    if plan:
        items = [item(dot(STATUS_COLORS[k]), f"ED: {k.lower()}") for k in
                 ("Over capacity", "Receiving patients", "No incident patients")]
        items.append(item(star(VENUE_COLOR, 22), "Incident venue"))
        items.append(item('<span style="display:inline-block;width:28px;height:3px;background:#888"></span>'
                          '<span style="display:inline-block;width:28px;height:9px;margin-left:4px;background:#888">'
                          '</span>', "Line: patients sent to that ED (thicker = more patients, "
                                     "label = patients and drive time)"))
    else:
        items = [item(dot(STATUS_COLORS["Hospital"]), "Emergency department")]
    items += [item(star(c), k) for k, c in EVENT_COLORS.items()]
    if buffers:
        items += [item(f'<span style="width:14px;height:14px;border-radius:50%;background:{rgb(c, 0.25)};'
                       f'border:2px solid {rgb(c)}"></span>', f"{MAP_LABELS[h]} (hospital picked in the sidebar)")
                  for h, c in BUFFER_COLORS.items() if focus in (None, h)]
        edge = round(BUFFER_KM * ROAD_FACTOR / DRIVE_KMH * 60)
        rings = ", ".join(f"{m}" for m in DRIVE_ZONES_MIN)
        items.append(item('<span style="width:14px;height:14px;border-radius:50%;border:1px solid #ccc"></span>',
                          f"Filled circle: {BUFFER_KM} km (about {edge} min drive). "
                          f"Thin rings: about {rings} min drive"))
    if areas:
        items.append(item('<span style="width:14px;height:14px;border:1px solid #aaa"></span>',
                          "Dissemination area (thicker line = City of Ottawa boundary)"))
    items.append('<span style="color:#888;white-space:nowrap">Hover a dot, star or line for details.</span>')
    return '<div style="font-size:0.85rem;line-height:2">' + "".join(items) + "</div>"


def _view(plan, venue, buffers):
    """Whole city by default. With a scenario, centre on the venue and the EDs that get patients."""
    if not (plan and venue):
        return 45.38, -75.70, 9.7 if buffers else 10.2
    h = plan["hospitals"]
    pts = h.loc[h["patients"] > 0, ["lat", "lon"]].values.tolist() + [[venue["lat"], venue["lon"]]]
    lats, lons = [p[0] for p in pts], [p[1] for p in pts]
    span_m = max((max(lats) - min(lats)) * 111_000, (max(lons) - min(lons)) * 78_000, 2_000)
    # Web map: about 110,700 m per pixel at zoom 0 at Ottawa's latitude; fit the span in about 380 px.
    zoom = min(max(math.log2(110_700 * 380 / span_m), 9.5), 12.5)
    return (max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2, zoom


def city_map(events, plan=None, venue=None, buffers=True, areas=True, focus=None):
    """pydeck map on a dark base map: dissemination areas, a 10 km buffer with drive-time rings around the ED
    picked in the sidebar (`focus`; all EDs if None), hospitals (coloured by status), event venues (stars), and
    straight lines from the incident venue. Pickable layers have a `tip` column."""
    h = plan["hospitals"].copy() if plan else load_hospitals().assign(patients=0, over_capacity=0, capacity=0)
    visits = load_hospitals().set_index("hospital_id")["annual_ed_visits"]
    h["visits"] = h["hospital_id"].map(visits)
    kids = ["<br/>18 and under only" if p else "" for p in h["pediatric_only"]]
    if plan:
        h["status"] = ["Over capacity" if o else "Receiving patients" if p else "No incident patients"
                       for p, o in zip(h["patients"], h["over_capacity"])]
        h["tip"] = [f"<b>{n}</b>{k}<br/>Status: {s}<br/>Incident patients: {p} (surge capacity {c})"
                    f"<br/>Over capacity by: {o}<br/>Drive from venue: {d} min ({km:.1f} km)"
                    for n, k, s, p, c, o, d, km in zip(h["name"], kids, h["status"], h["patients"], h["capacity"],
                                                     h["over_capacity"], h["drive_min"], h["km"])]
    else:
        h["status"] = "Hospital"
        h["tip"] = [f"<b>{n}</b>{k}<br/>{a}<br/>About {v:,} ED visits a year"
                    for n, k, a, v in zip(h["name"], kids, h["address"], h["visits"])]
    h["color"] = h["status"].map(STATUS_COLORS)
    # General and CHEO sit next to each other: nudge CHEO's label down so both are readable.
    h["offset"] = [[0, 24] if p else [0, -24] for p in h["pediatric_only"]]
    h["label"] = h["hospital_id"].map(MAP_LABELS).fillna(h["short_name"])
    h["tip"] = h["tip"].map(_plain)
    zone = h[h["hospital_id"] == focus].copy() if focus else h.copy()
    base = [BUFFER_COLORS.get(i, [150, 150, 150]) for i in zone["hospital_id"]]
    zone["buffer_color"] = [c + [BUFFER_ALPHA] for c in base]
    zone["edge_color"] = [c + [230] for c in base]
    # One row per ED per drive-time ring, with a small "N min" label just inside the ring's top edge.
    rings = pd.DataFrame([{"lon": lon, "lat": lat, "radius": zone_km(m) * 1000, "color": c + [170],
                           "label_lat": lat + zone_km(m) / 111.0, "label": f"{m} min"}
                          for lon, lat, c in zip(zone["lon"], zone["lat"], base) for m in DRIVE_ZONES_MIN])

    venues = _venue_tips(events)
    venues["tip"] = venues["tip"].map(_plain)
    venues["icon"] = [STAR_ICON] * len(venues)

    layers = []
    da, city_line = load_boundaries()
    if areas and da:
        layers += [
            pdk.Layer("GeoJsonLayer", da, stroked=True, filled=False, get_line_color=[170, 170, 170, 110],
                      line_width_min_pixels=0.5),
            pdk.Layer("GeoJsonLayer", city_line, stroked=True, filled=False, get_line_color=[220, 220, 220, 220],
                      line_width_min_pixels=2),
        ]
    if buffers:
        # Circle with a 10 km radius around each ED (deck.gl radius in metres), light fill and a solid edge.
        # Not pickable, so hover still reaches the hospitals and stars on top.
        layers += [
            pdk.Layer("ScatterplotLayer", zone, get_position="[lon, lat]", get_radius=BUFFER_KM * 1000,
                      get_fill_color="buffer_color", stroked=True, get_line_color="edge_color",
                      line_width_min_pixels=2),
            pdk.Layer("ScatterplotLayer", rings, get_position="[lon, lat]", get_radius="radius", filled=False,
                      stroked=True, get_line_color="color", line_width_min_pixels=1),
            pdk.Layer("TextLayer", rings, get_position="[lon, label_lat]", get_text="label", get_size=11,
                      get_color=LABEL_GREY + [200], get_alignment_baseline="'top'"),
        ]
    paths_at = len(layers)  # patient lines go under the stars and hospital dots
    layers += [
        pdk.Layer("IconLayer", venues, get_position="[lon, lat]", get_icon="icon", get_size=22,
                  get_color="color", pickable=True, auto_highlight=True),
        # Same size for every ED (pixels), so a dot is just a location.
        pdk.Layer("ScatterplotLayer", h, get_position="[lon, lat]", get_fill_color="color", get_radius=9,
                  radius_units="'pixels'", stroked=True, get_line_color=[240, 240, 240],
                  line_width_min_pixels=1.5, pickable=True, auto_highlight=True),
        # Light grey text on a dark tag, to match the dark map.
        pdk.Layer("TextLayer", h, get_position="[lon, lat]", get_text="label", get_size=13,
                  get_color=LABEL_GREY, get_pixel_offset="offset", font_weight=700,
                  background=True, get_background_color=[25, 25, 25, 220], background_padding=[5, 3]),
    ]
    if plan and venue:
        lines = h[h["patients"] > 0].assign(src_lon=venue["lon"], src_lat=venue["lat"])
        # Straight line, flat map; thickness in pixels by patients, relative to the busiest ED (3 to 16 px).
        lines["width"] = 3 + 13 * lines["patients"] / max(lines["patients"].max(), 1)
        lines["tip"] = [f"{p} patients to {n}\n{s:.0%} of all incident patients\n{d} min drive ({km:.1f} km)"
                        for p, n, s, d, km in zip(lines["patients"], lines["short_name"],
                                                  lines["patients"] / max(plan["patients"], 1),
                                                  lines["drive_min"], lines["km"])]
        lines["line_color"] = [c + [200] for c in lines["color"]]
        # width_units must be quoted ("'pixels'"): pydeck turns a bare string into a data expression, so deck.gl
        # got no unit and drew the widths as huge stripes across the map.
        lines["path"] = [[[slon, slat], [lon, lat]] for slon, slat, lon, lat
                         in zip(lines["src_lon"], lines["src_lat"], lines["lon"], lines["lat"])]
        layers.insert(paths_at, pdk.Layer("PathLayer", lines, get_path="path", get_width="width",
                                          width_units="'pixels'", cap_rounded=True, get_color="line_color",
                                          pickable=True, auto_highlight=True))
        # Label each line at its middle: "N patients · M min", so the route can be read without hovering.
        lines["mid_lon"] = (lines["src_lon"] + lines["lon"]) / 2
        lines["mid_lat"] = (lines["src_lat"] + lines["lat"]) / 2
        lines["line_label"] = [f"{p} pt · {d} min" for p, d in zip(lines["patients"], lines["drive_min"])]
        layers.insert(paths_at + 1, pdk.Layer(
            "TextLayer", lines, get_position="[mid_lon, mid_lat]", get_text="line_label", get_size=12,
            get_color=[255, 255, 255], background=True, get_background_color=[60, 60, 60, 230],
            background_padding=[4, 2]))
        spot = pd.DataFrame([{**venue, "tip": _plain(venue.get("tip", "")), "icon": STAR_ICON}])
        layers.append(pdk.Layer("IconLayer", spot, get_position="[lon, lat]", get_icon="icon", get_size=40,
                                get_color=VENUE_COLOR, pickable=True))
    lat, lon, zoom = _view(plan, venue, buffers)
    view = pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom, pitch=0, bearing=0, max_pitch=0)  # flat, no tilt
    return pdk.Deck(layers=layers, initial_view_state=view, map_style=DARK_MAP,
                    tooltip={"text": "{tip}", "style": TOOLTIP_STYLE})
