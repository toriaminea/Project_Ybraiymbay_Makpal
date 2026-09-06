# Adaptive Python Learning Prototype

This Streamlit application provides three sequential exercises on conditionals and the `for` loop. Answer validation and support-level selection are performed by deterministic Python modules. Gemini generates the wording of a hint only after the support level has been selected.

## Setup and launch

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py
```

Set your values in `.env`:

```text
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Do not commit the API key or include it in source code, task data, or result files. If Gemini is unavailable, the attempt is still recorded and the interface reports that the hint service is unavailable.

## Project structure

- `app.py` — Streamlit interface and learning session;
- `diagnostic_engine.py` — safe answer validation and micro-diagnostic indicators;
- `adaptive_engine.py` — deterministic support-level selection;
- `llm_service.py` — Gemini prompt and API call;
- `logger.py` — `results/experiment_log.csv` interaction log;
- `analytics.py` — progress indicators;
- `simulation.py` and `run_scenarios.py` — reproducible S1–S6 scenarios;
- `data/tasks.json` — tasks and accepted answers.

## Verification

```powershell
python -m unittest discover -s tests -v
python run_scenarios.py
python generate_article_artifacts.py
```

The second command creates `results/scenario_results.csv`. Learner interactions are written to `results/experiment_log.csv` using UTF-8 with BOM.

`python generate_article_artifacts.py` creates Table 3 for automated test results and Table 4 for the S1–S6 scenarios in CSV and Markdown formats. Run the optional 20-response Gemini evaluation separately with `python run_genai_evaluation.py`.
