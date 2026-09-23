locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "containers" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_repository_id
  description   = "Images Docker de la plateforme Energy Weather Monitor"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "energy-weather-deployer"
  display_name = "Energy Weather CI/CD deployer"
  description  = "Identité utilisée par le pipeline pour publier et déployer."

  depends_on = [google_project_service.required]
}

resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "energy-weather-api"
  display_name = "Energy Weather API runtime"
  description  = "Identité d'exécution du service FastAPI."

  depends_on = [google_project_service.required]
}

resource "google_service_account" "collectors" {
  project      = var.project_id
  account_id   = "energy-weather-collectors"
  display_name = "Energy Weather collectors runtime"
  description  = "Identité d'exécution des collecteurs météo et énergie."

  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository_iam_member" "deployer_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.containers.location
  repository = google_artifact_registry_repository.containers.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_cloud_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_uses_api_identity" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_uses_collectors_identity" {
  service_account_id = google_service_account.collectors.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}
