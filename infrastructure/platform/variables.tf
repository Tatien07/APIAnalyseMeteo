variable "project_id" {
  description = "Identifiant immuable du projet Google Cloud."
  type        = string

  validation {
    condition     = length(var.project_id) >= 6 && var.project_id != "mon-projet-gcp"
    error_message = "Renseignez le véritable identifiant du projet GCP."
  }
}

variable "region" {
  description = "Région des ressources Cloud Run et Secret Manager."
  type        = string
  default     = "europe-west1"
}

variable "artifact_repository_id" {
  description = "Dépôt Artifact Registry créé par le bootstrap."
  type        = string
  default     = "energy-weather"
}

variable "api_image_tag" {
  description = "Tag immuable de l'image FastAPI publiée."
  type        = string
  default     = "v0.2.0"
}

variable "dashboard_image_tag" {
  description = "Tag immuable de l'image Streamlit publiée."
  type        = string
  default     = "v0.2.0"
}

variable "database_url" {
  description = "URL PostgreSQL Neon utilisée par SQLAlchemy et stockée dans Secret Manager."
  type        = string
  sensitive   = true

  validation {
    condition = (
      startswith(var.database_url, "postgresql+psycopg://") &&
      strcontains(var.database_url, "sslmode=require")
    )
    error_message = "database_url doit commencer par postgresql+psycopg:// et activer sslmode=require."
  }
}

variable "allow_unauthenticated" {
  description = "Autorise l'accès public à l'API de démonstration."
  type        = bool
  default     = true
}

variable "schedulers_paused" {
  description = "Garde les collectes automatiques en pause jusqu'aux tests manuels."
  type        = bool
  default     = true
}
