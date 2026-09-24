pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
    }

    parameters {
        booleanParam(
            name: 'PUBLISH_IMAGES',
            defaultValue: false,
            description: 'Publier les images validées dans Artifact Registry.'
        )
        booleanParam(
            name: 'DEPLOY_TO_GCP',
            defaultValue: false,
            description: 'Appliquer Terraform après validation humaine.'
        )
        string(
            name: 'IMAGE_TAG',
            defaultValue: '',
            description: 'Tag optionnel. Vide = build-NUMERO.'
        )
        booleanParam(
            name: 'RUN_CLOUD_SMOKE_TEST',
            defaultValue: false,
            description: 'Vérifier une version déjà déployée dans Cloud Run.'
        )
        string(
            name: 'CLOUD_API_URL',
            defaultValue: '',
            description: 'URL Cloud Run de FastAPI, requise pour le test cloud.'
        )
        string(
            name: 'CLOUD_DASHBOARD_URL',
            defaultValue: '',
            description: 'URL Cloud Run de Streamlit, requise pour le test cloud.'
        )
    }

    environment {
        PROJECT_ID = 'energy-weather-2129519'
        REGION = 'europe-west1'
        REPOSITORY = 'energy-weather'
        REGISTRY = 'europe-west1-docker.pkg.dev'
        TEST_IMAGE = "energy-weather-test:${BUILD_NUMBER}"
        INTEGRATION_PROJECT = "energy-weather-it-${BUILD_NUMBER}"
    }

    stages {
        stage('Prepare release') {
            steps {
                script {
                    def requestedTag = params.IMAGE_TAG.trim()
                    env.RELEASE_TAG = requestedTag ?: "build-${env.BUILD_NUMBER}"

                    if (!(env.RELEASE_TAG ==~ /[A-Za-z0-9][A-Za-z0-9_.-]{0,127}/)) {
                        error('IMAGE_TAG invalide. Utilisez uniquement lettres, chiffres, _, . et -.')
                    }
                    if (params.DEPLOY_TO_GCP && !params.PUBLISH_IMAGES) {
                        error('DEPLOY_TO_GCP exige PUBLISH_IMAGES=true.')
                    }

                    if (params.RUN_CLOUD_SMOKE_TEST) {
                        if (!(params.CLOUD_API_URL ==~ /^https:\/\/[^\s]+$/)) {
                            error('CLOUD_API_URL doit contenir une URL HTTPS valide.')
                        }
                        if (!(params.CLOUD_DASHBOARD_URL ==~ /^https:\/\/[^\s]+$/)) {
                            error('CLOUD_DASHBOARD_URL doit contenir une URL HTTPS valide.')
                        }
                    }

                    env.API_IMAGE = "${env.REGISTRY}/${env.PROJECT_ID}/${env.REPOSITORY}/api:${env.RELEASE_TAG}"
                    env.DASHBOARD_IMAGE = "${env.REGISTRY}/${env.PROJECT_ID}/${env.REPOSITORY}/dashboard:${env.RELEASE_TAG}"
                }
                echo "Version de livraison : ${env.RELEASE_TAG}"
            }
        }

        stage('Build test image') {
            steps {
                sh 'docker build --target test --tag "$TEST_IMAGE" .'
            }
        }

        stage('Quality gates') {
            parallel {
                stage('Lint') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE" ruff check src tests migrations dashboard'
                        sh 'docker run --rm "$TEST_IMAGE" ruff format --check src tests migrations dashboard'
                    }
                }
                stage('Unit tests') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE" pytest -m "not integration" --cov=energy_weather --cov-report=term-missing'
                    }
                }
            }
        }

        stage('PostgreSQL integration tests') {
            steps {
                sh '''
                    docker compose -p "$INTEGRATION_PROJECT" --profile integration \
                      run --build --rm integration-test
                '''
            }
            post {
                always {
                    sh '''
                        docker compose -p "$INTEGRATION_PROJECT" --profile integration \
                          down --volumes --remove-orphans || true
                    '''
                }
            }
        }

        stage('Build production images') {
            parallel {
                stage('API image') {
                    steps {
                        sh 'docker build --target production --tag "$API_IMAGE" .'
                    }
                }
                stage('Dashboard image') {
                    steps {
                        sh 'docker build --file dashboard/Dockerfile --tag "$DASHBOARD_IMAGE" .'
                    }
                }
            }
        }

        stage('Authenticate to Artifact Registry') {
            when {
                expression { params.PUBLISH_IMAGES }
            }
            steps {
                sh '''
                    gcloud auth application-default print-access-token \
                      | docker login -u oauth2accesstoken --password-stdin "https://$REGISTRY"
                '''
            }
        }

        stage('Publish immutable images') {
            when {
                expression { params.PUBLISH_IMAGES }
            }
            parallel {
                stage('Publish API') {
                    steps {
                        retry(2) {
                            sh 'docker push "$API_IMAGE"'
                        }
                    }
                }
                stage('Publish dashboard') {
                    steps {
                        retry(2) {
                            sh 'docker push "$DASHBOARD_IMAGE"'
                        }
                    }
                }
            }
        }

        stage('Cloud smoke test') {
            when {
                expression { params.RUN_CLOUD_SMOKE_TEST }
            }
            steps {
                sh '''
                    docker run --rm "$TEST_IMAGE" \
                      python -m energy_weather.smoke \
                      --api-url "$CLOUD_API_URL" \
                      --dashboard-url "$CLOUD_DASHBOARD_URL"
                '''
            }
        }

        stage('Terraform plan') {
            when { expression { params.DEPLOY_TO_GCP } }
            steps {
                sh '''
                    terraform -chdir=infrastructure/platform init -input=false
                    terraform -chdir=infrastructure/platform plan -input=false \
                      -var-file=/run/secrets/platform.tfvars \
                      -var="api_image_tag=$RELEASE_TAG" \
                      -var="dashboard_image_tag=$RELEASE_TAG" \
                      -out=jenkins.tfplan
                    terraform -chdir=infrastructure/platform show -no-color jenkins.tfplan
                '''
            }
        }

        stage('Approve production deployment') {
            when { expression { params.DEPLOY_TO_GCP } }
            input {
                message "Appliquer ce plan Terraform dans GCP ?"
                ok "Déployer"
            }
            steps { echo "Déploiement de ${env.RELEASE_TAG} approuvé." }
        }

        stage('Terraform apply') {
            when { expression { params.DEPLOY_TO_GCP } }
            steps {
                sh 'terraform -chdir=infrastructure/platform apply -input=false jenkins.tfplan'
            }
        }

        stage('Post-deployment smoke test') {
            when { expression { params.DEPLOY_TO_GCP } }
            steps {
                sh '''
                    API_URL=$(terraform -chdir=infrastructure/platform output -raw api_url)
                    DASHBOARD_URL=$(terraform -chdir=infrastructure/platform output -raw dashboard_url)
                    docker run --rm "$TEST_IMAGE" python -m energy_weather.smoke \
                      --api-url "$API_URL" --dashboard-url "$DASHBOARD_URL"
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline réussi. Tag produit : ${env.RELEASE_TAG}"
            echo 'Le déploiement reste contrôlé par Terraform.'
        }
        always {
            sh 'docker image rm "$TEST_IMAGE" 2>/dev/null || true'
        }
    }
}
