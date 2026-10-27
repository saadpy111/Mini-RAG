# Mini-RAG

A minimal Retrieval-Augmented Generation (RAG) application for document processing and question answering.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Overview

Mini-RAG is a backend application built with FastAPI that provides the foundation for document processing and retrieval-augmented question answering.

The project uses MongoDB for data persistence and supports processing PDF and TXT documents.

### Key Features

- RESTful API built with FastAPI.
- Asynchronous MongoDB access using PyMongo.
- PDF and TXT document processing.
- Repository and business logic layers.
- Consistent error handling using the Result Pattern.
- Unit and integration tests.
- Isolated MongoDB databases for repository integration tests.

## Prerequisites

Make sure the following tools are installed:

- Python 3.10 or later.
- Miniconda or another Python environment manager.
- MongoDB for database-dependent functionality and integration tests.
- Git.

**Note:** Python 3.10+ is recommended for compatibility with the current dependency stack. Use the Python version supported by your project's pinned dependencies.

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Mini-RAG
```

Replace `<repository-url>` with the actual Git repository URL.

### 2. Create and Activate a Conda Environment

Create a dedicated environment:

```bash
conda create -n mini-rag python=3.10
```

Activate it:

```bash
conda activate mini-rag
```

Verify the Python version:

```bash
python --version
```

### 3. Install Dependencies

Install the project's required packages:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Environment Configuration

### 1. Create the Environment File

On Linux or macOS:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 2. Configure Environment Variables

Open `.env` and configure the variables required by the application, such as:

- MongoDB connection URI.
- MongoDB database name.
- OpenAI API key, if required by the configured application features.

Use `.env.example` as the source of truth for the required variable names.

**Security:** Never commit `.env` or expose API keys, database credentials, or other secrets in your repository. Keep `.env.example` limited to variable names and safe placeholder values.

## Running the Application

Make sure your Conda environment is active and the required services are available.

Start the FastAPI development server from the project root:

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 5000
```

The application will be available at:

- API base URL: `http://localhost:5000`
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

The `--reload` option automatically restarts the server when source files change. Use it for local development, not production deployment.

## API Documentation

FastAPI automatically generates interactive API documentation.

- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`
- **OpenAPI schema:** `/openapi.json`

Use Swagger UI to inspect available endpoints, review request and response schemas, and send test requests.

## Testing

The project contains unit tests and integration tests.

### Test Organization

```text
tests/
├── conftest.py
├── unit/
│   ├── business_logic/
│   ├── helpers/
│   ├── services/
│   └── validators/
└── integration/
    ├── api/
    └── repositories/
```

### 1. Run All Tests

From the project root:

```bash
python -m pytest -q
```

### 2. Run Unit Tests Only

Unit tests run without the integration-test marker:

```bash
python -m pytest -q -m "not integration"
```

### 3. Run Integration Tests Only

```bash
python -m pytest -q -m integration
```

Repository integration tests require a reachable MongoDB instance.

### MongoDB Test Database Isolation

Repository integration tests use a uniquely named test database following this pattern:

```text
mini_rag_test_<uuid>
```

The test infrastructure validates the database name and prevents cleanup operations from targeting the configured development database.

Test collections are cleaned between tests, and the isolated test database is dropped during teardown.

**Important:** Configure the MongoDB URI to point to a dedicated development or test MongoDB instance. Never run integration tests against a production MongoDB server. Database-name safeguards do not replace proper database access controls.

### Expected Test Results

A successful test run exits with status code `0`. Pytest displays the number of passed, failed, skipped, and deselected tests.

The exact counts may change as the test suite evolves.

## Project Structure

The following is a high-level overview of the project's main directories. Refer to the actual repository for the complete structure.

```text
Mini-RAG/
├── src/
│   ├── business_logic/
│   ├── helpers/
│   ├── models/
│   ├── repositories/
│   ├── routes/
│   ├── services/
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

Responsibilities may include:

- `business_logic/`: Application use cases and business rules.
- `repositories/`: Database operations and persistence.
- `routes/`: HTTP endpoints and request handling.
- `services/`: Document processing and supporting services.
- `helpers/`: Shared configuration and utility functions.
- `tests/`: Unit tests and integration tests.

Some directories may contain additional subdirectories or files depending on the current implementation.

## Troubleshooting

### ModuleNotFoundError

Run commands from the project root and verify that the Conda environment is activated.

```bash
python -c "import sys; print(sys.executable)"
```

### MongoDB Connection Errors

- Verify that MongoDB is running.
- Check the MongoDB URI in `.env`.
- Confirm the configured credentials and authentication database.
- Ensure the MongoDB server is reachable from the environment running the tests.

### Integration Tests Are Skipped

Integration tests may be skipped if the test MongoDB server is unavailable. Review the pytest output for the reason before treating the test suite as fully verified.

### Dependency Installation Errors

Check the Python version and install the dependencies using the project's requirements file:

```bash
python --version
python -m pip install -r requirements.txt
```

## Contributing

Before submitting changes:

1. Run the relevant unit tests.
2. Run integration tests when database-related behavior changes.
3. Run the complete test suite.
4. Review your changes and ensure no secrets or local environment files are committed.

```bash
python -m pytest -q
git diff --check
git status
```

## License

Add the project's license information here if a license has been selected.