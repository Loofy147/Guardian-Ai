# Agent Instructions

This document provides instructions for AI agents working on the Guardian AI repository.

## Toolchain

- **Python:** 3.9
- **Node.js:** 16
- **pylint:** 4.0.3
- **eslint:** 8.57.1
- **pip-audit:** 2.9.0
- **npm:** 11.6.2
- **semantic-release:** 23.0.0

## Environment Variables

- `HUGGING_FACE_TOKEN`: A Hugging Face Hub authentication token. This is required for the backend to download the time-series prediction model.
- `DATABASE_URL`: The URL for the PostgreSQL database. Defaults to a local SQLite database.
- `REDIS_URL`: The URL for the Redis server. Defaults to `redis://redis:6379/0`.
- `SECRET_KEY`: A secret key for signing JWTs. Defaults to a development key.

## Operational Procedures

### Running Tests

To run the backend tests, use the following command:

```bash
pytest
```

To run the frontend tests, use the following command:

```bash
cd frontend
npm test
```

### Linting

To lint the Python code, use the following command:

```bash
pylint guardian_ai tests
```

To lint the JavaScript code, use the following command:

```bash
cd frontend
./node_modules/.bin/eslint src/
```

### Security Audits

To audit the Python dependencies, use the following command:

```bash
pip-audit
```

To audit the Node.js dependencies, use the following command:

```bash
cd frontend
npm audit
```
