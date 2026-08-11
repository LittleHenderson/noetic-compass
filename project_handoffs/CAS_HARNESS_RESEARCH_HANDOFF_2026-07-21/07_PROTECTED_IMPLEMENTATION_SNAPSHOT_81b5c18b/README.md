# Noetic Compass

AI Cognitive Architecture Assessment Platform built on CAS v7.4 (Corrected Edition).

Noetic Compass evaluates AI system responses across 10 cognitive operators, 4 processing domains, 7 core drives, and 7 inversion axes to produce a composite NCCS score (0-100) with certification levels (Platinum/Gold/Silver/Bronze/Fail).

## Architecture

```
noetic-compass/
  cas-engine/        Rust scoring engine (PyO3 bindings)
  api/               FastAPI gateway (8-stage Wrap pipeline)
  dashboard/         React 18 + TypeScript + Recharts
  validation/        Reproducibility, sensitivity, and correlation analysis
  scenarios/         50+ assessment prompts
  infra/             Render deployment config
  docs/              DEPLOYMENT.md, engineering specs
```

### Scoring Pipeline (8 stages)

```
Input Analyzer -> RPM Gate -> Dial Adjustment -> Base LLM Call ->
Operator Scoring -> Domain Coherence -> Inversion Scan -> Output Gate
```

### NCCS Composite Weights

| Component | Weight |
|-----------|--------|
| Cognitive Operator Profile | 25% |
| Domain Coherence (DCI) | 20% |
| Core Drive / RPM Integrity | 20% |
| Inversion Resistance (7 axes) | 15% |
| Capability Pathway Quality | 10% |
| Social Engineering Resistance | 10% |

## Quick Start

### Prerequisites
- Python 3.10+, Rust toolchain, Node.js 18+

### Install

```bash
make install       # Python venv + Rust build + npm install
```

### Run Development Servers

```bash
make dev           # API on :8000, Dashboard on :3000
```

### Run Tests

```bash
make test          # Rust + Python + Vitest (all suites)
make validate      # Validation framework (reproducibility + sensitivity)
```

## LLM Providers

Copy `.env.example` to `.env` and set API keys:

```bash
cp .env.example .env
# Edit .env with your keys:
#   NC_OPENAI_API_KEY=sk-...
#   NC_ANTHROPIC_API_KEY=sk-ant-...
#   NC_GOOGLE_API_KEY=AI...
```

Supported providers: OpenAI (GPT-4), Anthropic (Claude), Google (Gemini), Mock (no key needed).

## Validation Study

```bash
# 1. Generate machine scores
python validation/run_baseline_study.py --provider mock --count 50

# 2. Collect human ratings
python validation/human_labeling_tool.py --results validation/baseline_results.json --rater "Your Name"

# 3. Correlation analysis
python validation/correlation_analysis.py
```

## Deployment

### Docker Compose

```bash
docker compose up --build
# API: http://localhost:8000  |  Dashboard: http://localhost:3000
```

### Render (Cloud)

Connect repo on Render dashboard. Blueprint auto-detected from `infra/render.yaml`.

See `docs/DEPLOYMENT.md` for full deployment guide.

## Rate Limiting Tiers

| Tier | Monthly Cap | RPM |
|------|------------|-----|
| Community | 50 | 10 |
| Professional | 500 | 30 |
| Enterprise | Unlimited | 120 |

Set via `NC_RATE_LIMIT_TIER` environment variable.

## License

Confidential. All rights reserved.
