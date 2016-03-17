from __future__ import absolute_import

import time
import json

from celery import shared_task
from celery.contrib.abortable import AbortableTask
from celery.utils.log import get_task_logger

from docker import Client

logger = get_task_logger(__name__)


# ################################### Sprint 2 Architecture

@shared_task(bind=True, base=AbortableTask)
def donothing(self):
    logger.info('Starting task "donothing"...')
    state_meta = {}
    self.update_state(state='DOINGNOTHING', meta=state_meta)
    logger.info('... task "donothing" Finished')
    return state_meta

@shared_task(bind=True, base=AbortableTask)
def postprocess(self):
    logger.info('Starting task "postprocess"...')
    for n in range(1, 1001):
        state_meta = {'progress': n / 1000.0 }
        self.update_state(state='SIMULATING', meta=state_meta)
    logger.info('... task "postprocess" Finished')
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def process(self, image, workingdir):

    volume_binds = ['{0}:/data/input:ro'.format(os.path.join(workingdir,'delft3d')),
                    '{0}:/data/output'.format(os.path.join(workingdir,'process'))]

    docker_run = DockerRun(image, volume_binds)
    docker_run.start()

    # process container will create json log
    with open(os.path.join(workingdir, 'process', 'log.json')) as logfile:    
        log = json.load(logfile)

    logger.info('Starting task "process"...')

    for log in docker_run.log():
        if (self.is_aborted()):
            docker_run.stop()
            state_meta = {'progress': 0 }
            self.update_state(state='ABORTING', meta=state_meta)

        state_meta = {
            'channel_network_images': {
                'location': '/sampledata/',
                'images': [
                    'example_channel_network_1.png',
                    'example_channel_network_2.png',
                    'example_channel_network_3.png'
                ]
            },
            'delta_fringe_images':  {
                'location': '/sampledata/',
                'images': [
                    'example_delta_fringe_1.png',
                    'example_delta_fringe_2.png',
                    'example_delta_fringe_3.png',
                    'example_delta_fringe_4.png',
                    'example_delta_fringe_5.png'
                ]
            },
            'logfile': '/sampledata/logfile.f34',
            'progress': 1 / 1000.0,
        }
        self.update_state(state='PROCESSING', meta=state_meta)

    docker_run.remove()
    logger.info('... task "process" Finished')

    return state_meta

@shared_task(bind=True, base=AbortableTask)
def simulate(self, image, workingdir):
    logger.info('Starting task simulate...')

    volume_binds = ['{0}:/data'.format(os.path.join(workingdir, 'delft3d'))]

    docker_run = DockerRun(image, volume_binds)
    docker_run.start()

    for log in docker_run.log():
        if (self.is_aborted()):
            docker_run.stop()
            state_meta = {'progress': 0 }
            self.update_state(state='ABORTING', meta=state_meta)

        state_meta = {'progress': 1 / 1000.0 }
        self.update_state(state='SIMULATING', meta=state_meta)

    logger.info('... task "simulate" Finished')

    docker_run.remove()

    return state_meta

#################################### Sprint 1 Architecture (deprecated)

@shared_task(bind=True, base=AbortableTask)
def rundocker(self, name, uuid, workingdir):

    """Task to run docker container"""

    logger.info('Creating docker container')

    docker_run = DockerRun(name, volume_binds)

    logger.info('Running docker container')
    docker_run.start()

    for log in docker_run.log():

        logger.info(log)

        # check for abortion
        if (self.is_aborted()):
            logger.info('ABORTING')
            items = log.split(',')
            self.update_state(state='ABORTING', meta={
                'time_to_finish': items[0].strip(),
                'percent_completed': 'abort procedure...',
                'timesteps_left': items[2].strip()
            })
            docker_run.stop()
        else:
            items = log.split(',')
            if len(items) == 3:
                self.update_state(state='SIMULATING', meta={
                    'time_to_finish': items[0].strip(),
                    'percent_completed': items[1].strip(),
                    'timesteps_left': items[2].strip()
                })

    logger.info('Destroying docker container')
    docker_run.remove()

    return


class DockerRun():

    """Class to run docker containers with specific configs"""

    def __init__(self, name, volumebinds, base_url='unix://var/run/docker.sock'):

        self.name = name
        self.volumebinds = volumebinds
        self.base_url = base_url

        self.client = Client(base_url=self.base_url)

        self._create_container()

    def start(self):
        self.client.start(container=self.id)

    def stop(self):
        self.client.stop(container=self.id)

    def log(self):
        self.log = self.client.logs(container=self.id,
                               stream=True, stdout=True, stderr=True)
        return self.log

    def remove(self):
        self.client.remove_container(container=self.id)

    def _create_container(self):

        config = self.client.create_host_config(binds=self.workingbinds)

        self.container = self.client.create_container(self.name, host_config=config)
        self.id = self.container.get('Id')
