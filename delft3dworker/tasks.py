from __future__ import absolute_import

import os
import json

from django.conf import settings

from celery import shared_task
from celery.contrib.abortable import AbortableTask
from celery.utils.log import get_task_logger

from docker import Client

logger = get_task_logger(__name__)


@shared_task(bind=True, base=AbortableTask)
def donothing(self):
    logger.info('Starting task "donothing"...')
    state_meta = {}
    self.update_state(state='DOINGNOTHING', meta=state_meta)
    logger.info('... task "donothing" finished.')
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def postprocess(self):
    logger.info('Starting task "postprocess"...')
    for n in range(1, 1001):
        state_meta = {'progress': n / 1000.0 }
        self.update_state(state='SIMULATING', meta=state_meta)
    logger.info('... task "postprocess" finished.')
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def process(self, workingdir):
    logger.info('Starting task "process"...')
    output = {}

    #  Make Delft3D Processing Docker Client
    self.update_state(state='CREATING', meta={})
    docker_client = Delft3DDockerClient(
        settings.PROCESS_IMAGE_NAME,
        [
            '{0}:/data/input:ro'.format(os.path.join(workingdir, 'delft3d')),
            '{0}:/data/output'.format(os.path.join(workingdir, 'process'))
        ],
        os.path.join(workingdir, 'process/log_json.json'),
        './run.sh channel_network delta_fringe',
    )

    # output
    output = {}

    try:

        # Start
        self.update_state(state='STARTING', meta=output)
        docker_client.start()

        for log in docker_client.log():
            logger.info(log.replace('\n', ''))

            if (self.is_aborted()):
                logger.warning('Aborting task "process"')
                self.update_state(state='ABORTING', meta=output)
                docker_client.stop()
                break

            self.update_state(state='PROCESSING', meta=output)

            try:
                output = json.loads(docker_client.get_output())

                if 'delta_fringe_images' in output:
                    output['delta_fringe_images']['location'] = os.path.join('process', output['delta_fringe_images']['location'])
                if 'channel_network_images' in output:
                    output['channel_network_images']['location'] = os.path.join('process', output['channel_network_images']['location'])
            except ValueError as e:
                logger.warn('ValueError in taks "process". Trying to load json: '+ docker_client.get_output())
                output['error'] = str(e)
                docker_client.stop()
                break

        self.update_state(state='DELETING', meta=output)
        docker_client.delete()

    except Exception as e:
        output['error'] = str(e)

    logger.info('... task "process" finished.')
    return output


@shared_task(bind=True, base=AbortableTask)
def simulate(self, workingdir):
    logger.info('Starting task "simulate"...')
    output = {}

    #  Make Delft3D Simulation Docker Client
    self.update_state(state='CREATING', meta={})
    docker_client = Delft3DDockerClient(
        settings.DELFT3D_IMAGE_NAME,
        [
            '{0}:/data'.format(os.path.join(workingdir, 'delft3d')),
        ],
        '',
        '',  # empty command
    )

    # output
    output = {}

    try:

        # Start
        self.update_state(state='STARTING', meta=output)
        docker_client.start()

        for log in docker_client.log():
            logger.info(log.replace('\n', ''))

            if (self.is_aborted()):
                logger.warning('Aborting task "simulate"')
                self.update_state(state='ABORTING', meta=output)
                docker_client.stop()
                break

            self.update_state(state='PROCESSING', meta=output)

            try:
                output = json.loads(docker_client.get_output())

                if 'delta_fringe_images' in output:
                    output['delta_fringe_images']['location'] = os.path.join('process', output['delta_fringe_images']['location'])
                if 'channel_network_images' in output:
                    output['channel_network_images']['location'] = os.path.join('process', output['channel_network_images']['location'])
            except ValueError as e:
                logger.warn('ValueError in taks "simulate". Trying to load json: '+ docker_client.get_output())
                output['error'] = str(e)
                docker_client.stop()
                break

        self.update_state(state='DELETING', meta=output)
        docker_client.delete()

    except Exception as e:
        output['error'] = str(e)

    logger.info('... task "simulate" finished.')
    return output


# ######################## Delft3DDockerClient

class Delft3DDockerClient():

    """Class to run docker containers with specific configs"""

    def __init__(self, name, volumebinds, outputfile, command, base_url='unix://var/run/docker.sock'):
        self.name = name
        self.volumebinds = volumebinds
        self.outputfile = outputfile
        self.base_url = base_url
        self.command = command

        self.client = Client(base_url=self.base_url)
        self.config = self.client.create_host_config(binds=self.volumebinds)
        self.container = self.client.create_container(self.name, cpu_shares=400, host_config=self.config, command=self.command)

        self.id = self.container.get('Id')

    def start(self):
        self.client.start(container=self.id)

    def stop(self):
        self.client.stop(container=self.id)

    def log(self):
        self.log = self.client.logs(
            container=self.id,
            stream=True,
            stdout=True,
            stderr=True
        )
        return self.log

    def get_output(self):
        if self.outputfile == '':
            return '{}'

        try:
            with open(self.outputfile, 'r') as f:
                returnval = f.read()
                f.close()
        except:
            return '{}'

        return returnval

    def delete(self):
        self.client.remove_container(container=self.id)
