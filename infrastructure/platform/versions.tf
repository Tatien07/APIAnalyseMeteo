terraform {
  required_version = ">= 1.8, < 2.0"

  backend "gcs" {
    bucket = "energy-weather-2129519-terraform-state"
    prefix = "platform"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0, < 8.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
