#!/usr/bin/env python3
"""
Kanban Board for Multi-Claude Task Management
Tracks tasks across todo, in_progress, review, done states

Identified in collaborative brainstorming as Priority 2 improvement
"""
import uuid
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(Enum):
    """Task status states"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class KanbanTask:
    """Task on kanban board"""

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)  # Task IDs that block this
    subtasks: List[str] = field(default_factory=list)
    comments: List[Dict] = field(default_factory=list)
    time_spent_minutes: int = 0
    estimated_minutes: int = 0


@dataclass
class BoardColumn:
    """Column on kanban board"""

    status: TaskStatus
    name: str
    tasks: List[str] = field(default_factory=list)  # Task IDs
    wip_limit: Optional[int] = None  # Work-in-progress limit


class KanbanBoard:
    """
    Kanban board for multi-Claude task coordination

    Features:
    - Todo, In Progress, Review, Done columns
    - Task assignment to Claudes
    - Priority levels
    - Dependencies tracking
    - WIP limits per column
    - Time tracking
    - Comments and collaboration
    - Board analytics
    """

    def __init__(self, board_id: str, name: str):
        self.board_id = board_id
        self.name = name
        self.created_at = datetime.now(timezone.utc)

        # Tasks
        self.tasks: Dict[str, KanbanTask] = {}

        # Columns
        self.columns: Dict[TaskStatus, BoardColumn] = {
            TaskStatus.TODO: BoardColumn(TaskStatus.TODO, "To Do", wip_limit=None),
            TaskStatus.IN_PROGRESS: BoardColumn(
                TaskStatus.IN_PROGRESS, "In Progress", wip_limit=5
            ),
            TaskStatus.REVIEW: BoardColumn(TaskStatus.REVIEW, "Review", wip_limit=3),
            TaskStatus.BLOCKED: BoardColumn(
                TaskStatus.BLOCKED, "Blocked", wip_limit=None
            ),
            TaskStatus.DONE: BoardColumn(TaskStatus.DONE, "Done", wip_limit=None),
        }

        # Members
        self.members: Set[str] = set()

    def create_task(
        self,
        title: str,
        description: str,
        created_by: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None,
        estimated_minutes: int = 0,
        tags: Set[str] = None,
    ) -> str:
        """
        Create new task

        Args:
            title: Task title
            description: Task description
            created_by: Creator client ID
            priority: Task priority
            assignee: Optional assignee
            due_date: Optional due date
            estimated_minutes: Time estimate
            tags: Task tags

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]

        task = KanbanTask(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            assignee=assignee,
            created_by=created_by,
            due_date=due_date,
            estimated_minutes=estimated_minutes,
            tags=tags or set(),
        )

        self.tasks[task_id] = task
        self.columns[TaskStatus.TODO].tasks.append(task_id)

        return task_id

    def move_task(
        self, task_id: str, new_status: TaskStatus, moved_by: str = ""
    ) -> bool:
        """
        Move task to new status

        Args:
            task_id: Task ID
            new_status: Target status
            moved_by: Who moved it

        Returns:
            True if moved successfully
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        old_status = task.status

        # Check WIP limit
        if new_status in [TaskStatus.IN_PROGRESS, TaskStatus.REVIEW]:
            column = self.columns[new_status]
            if column.wip_limit and len(column.tasks) >= column.wip_limit:
                raise Exception(
                    f"WIP limit reached for {new_status.value}: {column.wip_limit}"
                )

        # Check dependencies
        if new_status == TaskStatus.IN_PROGRESS:
            if not self._can_start_task(task_id):
                raise Exception(f"Task blocked by dependencies: {task.dependencies}")

        # Remove from old column
        if task_id in self.columns[old_status].tasks:
            self.columns[old_status].tasks.remove(task_id)

        # Add to new column
        self.columns[new_status].tasks.append(task_id)

        # Update task
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)

        # Add comment
        self.add_comment(
            task_id,
            moved_by or "SYSTEM",
            f"Moved from {old_status.value} to {new_status.value}",
        )

        return True

    def assign_task(self, task_id: str, assignee: str) -> bool:
        """Assign task to member"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        old_assignee = task.assignee
        task.assignee = assignee
        task.updated_at = datetime.now(timezone.utc)

        self.add_comment(
            task_id,
            "SYSTEM",
            f"Assigned to {assignee}"
            + (f" (was: {old_assignee})" if old_assignee else ""),
        )

        return True

    def add_dependency(self, task_id: str, depends_on: str) -> bool:
        """Add task dependency"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.dependencies.add(depends_on)
        task.updated_at = datetime.now(timezone.utc)

        return True

    def _can_start_task(self, task_id: str) -> bool:
        """Check if task can be started (all dependencies done)"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.DONE:
                return False

        return True

    def add_comment(self, task_id: str, author: str, text: str):
        """Add comment to task"""
        task = self.tasks.get(task_id)
        if not task:
            return

        task.comments.append(
            {
                "id": str(uuid.uuid4())[:8],
                "author": author,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        task.updated_at = datetime.now(timezone.utc)

    def add_time(self, task_id: str, minutes: int):
        """Add time spent on task"""
        task = self.tasks.get(task_id)
        if task:
            task.time_spent_minutes += minutes
            task.updated_at = datetime.now(timezone.utc)

    def get_task(self, task_id: str) -> Optional[KanbanTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[KanbanTask]:
        """Get all tasks in status"""
        task_ids = self.columns[status].tasks
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]

    def get_tasks_by_assignee(self, assignee: str) -> List[KanbanTask]:
        """Get all tasks assigned to member"""
        return [t for t in self.tasks.values() if t.assignee == assignee]

    def get_overdue_tasks(self) -> List[KanbanTask]:
        """Get overdue tasks"""
        now = datetime.now(timezone.utc)
        return [
            t
            for t in self.tasks.values()
            if t.due_date and t.due_date < now and t.status != TaskStatus.DONE
        ]

    def get_blocked_tasks(self) -> List[KanbanTask]:
        """Get tasks blocked by dependencies"""
        blocked = []
        for task in self.tasks.values():
            if task.status == TaskStatus.TODO and task.dependencies:
                if not self._can_start_task(task.id):
                    blocked.append(task)
        return blocked

    def get_analytics(self) -> Dict:
        """Get board analytics"""
        total_tasks = len(self.tasks)

        if total_tasks == 0:
            return {
                "total_tasks": 0,
                "by_status": {},
                "by_priority": {},
                "by_assignee": {},
                "completion_rate": 0,
                "avg_time_per_task": 0,
                "total_time_spent": 0,
            }

        # Count by status (only for columns that exist)
        by_status = {}
        for status in TaskStatus:
            if status in self.columns:
                by_status[status.value] = len(self.get_tasks_by_status(status))
            else:
                # Count tasks with this status that aren't in columns
                by_status[status.value] = sum(
                    1 for t in self.tasks.values() if t.status == status
                )

        # Count by priority
        by_priority = {}
        for priority in TaskPriority:
            by_priority[priority.value] = sum(
                1 for t in self.tasks.values() if t.priority == priority
            )

        # Count by assignee
        by_assignee = {}
        for task in self.tasks.values():
            if task.assignee:
                by_assignee[task.assignee] = by_assignee.get(task.assignee, 0) + 1

        # Completion rate
        done_count = by_status.get(TaskStatus.DONE.value, 0)
        completion_rate = (done_count / total_tasks * 100) if total_tasks > 0 else 0

        # Time tracking
        total_time = sum(t.time_spent_minutes for t in self.tasks.values())
        avg_time = total_time / total_tasks if total_tasks > 0 else 0

        # Overdue
        overdue = len(self.get_overdue_tasks())
        blocked = len(self.get_blocked_tasks())

        return {
            "total_tasks": total_tasks,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_assignee": by_assignee,
            "completion_rate": completion_rate,
            "avg_time_per_task": avg_time,
            "total_time_spent": total_time,
            "overdue_tasks": overdue,
            "blocked_tasks": blocked,
            "active_members": len(by_assignee),
        }

    def export_board(self) -> Dict:
        """Export board to JSON"""
        return {
            "board_id": self.board_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "members": list(self.members),
            "tasks": [
                {
                    **asdict(task),
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "tags": list(task.tags),
                    "dependencies": list(task.dependencies),
                }
                for task in self.tasks.values()
            ],
            "analytics": self.get_analytics(),
        }


class KanbanBoardManager:
    """Manage multiple kanban boards"""

    def __init__(self):
        self.boards: Dict[str, KanbanBoard] = {}

    def create_board(self, name: str) -> str:
        """Create new board"""
        board_id = str(uuid.uuid4())[:8]
        board = KanbanBoard(board_id, name)
        self.boards[board_id] = board
        return board_id

    def get_board(self, board_id: str) -> Optional[KanbanBoard]:
        """Get board by ID"""
        return self.boards.get(board_id)

    def list_boards(self) -> List[Dict]:
        """List all boards"""
        return [
            {
                "board_id": board.board_id,
                "name": board.name,
                "total_tasks": len(board.tasks),
                "done_tasks": len(board.get_tasks_by_status(TaskStatus.DONE)),
                "members": len(board.members),
            }
            for board in self.boards.values()
        ]


if __name__ == "__main__":
    print("=" * 80)
    print("📋 Kanban Board for Multi-Claude Task Management")
    print("=" * 80)

    # Create board
    manager = KanbanBoardManager()
    board_id = manager.create_board("Build Trading Bot")
    board = manager.get_board(board_id)

    print(f"\n📍 Board: {board.name} ({board_id})")

    # Create tasks
    print("\n📝 Creating tasks...")

    task1 = board.create_task(
        "Set up Python environment",
        "Install dependencies: pandas, yfinance, alpaca-py",
        created_by="claude-code",
        priority=TaskPriority.HIGH,
        assignee="claude-desktop-1",
        estimated_minutes=30,
    )

    task2 = board.create_task(
        "Implement momentum strategy",
        "Code RSI + MACD momentum detector",
        created_by="claude-code",
        priority=TaskPriority.HIGH,
        assignee="claude-desktop-1",
        estimated_minutes=120,
    )

    task3 = board.create_task(
        "Write unit tests",
        "Test all trading signals",
        created_by="claude-code",
        priority=TaskPriority.MEDIUM,
        assignee="claude-desktop-2",
        estimated_minutes=60,
    )

    # Add dependency
    board.add_dependency(task2, task1)  # Task 2 depends on task 1
    board.add_dependency(task3, task2)  # Task 3 depends on task 2

    # Move tasks
    print("\n🔄 Moving tasks through workflow...")

    board.move_task(task1, TaskStatus.IN_PROGRESS, "claude-desktop-1")
    board.add_time(task1, 25)
    board.add_comment(task1, "claude-desktop-1", "All dependencies installed")
    board.move_task(task1, TaskStatus.DONE, "claude-desktop-1")

    board.move_task(task2, TaskStatus.IN_PROGRESS, "claude-desktop-1")
    board.add_comment(
        task2, "claude-desktop-1", "RSI indicator complete, working on MACD"
    )

    # Analytics
    print("\n📊 Board Analytics:")
    analytics = board.get_analytics()
    for key, value in analytics.items():
        if not isinstance(value, dict):
            print(f"   {key}: {value}")

    print("\n📈 Tasks by Status:")
    for status, count in analytics["by_status"].items():
        if count > 0:
            print(f"   {status}: {count}")

    print("\n👥 Tasks by Assignee:")
    for assignee, count in analytics["by_assignee"].items():
        print(f"   {assignee}: {count}")

    # Show blocked tasks
    blocked = board.get_blocked_tasks()
    if blocked:
        print(f"\n🚫 Blocked tasks: {len(blocked)}")
        for task in blocked:
            print(f"   - {task.title} (blocked by: {task.dependencies})")

    print("\n✅ Kanban board demo complete!")
