# This file MUST use tabs, not spaces
.PHONY: help clean

help:
	@echo "Some make commands you can run (eg 'make allclean'):"
	@echo
	@echo "MOST USEFUL:"
	@echo "   build: compile & compress all packages (e.g. JS, LESS, templates)"
	@echo "   check: run 'small' and 'medium' tests, and linter"
	@echo "   clean: safe remove of auto-generated files (.pyc, etc)"
	@echo "   refresh: safeupdate + install_deps: can be run in cron!"
	@echo "   secrets_decrypt: to create secrets.py"
	@echo

clean:
	find . \( -name '*.pyc' -o -name '*.pyo' \
		-o -name '*.orig' \
		-o -name '*.rej' \
			\) -print0 | xargs -0 rm -rf
