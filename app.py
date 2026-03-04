import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import time

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NavIndia – Route Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Mono', monospace; }

.stApp { background: #0c0e14; color: #e2e4ed; }

[data-testid="stSidebar"] {
    background: #111318 !important;
    border-right: 1px solid #1e2130;
}

h1 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
    color: #f0c040 !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stMetric"] {
    background: #111318;
    border: 1px solid #1e2130;
    border-radius: 12px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"] {
    font-size: 0.65rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #6b7280 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    color: #f0c040 !important;
    font-size: 1.6rem !important;
}

.stButton > button {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.8rem !important;
    border-radius: 8px !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: #f0c040 !important;
    color: #0c0e14 !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #ffd060 !important;
    box-shadow: 0 4px 20px rgba(240,192,64,0.35) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #6b7280 !important;
    border: 1px solid #1e2130 !important;
}

.stTextInput > div > div > input {
    background: #0c0e14 !important;
    border: 1px solid #1e2130 !important;
    border-radius: 8px !important;
    color: #e2e4ed !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #f0c040 !important;
    box-shadow: 0 0 0 3px rgba(240,192,64,0.12) !important;
}

hr { border-color: #1e2130 !important; margin: 1rem 0 !important; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── SESSION STATE ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "route_data": None,
        "start_coords": None,
        "end_coords": None,
        "start_label": "",
        "end_label": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── API FUNCTIONS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def geocode(address: str) -> dict | None:
    """Convert address to coordinates using Nominatim. Returns dict or None."""
    query = address if "india" in address.lower() else f"{address}, India"
    try:
        time.sleep(1.2)  # Nominatim rate limit
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "in"},
            headers={"User-Agent": "NavIndia/2.0 (educational project)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display": data[0].get("display_name", address),
            }
    except requests.RequestException as e:
        st.error(f"Geocoding error: {e}")
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def get_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict | None:
    """Fetch driving route from OSRM. Returns route dict or None."""
    try:
        resp = requests.get(
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}",
            params={"overview": "full", "geometries": "geojson"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        routes = data.get("routes")
        if routes:
            return routes[0]
    except requests.RequestException as e:
        st.error(f"Routing error: {e}")
    return None


# ── MAP BUILDER ───────────────────────────────────────────────────────────────
def build_map(
    start_coords: dict | None = None,
    end_coords: dict | None = None,
    route: dict | None = None,
    start_label: str = "Start",
    end_label: str = "Destination",
) -> folium.Map:
    """Build a Folium dark map with optional route and markers."""
    center = [20.5937, 78.9629]
    zoom = 5

    if start_coords and end_coords:
        center = [
            (start_coords["lat"] + end_coords["lat"]) / 2,
            (start_coords["lon"] + end_coords["lon"]) / 2,
        ]
        zoom = 6

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    if route and start_coords and end_coords:
        coords = [[c[1], c[0]] for c in route["geometry"]["coordinates"]]

        # Glow effect
        folium.PolyLine(coords, weight=12, color="#f0c040", opacity=0.15).add_to(m)
        # Main route line
        folium.PolyLine(coords, weight=4, color="#f0c040", opacity=0.9).add_to(m)

        # Start marker (green)
        folium.CircleMarker(
            location=[start_coords["lat"], start_coords["lon"]],
            radius=9,
            color="#3df5a0",
            fill=True,
            fill_color="#3df5a0",
            fill_opacity=1.0,
            popup=folium.Popup(f"<b>Start:</b> {start_label}", max_width=240),
            tooltip=f"▶ {start_label}",
        ).add_to(m)

        # End marker (red)
        folium.CircleMarker(
            location=[end_coords["lat"], end_coords["lon"]],
            radius=9,
            color="#f87171",
            fill=True,
            fill_color="#f87171",
            fill_opacity=1.0,
            popup=folium.Popup(f"<b>Destination:</b> {end_label}", max_width=240),
            tooltip=f"⬛ {end_label}",
        ).add_to(m)

        m.fit_bounds(
            [
                [start_coords["lat"], start_coords["lon"]],
                [end_coords["lat"],   end_coords["lon"]],
            ],
            padding=(50, 50),
        )

    return m


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🗺️ NavIndia")
    st.markdown(
        "<p style='font-size:0.7rem;color:#6b7280;letter-spacing:0.08em;"
        "text-transform:uppercase;margin-top:-10px;margin-bottom:1.5rem'>"
        "India Road Route Planner</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='font-size:0.7rem;color:#3df5a0;letter-spacing:0.08em;"
        "text-transform:uppercase;margin-bottom:4px'>● Starting Point</p>",
        unsafe_allow_html=True,
    )
    start_input = st.text_input(
        "start", placeholder="e.g. Chennai, Tamil Nadu", label_visibility="collapsed"
    )

    st.markdown(
        "<p style='font-size:0.7rem;color:#f87171;letter-spacing:0.08em;"
        "text-transform:uppercase;margin-bottom:4px;margin-top:12px'>● Destination</p>",
        unsafe_allow_html=True,
    )
    end_input = st.text_input(
        "end", placeholder="e.g. Kochi, Kerala", label_visibility="collapsed"
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        calc_btn = st.button("Calculate Route", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("✕", type="secondary", use_container_width=True, help="Clear route")

    st.markdown("---")

    # Route stats
    if st.session_state.route_data:
        route = st.session_state.route_data
        dist_km = route["distance"] / 1000
        dur_min = route["duration"] / 60
        hours, mins = int(dur_min // 60), int(dur_min % 60)
        time_str = f"{hours}h {mins}m" if hours else f"{mins} min"

        st.metric("Distance", f"{dist_km:,.1f} km")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.metric("Est. Drive Time", time_str)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.72rem;color:#6b7280;line-height:1.8'>"
            f"<span style='color:#3df5a0'>▶</span> "
            f"<span style='color:#e2e4ed'>{st.session_state.start_label}</span><br>"
            f"<span style='color:#6b7280;padding-left:10px'>↓</span><br>"
            f"<span style='color:#f87171'>■</span> "
            f"<span style='color:#e2e4ed'>{st.session_state.end_label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<p style='font-size:0.75rem;color:#6b7280;line-height:1.7'>"
            "Enter two Indian cities above, then press "
            "<b style='color:#f0c040'>Calculate Route</b> to plan your drive.</p>",
            unsafe_allow_html=True,
        )


# ── CLEAR ─────────────────────────────────────────────────────────────────────
if clear_btn:
    st.session_state.route_data   = None
    st.session_state.start_coords = None
    st.session_state.end_coords   = None
    st.session_state.start_label  = ""
    st.session_state.end_label    = ""
    st.rerun()


# ── CALCULATE ─────────────────────────────────────────────────────────────────
if calc_btn:
    if not start_input or not end_input:
        st.warning("Please enter both a starting location and a destination.")
    else:
        with st.spinner("Finding locations and calculating route…"):
            start_geo = geocode(start_input)
            if not start_geo:
                st.error(f"❌ Could not find **{start_input}**. Try a more specific address.")
                st.stop()

            end_geo = geocode(end_input)
            if not end_geo:
                st.error(f"❌ Could not find **{end_input}**. Try a more specific address.")
                st.stop()

            route = get_route(
                start_geo["lat"], start_geo["lon"],
                end_geo["lat"],   end_geo["lon"],
            )
            if not route:
                st.error("❌ Could not find a driving route between these locations.")
                st.stop()

        st.session_state.route_data   = route
        st.session_state.start_coords = start_geo
        st.session_state.end_coords   = end_geo
        st.session_state.start_label  = start_input
        st.session_state.end_label    = end_input
        st.rerun()


# ── MAP ───────────────────────────────────────────────────────────────────────
if st.session_state.route_data:
    st.success(
        f"✅ Route found: **{st.session_state.start_label}** → **{st.session_state.end_label}**"
    )
else:
    st.info("👈 Enter a starting point and destination in the sidebar to get started.")

m = build_map(
    start_coords=st.session_state.start_coords,
    end_coords=st.session_state.end_coords,
    route=st.session_state.route_data,
    start_label=st.session_state.start_label,
    end_label=st.session_state.end_label,
)

st_folium(m, width="100%", height=620, returned_objects=[])
