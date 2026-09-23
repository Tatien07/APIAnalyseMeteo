# Stockage distant de l'état Terraform

Cette couche reste volontairement en état local : elle crée le bucket dont les deux autres couches
ont besoin pour leur backend. Le bucket possède un accès uniforme, interdit tout accès public,
conserve les versions précédentes et refuse sa suppression tant qu'il contient des objets.

## Création du bucket

```powershell
Copy-Item infrastructure/state-bootstrap/terraform.tfvars.example infrastructure/state-bootstrap/terraform.tfvars
docker compose --profile infra run --rm terraform-state init
docker compose --profile infra run --rm terraform-state fmt -check
docker compose --profile infra run --rm terraform-state validate
docker compose --profile infra run --rm terraform-state plan -out=state.tfplan
docker compose --profile infra run --rm terraform-state apply state.tfplan
```

Ne jamais supprimer manuellement ce bucket : les états peuvent contenir des secrets et constituent
le lien entre la configuration Terraform et les ressources GCP existantes.

## Migration des états existants

Après la création du bucket, migrer chaque couche séparément :

Avant la migration, conserver une copie locale temporaire dans le dossier `work`, ignoré par Git :

```powershell
New-Item -ItemType Directory -Force work/terraform-state-backup
Copy-Item infrastructure/bootstrap/terraform.tfstate* work/terraform-state-backup/
Copy-Item infrastructure/platform/terraform.tfstate* work/terraform-state-backup/
```

Ces sauvegardes contiennent potentiellement l'URL Neon et doivent rester locales. Migrer ensuite :

```powershell
docker compose --profile infra run --rm terraform init -migrate-state -force-copy
docker compose --profile infra run --rm terraform-platform init -migrate-state -force-copy
```

Puis vérifier que les ressources existantes sont toujours connues :

```powershell
docker compose --profile infra run --rm terraform state list
docker compose --profile infra run --rm terraform-platform state list
```

Les préfixes `bootstrap` et `platform` empêchent les deux états de se mélanger.
Les anciens fichiers `.tfplan` référencent le backend précédent : ne pas les appliquer après la
migration. Toujours produire un nouveau plan.
