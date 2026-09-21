@echo off
setlocal

where gcloud >nul 2>nul
if errorlevel 1 (
    echo ERREUR: gcloud est introuvable dans ce terminal.
    exit /b 1
)

where docker >nul 2>nul
if errorlevel 1 (
    echo ERREUR: Docker est introuvable dans ce terminal.
    exit /b 1
)

for /f "delims=" %%i in ('gcloud config get-value project 2^>nul') do set "PROJECT_ID=%%i"
if not defined PROJECT_ID (
    echo ERREUR: aucun projet GCP actif.
    echo Executez: gcloud config set project VOTRE_PROJECT_ID
    exit /b 1
)

if "%PROJECT_ID%"=="(unset)" (
    echo ERREUR: aucun projet GCP actif.
    echo Executez: gcloud config set project VOTRE_PROJECT_ID
    exit /b 1
)

set "REGION=europe-west1"
set "REPOSITORY=energy-weather"
set "IMAGE_TAG=%~1"
if not defined IMAGE_TAG set "IMAGE_TAG=latest"

set "REGISTRY=%REGION%-docker.pkg.dev"
set "IMAGE_URI=%REGISTRY%/%PROJECT_ID%/%REPOSITORY%/api:%IMAGE_TAG%"

echo Projet : %PROJECT_ID%
echo Image  : %IMAGE_URI%

echo [1/3] Configuration de l'authentification Docker...
call gcloud auth configure-docker "%REGISTRY%" --quiet
if errorlevel 1 exit /b 1

echo [2/3] Construction de l'image de production...
docker build --target production --tag "%IMAGE_URI%" .
if errorlevel 1 exit /b 1

echo [3/3] Envoi de l'image dans Artifact Registry...
docker push "%IMAGE_URI%"
if errorlevel 1 exit /b 1

echo.
echo Publication terminee.
echo IMAGE_URI=%IMAGE_URI%
