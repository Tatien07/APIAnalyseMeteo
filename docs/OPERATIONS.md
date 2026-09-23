# Guide d'exploitation

## Validation après déploiement

Récupérer les URL :

```powershell
$apiUrl = docker compose --profile infra run --rm terraform-platform output -raw api_url
$dashboardUrl = docker compose --profile infra run --rm terraform-platform output -raw dashboard_url
.\scripts\smoke-test.ps1 -ApiUrl $apiUrl -DashboardUrl $dashboardUrl
```

Docker Compose peut ajouter des lignes d'état aux variables PowerShell. Le script accepte cette
sortie multi-ligne et en extrait automatiquement la dernière URL HTTP ou HTTPS valide.

Le script vérifie successivement le processus FastAPI, PostgreSQL, la fraîcheur métier, l'analyse
sur 24 heures et le service Streamlit. Un code de sortie non nul signifie que la livraison ne doit
pas être considérée comme validée.

## Diagnostic d'une alerte

1. Identifier l'événement et le `run_id` dans Cloud Logging.
2. Vérifier l'historique du job Cloud Run concerné.
3. Consulter `/api/v1/data-freshness` pour distinguer météo et énergie.
4. Vérifier l'état de Neon si `/ready` échoue.
5. Relancer manuellement uniquement le job concerné.

```powershell
gcloud run jobs execute energy-weather-collect-weather --region=europe-west1 --wait
gcloud run jobs execute energy-weather-collect-energy --region=europe-west1 --wait
gcloud run jobs execute energy-weather-check-freshness --region=europe-west1 --wait
```

## Retour arrière

Un retour arrière ne modifie pas les données. Dans `infrastructure/platform/terraform.tfvars`,
remplacer les tags API et dashboard par le dernier tag connu comme stable, puis examiner le plan :

```powershell
docker compose --profile infra run --rm terraform-platform plan -out=rollback.tfplan
docker compose --profile infra run --rm terraform-platform apply rollback.tfplan
```

Exécuter ensuite le test post-déploiement. Les anciennes images ne doivent être supprimées
d'Artifact Registry qu'après expiration de la période de retour arrière choisie.

## Arrêt temporaire et maîtrise des coûts

Pour suspendre uniquement les collectes, régler `schedulers_paused = true` puis appliquer Terraform.
Les services Cloud Run restent déployés mais conservent leur mise à l'échelle à zéro. Ne jamais
utiliser `terraform destroy` comme simple mécanisme de pause : cela élargit inutilement la portée
des changements.
