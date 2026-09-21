# Plateforme GCP

Cette deuxième couche déploie l'application après le bootstrap :

- une base PostgreSQL gratuite créée séparément chez Neon ;
- l'URL Neon chiffrée dans Secret Manager ;
- un job Cloud Run pour les migrations Alembic ;
- le service FastAPI Cloud Run, avec mise à l'échelle jusqu'à zéro.
- deux jobs Cloud Run pour les collectes météo et énergie ;
- deux déclencheurs Cloud Scheduler authentifiés.
- un service Cloud Run public pour le dashboard Streamlit.

## Coût et choix pédagogiques

Cette variante ne crée pas Cloud SQL. Pour une faible utilisation restant dans les quotas gratuits :

- Neon fournit PostgreSQL avec un plan gratuit ;
- Secret Manager reste dans son quota gratuit ;
- Cloud Run limité à une instance et autorisé à descendre à zéro.

Le plan gratuit Neon peut mettre la base en veille et provoquer un premier accès plus lent. Cette
architecture convient à l'apprentissage, pas à une production critique.

## Prérequis

1. L'image indiquée par `api_image_tag` doit exister dans Artifact Registry.
   L'image `dashboard_image_tag` doit également avoir été publiée.
2. Créer un projet PostgreSQL gratuit dans Neon.
3. Dans Neon, copier la chaîne de connexion avec `sslmode=require`.
4. Remplacer son préfixe `postgresql://` par `postgresql+psycopg://` pour SQLAlchemy.
5. Ouvrir le fichier local :

```cmd
notepad infrastructure\platform\terraform.tfvars
```

Remplacer toute la valeur d'exemple de `database_url` par l'URL obtenue. Ce fichier est ignoré par
Git. Ne jamais afficher ni partager cette URL, car elle contient le mot de passe PostgreSQL.

## Initialiser et examiner sans créer

```cmd
docker compose --profile infra run --rm terraform-platform init
docker compose --profile infra run --rm terraform-platform fmt
docker compose --profile infra run --rm terraform-platform validate
docker compose --profile infra run --rm terraform-platform plan -out=platform.tfplan
```

L'ancien plan qui contenait Cloud SQL ne doit jamais être appliqué. La commande `plan -out`
ci-dessus le remplace par le nouveau plan Neon. Contrôler qu'aucune ressource Cloud SQL n'apparaît.

## Ordre d'exécution après une future application

Terraform crée les ressources, mais n'exécute pas automatiquement la migration. Après
l'application volontaire du plan :

```cmd
gcloud run jobs execute energy-weather-migrate --region=europe-west1 --wait
docker compose --profile infra run --rm terraform-platform output -raw api_url
```

Le job applique la migration Alembic puis s'arrête. FastAPI et le job lisent la même URL depuis
Secret Manager et se connectent à Neon avec TLS.

## Collecteurs planifiés

Les deux collecteurs réutilisent l'image FastAPI, mais remplacent sa commande de démarrage :

- `python -m energy_weather.collectors.weather`, chaque heure à la minute 5 ;
- `python -m energy_weather.collectors.energy`, chaque heure à la minute 20.

Les horaires utilisent le fuseau `Europe/Paris`. L'identité `energy-weather-scheduler` peut
uniquement invoquer les jobs. L'identité `energy-weather-collectors` exécute le code et lit le
secret Neon. Cette séparation applique le principe du moindre privilège.

Les planificateurs sont initialement créés en pause avec `schedulers_paused = true`. Après les
tests manuels ci-dessous, passer cette valeur à `false`, puis recréer et appliquer un plan Terraform
pour activer l'automatisation.

Après le déploiement, lancer les deux jobs une première fois sans attendre l'horaire :

```cmd
gcloud run jobs execute energy-weather-collect-weather --region=europe-west1 --wait
gcloud run jobs execute energy-weather-collect-energy --region=europe-west1 --wait
```

Vérifier ensuite les mesures avec l'URL renvoyée par `terraform output -raw api_url`.

## Dashboard Streamlit

Le dashboard est un second service Cloud Run. Terraform lui injecte automatiquement
`API_BASE_URL=<URL_FASTAPI>/api/v1`. Il ne connaît pas l'URL Neon et ne possède aucun droit de lecture
dans Secret Manager.

Publier son image avant de recalculer le plan :

```cmd
scripts\publish-dashboard.cmd v0.2.0
```

Après application du plan, obtenir son URL :

```cmd
docker compose --profile infra run --rm terraform-platform output -raw dashboard_url
```
