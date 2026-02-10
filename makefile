PROJECT_ROOT := $(CURDIR)
VENV := $(PROJECT_ROOT)/.venv
PYTHON := python3
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

BACK_DIR := $(PROJECT_ROOT)/back
ENV_FILE := $(BACK_DIR)/.env

BACK_PORT := 8080
FRONT_PORT := 5173

.PHONY: web env venv install run run-dev backend backend-dev front serve stop clean fclean re help

help:
	@echo "Targets:"
	@echo "  make web     - crée .env, installe deps, lance le backend"
	@echo "  make front   - lance le front statique"
	@echo "  make backend - lance le backend"
	@echo "  make clean   - supprime caches Python"
	@echo "  make fclean  - supprime venv et base sqlite"
	@echo "  make re      - fclean puis web"

env:
	@mkdir -p $(BACK_DIR)
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "SECRET_KEY=dev-secret-change-me" > $(ENV_FILE); \
		echo "SESSION_SECRET=dev-session-secret" >> $(ENV_FILE); \
		echo "DATABASE_URL=sqlite:///./app.db" >> $(ENV_FILE); \
		echo "BACKEND_URL=http://localhost:8080" >> $(ENV_FILE); \
		echo "FRONTEND_URL=http://localhost:5173" >> $(ENV_FILE); \
		echo "GOOGLE_CLIENT_ID=your-google-client-id" >> $(ENV_FILE); \
		echo "GOOGLE_CLIENT_SECRET=your-google-client-secret" >> $(ENV_FILE); \
		echo "Créé $(ENV_FILE)"; \
	else \
		echo "$(ENV_FILE) existe déjà"; \
	fi

venv:
	@if [ ! -d $(VENV) ]; then \
		$(PYTHON) -m venv $(VENV); \
	fi

install: venv
	$(PIP) install --upgrade pip
	PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 $(PIP) install -r $(BACK_DIR)/requirements.txt

run:
	cd $(BACK_DIR) && $(PY) -m uvicorn app.main:app --port $(BACK_PORT)

run-dev:
	cd $(BACK_DIR) && $(PY) -m uvicorn app.main:app --reload --port $(BACK_PORT)

backend: run

backend-dev: run-dev

front:
	python3 -m http.server $(FRONT_PORT) --directory $(PROJECT_ROOT)/front

stop:
	@pids=$$(lsof -ti:$(BACK_PORT) 2>/dev/null || true); \
	if [ -n "$$pids" ]; then \
		echo "Stop backend (:$(BACK_PORT)) -> $$pids"; \
		kill $$pids 2>/dev/null || true; \
		sleep 0.2; \
		kill -9 $$pids 2>/dev/null || true; \
	fi
	@pids=$$(lsof -ti:$(FRONT_PORT) 2>/dev/null || true); \
	if [ -n "$$pids" ]; then \
		echo "Stop front (:$(FRONT_PORT)) -> $$pids"; \
		kill $$pids 2>/dev/null || true; \
		sleep 0.2; \
		kill -9 $$pids 2>/dev/null || true; \
	fi

serve:
	@echo "Front:  http://127.0.0.1:$(FRONT_PORT)/"; \
	 echo "Back:   http://127.0.0.1:$(BACK_PORT)/ (docs: /docs)"; \
	 echo "(Ctrl+C pour arrêter)"; \
	 trap '$(MAKE) stop >/dev/null 2>&1 || true; exit 0' INT TERM; \
	 ( cd $(BACK_DIR) && $(PY) -m uvicorn app.main:app --port $(BACK_PORT) ) & back_pid=$$!; \
	 ( python3 -m http.server $(FRONT_PORT) --directory $(PROJECT_ROOT)/front ) & front_pid=$$!; \
	 echo "PIDs: back=$$back_pid front=$$front_pid"; \
	 wait $$back_pid || true; \
	 wait $$front_pid || true

web: stop env install
	@$(MAKE) serve

clean:
	find $(PROJECT_ROOT) -type d -name "__pycache__" -exec rm -rf {} +
	find $(PROJECT_ROOT) -type f -name "*.pyc" -delete
	find $(PROJECT_ROOT) -type d -name ".pytest_cache" -exec rm -rf {} +

fclean: clean
	rm -rf $(VENV)
	rm -f $(BACK_DIR)/app.db
	rm -f $(ENV_FILE)

re: fclean web
