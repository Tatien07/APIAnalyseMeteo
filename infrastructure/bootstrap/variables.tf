variable "project_id" {
  description = "Identifiant immuable du projet Google Cloud."
  type        = string

  validation {
    condition     = length(var.project_id) >= 6
    error_message = "project_id doit contenir un identifiant de projet GCP valide."
  }
}

variable "region" {
  description = "Région principale des ressources."
  type        = string
  default     = "europe-west1"
}

variable "artifact_repository_id" {
  description = "Nom du dépôt Docker Artifact Registry."
  type        = string
  default     = "energy-weather"
}
