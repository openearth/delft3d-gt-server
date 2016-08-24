from __future__ import absolute_import

from celery import shared_task
from celery.contrib.abortable import AbortableTask
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, base=AbortableTask)
def my_task(self):
    """
    A task
    """
    return 5
