from __future__ import absolute_import

import os
import json
import time

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

    # try:
    # Start
    self.update_state(state='STARTING')
    docker_client.start()

    output = json.loads(docker_client.get_output())

    self.update_state(state='PROCESSING', meta=output)

    while docker_client.running():
        logger.info(docker_client.get_log())

        output = json.loads(docker_client.get_output())

        if (self.is_aborted()):
            logger.warning('Aborting task "process"')
            self.update_state(state='ABORTING', meta=output)
            docker_client.stop()
            break
        else:
            self.update_state(state='PROCESSING', meta=output)
            if 'delta_fringe_images' in output:
                output['delta_fringe_images']['location'] = os.path.join('process', output['delta_fringe_images']['location'])
            if 'channel_network_images' in output:
                output['channel_network_images']['location'] = os.path.join('process', output['channel_network_images']['location'])

        time.sleep(5)

    if docker_client.status()['ExitCode'] != 0:
        error = docker_client.get_stderr()
        docker_client.delete()
        raise ValueError(error)

    self.update_state(state='DELETING', meta=output)
    docker_client.delete()

    # except Exception as e:
    #     logger.exception('Exception in task "process": '+ str(e))
    #     docker_client.delete()
    #     self.update_state(state="FAILURE")
    #     return

    logger.info('... task "process" finished.')
    return output


@shared_task(bind=True, base=AbortableTask)
def simulate(self, workingdir):
    logger.info('Starting task "simulate"...')

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

    # try:

    # Start
    self.update_state(state='STARTING', meta={})
    docker_client.start()

    output = docker_client.status()

    self.update_state(state='PROCESSING', meta=output)

    while docker_client.running():
        # logger.info(docker_client.get_log())

        output = docker_client.status()

        if (self.is_aborted()):
            logger.warning('Aborting task "simulate"')
            self.update_state(state='ABORTING', meta=output)
            docker_client.stop()
            break
        else:
            self.update_state(state='PROCESSING', meta=output)

        time.sleep(1)

    output = docker_client.status()

    if docker_client.status()['ExitCode'] != 0:
        error = docker_client.get_stderr()
        docker_client.delete()
        raise ValueError(error)

    self.update_state(state='DELETING', meta=output)
    docker_client.delete()

    # except Exception as e:
    #     logger.exception('Exception in task "simulate": '+ str(e))
    #     docker_client.delete()
    #     self.update_state(state="FAILURE")
    #     return

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

    def running(self):
        return self.client.inspect_container(self.id)['State']['Running']

    def status(self):
        return self.client.inspect_container(self.id)['State']

    def get_log(self):
        self.log = self.client.logs(
            container=self.id,
            stream=False,
            stdout=True,
            stderr=True,
            tail=1
        )
        return self.log

    def get_stderr(self):
        self.errlog = self.client.logs(
            container=self.id,
            stream=False,
            stdout=False,
            stderr=True,
            tail=5
        )
        print(self.errlog)
        return self.errlog

    def get_output(self):
        if self.outputfile == '':
            return '{"info": "get_output has no outputfile (empty string)"}'

        try:
            with open(self.outputfile, 'r') as f:
                returnval = f.read()
                json.loads(returnval)
        except Exception as e:
            return '{"info": "' + str(e) + '"}'

        return returnval

    def delete(self):
        self.client.remove_container(container=self.id)
