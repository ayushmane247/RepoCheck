
pipeline {
    agent any

    options {
        skipDefaultCheckout(false)
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Check Environment') {
            steps {
                bat '''
                    echo === Git ===
                    git --version

                    echo === Python ===
                    python --version

                    echo === Node.js ===
                    node --version

                    echo === npm ===
                    npm --version
                '''
            }
        }

        stage('Check Docker') {
            steps {
                bat 'docker info'
            }
        }

        stage('Backend Tests') {
            steps {
                bat '''
                    python -m venv .venv-ci
                    .venv-ci\\Scripts\\python.exe -m pip install --upgrade pip
                    .venv-ci\\Scripts\\python.exe -m pip install -r requirements.txt
                    .venv-ci\\Scripts\\python.exe -m pytest -q
                '''
            }
        }

        stage('Frontend Install') {
            steps {
                dir('frontend') {
                    bat 'npm ci'
                }
            }
        }

        stage('Frontend Tests') {
            steps {
                dir('frontend') {
                    bat 'npm test'
                }
            }
        }

        stage('Frontend Production Build') {
            steps {
                dir('frontend') {
                    bat 'npm run build'
                }
            }
        }
    }

    post {
        success {
            echo 'All RepoCheck CI stages passed.'
        }
        failure {
            echo 'RepoCheck CI failed. Inspect the first failed stage and its console output.'
        }
        always {
            echo 'RepoCheck CI pipeline finished.'
        }
    }
}
