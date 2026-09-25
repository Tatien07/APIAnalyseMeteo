# Guide complet — Energy Weather Monitor

## 1. Présentation générale

Energy Weather Monitor est une plateforme pédagogique d'agrégation, de stockage, d'analyse et de
visualisation de données météorologiques et électriques françaises.

Le projet récupère :

- les observations et prévisions horaires d'Open-Meteo pour Paris, Lyon, Marseille, Lille et
  Toulouse ;
- les données nationales RTE éCO2mix : consommation, intensité carbone et production par filière.

Les données sont normalisées dans PostgreSQL, exposées par une API FastAPI et affichées dans un
dashboard Streamlit. L'application fonctionne localement avec Docker Compose et dans Google Cloud
avec Cloud Run, Cloud Scheduler, Artifact Registry, Secret Manager, Logging et Monitoring.

La version documentée est `v1.0.0`.

## 2. Objectifs du projet

### 2.1 Objectifs fonctionnels

- centraliser deux sources de données publiques différentes ;
- conserver un historique exploitable dans PostgreSQL ;
- empêcher la création de doublons lors des collectes répétées ;
- proposer une API documentée et filtrable ;
- analyser la relation entre température et consommation électrique ;
- comparer la météo de plusieurs villes ;
- calculer les parts renouvelable, bas-carbone et fossile ;
- présenter les résultats dans une interface accessible ;
- détecter les données manquantes ou trop anciennes.

### 2.2 Objectifs pédagogiques

Le projet sert à apprendre une chaîne de développement complète :

```text
Python → API → base de données → tests → conteneurs → CI/CD
       → Infrastructure as Code → cloud → observabilité
```

Il complète une expérience Django ou Streamlit en introduisant notamment l'asynchronisme, les
services séparés, l'infrastructure déclarative et le déploiement continu contrôlé.

## 3. Technologies et utilité

| Technologie | Utilité dans le projet |
|---|---|
| Python 3.12 | Langage commun de l'API, des collecteurs, du monitoring et du dashboard. |
| FastAPI | API HTTP, validation automatique, injection de dépendances et documentation OpenAPI. |
| Uvicorn | Serveur ASGI qui exécute FastAPI dans le conteneur. |
| Pydantic | Validation des réponses externes, des schémas API et de la configuration. |
| pydantic-settings | Chargement typé des variables d'environnement. |
| HTTPX | Appels HTTP asynchrones vers Open-Meteo et RTE/ODRÉ. |
| SQLAlchemy asyncio | Accès asynchrone et structuré à PostgreSQL. |
| psycopg | Pilote PostgreSQL utilisé par SQLAlchemy. |
| Alembic | Versionnement et application des migrations du schéma SQL. |
| PostgreSQL | Stockage relationnel des mesures et exécution des agrégations temporelles. |
| Neon | PostgreSQL managé utilisé dans le cloud, avec une offre adaptée au projet. |
| Streamlit | Interface interactive Python destinée à l'exploration des données. |
| Pandas | Préparation des séries et des tableaux du dashboard. |
| Plotly | Graphiques interactifs à une ou deux échelles. |
| Docker | Construction d'images reproductibles pour l'API, les tests et Streamlit. |
| Docker Compose | Orchestration locale de PostgreSQL, migrations, API, dashboard et jobs. |
| Pytest | Tests unitaires et tests d'intégration. |
| Ruff | Lint et formatage homogène du code Python. |
| Jenkins | Pipeline CI/CD : qualité, tests, images, publication, plan et déploiement. |
| Terraform | Description versionnée de l'infrastructure GCP. |
| Artifact Registry | Registre privé des images Docker versionnées. |
| Cloud Run | Exécution serverless de FastAPI, Streamlit et des jobs. |
| Cloud Scheduler | Déclenchement horaire et authentifié des jobs. |
| Secret Manager | Conservation de l'URL PostgreSQL Neon hors du code et des images. |
| Cloud Logging | Centralisation et recherche des journaux JSON structurés. |
| Cloud Monitoring | Incidents et notifications à partir des événements d'échec. |
| Cloud Storage | Stockage privé et versionné des états Terraform. |
| Git et GitHub | Historique du code, tags de version et source du pipeline Jenkins. |

## 4. Architecture

### 4.1 Architecture cloud

```text
 Open-Meteo                 RTE / ODRÉ
      │                         │
      ▼                         ▼
 Job météo Cloud Run      Job énergie Cloud Run
      │                         │
      └────────────┬────────────┘
                   ▼
             Neon PostgreSQL
                   ▲
                   │ SQLAlchemy asyncio
                   ▼
             FastAPI Cloud Run
                   ▲
                   │ HTTPS / JSON
                   ▼
            Streamlit Cloud Run
                   ▲
                   │
               Utilisateur

 Cloud Scheduler ──> météo :05, énergie :20, fraîcheur :40
 Cloud Logging ─────> métrique d'échec ──> Cloud Monitoring
 Jenkins ───────────> Artifact Registry ──> Terraform ──> Cloud Run
 GCS ───────────────> états Terraform bootstrap et platform
```

### 4.2 Architecture locale

Docker Compose crée :

- `db` : PostgreSQL local ;
- `migrate` : application d'Alembic avant le démarrage de l'API ;
- `api` : FastAPI sur `localhost:8001` ;
- `dashboard` : Streamlit sur `localhost:8502` ;
- trois jobs facultatifs : météo, énergie et contrôle de fraîcheur ;
- des profils séparés pour les tests, Jenkins et Terraform.

Les noms `db`, `api` et `integration-db` sont aussi des noms DNS internes au réseau Docker. C'est
pourquoi un conteneur utilise `db:5432`, tandis qu'un programme Windows utiliserait
`localhost:<port publié>`.

### 4.3 Séparation des responsabilités applicatives

```text
api/routes       reçoit les requêtes HTTP
schemas          définit les contrats JSON
services         contient les règles métier
repositories     exécute les requêtes SQL
models           décrit les tables SQLAlchemy
collectors       communique avec les sources externes
monitoring       vérifie la fraîcheur indépendamment de l'API
core             configuration et journalisation
db               moteur et sessions PostgreSQL
```

Cette séparation facilite les tests : une formule métier peut être testée sans réseau ni base, et
le dépôt SQL peut être testé avec une base PostgreSQL éphémère.

## 5. Modèle de données

La table principale `measurements` contient :

| Champ | Signification |
|---|---|
| `id` | Identifiant technique. |
| `source` | `open-meteo` ou `rte-eco2mix`. |
| `location` | Ville ou `france`. |
| `kind` | Type de mesure : température, consommation, nucléaire, etc. |
| `value` | Valeur numérique décimale. |
| `unit` | °C, %, km/h, MW, W/m² ou gCO₂/kWh. |
| `observed_at` | Date à laquelle la valeur s'applique. |
| `collected_at` | Date de récupération par l'application. |

La contrainte unique suivante rend la collecte idempotente :

```text
source + location + kind + observed_at
```

Relancer un collecteur ne crée donc pas une seconde copie de la même observation.

## 6. Sources et collecte

### 6.1 Open-Meteo

Pour chaque ville, le collecteur demande :

- température à 2 mètres ;
- humidité relative ;
- vitesse du vent ;
- couverture nuageuse ;
- rayonnement solaire.

Les tableaux retournés sont validés par Pydantic, convertis en objets `MeasurementInput`, puis
insérés par le repository. Les cinq villes sont configurées dans `core/config.py`.

### 6.2 RTE éCO2mix via ODRÉ

Le collecteur demande les enregistrements les plus récents dont la consommation est renseignée. Il
normalise :

- consommation et intensité carbone ;
- nucléaire, éolien, solaire, hydraulique ;
- gaz, charbon, fioul et bioénergies.

La publication de la source peut avoir du retard. L'application distingue donc une absence de
points communs d'une panne de l'API elle-même.

## 7. API FastAPI

Principaux endpoints :

| Endpoint | Rôle |
|---|---|
| `/docs` | Documentation Swagger interactive. |
| `/api/v1/health` | Vérifie que le processus FastAPI répond. |
| `/api/v1/ready` | Vérifie que PostgreSQL est joignable. |
| `/api/v1/data-freshness` | Évalue l'âge des dernières collectes. |
| `/api/v1/measurements` | Liste filtrée des mesures. |
| `/api/v1/analytics/weather-energy` | Série horaire et corrélation de Pearson. |
| `/api/v1/analytics/energy-summary` | Moyennes et parts du mix énergétique. |

Exemple :

```text
/api/v1/measurements?location=lyon&kind=temperature&limit=10
/api/v1/analytics/weather-energy?hours=168&weather_location=lyon
/api/v1/analytics/energy-summary?hours=24
```

## 8. Analyses métier

### 8.1 Corrélation météo-énergie

PostgreSQL regroupe température et consommation par heure avec `date_trunc`. Une jointure conserve
uniquement les heures présentes dans les deux séries. Le service calcule ensuite le coefficient de
corrélation de Pearson. Une corrélation ne prouve pas une causalité ; elle mesure seulement une
relation linéaire sur les points disponibles.

### 8.2 Synthèse du mix

Les moyennes sont calculées sur la période demandée :

```text
renouvelable = éolien + solaire + hydraulique + bioénergies
bas-carbone  = renouvelable + nucléaire
fossile      = gaz + charbon + fioul
part         = catégorie / production totale × 100
```

### 8.3 Fraîcheur

Les états possibles sont :

- `fresh` : collecte dans le seuil configuré ;
- `stale` : collecte trop ancienne ;
- `missing` : aucune mesure disponible.

Le job indépendant termine avec un code non nul en cas de données dégradées, ce qui rend l'échec
visible dans Cloud Run et Cloud Monitoring.

## 9. Dashboard Streamlit

Le dashboard propose :

- indicateurs température, consommation et carbone ;
- choix de la ville utilisée pour la corrélation ;
- choix de plusieurs villes à comparer ;
- courbes historiques et prévisions sur 24 heures ;
- tableau température, humidité, vent et nuages ;
- graphique de production par filière ;
- synthèse renouvelable, bas-carbone et fossile ;
- export CSV ;
- cache de cinq minutes et bouton d'actualisation manuelle.

Streamlit ne se connecte jamais directement à PostgreSQL. Il consomme uniquement FastAPI, ce qui
préserve la séparation entre présentation, logique et données.

## 10. Étapes de conception et de développement

1. **Cadrage** : choix d'un agrégateur météo-énergie et définition d'un modèle commun de mesure.
2. **Socle FastAPI** : configuration, endpoints de santé et structure en couches.
3. **Persistance** : modèle SQLAlchemy, PostgreSQL, Alembic et contrainte d'idempotence.
4. **Collecte météo** : client HTTP, validation Pydantic, normalisation et tests sans réseau réel.
5. **Collecte énergie** : intégration éCO2mix et harmonisation des unités et dates UTC.
6. **API de consultation** : filtres par type, lieu, période et limite.
7. **Analyse** : agrégation SQL horaire et corrélation de Pearson.
8. **Dashboard** : métriques, graphiques, comparaison et export.
9. **Conteneurisation** : images multi-stage et orchestration Compose.
10. **Tests d'intégration** : PostgreSQL éphémère et migrations réelles.
11. **CI Jenkins** : lint, couverture, intégration, construction et publication.
12. **Infrastructure GCP** : Terraform, IAM, Artifact Registry, Cloud Run et Scheduler.
13. **Base cloud** : remplacement de Cloud SQL par Neon pour limiter le coût pédagogique.
14. **Observabilité** : journaux JSON, `request_id`, métriques, alertes et contrôle de fraîcheur.
15. **CD contrôlé** : état Terraform GCS, plan visible, approbation humaine, apply et smoke test.
16. **Version 1.0** : multi-villes, mix énergétique et documentation d'exploitation.

## 11. Tests et qualité

### Tests unitaires

Ils vérifient les parseurs, calculs, schémas, logs et contrôles sans contacter les vraies API.

### Tests d'intégration

Une base PostgreSQL 17 temporaire reçoit les migrations Alembic. Les tests vérifient ensuite la
disponibilité, l'idempotence, les endpoints analytiques et les requêtes réelles.

### Smoke test

Après un déploiement, il contrôle FastAPI, Neon, la fraîcheur, l'analyse et Streamlit. Jenkins rend
le build rouge si l'un de ces contrôles échoue.

## 12. CI/CD Jenkins

Le pipeline suit cet ordre :

```text
préparation du tag
→ image de test
→ Ruff + tests unitaires
→ tests PostgreSQL
→ images de production
→ publication Artifact Registry
→ terraform plan
→ approbation humaine
→ terraform apply
→ smoke test cloud
```

Les paramètres importants sont :

- `PUBLISH_IMAGES` : publication des images ;
- `DEPLOY_TO_GCP` : plan et déploiement contrôlé ;
- `IMAGE_TAG` : version immuable, par exemple `v1.0.0` ;
- `RUN_CLOUD_SMOKE_TEST` : test d'une version déjà déployée ;
- `CLOUD_API_URL` et `CLOUD_DASHBOARD_URL` : URL du test autonome.

## 13. Infrastructure Terraform

Trois racines sont séparées :

- `state-bootstrap` crée le bucket privé des états ;
- `bootstrap` active les API, crée Artifact Registry et les identités principales ;
- `platform` déploie secrets, services, jobs, planificateurs et alertes.

Les états `bootstrap` et `platform` utilisent des préfixes GCS distincts. Le versionnement protège
contre une suppression accidentelle et le backend fournit un verrou lors des écritures.

## 14. Sécurité

- l'URL Neon reste dans `terraform.tfvars` local et Secret Manager ;
- les fichiers `.env`, `terraform.tfvars`, états et plans sont ignorés par Git ;
- le dashboard ne possède aucun accès au secret ;
- le planificateur peut invoquer les jobs mais ne peut pas lire la base ;
- les comptes de service API, collecteurs, dashboard et déploiement sont séparés ;
- les images utilisent des tags immuables ;
- Terraform affiche les changements avant approbation.

Le montage du socket Docker dans Jenkins donne des privilèges importants. Il est acceptable pour ce
laboratoire local, mais une CI distante devrait utiliser une identité fédérée et des agents isolés.

## 15. Observabilité

En local, les logs sont lisibles. Dans Cloud Run, ils sont au format JSON avec :

- `event` ;
- `request_id` ou `run_id` ;
- statut HTTP et durée ;
- nombres reçus et insérés ;
- état et âge des sources.

La métrique `energy_weather/application_failures` compte les échecs structurés. Cloud Monitoring
ouvre un incident et peut notifier une adresse e-mail confirmée.

## 16. Commandes essentielles

Toutes les commandes suivantes sont lancées depuis la racine du projet.

### Application locale

```powershell
docker compose up --build -d
```

Construit et démarre PostgreSQL, les migrations, FastAPI et Streamlit en arrière-plan.

```powershell
docker compose ps
docker compose logs --tail=100 api
docker compose down
```

Affiche l'état, consulte les logs, puis arrête les services sans supprimer le volume PostgreSQL.

### Collecteurs

```powershell
docker compose --profile jobs run --rm weather-collector
docker compose --profile jobs run --rm energy-collector
docker compose --profile jobs run --rm freshness-check
```

Exécute ponctuellement chaque job local et supprime son conteneur après exécution.

### Tests

```powershell
docker compose --profile ci run --build --rm test
```

Lance Ruff, le contrôle de format et les tests unitaires avec couverture.

```powershell
docker compose -p energy-weather-integration --profile integration run --build --rm integration-test
docker compose -p energy-weather-integration --profile integration down --volumes --remove-orphans
```

Crée une base isolée, applique Alembic, exécute les tests réels puis nettoie uniquement les
ressources d'intégration. Le `-p` distinct protège la base locale.

### Jenkins

```powershell
docker compose --profile jenkins up --build -d jenkins
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
docker compose exec jenkins terraform version
```

Construit Jenkins, récupère le mot de passe initial et vérifie Terraform dans l'agent.

### Git

```powershell
git status
git add .
git commit -m "Description du changement"
git push origin main
git tag -a v1.0.0 -m "Energy Weather Monitor version 1.0.0"
git push origin v1.0.0
```

Inspecte, enregistre, publie le code puis crée la version officielle.

### Authentification GCP

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project energy-weather-2129519
```

Authentifie la CLI, crée les identifiants utilisés par Terraform et sélectionne le projet.

### Terraform

```powershell
docker compose --profile infra run --rm terraform-platform init
docker compose --profile infra run --rm terraform-platform fmt
docker compose --profile infra run --rm terraform-platform validate
docker compose --profile infra run --rm terraform-platform plan -out=platform.tfplan
docker compose --profile infra run --rm terraform-platform apply platform.tfplan
```

Initialise le backend GCS, formate, valide, prépare un plan immuable puis l'applique.

Ne jamais appliquer un ancien plan après une modification de code, de variables ou de backend.

### Jobs et services cloud

```powershell
gcloud run jobs execute energy-weather-migrate --region=europe-west1 --wait
gcloud run jobs execute energy-weather-collect-weather --region=europe-west1 --wait
gcloud run jobs execute energy-weather-collect-energy --region=europe-west1 --wait
gcloud run jobs execute energy-weather-check-freshness --region=europe-west1 --wait
```

Exécute manuellement migration, collectes et contrôle en attendant leur résultat.

```powershell
gcloud run services describe energy-weather-api --region=europe-west1 --format="value(status.url)"
gcloud run services describe energy-weather-dashboard --region=europe-west1 --format="value(status.url)"
gcloud scheduler jobs list --location=europe-west1
```

Récupère les URL et vérifie les planificateurs.

### Logs et diagnostic

```powershell
gcloud logging read 'resource.type="cloud_run_job"' --project=energy-weather-2129519 --limit=30
```

Recherche les dernières exécutions de jobs dans Cloud Logging.

```powershell
$apiUrl = gcloud run services describe energy-weather-api --region=europe-west1 --format="value(status.url)"
Invoke-RestMethod "$apiUrl/api/v1/data-freshness" | ConvertTo-Json -Depth 5
```

Affiche le diagnostic détaillé de fraîcheur.

### Test post-déploiement

```powershell
$apiUrl = docker compose --profile infra run --rm terraform-platform output -raw api_url
$dashboardUrl = docker compose --profile infra run --rm terraform-platform output -raw dashboard_url
.\scripts\smoke-test.ps1 -ApiUrl $apiUrl -DashboardUrl $dashboardUrl
```

Valide l'ensemble du parcours utilisateur après une livraison.

## 17. Incidents courants

| Symptôme | Cause probable | Action |
|---|---|---|
| Port 5432 ou 8000 déjà utilisé | Un autre service écoute sur le port. | Modifier le port publié ou arrêter l'autre service. |
| `Name or service not known` | Mauvaise URL entre hôte et réseau Docker. | Utiliser `api:8000` dans Docker, `localhost:8001` depuis Windows. |
| `greenlet` absent | SQLAlchemy installé sans son extra asyncio. | Utiliser `sqlalchemy[asyncio]`. |
| Aucune heure commune | Séries météo et énergie sans recouvrement temporel. | Relancer les jobs et élargir la période. |
| Énergie `stale` | Job non exécuté ou retard de publication ODRÉ. | Examiner Scheduler, job et dates `observed_at`. |
| Réseau Docker encore utilisé | Un conteneur reste attaché. | Identifier le conteneur ; ne pas supprimer la base locale inutilement. |
| Paramètres Jenkins absents | Jenkins utilise un ancien Jenkinsfile. | Lancer un build, vérifier SCM `main` et actualiser le job. |
| Terraform veut tout recréer | Mauvais état ou backend non migré. | Ne pas appliquer ; vérifier `terraform state list`. |

## 18. Limites et améliorations possibles

- l'API de démonstration est publique ; une authentification pourrait être ajoutée ;
- les données RTE peuvent être publiées avec retard ;
- Neon peut se mettre en veille et ralentir le premier appel ;
- la corrélation dépend de la quantité et de la qualité de l'historique ;
- Jenkins local utilise les identifiants ADC de l'utilisateur ; une CI distante devrait utiliser
  Workload Identity Federation ;
- un modèle prédictif ne sera pertinent qu'après plusieurs semaines ou mois de données fiables.

Évolutions envisageables : prévision de consommation, alertes de seuil carbone, nouvelles villes,
tests de charge, authentification, politiques de rétention et tableau de coûts.

## 19. Conclusion

Energy Weather Monitor illustre une application moderne de bout en bout. Il ne s'agit pas seulement
d'une API ou d'un dashboard : le projet couvre la qualité du code, les données, le déploiement,
l'infrastructure, la sécurité, les opérations et la supervision. La version 1.0 constitue un MVP
cohérent et présentable, tout en laissant une trajectoire claire vers des usages plus avancés.
