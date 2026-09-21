output "artifact_registry_hostname" {
  description = "Hôte Docker à configurer dans gcloud et Docker."
  value       = "${var.region}-docker.pkg.dev"
}

output "artifact_registry_repository" {
  description = "Chemin complet du dépôt Docker."
  value       = join("/", [
    "${var.region}-docker.pkg.dev",
    var.project_id,
    var.artifact_repository_id,
  ])
}

output "deployer_service_account" {
  value = google_service_account.deployer.email
}

output "api_service_account" {
  value = google_service_account.api.email
}

output "collectors_service_account" {
  value = google_service_account.collectors.email
}
