from __future__ import absolute_import

from celery import shared_task
from celery.utils.log import get_task_logger
from docker import Client

logger = get_task_logger(__name__)


@shared_task
def add(x, y):
    """Test task, adds x + y"""
    logger.info('Adding {0} + {1}'.format(x, y))
    return x + y


@shared_task
def rundocker(name):
    """Task to run docker container"""
    logger.info('Running docker container')
    d = docker_run(name)
    for log in d.log():
        logger.info(log)
        # current_task.update_state(task_id=current_task.request.id, state='PROGRESS', meta={'current': 1, 'total':100})
    logger.info('Destroying docker container')
    d.remove()
    return


class docker_run():

    """Class to run docker containers with specific configs"""

    def __init__(self, name, image='x', base_url='unix://var/run/docker.sock'):
        from docker import Client

        self.image = image
        self.name = name
        self.base_url = base_url
        self.c = Client(base_url=self.base_url)

        self.create_container()
        self.start_container()

    def create_container(self):
        config = self.c.create_host_config(binds=[
             # '/home/epta/git/celery_test/01_standard:/data',
             '/data/container/01_standard:/data', # for vagrant host
         ])

        self.container = self.c.create_container(self.name, host_config=config)
        self.id = self.container.get('Id')

    def start_container(self):
        self.c.start(container=self.id)

    def log(self):
        self.log = self.c.logs(container=self.id,
                               stream=True, stdout=True, stderr=True)
        return self.log

    def remove(self):
        self.c.remove_container(container=self.id)