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

resource "google_cloud_run_v2_job" "freshness_check" {
  project  = var.project_id
  name     = "energy-weather-check-freshness"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = data.google_service_account.collectors.email
      timeout         = "300s"
      max_retries     = 1

      containers {
        image   = local.api_image
        command = ["python"]
        args    = ["-m", "energy_weather.monitoring"]

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
          name  = "FRESHNESS_THRESHOLD_MINUTES"
          value = tostring(var.freshness_threshold_minutes)
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

resource "google_cloud_run_v2_job_iam_member" "scheduler_invokes_freshness_check" {
  project  = var.project_id
  location = google_cloud_run_v2_job.freshness_check.location
  name     = google_cloud_run_v2_job.freshness_check.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "freshness_check" {
  project          = var.project_id
  region           = var.region
  name             = "schedule-energy-weather-check-freshness"
  description      = "Vérifie que les collectes météo et énergie sont récentes."
  schedule         = "40 * * * *"
  time_zone        = "Europe/Paris"
  attempt_deadline = "180s"
  paused           = var.schedulers_paused

  retry_config {
    retry_count          = 1
    min_backoff_duration = "60s"
    max_backoff_duration = "300s"
    max_doublings        = 1
  }

  http_target {
    http_method = "POST"
    uri = join("", [
      "https://run.googleapis.com/v2/projects/${var.project_id}",
      "/locations/${var.region}/jobs/${google_cloud_run_v2_job.freshness_check.name}:run",
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
    google_cloud_run_v2_job_iam_member.scheduler_invokes_freshness_check,
  ]
}

resource "google_logging_metric" "application_failures" {
  project     = var.project_id
  name        = "energy_weather/application_failures"
  description = "Nombre d'échecs structurés émis par l'API et les collecteurs."
  filter = join("\n", [
    "(resource.type=\"cloud_run_job\" OR resource.type=\"cloud_run_revision\")",
    "(jsonPayload.event=\"weather_collection_failed\" OR",
    " jsonPayload.event=\"energy_collection_failed\" OR",
    " jsonPayload.event=\"http_request_failed\" OR",
    " jsonPayload.event=\"data_freshness_failed\" OR",
    " jsonPayload.event=\"data_freshness_check_failed\")",
  ])

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Energy Weather application failures"

    labels {
      key         = "event"
      value_type  = "STRING"
      description = "Type d'échec structuré."
    }
  }

  label_extractors = {
    event = "EXTRACT(jsonPayload.event)"
  }
}

resource "google_monitoring_notification_channel" "email" {
  count = var.alert_email == "" ? 0 : 1

  project      = var.project_id
  display_name = "Energy Weather operations email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "application_failure" {
  project      = var.project_id
  display_name = "Energy Weather - application failure"
  combiner     = "OR"
  severity     = "ERROR"
  enabled      = true

  conditions {
    display_name = "Structured failure log detected"

    condition_matched_log {
      filter = join("\n", [
        "(resource.type=\"cloud_run_job\" OR resource.type=\"cloud_run_revision\")",
        "(jsonPayload.event=\"weather_collection_failed\" OR",
        " jsonPayload.event=\"energy_collection_failed\" OR",
        " jsonPayload.event=\"http_request_failed\" OR",
        " jsonPayload.event=\"data_freshness_failed\" OR",
        " jsonPayload.event=\"data_freshness_check_failed\")",
      ])
      label_extractors = {
        event = "EXTRACT(jsonPayload.event)"
      }
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      Un échec a été journalisé par Energy Weather Monitor.

      1. Ouvrir Cloud Logging et filtrer les événements `*_failed`.
      2. Vérifier l'exécution Cloud Run concernée et son `run_id` ou `request_id`.
      3. Contrôler Neon et relancer le job si la cause était temporaire.
    EOT
  }

  alert_strategy {
    notification_rate_limit {
      period = "3600s"
    }
    auto_close = "604800s"
  }

  notification_channels = var.alert_email == "" ? [] : [
    google_monitoring_notification_channel.email[0].name,
  ]
}
