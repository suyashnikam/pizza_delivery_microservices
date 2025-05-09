pipeline {
    agent any
    
    triggers {
        pollSCM('H/5 * * * *')
    }
    
    environment {
        DOCKER_REGISTRY = 'suyashnikam1998'
        DOCKER_CREDENTIALS_ID = 'dockerhub-credentials'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout([$class: 'GitSCM',
                    branches: [[name: '*/development']],
                    userRemoteConfigs: [[
                        url: 'https://github.com/suyashnikam/pizza_delivery_microservices.git'
                    ]],
                    extensions: [
                        [$class: 'CleanBeforeCheckout'],
                        [$class: 'CleanCheckout']
                    ]
                ])
            }
        }
        
        stage('Setup Python') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip
                    pip install virtualenv
                '''
            }
        }
        
        stage('Build') {
            parallel {
                stage('Auth Service') {
                    steps {
                        dir('auth-service') {
                            sh '''
                                python3 -m venv venv
                                . venv/bin/activate
                                pip install -r requirements.txt
                            '''
                        }
                    }
                }
                stage('Pizza Service') {
                    steps {
                        dir('pizza-service') {
                            sh '''
                                python3 -m venv venv
                                . venv/bin/activate
                                pip install -r requirements.txt
                            '''
                        }
                    }
                }
                stage('Order Service') {
                    steps {
                        dir('order-service') {
                            sh '''
                                python3 -m venv venv
                                . venv/bin/activate
                                pip install -r requirements.txt
                            '''
                        }
                    }
                }
                stage('Outlet Service') {
                    steps {
                        dir('outlet-service') {
                            sh '''
                                python3 -m venv venv
                                . venv/bin/activate
                                pip install -r requirements.txt
                            '''
                        }
                    }
                }
                stage('Delivery Service') {
                    steps {
                        dir('delivery-service') {
                            sh '''
                                python3 -m venv venv
                                . venv/bin/activate
                                pip install -r requirements.txt
                            '''
                        }
                    }
                }
            }
        }
        
        stage('Build Docker Images') {
            steps {
                script {
                    def services = ['auth-service', 'pizza-service', 'order-service', 'outlet-service', 'delivery-service']
                    services.each { service ->
                        dir(service) {
                            docker.build("${DOCKER_REGISTRY}/${service}:${BUILD_NUMBER}")
                            docker.build("${DOCKER_REGISTRY}/${service}:latest")
                        }
                    }
                }
            }
        }
        
        stage('Push Docker Images') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: DOCKER_CREDENTIALS_ID, 
                                                    passwordVariable: 'DOCKER_PASSWORD', 
                                                    usernameVariable: 'DOCKER_USERNAME')]) {
                        sh 'echo $DOCKER_PASSWORD | docker login --username $DOCKER_USERNAME --password-stdin'
                        
                        def services = ['auth-service', 'pizza-service', 'order-service', 'outlet-service', 'delivery-service']
                        services.each { service ->
                            sh "docker push ${DOCKER_REGISTRY}/${service}:${BUILD_NUMBER}"
                            sh "docker push ${DOCKER_REGISTRY}/${service}:latest"
                        }
                    }
                }
            }
        }
        
        stage('Update Docker Compose') {
            steps {
                script {
                    def services = ['auth-service', 'pizza-service', 'order-service', 'outlet-service', 'delivery-service']
                    services.each { service ->
                        sh "sed -i 's|image: ${DOCKER_REGISTRY}/${service}:.*|image: ${DOCKER_REGISTRY}/${service}:${BUILD_NUMBER}|' docker-compose.yml"
                    }
                    
                    writeFile file: 'deploy.sh', text: '''
                        #!/bin/bash
                        docker-compose pull
                        docker-compose up -d
                    '''
                    sh 'chmod +x deploy.sh'
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo '''
                ✅ Pipeline completed successfully!
                To deploy the updated services:
                1️⃣ Pull the latest changes from your repository
                2️⃣ Run the deploy.sh script: ./deploy.sh
            '''
        }
        failure {
            echo '❌ Pipeline failed!'
        }
    }
}
