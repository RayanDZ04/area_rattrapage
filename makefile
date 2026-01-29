PROJECT_ROOT := /home/goten/Bureau/goten/TEK3/Application_developement/area_rattrapage
VENV := $(PROJECT_ROOT)/.venv
PYTHON := python3.12
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

BACK_DIR := $(PROJECT_ROOT)/back
ENV_FILE := $(BACK_DIR)/.env

.PHONY: web env venv install run backend front serve clean fclean re help

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
		echo "DATABASE_URL=sqlite:///./app.db" >> $(ENV_FILE); \
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
	cd $(BACK_DIR) && $(PY) -m uvicorn app.main:app --reload --port 8080

backend: run

front:
	python3 -m http.server 5173 --directory $(PROJECT_ROOT)/front

serve: backend front

web: env install
	@$(MAKE) -j2 serve

clean:
	find $(PROJECT_ROOT) -type d -name "__pycache__" -exec rm -rf {} +
	find $(PROJECT_ROOT) -type f -name "*.pyc" -delete
	find $(PROJECT_ROOT) -type d -name ".pytest_cache" -exec rm -rf {} +

fclean: clean
	rm -rf $(VENV)
	rm -f $(BACK_DIR)/app.db
	rm -f $(ENV_FILE)

re: fclean web
