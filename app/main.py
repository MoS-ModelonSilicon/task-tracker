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
