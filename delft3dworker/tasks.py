from __future__ import absolute_import

from celery import shared_task
from celery.utils.log import get_task_logger
from docker import Client

logger = get_task_logger(__name__)


@shared_task
def rundocker(name, workingdir):
    
    """Task to run docker container"""
    
    logger.info('Creating docker container')
    d = DockerRun(name, workingdir)

    logger.info('Running docker container')
    d.start()
    for log in d.log():
        logger.info(log)
    
    logger.info('Destroying docker container')
    d.remove()
    
    return


class DockerRun():

    """Class to run docker containers with specific configs"""

    def __init__(self, name, workingdir, base_url='unix://var/run/docker.sock'):
        self.name = name
        self.workingdir = workingdir        
        self.base_url = base_url

        self.client = Client(base_url=self.base_url)

        self._create_container()

    def start(self):
        self.client.start(container=self.id)

    def log(self):
        self.log = self.client.logs(container=self.id,
                               stream=True, stdout=True, stderr=True)
        return self.log

    def remove(self):
        self.client.remove_container(container=self.id)

    def _create_container(self):

        config = self.client.create_host_config(binds=[
             '{0}:/data'.format(self.workingdir),
         ])

        self.container = self.client.create_container(self.name, host_config=config)
        self.id = self.container.get('Id')

