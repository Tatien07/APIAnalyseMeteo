pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        TEST_IMAGE = "energy-weather-test:${BUILD_NUMBER}"
        API_IMAGE = "energy-weather-api:${BUILD_NUMBER}"
        DASHBOARD_IMAGE = "energy-weather-dashboard:${BUILD_NUMBER}"
    }

    stages {
        stage('Build test image') {
            steps {
                sh 'docker build --target test --tag $TEST_IMAGE .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm $TEST_IMAGE ruff check src tests migrations dashboard'
                sh 'docker run --rm $TEST_IMAGE ruff format --check src tests migrations dashboard'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'docker run --rm $TEST_IMAGE pytest --cov=energy_weather --cov-report=term-missing'
            }
        }

        stage('Build production images') {
            parallel {
                stage('API image') {
                    steps {
                        sh 'docker build --target production --tag $API_IMAGE .'
                    }
                }
                stage('Dashboard image') {
                    steps {
                        sh 'docker build --file dashboard/Dockerfile --tag $DASHBOARD_IMAGE .'
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Quality gates passed and production images built.'
        }
        always {
            sh 'docker image rm $TEST_IMAGE 2>/dev/null || true'
        }
    }
}
