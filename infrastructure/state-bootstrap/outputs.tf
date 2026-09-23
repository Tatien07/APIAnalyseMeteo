output "state_bucket_name" {
  description = "Bucket GCS privé utilisé par les backends Terraform."
  value       = google_storage_bucket.terraform_state.name
}
