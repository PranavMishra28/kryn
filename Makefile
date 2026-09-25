PYTHON ?= python3
NODE ?= node

.PHONY: check docs-check package-smoke eval-prepare eval-grade

check: docs-check
	$(PYTHON) -B -m unittest discover -s setup
	$(PYTHON) -B -m unittest discover -s tools -p 'test_*.py'
	$(NODE) --test tools/test_kryn_plugin.mjs tools/inference-audit/server.test.js
	$(PYTHON) -B tools/run_native_trial.py --self-check
	$(PYTHON) -B evals/bench.py verify
	$(PYTHON) -B evals/bench.py selftest

docs-check:
	$(PYTHON) -B tools/check_docs.py
	git diff --check

package-smoke:
	@set -eu; stage=$$(mktemp -d "$${TMPDIR:-/tmp}/kryn-package-smoke.XXXXXX"); \
	stage=$$(cd "$$stage" && pwd -P); \
	trap 'rm -rf "$$stage"' EXIT; \
	export UV_CACHE_DIR="$$stage/uv-cache"; \
	$(PYTHON) -B build_package.py $(BUILD_FLAGS) --out-dir "$$stage/dist"; \
	$(PYTHON) -m venv "$$stage/venv"; \
	uv pip install --python "$$stage/venv/bin/python" --no-index --no-deps "$$stage"/dist/*.whl; \
	(cd "$$stage" && "$$stage/venv/bin/python" -I -B -m kryn --package-check && "$$stage/venv/bin/python" -I -B -m kryn --version)

eval-prepare:
	@test -n "$(TASK)" && test -n "$(RUN)" || { echo 'Use TASK=02 RUN=unique-run-id' >&2; exit 2; }
	$(PYTHON) -B evals/bench.py prepare "$(TASK)" "$(RUN)"

eval-grade:
	@test -n "$(RUN)" || { echo 'Use RUN=existing-run-id' >&2; exit 2; }
	$(PYTHON) -B evals/bench.py grade "$(RUN)"
