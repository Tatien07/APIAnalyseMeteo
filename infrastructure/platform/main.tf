locals {
  api_image = join("/", [
    "${var.region}-docker.pkg.dev",
    var.project_id,
    var.artifact_repository_id,
    "api:${var.api_image_tag}",
  ])
  dashboard_image = join("/", [
    "${var.region}-docker.pkg.dev",
    var.project_id,
    var.artifact_repository_id,
    "dashboard:${var.dashboard_image_tag}",
  ])
  collector_jobs = {
    weather = {
      name     = "energy-weather-collect-weather"
      module   = "energy_weather.collectors.weather"
      schedule = "5 * * * *"
    }
    energy = {
      name     = "energy-weather-collect-energy"
      module   = "energy_weather.collectors.energy"
      schedule = "20 * * * *"
    }
  }
}

data "google_service_account" "api" {
  project    = var.project_id
  account_id = "energy-weather-api"
}

data "google_service_account" "collectors" {
  project    = var.project_id
  account_id = "energy-weather-collectors"
}

resource "google_service_account" "dashboard" {
  project      = var.project_id
  account_id   = "energy-weather-dashboard"
  display_name = "Energy Weather dashboard runtime"
  description  = "Identité sans accès à la base, utilisée par Streamlit."
}

resource "google_service_account" "scheduler" {
  project      = var.project_id
  account_id   = "energy-weather-scheduler"
  display_name = "Energy Weather scheduler"
  description  = "Identité autorisée uniquement à déclencher les collecteurs Cloud Run."
}

resource "google_secret_manager_secret" "database_url" {
  project   = var.project_id
  secret_id = "energy-weather-database-url"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

resource "google_secret_manager_secret_iam_member" "api_database_url" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "collectors_database_url" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_service_account.collectors.email}"
}

resource "google_cloud_run_v2_job" "migrate" {
  project  = var.project_id
  name     = "energy-weather-migrate"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = data.google_service_account.collectors.email
      timeout         = "600s"
      max_retries     = 1

      containers {
        image   = local.api_image
        command = ["alembic"]
        args    = ["upgrade", "head"]

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "APP_ENV"
          value = "production"
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = google_secret_manager_secret_version.database_url.version
            }
          }
        }

      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.collectors_database_url,
  ]
}

resource "google_cloud_run_v2_service" "api" {
  project  = var.project_id
  name     = "energy-weather-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  deletion_protection = false

  template {
    service_account = data.google_service_account.api.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = local.api_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "APP_ENV"
        value = "production"
      }

      env {
        name  = "APP_LOG_FORMAT"
        value = "json"
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = google_secret_manager_secret_version.database_url.version
          }
        }
      }

    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.api_database_url,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_api" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "dashboard" {
  project  = var.project_id
  name     = "energy-weather-dashboard"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  deletion_protection = false

  template {
    service_account = google_service_account.dashboard.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = local.dashboard_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "API_BASE_URL"
        value = "${google_cloud_run_v2_service.api.uri}/api/v1"
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_dashboard" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.dashboard.location
  name     = google_cloud_run_v2_service.dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "collectors" {
  for_each = local.collector_jobs

  project  = var.project_id
  name     = each.value.name
  location = var.region

  deletion_protection = false

  template {
    task_count  = 1
    parallelism = 1

    template {
      service_account = data.google_service_account.collectors.email
      timeout         = "600s"
      max_retries     = 2

      containers {
        image   = local.api_image
        command = ["python"]
        args    = ["-m", each.value.module]

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "APP_ENV"
          value = "production"
        }

        env {
          name  = "APP_LOG_FORMAT"
          value = "json"
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = google_secret_manager_secret_version.database_url.version
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.collectors_database_url,
  ]
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  for_each = local.collector_jobs

  project  = var.project_id
  location = google_cloud_run_v2_job.collectors[each.key].location
  name     = google_cloud_run_v2_job.collectors[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "collectors" {
  for_each = local.collector_jobs

  project          = var.project_id
  region           = var.region
  name             = "schedule-${each.value.name}"
  description      = "Déclenche automatiquement le collecteur ${each.key}."
  schedule         = each.value.schedule
  time_zone        = "Europe/Paris"
  attempt_deadline = "180s"
  paused           = var.schedulers_paused

  retry_config {
    retry_count          = 2
    min_backoff_duration = "30s"
    max_backoff_duration = "300s"
    max_doublings        = 2
  }

  http_target {
    http_method = "POST"
    uri = join("", [
      "https://run.googleapis.com/v2/projects/${var.project_id}",
      "/locations/${var.region}/jobs/${google_cloud_run_v2_job.collectors[each.key].name}:run",
    ])
    body = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_cloud_run_v2_job_iam_member.scheduler_invoker,
  ]
}
