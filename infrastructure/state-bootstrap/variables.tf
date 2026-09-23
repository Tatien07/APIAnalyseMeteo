variable "project_id" {
  description = "Identifiant du projet Google Cloud."
  type        = string
}

variable "region" {
  description = "Région du bucket d'état Terraform."
  type        = string
  default     = "europe-west1"
}

variable "state_bucket_name" {
  description = "Nom globalement unique du bucket d'état Terraform."
  type        = string
  default     = "energy-weather-2129519-terraform-state"
}
