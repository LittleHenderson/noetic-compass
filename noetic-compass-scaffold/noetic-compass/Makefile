# Noetic Compass — Development Makefile
# Handles Rust engine, Python API, and React dashboard orchestration.
#
# Prerequisites: cargo, python3, node/npm installed and on PATH.
# On Windows, use Git Bash or WSL for make invocation.

SHELL := /bin/bash

VENV        := .venv
PYTHON      := $(VENV)/Scripts/python
PIP         := $(VENV)/Scripts/pip
PYTEST      := $(VENV)/Scripts/pytest
UVICORN     := $(VENV)/Scripts/uvicorn
MATURIN     := $(VENV)/Scripts/maturin
NPM         := npm
DASHBOARD   := dashboard
ENGINE      := cas-engine

# Detect Unix vs Windows venv layout
ifeq ($(wildcard $(VENV)/Scripts/python),)
  ifeq ($(wildcard $(VENV)/Scripts/python.exe),)
    PYTHON  := $(VENV)/bin/python
    PIP     := $(VENV)/bin/pip
    PYTEST  := $(VENV)/bin/pytest
    UVICORN := $(VENV)/bin/uvicorn
    MATURIN := $(VENV)/bin/maturin
  endif
endif

.PHONY: all install install-rust install-python install-node \
        dev dev-api dev-ui \
        build build-engine build-ui \
        test test-rust test-python test-node \
        lint lint-python lint-node \
        clean help

# ─── Default ──────────────────────────────────────────────────────────

all: install build test  ## Full setup: install, build, test

# ─── Install ──────────────────────────────────────────────────────────

install: install-python install-rust install-node  ## Install all dependencies

install-python:  ## Create venv and install Python deps
	@echo "──── Installing Python dependencies ────"
	@test -d $(VENV) || python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-rust: install-python  ## Build cas-engine Rust crate and install via maturin
	@echo "──── Building Rust engine (maturin develop) ────"
	cd $(ENGINE) && $(MATURIN) develop --features python

install-node:  ## Install Node.js dashboard dependencies
	@echo "──── Installing Node dependencies ────"
	cd $(DASHBOARD) && $(NPM) install

# ─── Build ────────────────────────────────────────────────────────────

build: build-engine build-ui  ## Build all artifacts

build-engine:  ## Build cas-engine in release mode
	@echo "──── Building Rust engine (release) ────"
	cd $(ENGINE) && cargo build --release --features python

build-ui:  ## TypeScript check + Vite production build
	@echo "──── Building dashboard ────"
	cd $(DASHBOARD) && $(NPM) run build

# ─── Dev Servers ──────────────────────────────────────────────────────

dev:  ## Start API (port 8000) and frontend (port 3000) concurrently
	@echo "──── Starting dev servers ────"
	@echo "  API:       http://localhost:8000"
	@echo "  Dashboard: http://localhost:3000"
	@trap 'kill 0' EXIT; \
	  $(UVICORN) api.main:app --reload --port 8000 & \
	  cd $(DASHBOARD) && $(NPM) run dev & \
	  wait

dev-api:  ## Start only the FastAPI backend
	$(UVICORN) api.main:app --reload --port 8000

dev-ui:  ## Start only the Vite frontend
	cd $(DASHBOARD) && $(NPM) run dev

# ─── Test ─────────────────────────────────────────────────────────────

test: test-rust test-python test-node  ## Run all test suites

test-rust:  ## Run Rust unit + integration tests
	@echo "──── Running Rust tests ────"
	cd $(ENGINE) && cargo test

test-python:  ## Run Python pytest suite
	@echo "──── Running Python tests ────"
	$(PYTEST) tests/ -v

test-node:  ## Run Vitest dashboard tests
	@echo "──── Running dashboard tests ────"
	cd $(DASHBOARD) && $(NPM) run test

# ─── Lint ─────────────────────────────────────────────────────────────

lint: lint-python lint-node  ## Lint all code

lint-python:  ## Type-check Python with mypy (if installed)
	@echo "──── Linting Python ────"
	-$(PYTHON) -m mypy api/ --ignore-missing-imports

lint-node:  ## ESLint + TypeScript check
	@echo "──── Linting dashboard ────"
	cd $(DASHBOARD) && $(NPM) run lint
	cd $(DASHBOARD) && npx tsc --noEmit

# ─── Clean ────────────────────────────────────────────────────────────

clean:  ## Remove all build artifacts, caches, and node_modules
	@echo "──── Cleaning ────"
	rm -rf $(VENV)
	rm -rf $(ENGINE)/target
	rm -rf $(DASHBOARD)/node_modules $(DASHBOARD)/dist
	rm -rf __pycache__ api/__pycache__ tests/__pycache__
	rm -rf .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."

# ─── Help ─────────────────────────────────────────────────────────────

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
