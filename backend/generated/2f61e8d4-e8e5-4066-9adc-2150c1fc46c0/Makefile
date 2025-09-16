# CRM Flagship v1.0.0 - Makefile

.PHONY: help smoke test-backend test-frontend clean

help:
	@echo "CRM Flagship v1.0.0 - Available commands:"
	@echo "  smoke        - Run comprehensive smoke test"
	@echo "  test-backend - Run backend tests only"
	@echo "  test-frontend- Run frontend tests only"
	@echo "  clean        - Clean up temporary files"
	@echo "  start        - Start backend server"
	@echo "  stop         - Stop backend server"

smoke:
	@echo "Running CRM Flagship v1.0.0 smoke test..."
	@./scripts/smoke_verify.sh

test-backend:
	@echo "Running backend tests..."
	@cd backend && python test_rbac.py
	@cd backend && python test_communications.py
	@cd backend && python test_webhooks.py

test-frontend:
	@echo "Running frontend tests..."
	@cd frontend && npm test

start:
	@echo "Starting backend server..."
	@cd backend && nohup python app.py > app.log 2>&1 &
	@echo "Backend started. Logs: backend/app.log"

stop:
	@echo "Stopping backend server..."
	@pkill -f "python app.py" || true
	@echo "Backend stopped"

clean:
	@echo "Cleaning up..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"
