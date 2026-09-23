# Architecture d'Energy Weather Monitor

## Vue d'ensemble

```text
Open-Meteo ──> Job météo ─────┐
                              ├──> Neon PostgreSQL <──> FastAPI <──> Streamlit
RTE éCO2mix ─> Job énergie ───┘                         │
                                                       └──> utilisateurs

Cloud Scheduler ──> jobs de collecte et de fraîcheur
Cloud Logging ────> métrique d'échec ──> Cloud Monitoring ──> alerte
Jenkins ──────────> tests ──> images Docker ──> Artifact Registry
Terraform ────────> Cloud Run, Scheduler, secrets, IAM et alertes
```

## Responsabilités

- **Collecteurs** : transforment les réponses externes en mesures communes et les insèrent de
  manière idempotente.
- **Neon PostgreSQL** : conserve les observations. Son URL n'est accessible qu'aux identités API
  et collecteurs au travers de Secret Manager.
- **FastAPI** : expose les mesures, l'analyse météo-énergie et les contrôles de santé.
- **Streamlit** : consomme uniquement l'API publique et ne connaît jamais le secret PostgreSQL.
- **Cloud Scheduler** : déclenche la météo à `:05`, l'énergie à `:20` et la fraîcheur à `:40`.
- **Cloud Run** : exécute les services à la demande et descend à zéro instance lorsqu'ils sont
  inactifs.
- **Jenkins** : bloque une livraison si le format, les tests unitaires ou les tests PostgreSQL
  échouent, puis publie des images immuables.
- **Terraform** : décrit l'état voulu de l'infrastructure et rend les changements examinables avant
  application. Ses états `bootstrap` et `platform` sont séparés dans un bucket GCS privé et
  versionné qui prend en charge le verrouillage.

## Flux d'une mesure

1. Cloud Scheduler appelle un job avec une identité OAuth dédiée.
2. Le collecteur appelle la source publique, valide et normalise les données.
3. PostgreSQL ignore les doublons selon `source + location + kind + observed_at`.
4. FastAPI lit les mesures avec SQLAlchemy asynchrone.
5. Streamlit transforme les réponses JSON en indicateurs et graphiques.
6. Le job de fraîcheur contrôle que les deux familles de données continuent d'être alimentées.

## Sécurité

Les responsabilités sont séparées entre les comptes de service du déploiement, de l'API, des
collecteurs, du dashboard et du planificateur. Le dashboard n'accède ni à Neon ni à Secret Manager.
Les identifiants personnels ne sont pas incorporés dans les images Docker.
