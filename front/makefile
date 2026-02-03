PROJECT_ROOT := ..

.PHONY: help web backend front serve clean fclean re

help:
	@echo "Proxy makefile (from front/)"
	@echo "Use: make front | make web"
	@echo "(delegates to $(PROJECT_ROOT)/makefile)"

web backend front serve clean fclean re:
	@$(MAKE) -C $(PROJECT_ROOT) $@
