[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$ApiUrl,

    [Parameter(Mandatory = $true)]
    [string[]]$DashboardUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-HttpUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Values,

        [Parameter(Mandatory = $true)]
        [string]$ParameterName
    )

    $candidate = $Values |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -match '^https?://[^\s]+$' } |
        Select-Object -Last 1

    if ([string]::IsNullOrWhiteSpace($candidate)) {
        throw "Aucune URL HTTP valide trouvee dans le parametre $ParameterName."
    }

    return $candidate.TrimEnd('/')
}

$apiBase = Resolve-HttpUrl -Values $ApiUrl -ParameterName 'ApiUrl'
$dashboardBase = Resolve-HttpUrl -Values $DashboardUrl -ParameterName 'DashboardUrl'

function Invoke-ApiCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $url = "$apiBase$Path"
    Write-Host "Verification : $url"
    return Invoke-RestMethod -Uri $url -TimeoutSec 30
}

try {
    $health = Invoke-ApiCheck -Path '/api/v1/health'
    if ($health.status -ne 'ok') {
        throw "L'endpoint health ne renvoie pas le statut ok."
    }

    $readiness = Invoke-ApiCheck -Path '/api/v1/ready'
    if ($readiness.status -ne 'ready' -or $readiness.database -ne 'up') {
        throw "L'API ou PostgreSQL n'est pas pret."
    }

    $freshness = Invoke-ApiCheck -Path '/api/v1/data-freshness'
    if ($freshness.status -ne 'healthy') {
        $weatherStatus = $freshness.weather.status
        $energyStatus = $freshness.energy.status
        throw "Donnees degradees : meteo=$weatherStatus, energie=$energyStatus."
    }

    $analytics = Invoke-ApiCheck -Path '/api/v1/analytics/weather-energy?hours=24'
    if ($null -eq $analytics.points_count) {
        throw "La reponse analytique ne contient pas points_count."
    }

    Write-Host "Verification : $dashboardBase"
    $dashboard = Invoke-WebRequest -Uri $dashboardBase -TimeoutSec 30 -UseBasicParsing
    if ($dashboard.StatusCode -ne 200) {
        throw "Le dashboard renvoie le statut HTTP $($dashboard.StatusCode)."
    }

    Write-Host ''
    Write-Host 'Tous les tests post-deploiement ont reussi.' -ForegroundColor Green
    Write-Host "Fraicheur : meteo=$($freshness.weather.status), energie=$($freshness.energy.status)"
    Write-Host "Analyse : $($analytics.points_count) points communs sur 24 heures"
}
catch {
    Write-Error "Echec du test post-deploiement : $($_.Exception.Message)"
    exit 1
}
