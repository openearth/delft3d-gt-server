from __future__ import absolute_import

import json
import os
import time
from shutil import copyfile

from delft3dworker.utils import delft3d_logparser
from delft3dworker.utils import python_logparser

from django.conf import settings  # noqa

from celery import shared_task
from celery.contrib.abortable import AbortableTask, AbortableAsyncResult
from celery.utils.log import get_task_logger
from itertools import chain as explode
from docker import Client

logger = get_task_logger(__name__)

@shared_task(bind=True, base=AbortableTask)
def chainedtask(self, workingdir):
    """ Chained task which can be aborted. Contains model logic. """

    # define chain and results
    chain = pre_dummy.s(workingdir, "") | sim_dummy.s(workingdir) | post_dummy.s(workingdir)
    chain_result = chain()
    results = {}

    # main task loop
    running = True
    while running:

        # abort handling
        if self.is_aborted():

            logger.info("Chain is aborted")
            leaf = chain_result
            while leaf:
                if leaf.status == "PENDING":
                    leaf.revoke()
                    results[leaf.id] = leaf.state
                else:
                    AbortableAsyncResult(leaf.id).abort()
                    results[leaf.id] = leaf.state
                leaf = leaf.parent
            results['result'] = "Aborted"
            self.update_state(state="ABORTED", meta=results)
            return results

        # revoke handling
        elif (
            not self.app.control.inspect().revoked() is None
            and
            self.request.id in explode.from_iterable(
                self.app.control.inspect().revoked().values()
            )
        ):

            logger.info("Chain is revoked")
            leaf = chain_result
            while leaf:
                leaf.revoke()
                results[leaf.id] = leaf.state
                leaf = leaf.parent
            results['result'] = "Revoked"
            self.update_state(state="REVOKED", meta=results)
            return results

        # if no abort or revoke: update state
        else:

            leaf = chain_result
            while leaf:
                results[leaf.id] = leaf.state
                leaf = leaf.parent
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted(): self.update_state(state="PROCESSING", meta=results)

        time.sleep(0.5)

        logger.info("Running loop in chain")
        running = not chain_result.ready()

    logger.info("Finishing chain")
    results['result'] = "Finished"
    self.update_state(state="FINISHING", meta=results)

    return results


@shared_task(bind=True, base=AbortableTask)
def pre_dummy(self, workingdir, _):
    """ Chained task which can be aborted. Contains model logic. """

    # create folders
    inputfolder = os.path.join(workingdir, 'preprocess')
    os.makedirs(inputfolder)

    # copy input.ini
    copyfile(os.path.join(workingdir, 'input.ini'), os.path.join(inputfolder, 'input.ini'))

    # create Preprocess container
    volumes = ['{0}:/data/output'.format(workingdir),
               '{0}:/data/input'.format(inputfolder)]
    # command = "python dummy_create_config.py {}".format(10)  # old dummy
    command = "python /data/input/svn/scripts/preprocessing/preprocessing.py"  # new hotness
    preprocess_container = DockerClient(settings.PREPROCESS_IMAGE_NAME, volumes, '', command)

    # start preprocess
    state_meta = {"model_id": self.request.id, "output": ""}

    preprocess_container.start()
    logger.info("Started preprocessing")
    self.update_state(state='STARTED', meta=state_meta)

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            preprocess_container.stop()
            break

        # if no abort or revoke: update state
        else:
            state_meta["output"] = python_logparser(preprocess_container.get_log())
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted(): self.update_state(state='PROCESSING', meta=state_meta)

        running = preprocess_container.running()

    # preprocess_container.delete()  # Doesn't work on NFS fs

    return state_meta


@shared_task(bind=True, base=AbortableTask)
def sim_dummy(self, _, workingdir):
    # create folders
    outputfolder = os.path.join(workingdir, 'process')
    os.makedirs(outputfolder)

    # create Sim container
    volumes = ['{0}:/data'.format(workingdir)]
    command = ""
    simulation_container = DockerClient(settings.DELFT3D_IMAGE_NAME, volumes, '', command)

    # create Process container
    volumes = ['{0}:/data/input:ro'.format(workingdir),
               '{0}:/data/output'.format(outputfolder)]
    command = ""
    processing_container = DockerClient(settings.PROCESS_IMAGE_NAME, volumes, '', command)

    # start simulation
    state_meta = {"model_id": self.request.id, "output": ""}
    simulation_container.start()
    logger.info("Started simulation")
    self.update_state(state='STARTED', meta=state_meta)

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            processing_container.stop()
            simulation_container.stop()
            break

        # if no abort or revoke: update state
        else:
            # process
            logger.info("Started processing")
            processing_container.start()

            # update state
            state_meta["output"] = [
                delft3d_logparser(simulation_container.get_log()),
                python_logparser(processing_container.get_log())
            ]
            logger.info(state_meta["output"])
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted(): self.update_state(state="PROCESSING", meta=state_meta)

        time.sleep(2)

        running = simulation_container.running()

    # simulation_container.delete()  # Doesn't work on NFS fs
    # processing_container.delete()  # Doesn't work on NFS fs

    return state_meta


@shared_task(bind=True, base=AbortableTask)
def post_dummy(self, _, workingdir):
    # create folders
    outputfolder = os.path.join(workingdir, 'postprocess')
    os.makedirs(outputfolder)

    # create Postprocess container
    volumes = ['{0}:/data/input:ro'.format(workingdir),
               '{0}:/data/output'.format(outputfolder)]
    command = ""
    postprocessing_container = DockerClient(settings.PROCESS_IMAGE_NAME, volumes, '', command)

    # start Postprocess
    state_meta = {"model_id": self.request.id, "output": ""}
    postprocessing_container.start()
    logger.info("Started postprocessing")
    self.update_state(state='PROCESSING', meta=state_meta)

    # loop task
    self.update_state(state='STARTED', meta=state_meta)

    running = True
    while running:
        if self.is_aborted():
            postprocessing_container.stop()
            break
        else:
            state_meta["output"] = python_logparser(postprocessing_container.get_log())
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted(): self.update_state(state='PROCESSING', meta=state_meta)

        time.sleep(2)

        running = postprocessing_container.running()

    # postprocessing_container.delete()  # Doesn't work on NFS fs

    return state_meta


######################### DockerClient

class DockerClient():

    """Class to run docker containers with specific configs.
    TODO kwargs input, integration with wrapper.
    """

    def __init__(self, name, volumebinds, outputfile, command, base_url='unix://var/run/docker.sock'):
        self.name = name
        self.volumebinds = volumebinds
        self.outputfile = outputfile
        self.base_url = base_url
        self.command = command

        self.client = Client(base_url=self.base_url)
        self.config = self.client.create_host_config(binds=self.volumebinds)
        self.container = self.client.create_container(self.name, host_config=self.config, command=self.command)

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
        ).replace('\n', '')
        return self.log

    def get_stderr(self):
        self.errlog = self.client.logs(
            container=self.id,
            stream=False,
            stdout=False,
            stderr=True,
            tail=5
        ).replace('\n', '')
        return self.errlog

    # Deprecated (wrapper should enable this)
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
