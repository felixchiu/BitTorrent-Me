# Makefile for Modern BitTorrent Client
# Based on "Mastering Python Design Patterns" best practices

.PHONY: help install install-dev test test-cov lint format type-check clean run build docker-build docker-run docs

# Default target
help:
	@echo "Modern BitTorrent Client - Development Commands"
	@echo "=============================================="
	@echo ""
	@echo "Installation:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test         - Run all tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  test-fast    - Run tests in parallel"
	@echo "  test-design  - Run design pattern tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         - Run all linting tools"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  security     - Run security checks"
	@echo ""
	@echo "Development:"
	@echo "  run          - Start the application"
	@echo "  clean        - Clean up generated files"
	@echo "  build        - Build the application"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo ""
	@echo "Documentation:"
	@echo "  docs         - Build documentation"
	@echo "  docs-serve   - Serve documentation locally"

# Installation
install:
	@echo "Installing production dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "Setting up pre-commit hooks..."
	pre-commit install

# Testing
test:
	@echo "Running all tests..."
	pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=app --cov=design_patterns --cov-report=html --cov-report=term -v

test-fast:
	@echo "Running tests in parallel..."
	pytest tests/ -n auto -v

test-design:
	@echo "Running design pattern tests..."
	pytest tests/test_design_patterns.py -v

test-benchmark:
	@echo "Running performance benchmarks..."
	pytest tests/ --benchmark-only

# Code Quality
lint:
	@echo "Running linting checks..."
	flake8 app.py design_patterns.py tests/
	pylint app.py design_patterns.py --disable=C0114,C0116
	bandit -r . -f json -o bandit-report.json

format:
	@echo "Formatting code..."
	black app.py design_patterns.py tests/ templates/
	isort app.py design_patterns.py tests/

type-check:
	@echo "Running type checks..."
	mypy app.py design_patterns.py --ignore-missing-imports

security:
	@echo "Running security checks..."
	safety check
	pip-audit

# Development
run:
	@echo "Starting BitTorrent client..."
	python app.py

run-dev:
	@echo "Starting BitTorrent client in development mode..."
	uvicorn app:app --reload --host 0.0.0.0 --port 5001

clean:
	@echo "Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/
	rm -rf downloads/* logs/* *.log

build:
	@echo "Building application..."
	python -m py_compile app.py design_patterns.py
	@echo "Build completed successfully!"

# Docker
docker-build:
	@echo "Building Docker image..."
	docker build -t bittorrent-client .

docker-run:
	@echo "Running Docker container..."
	docker run -p 5001:5001 -v $(PWD)/downloads:/app/downloads bittorrent-client

docker-compose-up:
	@echo "Starting services with Docker Compose..."
	docker-compose up -d

docker-compose-down:
	@echo "Stopping services..."
	docker-compose down

# Documentation
docs:
	@echo "Building documentation..."
	sphinx-build -b html docs/ docs/_build/html

docs-serve:
	@echo "Serving documentation..."
	cd docs/_build/html && python -m http.server 8000

# Performance
profile:
	@echo "Profiling application..."
	python -m cProfile -o profile.stats app.py

profile-view:
	@echo "Viewing profile results..."
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"

# Monitoring
monitor:
	@echo "Starting application monitoring..."
	python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')"

# Database
db-migrate:
	@echo "Running database migrations..."
	alembic upgrade head

db-rollback:
	@echo "Rolling back database..."
	alembic downgrade -1

# Git hooks
pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# CI/CD
ci-test:
	@echo "Running CI tests..."
	pytest tests/ --cov=app --cov-report=xml
	black --check app.py design_patterns.py tests/
	isort --check-only app.py design_patterns.py tests/
	mypy app.py design_patterns.py --ignore-missing-imports

# Development utilities
dev-setup:
	@echo "Setting up development environment..."
	make install-dev
	make format
	make type-check
	@echo "Development environment setup complete!"

check-all:
	@echo "Running all checks..."
	make format
	make lint
	make type-check
	make security
	make test-cov
	@echo "All checks completed!"

# Quick start
quick-start:
	@echo "Quick start setup..."
	make install
	make run

# Production
prod-build:
	@echo "Building for production..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	python -m py_compile app.py

prod-run:
	@echo "Running in production mode..."
	uvicorn app:app --host 0.0.0.0 --port 5001 --workers 4

# Backup and restore
backup:
	@echo "Creating backup..."
	tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz downloads/ *.json *.log

restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup filename: " backup_file; \
	tar -xzf $$backup_file

# Health checks
health-check:
	@echo "Performing health checks..."
	@curl -f http://localhost:5001/health || echo "Application not responding"
	@python -c "import psutil; print(f'System health: CPU {psutil.cpu_percent()}%, Memory {psutil.virtual_memory().percent}%')"

# Logs
logs:
	@echo "Viewing application logs..."
	tail -f bittorrent.log

logs-clear:
	@echo "Clearing logs..."
	rm -f *.log
	rm -rf logs/*

# Statistics
stats:
	@echo "Application statistics..."
	@echo "Python files: $$(find . -name '*.py' | wc -l)"
	@echo "Lines of code: $$(find . -name '*.py' -exec wc -l {} + | tail -1)"
	@echo "Test files: $$(find tests/ -name '*.py' | wc -l)"

# Helpers
create-test-torrent:
	@echo "Creating test torrent file..."
	python -c "
import bencodepy
import hashlib
import os

# Create a simple test torrent
info = {
    b'name': b'test.torrent',
    b'piece length': 16384,
    b'length': 1024,
    b'pieces': b'0' * 20
}

torrent_data = {
    b'announce': b'http://localhost:8080/announce',
    b'info': info
}

with open('test.torrent', 'wb') as f:
    f.write(bencodepy.encode(torrent_data))

print('Test torrent created: test.torrent')
"

# Environment
env-setup:
	@echo "Setting up environment variables..."
	@echo "BT_DOWNLOAD_DIR=./downloads" > .env
	@echo "BT_MAX_CONCURRENT_DOWNLOADS=5" >> .env
	@echo "BT_DEFAULT_SPEED_LIMIT=0" >> .env
	@echo "BT_LOG_LEVEL=INFO" >> .env
	@echo "BT_HOST=0.0.0.0" >> .env
	@echo "BT_PORT=5001" >> .env
	@echo "Environment file created: .env"

# Development server with auto-reload
dev:
	@echo "Starting development server with auto-reload..."
	watchmedo auto-restart --patterns="*.py" --recursive -- python app.py

# Package management
update-deps:
	@echo "Updating dependencies..."
	pip install --upgrade -r requirements.txt
	pip install --upgrade -r requirements-dev.txt

freeze-deps:
	@echo "Freezing current dependencies..."
	pip freeze > requirements-frozen.txt

# Testing utilities
test-unit:
	@echo "Running unit tests..."
	pytest tests/ -k "not integration" -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -k "integration" -v

test-performance:
	@echo "Running performance tests..."
	pytest tests/ -k "performance" --benchmark-only

# Code generation
generate-tests:
	@echo "Generating test files..."
	pytest --genscript=tests/generated_tests.py

# Documentation generation
generate-docs:
	@echo "Generating API documentation..."
	python -c "
from app import app
from fastapi.openapi.utils import get_openapi

openapi_schema = get_openapi(
    title='Modern BitTorrent Client API',
    version='2.0.0',
    description='API documentation for the Modern BitTorrent Client',
    routes=app.routes,
)

with open('openapi.json', 'w') as f:
    import json
    json.dump(openapi_schema, f, indent=2)

print('OpenAPI schema generated: openapi.json')
"

# Release
release:
	@echo "Creating release..."
	@read -p "Enter version number: " version; \
	git tag -a v$$version -m "Release v$$version"; \
	git push origin v$$version; \
	echo "Release v$$version created and pushed"

# Debug
debug:
	@echo "Starting debug mode..."
	python -m pdb app.py

debug-remote:
	@echo "Starting remote debug server..."
	python -m debugpy --listen 0.0.0.0:5678 app.py

# Maintenance
maintenance:
	@echo "Running maintenance tasks..."
	make clean
	make format
	make lint
	make type-check
	make test-cov
	@echo "Maintenance completed!"

# Help for specific targets
help-install:
	@echo "Installation targets:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  update-deps  - Update all dependencies"
	@echo "  freeze-deps  - Freeze current dependency versions"

help-test:
	@echo "Testing targets:"
	@echo "  test         - Run all tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  test-fast    - Run tests in parallel"
	@echo "  test-design  - Run design pattern tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-integration - Run integration tests only"

help-dev:
	@echo "Development targets:"
	@echo "  run          - Start the application"
	@echo "  run-dev      - Start with auto-reload"
	@echo "  dev          - Start with file watching"
	@echo "  debug        - Start with debugger"
	@echo "  debug-remote - Start remote debug server" 