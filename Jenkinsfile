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
        string(
            name: 'IMAGE_TAG',
            defaultValue: '',
            description: 'Tag optionnel. Vide = build-NUMERO.'
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
