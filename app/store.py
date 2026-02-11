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
