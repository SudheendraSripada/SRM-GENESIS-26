# SRM-GENESIS-26

CrewAI is installed in the local `.venv` environment, and the starter crew lives in `srm_genesis/`.

## Setup

```bash
source .venv/bin/activate
```

Add your model provider key to `srm_genesis/.env` before running the crew. The generated example uses `OPENAI_API_KEY` by default.

## Run

```bash
cd srm_genesis
crewai run
```

The example crew researches AI and writes `report.md` in the project directory. Configure agents and tasks in `srm_genesis/src/srm_genesis/config/`.
