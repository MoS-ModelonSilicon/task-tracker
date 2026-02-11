# Copilot Custom Instructions

## Project Overview
This is a Python Flask REST API for task management ("Task Tracker").

## Tech Stack
- Python 3.12+
- Flask 3.x
- pytest for testing

## Coding Standards
- Follow PEP 8 style guidelines
- Use type hints on all function signatures
- Use dataclasses for data models
- Write docstrings for all public functions and classes
- Keep functions small and focused (< 30 lines)

## Testing
- All new features MUST include corresponding tests in the `tests/` directory
- Run `pytest` to verify changes pass
- Tests should cover both success and error cases

## Project Structure
```
app/
  __init__.py
  main.py        # Flask app and route handlers
  models.py      # Data models (dataclasses)
  store.py        # In-memory data store
tests/
  test_api.py    # API integration tests
```

## Build & Run
```bash
pip install -r requirements.txt
pytest
python -m app.main
```
