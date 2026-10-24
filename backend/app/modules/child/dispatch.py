"""Queue boundary for durable Child Report generations."""

from __future__ import annotations

from uuid import UUID


def dispatch_child_generation(*, generation_id: UUID) -> str:
    from workers.tasks.child import generate_child_report

    task_id = f"child-generation-{generation_id}"
    generate_child_report.apply_async(
        kwargs={"generation_id": str(generation_id)},
        task_id=task_id,
    )
    return task_id
