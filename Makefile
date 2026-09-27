.PHONY: dev test eval

dev:
	docker compose up --build

test:
	cd backend && pytest
	cd frontend && npm run lint && npm run build

eval:
	cd backend && python -m evals.runner
