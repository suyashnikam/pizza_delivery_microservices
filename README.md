# Pizza Delivery Microservices

A microservices-based pizza delivery system built with Python FastAPI and Docker.

## Architecture

The system consists of the following microservices:

- **Auth Service**: Handles user authentication and authorization
- **Pizza Service**: Manages pizza menu and inventory
- **Order Service**: Processes and tracks orders
- **Outlet Service**: Manages pizza outlets and their operations
- **Delivery Service**: Handles delivery tracking and management

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Jenkins (for CI/CD)

## Project Structure

```
pizza-delivery-api/
├── auth-service/
├── pizza-service/
├── order-service/
├── outlet-service/
├── delivery-service/
├── docker-compose.yml
└── Jenkinsfile
```

## Setup and Deployment

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/suyashnikam/pizza_delivery_microservices.git
   cd pizza_delivery_microservices
   ```

2. Start the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

### CI/CD Pipeline

The project uses Jenkins for continuous integration and deployment. The pipeline:

1. Monitors the development branch for changes
2. Builds Docker images for each service
3. Pushes images to DockerHub
4. Updates docker-compose.yml with new image versions

To deploy updates:
1. Pull the latest changes
2. Run the deploy script:
   ```bash
   ./deploy.sh
   ```

## Services

### Auth Service
- User authentication
- JWT token management
- User roles and permissions

### Pizza Service
- Pizza menu management
- Inventory tracking
- Price management

### Order Service
- Order processing
- Order status tracking
- Payment integration

### Outlet Service
- Outlet management
- Staff management
- Operating hours

### Delivery Service
- Delivery tracking
- Delivery agent management
- Route optimization

## API Documentation

Each service provides its own API documentation at:
- Auth Service: `http://localhost:8001/docs`
- Pizza Service: `http://localhost:8002/docs`
- Order Service: `http://localhost:8003/docs`
- Outlet Service: `http://localhost:8004/docs`
- Delivery Service: `http://localhost:8005/docs`

## Contributing

1. Create a feature branch from development
2. Make your changes
3. Submit a pull request

## License

This project is licensed under the MIT License.



