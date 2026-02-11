# Building an Agentic Platform with GitHub Copilot Coding Agent

A complete, step-by-step guide to setting up a project that leverages **GitHub Copilot Coding Agent** — an autonomous AI developer that runs in the cloud, picks up tasks from GitHub Issues, writes code, runs tests, and opens pull requests for your review.

---

## Table of Contents

1. [What Is the Copilot Coding Agent?](#1-what-is-the-copilot-coding-agent)
2. [Prerequisites](#2-prerequisites)
3. [Project Structure](#3-project-structure)
4. [Step-by-Step Setup](#4-step-by-step-setup)
   - [4.1 Create the Application Code](#41-create-the-application-code)
   - [4.2 Create the Test Suite](#42-create-the-test-suite)
   - [4.3 Configure Custom Instructions for the Agent](#43-configure-custom-instructions-for-the-agent)
   - [4.4 Configure CI Pipeline (GitHub Actions)](#44-configure-ci-pipeline-github-actions)
   - [4.5 Supporting Files](#45-supporting-files)
5. [Environment & Proxy Configuration](#5-environment--proxy-configuration)
6. [Git & GitHub Setup](#6-git--github-setup)
   - [6.1 Install GitHub CLI](#61-install-github-cli)
   - [6.2 Initialize and Push to GitHub](#62-initialize-and-push-to-github)
7. [Enable Copilot Coding Agent](#7-enable-copilot-coding-agent)
8. [Creating Issues for the Agent](#8-creating-issues-for-the-agent)
9. [How It Works End-to-End](#9-how-it-works-end-to-end)
10. [Customization Options](#10-customization-options)
11. [Costs & Limits](#11-costs--limits)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What Is the Copilot Coding Agent?

The Copilot Coding Agent is **not** the same as "Agent mode" in VS Code. Here's the difference:

| Feature | Agent Mode (VS Code) | Copilot Coding Agent (Cloud) |
|---|---|---|
| **Where it runs** | Locally in your IDE | Cloud via GitHub Actions |
| **How you trigger it** | Chat in VS Code | Assign a GitHub Issue to Copilot |
| **Workflow** | Synchronous, you watch it work | Asynchronous, it works in the background |
| **Output** | Direct file edits locally | Opens a Draft Pull Request on GitHub |
| **Collaboration** | Just you | Whole team can review the PR |

The Coding Agent:
- Spins up an **ephemeral dev environment** via GitHub Actions
- Clones your repo, reads your custom instructions
- Writes code, runs your tests and linters
- Creates a `copilot/` branch and opens a **Draft PR**
- Requests a review from you — you iterate via PR comments

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| **GitHub Plan** | Copilot Pro, Pro+, Business, or Enterprise |
| **Python** | 3.12+ |
| **Git** | Installed and configured |
| **GitHub CLI (gh)** | v2.x+ (optional but recommended) |
| **VS Code** | With GitHub Copilot extension |

---

## 3. Project Structure

```
task-tracker/
├── .github/
│   ├── copilot-instructions.md    # Tells the agent HOW to work
│   └── workflows/
│       └── ci.yml                 # CI pipeline the agent uses to validate
├── app/
│   ├── __init__.py
│   ├── main.py                    # Flask app and route handlers
│   ├── models.py                  # Data models (dataclasses)
│   └── store.py                   # In-memory data store
├── tests/
│   └── test_api.py                # API integration tests
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 4. Step-by-Step Setup

### 4.1 Create the Application Code

#### `app/__init__.py`
```python
# empty — marks app/ as a Python package
```

#### `app/models.py`
```python
"""Data models for the Task Tracker API."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    assignee: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "assignee": self.assignee,
        }
```

#### `app/store.py`
```python
"""In-memory task store."""

from datetime import datetime
from typing import Optional

from app.models import Task, TaskPriority, TaskStatus


class TaskStore:
    """Simple in-memory store for tasks."""

    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1

    def create(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        assignee: Optional[str] = None,
    ) -> Task:
        task = Task(
            id=self._next_id,
            title=title,
            description=description,
            priority=TaskPriority(priority),
            assignee=assignee,
        )
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_all(self) -> list[Task]:
        return list(self._tasks.values())

    def update(self, task_id: int, **kwargs) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if key == "status":
                value = TaskStatus(value)
            if key == "priority":
                value = TaskPriority(value)
            setattr(task, key, value)
        task.updated_at = datetime.now()
        return task

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
```

#### `app/main.py`
```python
"""Task Tracker API - A simple Flask REST API for task management."""

from flask import Flask, jsonify, request

from app.store import TaskStore

app = Flask(__name__)
store = TaskStore()


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})


@app.route("/tasks", methods=["GET"])
def list_tasks():
    tasks = store.list_all()
    return jsonify([t.to_dict() for t in tasks])


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "title is required"}), 400

    task = store.create(
        title=data["title"],
        description=data.get("description", ""),
        priority=data.get("priority", "medium"),
        assignee=data.get("assignee"),
    )
    return jsonify(task.to_dict()), 201


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = store.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


@app.route("/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):
    data = request.get_json()
    task = store.update(task_id, **data)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if store.delete(task_id):
        return "", 204
    return jsonify({"error": "Task not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

### 4.2 Create the Test Suite

#### `tests/test_api.py`
```python
"""Tests for the Task Tracker API."""

import pytest

from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_create_task(client):
    response = client.post("/tasks", json={"title": "Test task"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "Test task"
    assert data["status"] == "todo"


def test_create_task_missing_title(client):
    response = client.post("/tasks", json={})
    assert response.status_code == 400


def test_list_tasks(client):
    client.post("/tasks", json={"title": "Task 1"})
    client.post("/tasks", json={"title": "Task 2"})
    response = client.get("/tasks")
    assert response.status_code == 200


def test_get_task_not_found(client):
    response = client.get("/tasks/999")
    assert response.status_code == 404


def test_delete_task_not_found(client):
    response = client.delete("/tasks/999")
    assert response.status_code == 404
```

### 4.3 Configure Custom Instructions for the Agent

This is the **most important file** for the coding agent. It lives at `.github/copilot-instructions.md` and tells the agent everything about your project — coding standards, how to build, how to test, and your project layout.

#### `.github/copilot-instructions.md`
```markdown
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
app/
  __init__.py
  main.py        # Flask app and route handlers
  models.py      # Data models (dataclasses)
  store.py       # In-memory data store
tests/
  test_api.py    # API integration tests

## Build & Run
pip install -r requirements.txt
pytest
python -m app.main
```

> **Why this matters:** The coding agent reads this file before doing any work. The more specific you are about your standards, structure, and build commands, the better the agent's output will be. This is your way of "onboarding" the AI developer.

### 4.4 Configure CI Pipeline (GitHub Actions)

The coding agent uses your CI pipeline to **validate its own changes**. It will run `pytest` and check that everything passes before opening a PR.

#### `.github/workflows/ci.yml`
```yaml
name: CI

on:
  push:
    branches: [main, copilot/**]   # <-- CRITICAL: include copilot/** branches
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest -v
```

> **Key detail:** The `copilot/**` branch pattern is essential. The coding agent creates branches like `copilot/issue-3` — your CI must trigger on these branches so the agent can verify its work.

### 4.5 Supporting Files

#### `requirements.txt`
```
flask>=3.0
pytest>=8.0
```

#### `.gitignore`
```
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
.venv/
venv/
.env
```

---

## 5. Environment & Proxy Configuration

If you're behind a corporate proxy (like Intel), set these environment variables before any network operations:

### PowerShell (Windows)
```powershell
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912/"
$env:HTTP_PROXY  = "http://proxy-dmz.intel.com:911/"
$env:http_proxy  = "http://proxy-dmz.intel.com:911/"
$env:https_proxy = "http://proxy-dmz.intel.com:912/"
$env:RSYNC_PROXY = "http://proxy-dmz.intel.com:911/"
```

### Bash/Linux
```bash
export HTTPS_PROXY=http://proxy-dmz.intel.com:912/
export HTTP_PROXY=http://proxy-dmz.intel.com:911/
export http_proxy=http://proxy-dmz.intel.com:911/
export https_proxy=http://proxy-dmz.intel.com:912/
export RSYNC_PROXY=http://proxy-dmz.intel.com:911/
```

### Python Environment Setup
```powershell
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Verify tests pass
pytest -v
```

---

## 6. Git & GitHub Setup

### 6.1 Install GitHub CLI

The `gh` CLI makes repo creation and issue management much faster.

#### Option A: winget (requires admin)
```powershell
winget install --id GitHub.cli -e
```

#### Option B: Portable install (no admin needed)
```powershell
# Download the zip
Invoke-WebRequest -Uri "https://github.com/cli/cli/releases/download/v2.86.0/gh_2.86.0_windows_amd64.zip" `
  -OutFile "$env:TEMP\gh.zip" `
  -Proxy "http://proxy-dmz.intel.com:912/"

# Extract to local app data
Expand-Archive -Path "$env:TEMP\gh.zip" -DestinationPath "$env:LOCALAPPDATA\gh-cli" -Force

# Add to PATH for current session
$env:PATH = "C:\Users\$env:USERNAME\AppData\Local\gh-cli\bin;$env:PATH"

# Verify
gh --version
```

#### Authenticate
```powershell
gh auth login -h github.com -p https -w
# This opens a browser — paste the one-time code, authorize, done.
```

### 6.2 Initialize and Push to GitHub

```powershell
# Initialize git
git init
git add -A
git commit -m "Initial commit: Task Tracker Flask API with tests"
git branch -M main

# Create GitHub repo and push in one command
gh repo create task-tracker --public --source=. --push
```

---

## 7. Enable Copilot Coding Agent

### For Individual Users (Copilot Pro / Pro+)

1. Go to **github.com** → click your **avatar** → **Settings**
2. Navigate to **Copilot** in the left sidebar
3. Under **Policies**, find **"Copilot coding agent"**
4. Set it to **Enabled**

### For Organizations (Copilot Business / Enterprise)

1. Go to your **organization** → **Settings**
2. Navigate to **Copilot** → **Policies**
3. Enable **"Copilot coding agent"**
4. Optionally configure which repos can use it

### Verify It's Working

Once enabled, when you open any Issue in your repo, you should see **"Copilot"** as an option in the **Assignees** dropdown on the right sidebar.

---

## 8. Creating Issues for the Agent

Write clear, specific issues. The coding agent performs best with well-defined tasks.

### Good Issue Examples

```powershell
# Issue 1: New endpoint
gh issue create --repo YOUR_USER/task-tracker `
  --title "Add GET /tasks/search endpoint to filter tasks by status" `
  --body "Add a new endpoint GET /tasks/search?status=todo that filters tasks by their status field. Should return 400 if an invalid status is provided. Include tests in tests/test_api.py for both success and error cases."

# Issue 2: Validation
gh issue create --repo YOUR_USER/task-tracker `
  --title "Add request validation: task title must be 1-200 characters" `
  --body "Validate the title field on POST /tasks: it must be between 1 and 200 characters. Return 400 with an appropriate error message if validation fails. Add tests for empty title, title too long, and valid title edge cases."

# Issue 3: New feature (pipe body to avoid escaping)
'Create a new endpoint GET /tasks/stats that returns a JSON object with the count of tasks grouped by status. Include tests.' |
  gh issue create --repo YOUR_USER/task-tracker `
    --title "Add GET /tasks/stats endpoint returning count by status" -F -
```

### Assigning Issues to Copilot

The `gh` CLI doesn't support assigning to `copilot` directly. Use one of these methods:

1. **GitHub Web UI:** Open the issue → Assignees sidebar → select **Copilot**
2. **VS Code:** In Copilot Chat (agent mode), describe the task → click **"Delegate to coding agent"**
3. **GitHub Agents Panel:** Available on every GitHub page in the top nav

### Tips for Writing Effective Issues

| Do | Don't |
|---|---|
| Be specific about endpoints, parameters, responses | "Make the app better" |
| Reference specific files: `tests/test_api.py` | Leave the scope vague |
| Mention error cases to handle | Only describe happy path |
| Say "Include tests" explicitly | Assume it will write tests |
| One focused task per issue | Bundle 5 features into one issue |

---

## 9. How It Works End-to-End

```
 YOU                              GITHUB (CLOUD)
 ───                              ──────────────

 1. Create Issue #4:
    "Add pagination to
     GET /tasks"
         │
         ▼
 2. Assign to Copilot ──────────► 3. GitHub Actions spins up
    (via web UI)                      ephemeral environment
                                          │
                                          ▼
                                  4. Agent clones repo
                                     Reads .github/copilot-instructions.md
                                     Understands project structure
                                          │
                                          ▼
                                  5. Agent writes code:
                                     - Edits app/main.py (adds pagination)
                                     - Edits app/store.py (offset/limit)
                                     - Adds tests in tests/test_api.py
                                          │
                                          ▼
                                  6. Agent runs pytest
                                     Runs security scans (CodeQL, secrets)
                                     Fixes any issues it finds
                                          │
                                          ▼
                                  7. Creates branch: copilot/issue-4
                                     Commits changes
                                     Opens Draft Pull Request
                                     Writes PR description
                                          │
                                          ▼
 8. You get a notification ◄───── 9. Requests review from YOU
         │
         ▼
 10. Review the PR
     - Approve → merge
     - Comment "Also add a test
       for page=0" → Agent iterates
       and pushes new commits
```

### Security Protections Built In

- Agent can **only** push to `copilot/` branches (never `main`)
- PRs are always **Draft** — require human approval
- Code is scanned with **CodeQL** for vulnerabilities
- **Secret scanning** checks for leaked credentials
- Dependencies checked against **GitHub Advisory Database**
- Only users with **write access** can trigger the agent
- The person who triggered the PR **cannot approve it** (enforces review)

---

## 10. Customization Options

### Custom Instructions (what we set up)
The `.github/copilot-instructions.md` file — tells the agent your coding standards, project layout, and how to build/test.

### Custom Agents
Create specialized versions of Copilot for different tasks:
- A **frontend agent** that focuses on React components
- A **testing agent** that specializes in writing comprehensive tests
- A **docs agent** that excels at technical documentation

### MCP Servers
Give the agent access to external tools and data sources via Model Context Protocol servers.

### Hooks
Execute custom shell commands at key points during agent execution (validation, logging, security scanning).

### AI Model Selection
Copilot Pro/Pro+ users can choose which AI model the coding agent uses. Different models may work better for different task types.

---

## 11. Costs & Limits

| Resource | Usage |
|---|---|
| **GitHub Actions minutes** | Each agent session uses Actions minutes from your plan |
| **Copilot premium requests** | Each task counts as premium requests |
| **Within your plan limits** | No additional cost if you stay within your monthly allowance |

### Limitations
- Agent can only work in **one repo per task**
- Opens exactly **one PR per task**
- Cannot push to `main`/`master` directly
- Cannot approve or merge its own PRs

---

## 12. Troubleshooting

| Problem | Solution |
|---|---|
| "Copilot" not in Assignees dropdown | Enable coding agent in GitHub Settings → Copilot → Policies |
| Agent fails to run tests | Ensure `copilot/**` is in your CI workflow branch triggers |
| Agent doesn't follow your standards | Improve `.github/copilot-instructions.md` with more detail |
| "Require signed commits" blocks agent | Add Copilot as a bypass actor in your ruleset |
| Agent can't install dependencies | Check `requirements.txt` is complete and correct |
| Behind corporate proxy | Proxy settings don't affect the cloud agent — it runs on GitHub's infra |

---

## Quick Reference: Commands We Used

```powershell
# Proxy setup (Intel)
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912/"
$env:HTTP_PROXY  = "http://proxy-dmz.intel.com:911/"

# Python setup
pip install -r requirements.txt
pytest -v

# Git setup
git init; git add -A; git commit -m "Initial commit"
git branch -M main

# GitHub CLI
gh auth login -h github.com -p https -w
gh repo create task-tracker --public --source=. --push
gh issue create --repo USER/task-tracker --title "..." --body "..."
gh browse --repo USER/task-tracker
```
