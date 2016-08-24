from __future__ import absolute_import

from celery import shared_task

logger = get_task_logger(__name__)


@shared_task(bind=True, base=AbortableTask)
def task(self):
    """
    A task
    """
    pass
