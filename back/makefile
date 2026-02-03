PROJECT_ROOT := ..

.PHONY: help web env venv install run backend front serve clean fclean re

help:
	@echo "Proxy makefile (from back/)"
	@echo "Use: make web | make backend | make front"
	@echo "(delegates to $(PROJECT_ROOT)/makefile)"

web env venv install run backend front serve clean fclean re:
	@$(MAKE) -C $(PROJECT_ROOT) $@
