# Bootstrap GCP

Cette configuration prépare le projet sans déployer l'application :

- activation des API GCP nécessaires ;
- dépôt Docker Artifact Registry ;
- compte de service de déploiement ;
- identités d'exécution séparées pour l'API et les collecteurs ;
- permissions minimales nécessaires à cette première phase.

## Prérequis

1. Créer ou choisir un projet GCP avec facturation activée.
2. Installer et initialiser la CLI Google Cloud.
3. Créer les Application Default Credentials :

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project PROJECT_ID
gcloud auth application-default set-quota-project PROJECT_ID
```

Vérifier sous Windows que le fichier existe :

```powershell
Test-Path "$env:APPDATA\gcloud\application_default_credentials.json"
```

Docker Compose le monte en lecture seule sous `/gcloud` et définit explicitement
`GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json` pour Terraform.

4. Créer la configuration locale :

```powershell
Copy-Item infrastructure/bootstrap/terraform.tfvars.example infrastructure/bootstrap/terraform.tfvars
```

Remplacer ensuite `mon-projet-gcp` par le véritable identifiant du projet.

## Vérifier puis appliquer

```powershell
docker compose --profile infra run --rm terraform init
docker compose --profile infra run --rm terraform fmt -check
docker compose --profile infra run --rm terraform validate
docker compose --profile infra run --rm terraform plan -out=bootstrap.tfplan
docker compose --profile infra run --rm terraform apply bootstrap.tfplan
```

`plan` est une lecture prévisionnelle. `apply` crée réellement les ressources.

## Configurer Docker pour Artifact Registry

Après l'application, lire les sorties :

```powershell
docker compose --profile infra run --rm terraform output
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

Ne créez pas de clé JSON longue durée pour le compte de service de déploiement. Une étape ultérieure
configurera une authentification adaptée au pipeline.
