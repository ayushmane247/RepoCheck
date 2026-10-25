pipeline {
    agent any

    options {
        skipDefaultCheckout(false)
        disableConcurrentBuilds()
        timeout(time: 10, unit: 'MINUTES')
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
    }

    post {
        always {
            echo 'RepoCheck CI pipeline finished. Check the stage results above.'
        }
    }
}
