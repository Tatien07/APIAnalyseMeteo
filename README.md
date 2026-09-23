# Energy Weather Monitor

API pédagogique d'agrégation de données météorologiques et énergétiques.

Documentation complémentaire :

- [architecture](docs/ARCHITECTURE.md) ;
- [exploitation, validation et retour arrière](docs/OPERATIONS.md).

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
- contrôle de fraîcheur des collectes météo et énergie.

## Démarrage avec Docker

```powershell
docker compose up --build -d
docker compose --profile jobs run --rm weather-collector
docker compose --profile jobs run --rm energy-collector
docker compose --profile jobs run --rm freshness-check
```

Ouvrir ensuite :

- http://localhost:8001/docs
- http://localhost:8001/api/v1/health
- http://localhost:8001/api/v1/ready
- http://localhost:8001/api/v1/data-freshness
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

Après un déploiement cloud, exécuter le test de fumée décrit dans
[`docs/OPERATIONS.md`](docs/OPERATIONS.md). Il vérifie l'API, Neon, la fraîcheur des données,
l'analyse et le dashboard avec un seul script PowerShell.

Les tests d'intégration utilisent une base PostgreSQL 17 éphémère distincte. Ils appliquent
Alembic, testent la disponibilité, l'idempotence des insertions et l'analyse horaire, puis la base
peut être entièrement supprimée :

```powershell
docker compose -p energy-weather-integration --profile integration run --build --rm integration-test
docker compose -p energy-weather-integration --profile integration down --volumes --remove-orphans
```

L'option `-p energy-weather-integration` place les conteneurs, le réseau et les volumes de test dans
un projet Compose distinct. Le nettoyage ne peut donc pas supprimer la base locale utilisée par
l'API et le dashboard. Cette base de test n'expose aucun port Windows et n'utilise ni Neon, ni la
base PostgreSQL locale. Jenkins applique déjà cette isolation avec un nom unique par build et
nettoie les ressources même lorsque les tests échouent.

Si la vérification de format échoue, appliquer le format depuis le même conteneur puis relancer :

```powershell
docker compose --profile ci run --rm test ruff format src tests migrations dashboard
docker compose --profile ci run --rm test
```

## Jenkins local

Le `Jenkinsfile` applique successivement le lint, les tests avec couverture, la construction des
images API et dashboard, puis leur publication optionnelle dans Artifact Registry. Démarrer ou
reconstruire Jenkins :

```powershell
docker compose --profile jenkins up --build -d jenkins
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

L'interface est disponible sur http://localhost:8081. Le montage du socket Docker et l'utilisateur
root sont réservés à cet environnement pédagogique local, car ils donnent à Jenkins un accès élevé
au moteur Docker.

Le pipeline propose deux paramètres :

- `PUBLISH_IMAGES=false` : lint, tests et constructions uniquement ;
- `PUBLISH_IMAGES=true` : ajoute l'authentification et le push vers Artifact Registry ;
- `IMAGE_TAG` vide : produit automatiquement `build-NUMERO` ;
- `IMAGE_TAG=v0.3.0` : utilise un tag de version choisi explicitement.

Les Application Default Credentials Windows sont montées en lecture seule. Jenkins demande un
jeton d'accès court avec `gcloud auth application-default print-access-token`, puis Docker l'utilise
pour se connecter au registre. Cette approche convient au laboratoire local ; une CI distante doit
utiliser Workload Identity Federation plutôt que les identifiants personnels ou une clé JSON.

Une publication ne déploie pas directement Cloud Run. Pour promouvoir un tag validé, modifier dans
`infrastructure/platform/terraform.tfvars` :

```hcl
api_image_tag       = "build-42"
dashboard_image_tag = "build-42"
```

Puis examiner et appliquer le changement :

```cmd
docker compose --profile infra run --rm terraform-platform plan -out=platform.tfplan
docker compose --profile infra run --rm terraform-platform apply platform.tfplan
```

Terraform met alors à jour l'API, le dashboard, la migration et les collecteurs vers les images
validées sans modifier Neon ni les données.

## Préparation GCP avec Terraform

La première couche d'infrastructure se trouve dans `infrastructure/bootstrap`. Elle active les API,
crée Artifact Registry et sépare les identités du déploiement, de l'API et des collecteurs. Elle ne
crée encore ni Cloud SQL ni Cloud Run afin d'éviter des ressources payantes avant validation.

```powershell
Copy-Item infrastructure/bootstrap/terraform.tfvars.example infrastructure/bootstrap/terraform.tfvars
docker compose --profile infra run --rm terraform init
docker compose --profile infra run --rm terraform validate
docker compose --profile infra run --rm terraform plan
```

Consulter `infrastructure/bootstrap/README.md` avant tout `terraform apply`.

## Publication de l'image FastAPI

Après l'application du bootstrap Terraform, le script Windows suivant construit l'étage
`production` du Dockerfile et publie l'image dans Artifact Registry :

```cmd
scripts\publish-api.cmd v0.2.0
```

Le script :

1. lit le projet actif dans la configuration `gcloud` ;
2. vérifie que le dépôt `energy-weather` existe dans `europe-west1` ;
3. configure Docker pour s'authentifier au registre ;
4. construit l'image de production ;
5. l'envoie sous le nom
   `europe-west1-docker.pkg.dev/PROJECT_ID/energy-weather/api:v0.2.0`.

Le tag versionné permet de savoir exactement quelle image sera déployée et d'effectuer un
retour arrière. Sans argument, le script utilise le tag `latest`, moins adapté à un déploiement
reproductible.

Le conteneur utilise la variable `PORT` fournie par Cloud Run. En local, lorsque cette variable
n'existe pas, il continue d'écouter sur le port `8000`.

## Plateforme Neon et Cloud Run

La seconde couche Terraform se trouve dans `infrastructure/platform`. Elle place l'URL d'une base
PostgreSQL Neon dans Secret Manager, puis prépare le job de migration Alembic et le service FastAPI
Cloud Run. Elle remplace l'ancienne variante Cloud SQL afin de rester proche de zéro euro sous les
quotas gratuits.

La même couche crée deux Cloud Run Jobs qui lancent les collecteurs Python, puis deux tâches Cloud
Scheduler horaires. Les appels de Scheduler utilisent OAuth et une identité dédiée qui possède
uniquement le rôle d'invocation des jobs.

Le dashboard Streamlit possède sa propre image et son propre service Cloud Run. Son conteneur reçoit
uniquement l'URL publique de FastAPI ; il n'accède jamais directement à PostgreSQL ni au secret Neon.

```cmd
scripts\publish-dashboard.cmd v0.2.0
```

## Observabilité et Cloud Logging

En local, `APP_LOG_FORMAT=plain` produit des lignes lisibles. Sur Cloud Run, Terraform injecte
`APP_LOG_FORMAT=json` dans FastAPI et les collecteurs. Cloud Logging peut alors indexer notamment :

- `event` : type d'événement stable ;
- `request_id` : identifiant permettant de suivre un appel HTTP ;
- `http_method`, `http_path` et `http_status` ;
- `duration_ms` ;
- `run_id`, `received` et `inserted` pour une collecte.

FastAPI accepte un en-tête `X-Request-ID` fourni par le client ou en génère un, puis le renvoie dans
la réponse. Ne journaliser que le chemin, sans la chaîne de requête, évite d'enregistrer par erreur
des paramètres sensibles.

Exemples de recherches après déploiement :

```cmd
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.event=http_request_completed" --project=energy-weather-2129519 --limit=20
gcloud logging read "resource.type=cloud_run_job AND jsonPayload.event=weather_collection_completed" --project=energy-weather-2129519 --limit=20
gcloud logging read "jsonPayload.request_id=IDENTIFIANT" --project=energy-weather-2129519 --limit=20
```

Les événements `weather_collection_failed`, `energy_collection_failed` et `http_request_failed`
contiennent également l'exception avant que Cloud Run marque l'exécution en erreur.

Terraform crée également une métrique `energy_weather/application_failures` et une politique
d'alerte Cloud Monitoring. Le canal e-mail est facultatif et se configure avec `alert_email` dans
le fichier local `infrastructure/platform/terraform.tfvars`.

Un job Cloud Run indépendant vérifie aussi la fraîcheur chaque heure. Cette vérification détecte
le cas où un collecteur ne démarre plus du tout et ne peut donc pas produire son propre journal
d'erreur.

La version `v0.6.0` ajoute ce job planifié. Elle doit être publiée par Jenkins avant d'appliquer la
configuration Terraform qui crée `energy-weather-check-freshness`.

## Fraîcheur des données

L'endpoint `/api/v1/data-freshness` vérifie la date de dernière collecte, et non la date de la
mesure : les prévisions météo peuvent en effet contenir des observations futures. Par défaut, une
source est `fresh` si son collecteur a écrit dans les trois dernières heures. Elle devient `stale`
au-delà de ce seuil et `missing` si aucune donnée n'existe. Le statut global est alors `degraded`.

Le seuil peut être ajusté pour un diagnostic ponctuel, par exemple :

```text
/api/v1/data-freshness?threshold_minutes=240
```

Ce contrôle métier complète `/health` (processus FastAPI actif) et `/ready` (base accessible).

### Livraison de la version 0.5.0

Cette version ajoute le contrôle de fraîcheur et son affichage dans Streamlit. Après avoir envoyé
le code sur GitHub, lancer Jenkins avec `PUBLISH_IMAGES=true` et `IMAGE_TAG=v0.5.0`. Une fois les
deux images publiées, examiner puis appliquer la couche Terraform `platform`. Cloud Run crée de
nouvelles révisions avec les images `v0.5.0`, tandis que les versions précédentes restent
disponibles dans Artifact Registry pour un éventuel retour arrière.

Consulter `infrastructure/platform/README.md` avant toute application ou modification de la
planification des collecteurs.

Si l'API est lancée hors Docker, remplacer `@db:5432` par `@localhost:5432` dans `.env`.
Dans ce cas, il faut également publier PostgreSQL sur un port Windows libre, par exemple
`5433:5432`. Lorsque toute l'application tourne avec Docker Compose, cette publication n'est pas
nécessaire : les services communiquent directement avec `db:5432` sur le réseau Docker interne.
