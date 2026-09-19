# Energy Weather Monitor

API pédagogique d'agrégation de données météorologiques et énergétiques.

## Fonctionnalités actuelles

- API FastAPI et documentation OpenAPI ;
- PostgreSQL avec SQLAlchemy asynchrone et migrations Alembic ;
- collecte des prévisions horaires Open-Meteo pour Paris ;
- collecte des données électriques nationales RTE éCO2mix ;
- température, humidité, vent, couverture nuageuse et rayonnement solaire ;
- consommation, intensité carbone et production par filière ;
- insertion idempotente des observations ;
- consultation filtrée des mesures ;
- agrégation horaire et corrélation température-consommation ;
- dashboard Streamlit avec indicateurs et graphiques ;
- tests unitaires sans appel réseau réel.

## Démarrage avec Docker

```powershell
docker compose up --build -d
docker compose --profile jobs run --rm weather-collector
docker compose --profile jobs run --rm energy-collector
```

Ouvrir ensuite :

- http://localhost:8001/docs
- http://localhost:8001/api/v1/health
- http://localhost:8001/api/v1/ready
- http://localhost:8001/api/v1/measurements?location=paris&kind=temperature
- http://localhost:8001/api/v1/measurements?location=france&kind=electricity_consumption
- http://localhost:8001/api/v1/analytics/weather-energy?hours=24
- http://localhost:8502

Relancer le collecteur ne duplique pas une observation existante : la base ignore les conflits sur
`source + location + kind + observed_at`.
Le nombre `inserted` est calculé à partir des identifiants renvoyés par PostgreSQL, ce qui reste
fiable même pour une insertion groupée avec des conflits ignorés.

## Vérifications de développement

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

Les mêmes vérifications peuvent être exécutées sans Python local :

```powershell
docker compose --profile ci run --build --rm test
```

## Jenkins local

Le `Jenkinsfile` applique successivement le lint, les tests avec couverture puis la construction des
images API et dashboard. Démarrer Jenkins :

```powershell
docker compose --profile jenkins up --build -d jenkins
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

L'interface est disponible sur http://localhost:8081. Le montage du socket Docker et l'utilisateur
root sont réservés à cet environnement pédagogique local, car ils donnent à Jenkins un accès élevé
au moteur Docker.

Si l'API est lancée hors Docker, remplacer `@db:5432` par `@localhost:5432` dans `.env`.
Dans ce cas, il faut également publier PostgreSQL sur un port Windows libre, par exemple
`5433:5432`. Lorsque toute l'application tourne avec Docker Compose, cette publication n'est pas
nécessaire : les services communiquent directement avec `db:5432` sur le réseau Docker interne.
