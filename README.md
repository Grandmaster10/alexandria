# Alexandria

**Overview**
Alexandria is an AI-powered recommendation and cataloging platform for books. It uses a dedicated sentence transformer engine to generate text embeddings, allowing users to query a cloud-hosted library using natural language rather than exact keyword matches.

## Architecture
* **Frontend:** Streamlit (Port 8501)
* **Backend API:** NestJS & Prisma (Port 3001)
* **ML Engine:** FastAPI (Port 8000)
* **Database:** PostgreSQL (Cloud-hosted)

## Prerequisites
* Docker
* Docker Compose

## Setup and Execution

1. Clone the repository to your local machine.
2. Copy the `.env.example` file to create your own `.env` file, and add your cloud database connection string:
   `cp .env.example .env`
3. Build and launch the container cluster:
   `docker-compose up --build`

## Local Access
Once the containers are successfully running, the services will be available at the following local addresses:
* **Streamlit UI:** http://localhost:8501
* **NestJS API:** http://localhost:3001
* **FastAPI Engine:** http://localhost:8000

## Development Notes
* The application utilizes Docker Compose's internal DNS for cross-container communication (e.g., the frontend accesses the backend via `http://backend-api:3001`).
* Windows host volumes (like `node_modules` and `dist`) are explicitly blocked via `.dockerignore` to ensure pristine Linux builds inside the containers.
