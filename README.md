# Task Tracker API

A simple REST API for task management, built with Flask.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m app.main
```

## Test

```bash
pytest
```

## API Endpoints

| Method | Endpoint           | Description       |
|--------|--------------------|--------------------|
| GET    | /health            | Health check       |
| GET    | /tasks             | List all tasks     |
| POST   | /tasks             | Create a task      |
| GET    | /tasks/<id>        | Get a task         |
| PATCH  | /tasks/<id>        | Update a task      |
| DELETE | /tasks/<id>        | Delete a task      |
