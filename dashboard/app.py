import os

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001/api/v1")
PRODUCTION_KINDS = {
    "Nucléaire": "nuclear_production",
    "Éolien": "wind_production",
    "Solaire": "solar_production",
    "Hydraulique": "hydro_production",
    "Gaz": "gas_production",
    "Bioénergies": "bioenergy_production",
}
WEATHER_LOCATIONS = {
    "Paris": "paris",
    "Lyon": "lyon",
    "Marseille": "marseille",
    "Lille": "lille",
    "Toulouse": "toulouse",
}


def api_get(path: str, params: dict | None = None) -> object:
    response = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def latest_measurement(kind: str, location: str) -> dict | None:
    data = api_get(
        "/measurements",
        {"kind": kind, "location": location, "limit": 1},
    )
    return data[0] if isinstance(data, list) and data else None


st.set_page_config(page_title="Energy Weather Monitor", page_icon="⚡", layout="wide")
st.title("⚡ Energy Weather Monitor")
st.caption("Météo dans cinq villes et système électrique français — données en UTC")

hours = st.sidebar.slider("Période analysée (heures)", min_value=6, max_value=168, value=24)
weather_label = st.sidebar.selectbox("Ville météo", options=list(WEATHER_LOCATIONS))
weather_location = WEATHER_LOCATIONS[weather_label]
st.sidebar.caption("Actualisez après avoir relancé les collecteurs.")

try:
    freshness = api_get("/data-freshness")
    if freshness["status"] == "healthy":
        st.success("Collectes météo et énergie à jour")
    else:
        stale_sources = [
            label
            for label, key in [("météo", "weather"), ("énergie", "energy")]
            if freshness[key]["status"] != "fresh"
        ]
        st.warning(f"Données à vérifier : {', '.join(stale_sources)}")

    temperature = latest_measurement("temperature", weather_location)
    consumption = latest_measurement("electricity_consumption", "france")
    carbon = latest_measurement("carbon_intensity", "france")

    metric_columns = st.columns(3)
    metric_columns[0].metric(
        f"Température {weather_label}",
        f"{float(temperature['value']):.1f} °C" if temperature else "Indisponible",
    )
    metric_columns[1].metric(
        "Consommation France",
        f"{float(consumption['value']):,.0f} MW" if consumption else "Indisponible",
    )
    metric_columns[2].metric(
        "Intensité carbone",
        f"{float(carbon['value']):.0f} gCO₂/kWh" if carbon else "Indisponible",
    )

    analysis = api_get(
        "/analytics/weather-energy",
        {"hours": hours, "weather_location": weather_location},
    )
    points = analysis["points"]
    st.subheader("Température et consommation horaire")
    if points:
        frame = pd.DataFrame(points)
        frame["hour"] = pd.to_datetime(frame["hour"], utc=True)
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=frame["hour"],
                y=frame["temperature_c"],
                name="Température (°C)",
                line={"color": "#2f80ed"},
            )
        )
        figure.add_trace(
            go.Scatter(
                x=frame["hour"],
                y=frame["consumption_mw"],
                name="Consommation (MW)",
                yaxis="y2",
                line={"color": "#eb5757"},
            )
        )
        figure.update_layout(
            yaxis={"title": "Température (°C)"},
            yaxis2={"title": "Consommation (MW)", "overlaying": "y", "side": "right"},
            legend={"orientation": "h"},
            hovermode="x unified",
        )
        st.plotly_chart(figure, use_container_width=True)
        correlation = analysis["temperature_consumption_correlation"]
        if correlation is not None:
            correlation_label = (
                f"Corrélation de Pearson sur {analysis['points_count']} heures : {correlation:.3f}"
            )
            st.info(correlation_label)
    else:
        st.warning("Aucune heure commune. Relancez d'abord les deux collecteurs.")

    st.subheader("Dernière production par filière")
    production = []
    for label, kind in PRODUCTION_KINDS.items():
        measurement = latest_measurement(kind, "france")
        if measurement:
            production.append({"Filière": label, "Production (MW)": float(measurement["value"])})
    if production:
        production_frame = pd.DataFrame(production).set_index("Filière")
        st.bar_chart(production_frame)
    else:
        st.warning("Aucune donnée de production. Lancez le collecteur énergétique.")
except httpx.HTTPError as error:
    st.error(f"Impossible de joindre l'API : {error}")
    st.code(f"API_BASE_URL={API_BASE_URL}")
