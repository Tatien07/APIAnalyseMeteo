import os
from datetime import UTC, datetime, timedelta

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


@st.cache_data(ttl=300, show_spinner=False)
def api_get(path: str, params: dict | None = None) -> object:
    response = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def latest_measurement(
    kind: str,
    location: str,
    *,
    observed_to: datetime | None = None,
) -> dict | None:
    params = {"kind": kind, "location": location, "limit": 1}
    if observed_to is not None:
        params["observed_to"] = observed_to.isoformat()
    data = api_get(
        "/measurements",
        params,
    )
    return data[0] if isinstance(data, list) and data else None


st.set_page_config(page_title="Energy Weather Monitor", page_icon="⚡", layout="wide")
st.title("⚡ Energy Weather Monitor")
st.caption("Météo dans cinq villes et système électrique français — données en UTC")

hours = st.sidebar.slider("Période analysée (heures)", min_value=6, max_value=168, value=24)
weather_label = st.sidebar.selectbox("Ville météo", options=list(WEATHER_LOCATIONS))
weather_location = WEATHER_LOCATIONS[weather_label]
compared_weather_labels = st.sidebar.multiselect(
    "Villes à comparer",
    options=list(WEATHER_LOCATIONS),
    default=list(WEATHER_LOCATIONS),
)
if st.sidebar.button("Actualiser maintenant", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("Les réponses de l'API sont conservées pendant 5 minutes.")

try:
    now = datetime.now(UTC)
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

    temperature = latest_measurement("temperature", weather_location, observed_to=now)
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

    energy_summary = api_get("/analytics/energy-summary", {"hours": hours})
    st.subheader(f"Synthèse énergétique sur {hours} heures")
    summary_columns = st.columns(4)
    summary_columns[0].metric(
        "Consommation moyenne",
        f"{energy_summary['average_consumption_mw']:,.0f} MW"
        if energy_summary["average_consumption_mw"] is not None
        else "Indisponible",
    )
    for column, label, key in [
        (summary_columns[1], "Part renouvelable", "renewable_share_percent"),
        (summary_columns[2], "Part bas-carbone", "low_carbon_share_percent"),
        (summary_columns[3], "Part fossile", "fossil_share_percent"),
    ]:
        value = energy_summary[key]
        column.metric(label, f"{value:.1f} %" if value is not None else "Indisponible")

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

    st.subheader("Comparaison météo des villes")
    comparison_rows = []
    current_weather_rows = []
    for city_label in compared_weather_labels:
        city_location = WEATHER_LOCATIONS[city_label]
        city_measurements = api_get(
            "/measurements",
            {
                "location": city_location,
                "observed_from": (now - timedelta(hours=hours)).isoformat(),
                "observed_to": (now + timedelta(hours=24)).isoformat(),
                "limit": 1000,
            },
        )
        current_by_kind = {}
        for measurement in city_measurements:
            observed_at = pd.to_datetime(measurement["observed_at"], utc=True)
            if measurement["kind"] == "temperature":
                comparison_rows.append(
                    {
                        "Ville": city_label,
                        "Date": observed_at,
                        "Température (°C)": float(measurement["value"]),
                    }
                )
            if observed_at <= pd.Timestamp(now) and measurement["kind"] not in current_by_kind:
                current_by_kind[measurement["kind"]] = float(measurement["value"])

        current_weather_rows.append(
            {
                "Ville": city_label,
                "Température (°C)": current_by_kind.get("temperature"),
                "Humidité (%)": current_by_kind.get("relative_humidity"),
                "Vent (km/h)": current_by_kind.get("wind_speed"),
                "Nuages (%)": current_by_kind.get("cloud_cover"),
            }
        )

    if comparison_rows:
        comparison_frame = pd.DataFrame(comparison_rows).sort_values("Date")
        comparison_figure = go.Figure()
        for city_label in compared_weather_labels:
            city_frame = comparison_frame[comparison_frame["Ville"] == city_label]
            comparison_figure.add_trace(
                go.Scatter(
                    x=city_frame["Date"],
                    y=city_frame["Température (°C)"],
                    name=city_label,
                )
            )
        comparison_figure.add_vline(x=now, line_dash="dash", line_color="gray")
        comparison_figure.update_layout(
            yaxis={"title": "Température (°C)"},
            legend={"orientation": "h"},
            hovermode="x unified",
        )
        st.plotly_chart(comparison_figure, use_container_width=True)
        st.caption("À gauche de la ligne : historique. À droite : prévisions Open-Meteo.")
        st.dataframe(
            pd.DataFrame(current_weather_rows).set_index("Ville"),
            use_container_width=True,
        )
        export_frame = comparison_frame.rename(
            columns={"Date": "observed_at", "Ville": "city", "Température (°C)": "temperature_c"}
        )
        st.download_button(
            "Télécharger la comparaison en CSV",
            data=export_frame.to_csv(index=False).encode("utf-8"),
            file_name=f"weather-comparison-{now:%Y%m%d-%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Sélectionnez au moins une ville pour afficher la comparaison.")

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
