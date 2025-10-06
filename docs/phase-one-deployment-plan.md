# PulseStream: Phase One Deployment Plan

This document outlines the features available in Phase One of PulseStream and provides a guide for external API testing.

## Phase One Features

The initial deployment of PulseStream includes the following core functionalities:

- **Multi-Tenant Architecture**: The system supports multiple tenants, with data isolation between them. Each tenant has its own users and resources.
- **User Authentication**: Secure user authentication is implemented using JWT (JSON Web Tokens). Users can register, log in, and receive tokens to access protected endpoints.
- **Event Ingestion API**: A robust API for ingesting events into the system. It supports both single and batch event ingestion.
- **Asynchronous Processing**: Ingested events are processed asynchronously by a Celery worker, ensuring high availability and performance of the ingestion endpoint.
- **Data Persistence**: Events and user data are stored in a PostgreSQL database.

## External API Testing Guide

This guide provides instructions on how to interact with the PulseStream API.

### Prerequisites

- The PulseStream application must be running.
- You will need a command-line tool like `curl` to make HTTP requests.
- The API is prefixed with `/api/v1`.

### Step 1: Register a New Tenant

First, create a tenant and an owner user. The `slug` you choose will be used to identify your tenant during login.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register/tenant" \
-H "Content-Type: application/json" \
-d '{
  "name": "My Test Company",
  "slug": "my-test-company",
  "contact_email": "owner@testcompany.com"
}'
```

The response will provide a temporary password for the owner user.

### Step 2: Log In and Get an Access Token

Next, use the owner's email, the temporary password, and the tenant slug to log in. This will return a JWT access token.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
-H "Content-Type: application/json" \
-d '{
  "email": "owner@testcompany.com",
  "password": "YOUR_TEMPORARY_PASSWORD",
  "tenant_slug": "my-test-company"
}'
```

The response will contain an `access_token`. Copy this token for the next step.

### Step 3: Ingest an Event

Finally, use the `access_token` to authenticate and send an event to the ingestion API.

Replace `YOUR_ACCESS_TOKEN` with the token you received in the previous step.

```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/events" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-d '{
  "event_type": "api_call",
  "title": "User Login Attempt",
  "message": "User attempted to log in.",
  "severity": "info",
  "source": {
    "service": "auth-service",
    "endpoint": "/api/v1/auth/login",
    "method": "POST",
    "version": "1.0"
  },
  "context": {
    "user_id": "user-123",
    "ip_address": "192.168.1.100"
  },
  "metrics": {
    "response_time_ms": 150.5,
    "status_code": 200
  },
  "payload": {
    "username": "testuser"
  }
}'
```

### Expected Outcome

If the request is successful, you will receive a `200 OK` response with a body similar to this, indicating that the event has been successfully queued for processing:

```json
{
  "success": true,
  "event_id": "...",
  "ingested_at": "...",
  "processing_status": "queued",
  "message": "Event ingested successfully"
}
```

## Environment Setup

To run the application for testing, you need to create a `.env` file. An example file is provided as `env.example`.

You can copy the example file to create your own configuration:

```bash
cp env.example .env
```

After copying, you must review and update the variables in the `.env` file with your specific settings for the database, Redis, and other services.
