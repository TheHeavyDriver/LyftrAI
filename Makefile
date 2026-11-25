.PHONY: up down logs test clean help

help:
	@echo "Lyftr AI - Makefile commands"
	@echo ""
	@echo "  make up       - Start the full stack (backend + frontend)"
	@echo "  make down     - Stop the stack (preserves data volume)"
	@echo "  make logs     - Follow logs from all services"
	@echo "  make test     - Run backend tests"
	@echo "  make clean    - Remove containers and volumes (destructive)"
	@echo ""

up:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	docker compose up --build -d
	@echo ""
	@echo "✓ Stack is running:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Health:   http://localhost:8000/health"

down:
	docker compose down

logs:
	docker compose logs -f

test:
	@if [ -x backend/.venv/bin/python ]; then \
		cd backend && .venv/bin/python -m pytest -v; \
	else \
		cd backend && python -m pytest -v; \
	fi

clean:
	docker compose down -v
	@echo "✓ Containers and volumes removed"
