.PHONY: help test lint rc clean

help:
	@echo "Available targets:"
	@echo "  test     - Run all tests"
	@echo "  lint     - Run linting"
	@echo "  rc       - Create release candidate (usage: make rc TAG=vX.Y.Z-rc1)"
	@echo "  clean    - Clean up generated files"

test:
	python -m pytest tests/ -v --tb=short

test-unit:
	python -m pytest tests/meta_builder_v3/ -v --tb=short

test-integration:
	python -m pytest tests/ -k "not smoke" -v --tb=short

test-smoke:
	python -m pytest tests/smoke/ -v --tb=short

lint:
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
	black --check src/ tests/
	isort --check-only src/ tests/
	mypy src/ --ignore-missing-imports

rc:
	@if [ -z "$(TAG)" ]; then \
		echo "Error: TAG is required. Usage: make rc TAG=vX.Y.Z-rc1"; \
		exit 1; \
	fi
	@echo "Creating release candidate $(TAG)..."
	@echo "Running tests..."
	$(MAKE) test
	@echo "Running linting..."
	$(MAKE) lint
	@echo "Writing VERSION file..."
	echo "$(TAG)" > VERSION
	@echo "Creating git tag..."
	git add VERSION
	git commit -m "Release $(TAG)"
	git tag $(TAG)
	@echo "Pushing tag..."
	git push origin $(TAG)
	@echo "Release candidate $(TAG) created and pushed!"

clean:
	rm -f VERSION
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Evaluation Lab targets
eval:
	@echo "Running evaluation lab tests..."
	python -m pytest tests/eval_lab/ -v --tb=short

eval-suite:
	@if [ -z "$(SUITE)" ]; then \
		echo "Error: SUITE is required. Usage: make eval-suite SUITE=core_crm"; \
		exit 1; \
	fi
	@echo "Running evaluation suite $(SUITE)..."
	python -m eval_lab.runner run-suite suites/$(SUITE).yaml

eval-regression:
	@echo "Checking regression gates..."
	python -m eval_lab.runner check-regressions

eval-report:
	@echo "Generating evaluation report..."
	python -m eval_lab.runner generate-report --output eval_report.json

eval-all: eval eval-suite eval-regression eval-report
	@echo "Evaluation lab complete!"

# Update help target
help:
	@echo "Available targets:"
	@echo "  test     - Run all tests"
	@echo "  lint     - Run linting"
	@echo "  rc       - Create release candidate (usage: make rc TAG=vX.Y.Z-rc1)"
	@echo "  clean    - Clean up generated files"
	@echo "  eval     - Run evaluation lab tests"
	@echo "  eval-suite - Run evaluation suite (usage: make eval-suite SUITE=core_crm)"
	@echo "  eval-regression - Check regression gates"
	@echo "  eval-report - Generate evaluation report"
	@echo "  eval-all - Run all evaluation lab components"

# Evaluation Lab v1.1 targets
eval:
	python -m pytest tests/eval_lab/ -v --tb=short

eval-full:
	python -m src.eval_lab.runner run-suite-with-reruns suites/meta_builder_kitchen_sink.yaml --environment test

eval-smoke:
	python -m src.eval_lab.runner run-suite-with-reruns suites/template_smoke.yaml --environment test

# UI Development targets
ui-dev:
	@echo "Starting UI development server..."
	@if [ -d "../frontend" ] && [ -f "../frontend/package.json" ]; then \
		echo "Found modern frontend, starting dev server..."; \
		cd ../frontend && npm install && npm run dev; \
	else \
		echo "No modern frontend found. Using Flask templates only."; \
		echo "To set up a modern frontend:"; \
		echo "  cd ../frontend"; \
		echo "  npm init -y"; \
		echo "  npm install react react-dom"; \
		echo "  # Add your preferred build tool (Vite, Webpack, etc.)"; \
	fi

ui-build:
	@echo "Building UI for production..."
	@if [ -d "../frontend" ] && [ -f "../frontend/package.json" ]; then \
		echo "Found modern frontend, building..."; \
		cd ../frontend && npm install && npm run build; \
		@if [ -d "../frontend/dist" ]; then \
			echo "Copying built assets to backend/static/ui/..."; \
			mkdir -p static/ui; \
			cp -r ../frontend/dist/* static/ui/; \
		fi; \
	else \
		echo "No modern frontend found. Using Flask templates only."; \
	fi

ui-clean:
	@echo "Cleaning UI build artifacts..."
	rm -rf static/ui
	@if [ -d "../frontend" ]; then \
		cd ../frontend && rm -rf node_modules dist build; \
	fi

eval-templates:
	python -m src.eval_lab.runner run-suite-with-reruns suites/templates/crm.yaml --environment test
	python -m src.eval_lab.runner run-suite-with-reruns suites/templates/lms.yaml --environment test
	python -m src.eval_lab.runner run-suite-with-reruns suites/templates/recruiting.yaml --environment test
	python -m src.eval_lab.runner run-suite-with-reruns suites/templates/helpdesk.yaml --environment test
	python -m src.eval_lab.runner run-suite-with-reruns suites/templates/analytics.yaml --environment test

eval-report:
	python -m src.eval_lab.runner generate-report --run-id $(RUN_ID) --output eval-report.json

eval-quarantine-list:
	python -m src.eval_lab.runner quarantine-list --tenant-id $(TENANT_ID)

eval-quarantine-release:
	python -m src.eval_lab.runner quarantine-release --tenant-id $(TENANT_ID) --case-id $(CASE_ID)

eval-quarantine-cleanup:
	python -m src.eval_lab.runner quarantine-cleanup

eval-regression:
	python -m src.eval_lab.runner check-regressions --run-id $(RUN_ID)

eval-flake-test:
	python -m pytest tests/eval_lab/test_flake_detection.py -v

eval-alerts-test:
	python -m pytest tests/eval_lab/test_alerts.py -v

eval-costs-test:
	python -m pytest tests/eval_lab/test_costs_reruns.py -v

eval-api-test:
	python -m pytest tests/eval_lab/test_api_quarantine.py -v

eval-report-test:
	python -m pytest tests/eval_lab/test_report_artifacts.py -v

# Nightly evaluation
eval-nightly:
	python -m src.eval_lab.runner run-suite-with-reruns suites/meta_builder_kitchen_sink.yaml --environment staging

# PR evaluation
eval-pr:
	python -m src.eval_lab.runner run-suite-with-reruns suites/template_smoke.yaml --environment test

# All evaluation tests
eval-all: eval-flake-test eval-alerts-test eval-costs-test eval-api-test eval-report-test eval

# Database reset targets
reset-db:
	@python src/cli.py reset-db

reset-db-with-server:
	@python src/cli.py reset-db --with-server

# Worker targets
worker:
	@echo "🚀 Starting background worker..."
	@python src/cli.py worker

worker-queues:
	@echo "🚀 Starting worker with specific queues..."
	@python src/cli.py worker --queues default,high,low

worker-burst:
	@echo "⚡ Starting worker in burst mode..."
	@python src/cli.py worker --burst

worker-verbose:
	@echo "🔍 Starting worker with verbose logging..."
	@python src/cli.py worker --verbose

worker-named:
	@echo "🏷️  Starting named worker..."
	@python src/cli.py worker --name "worker-$(shell date +%s)"

worker-ipv4:
	@echo "🔗 Starting worker with IPv4 Redis..."
	@python src/cli.py worker --redis-url "redis://127.0.0.1:6379/0"

# Multiple workers for different queues
worker-high:
	@echo "🚀 Starting high priority worker..."
	@python src/cli.py worker --queues high --name "worker-high"

worker-default:
	@echo "🚀 Starting default priority worker..."
	@python src/cli.py worker --queues default --name "worker-default"

worker-low:
	@echo "🚀 Starting low priority worker..."
	@python src/cli.py worker --queues low --name "worker-low"

# Start all workers (in separate processes)
workers-all:
	@echo "🚀 Starting all workers..."
	@make worker-high &
	@make worker-default &
	@make worker-low &
	@echo "✅ All workers started. Use 'make workers-stop' to stop them."

workers-stop:
	@echo "⏹️  Stopping all workers..."
	@pkill -f "python src/cli.py worker" || true
	@echo "✅ Workers stopped."

# Quick reset (just database, no services)
reset-quick:
	@echo "🔄 Quick database reset..."
	@rm -f system_builder_hub.db
	@alembic upgrade head
	@python src/cli.py demo --name "Demo Project"
	@echo "✅ Quick reset completed"

# Full reset with verification
reset-full: reset-db-with-server
	@echo "🎉 Full reset with services completed!"
