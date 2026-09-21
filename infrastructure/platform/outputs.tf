output "api_image" {
  description = "Image immuable utilisée par Cloud Run."
  value       = local.api_image
}

output "api_url" {
  description = "URL publique du service FastAPI."
  value       = google_cloud_run_v2_service.api.uri
}

output "dashboard_image" {
  description = "Image immuable utilisée par Streamlit."
  value       = local.dashboard_image
}

output "dashboard_url" {
  description = "URL publique du dashboard Streamlit."
  value       = google_cloud_run_v2_service.dashboard.uri
}

output "migration_job_name" {
  description = "Job à exécuter avant la première utilisation de l'API."
  value       = google_cloud_run_v2_job.migrate.name
}

output "collector_job_names" {
  description = "Jobs Cloud Run utilisés pour collecter les données."
  value       = { for key, job in google_cloud_run_v2_job.collectors : key => job.name }
}

output "scheduler_job_names" {
  description = "Tâches Cloud Scheduler qui déclenchent les collecteurs."
  value       = { for key, job in google_cloud_scheduler_job.collectors : key => job.name }
}
