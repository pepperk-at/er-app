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
import math
import os

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
    return {"patients": n, "hospitals": h, "hourly": hourly}


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
EVENT_COLORS = {"Event (events.csv)": [148, 103, 189], "Event (live, Ticketmaster)": [23, 190, 207]}
VENUE_COLOR = [148, 103, 189]  # the incident venue
# Map labels: clearer than the short names used in tables and charts.
MAP_LABELS = {"civic": "Ottawa Hospital - Civic", "general": "Ottawa Hospital - General",
              "qch": "Queensway Carleton", "montfort": "Montfort", "cheo": "CHEO (children)"}
LIGHT_MAP = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"  # free Carto light map, no key
TOOLTIP_STYLE = {"backgroundColor": "white", "color": "#222", "fontSize": "13px", "maxWidth": "360px",
                 "border": "1px solid #999", "borderRadius": "6px", "boxShadow": "0 2px 8px rgba(0,0,0,0.3)",
                 "padding": "8px 10px", "whiteSpace": "pre-line", "zIndex": "1000",
                 # Streamlit 1.65 places the hover box one map-height above the mouse; top: 100% (of the
                 # map-sized box it sits in) cancels that, also in fullscreen.
                 "top": "100%", "marginTop": "12px", "marginLeft": "12px"}


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


def map_legend(plan=None):
    """HTML legend for city_map (pydeck has no built-in legend)."""
    def dot(rgb, label, size=12, ring=False):
        border = "2px solid #fff;box-shadow:0 0 0 1px #555" if ring else "1px solid #333"
        return (f'<span style="display:inline-flex;align-items:center;margin-right:18px;white-space:nowrap">'
                f'<span style="width:{size}px;height:{size}px;border-radius:50%;border:{border};'
                f'background:rgb({rgb[0]},{rgb[1]},{rgb[2]});margin-right:6px"></span>{label}</span>')
    if plan:
        items = [dot(STATUS_COLORS[k], f"ED: {k.lower()}") for k in
                 ("Over capacity", "Receiving patients", "No incident patients")]
        items.append(dot(VENUE_COLOR, "Incident venue", 16, ring=True))
        items.append('<span style="margin-right:18px;white-space:nowrap">'
                     '<span style="display:inline-block;width:28px;height:3px;vertical-align:middle;margin-right:4px;'
                     'background:#888"></span><span style="display:inline-block;width:28px;height:9px;'
                     'vertical-align:middle;margin-right:6px;background:#888"></span>'
                     'Line: patients sent to that ED (thicker = more patients)</span>')
    else:
        items = [dot(STATUS_COLORS["Hospital"], "Emergency department")]
    items += [dot(c, k, 9) for k, c in EVENT_COLORS.items()]
    items.append('<span style="color:#777;white-space:nowrap">Bigger ED circle = more visits a year. '
                 'Hover any circle or line for details.</span>')
    return '<div style="font-size:0.85rem;line-height:2">' + "".join(items) + "</div>"


def city_map(events, plan=None, venue=None):
    """pydeck map: hospitals (coloured by status), event venues, and straight lines from the incident venue.
    Every layer has a `tip` column, shown on hover."""
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
    h["radius"] = 250 + 350 * h["scale"]
    # General and CHEO sit next to each other: nudge CHEO's label down so both are readable.
    h["offset"] = [[0, 24] if p else [0, -24] for p in h["pediatric_only"]]
    h["label"] = h["hospital_id"].map(MAP_LABELS).fillna(h["short_name"])

    h["tip"] = h["tip"].map(_plain)
    venues = _venue_tips(events)
    venues["tip"] = venues["tip"].map(_plain)
    layers = [
        pdk.Layer("ScatterplotLayer", venues, get_position="[lon, lat]", get_fill_color="color",
                  opacity=0.7, get_radius=250, radius_min_pixels=4, pickable=True, auto_highlight=True),
        pdk.Layer("ScatterplotLayer", h, get_position="[lon, lat]", get_fill_color="color", get_radius="radius",
                  stroked=True, get_line_color=[40, 40, 40], line_width_min_pixels=1, radius_min_pixels=8,
                  pickable=True, auto_highlight=True),
        # Dark text on a white tag, readable on any map.
        pdk.Layer("TextLayer", h, get_position="[lon, lat]", get_text="label", get_size=13,
                  get_color=[20, 20, 20], get_pixel_offset="offset", font_weight=700,
                  background=True, get_background_color=[255, 255, 255, 230], background_padding=[5, 3]),
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
        layers.insert(0, pdk.Layer("PathLayer", lines, get_path="path", get_width="width", width_units="'pixels'",
                                   cap_rounded=True, get_color="line_color", pickable=True, auto_highlight=True))
        layers.append(pdk.Layer("ScatterplotLayer", pd.DataFrame([{**venue, "tip": _plain(venue.get("tip", ""))}]), get_position="[lon, lat]",
                                get_fill_color=VENUE_COLOR, get_radius=600, stroked=True,
                                get_line_color=[255, 255, 255], line_width_min_pixels=2, pickable=True))
    view = pdk.ViewState(latitude=45.37, longitude=-75.75, zoom=10.2, pitch=0, bearing=0, max_pitch=0)  # flat, no 3D tilt
    return pdk.Deck(layers=layers, initial_view_state=view, map_style=LIGHT_MAP,
                    tooltip={"text": "{tip}", "style": TOOLTIP_STYLE})
