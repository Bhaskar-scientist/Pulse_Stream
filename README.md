# PulseStream

Multi-tenant, real-time API monitoring and analytics platform.

## Overview

PulseStream is an enterprise-grade observability system that ingests streaming data from various APIs, processes them through complex pipelines, and provides dashboards, reports, and AI-powered insights.

## Features

- **Multi-tenant Architecture**: Secure isolation between different organizations
- **Real-time Event Processing**: High-performance event ingestion and processing
- **JWT Authentication**: Secure authentication with role-based access control
- **TimescaleDB Integration**: Optimized for time-series data
- **Background Processing**: Celery-based async task processing
- **Comprehensive Monitoring**: Health checks, metrics, and structured logging
- **WebSocket Integration**: Real-time data streaming from external APIs (Coinbase)

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Pulse_Stream
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Set up environment**:
   ```bash
   cp env.example .env
   poetry run python scripts/setup_env.py
   ```

4. **Start services**:
   ```bash
   docker-compose up -d
   ```

5. **Run migrations**:
   ```bash
   poetry run alembic upgrade head
   ```

6. **Start the application**:
   ```bash
   poetry run uvicorn main:app --reload
   ```

## Coinbase Market Data Integration

PulseStream includes a WebSocket bridge that ingests real-time market data from Coinbase Exchange.

### Features
- Real-time BTC-USD and ETH-USD price updates
- Automatic reconnection and error handling
- Asynchronous event forwarding to PulseStream
- Comprehensive logging and monitoring

### Setup

1. **Install bridge dependencies**:
   ```bash
   pip install -r coinbase_bridge_requirements.txt
   ```

2. **Configure API key** in `coinbase_bridge.py`:
   ```python
   API_KEY = "your-pulsestream-api-key"
   ```

3. **Test the setup**:
   ```bash
   python scripts/test_coinbase_bridge.py
   ```

4. **Run the bridge**:
   ```bash
   python coinbase_bridge.py
   ```

For detailed setup instructions, see [Coinbase Bridge Setup Guide](docs/coinbase-bridge-setup.md).

## Development

- **Code Quality**: Black, isort, flake8, mypy
- **Testing**: pytest with coverage
- **Documentation**: Comprehensive guides and inline docs
- **Security**: Automated secret generation and validation

## Architecture

- **FastAPI**: Modern, fast web framework
- **PostgreSQL + TimescaleDB**: Primary database with time-series optimization
- **Redis**: Caching and message brokering
- **Celery**: Background task processing
- **Docker**: Containerized development environment

## License

MIT License
