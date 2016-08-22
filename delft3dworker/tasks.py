from __future__ import absolute_import

import json
import logging
import os
import shlex
import shutil
import sys
import subprocess
import time

from six.moves import configparser

from delft3dworker.utils import PersistentLogger

from django.conf import settings  # noqa

from celery import shared_task
from celery.contrib.abortable import AbortableTask, AbortableAsyncResult
from celery.utils.log import get_task_logger
from itertools import chain as explode
from docker import Client

logger = get_task_logger(__name__)

COMMAND_FRINGE = """/bin/ffmpeg -framerate 13 -pattern_type glob -i
 '{}/delta_fringe_*.png' -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"
 -vcodec libx264 -pix_fmt yuv420p -preset slower -b:v 1000k -maxrate 1000k
 -bufsize 2000k -an -force_key_frames expr:gte'('t,n_forced/4')'
 -y {}/delta_fringe.mp4"""

COMMAND_CHANNEL = """/bin/ffmpeg -framerate 13 -pattern_type glob -i
 '{}/channel_network_*.png' -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"
 -vcodec libx264 -pix_fmt yuv420p -preset slower -b:v 1000k -maxrate 1000k
 -bufsize 2000k -an -force_key_frames expr:gte'('t,n_forced/4')'
 -y {}/channel_network.mp4"""

COMMAND_SEDIMENT = """/bin/ffmpeg -framerate 13 -pattern_type glob -i
 '{}/sediment_fraction_*.png' -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2"
 -vcodec libx264 -pix_fmt yuv420p -preset slower -b:v 1000k -maxrate 1000k
 -bufsize 2000k -an -force_key_frames expr:gte'('t,n_forced/4')'
 -y {}/sediment_fraction.mp4"""


@shared_task(bind=True, base=AbortableTask)
def chainedtask(self, uuid, parameters, workingdir, workflow):
    """
    Chained task which can be aborted. Contains model logic.
    """

    # real chains:
    if workflow == "export":
        chain = (
            dummy.s(uuid, workingdir, parameters) |
            export.s(uuid, workingdir, parameters)
        )
    elif workflow == "main":

        chain = (
            create_directory_layout.s(uuid, workingdir, parameters) |
            preprocess.s(uuid, workingdir, parameters) |
            simulation.s(uuid, workingdir, parameters)
        )
    elif workflow == "dummy":
        chain = (
            dummy_preprocess.s(uuid, workingdir, parameters) |
            dummy_simulation.s(uuid, workingdir, parameters)
        )
    elif workflow == "dummy_export":
        chain = (
            dummy.s(uuid, workingdir, parameters) |
            dummy_export.s(uuid, workingdir, parameters)
        )
    else:
        logging.error("workflow not available")
        return

    chain_result = chain()
    state_meta = {'export': False}

    # main task loop
    running = True
    while running:

        # revoke handling
        revoked = self.app.control.inspect().revoked()
        if (
            revoked is not None and
            hasattr(revoked, 'values') and
            self.request.id in explode.from_iterable(
                revoked.values()
            )
        ):

            logger.info("Chain is revoked")
            leaf = chain_result
            while leaf:
                leaf.revoke()
                state_meta[leaf.id] = {
                    "state": leaf.state,
                    "info": leaf.info
                }
                leaf = leaf.parent
            state_meta['result'] = "Revoked"
            self.update_state(state="REVOKED", meta=state_meta)
            return state_meta

        # abort handling
        elif self.is_aborted():

            logger.info("Chain is aborted")
            leaf = chain_result
            while leaf:
                if leaf.status == "PENDING":
                    leaf.revoke()
                    state_meta[leaf.id] = {
                        "state": leaf.state,
                        "info": leaf.info
                    }
                else:
                    AbortableAsyncResult(leaf.id).abort()
                    state_meta[leaf.id] = {
                        "state": leaf.state,
                        "info": leaf.info
                    }
                leaf = leaf.parent
            state_meta['result'] = "Aborted"
            self.update_state(state="ABORTED", meta=state_meta)
            return state_meta

        # if no abort or revoke: update state
        else:

            leaf = chain_result
            while leaf:
                state_meta[leaf.id] = {
                    "state": leaf.state,
                    "info": leaf.info
                }
                leaf = leaf.parent
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                # TODO Crashes here (not json serializable)
                self.update_state(state="PROCESSING", meta=state_meta)

        time.sleep(0.5)

        logger.info("Running loop in chain")
        running = not chain_result.ready()

    logger.info("Finishing chain")
    if workflow == 'export' and os.path.exists(
        os.path.join(workingdir, 'export', 'trim-a.grdecl')
    ):
        state_meta['export'] = True

    # update status one last time
    leaf = chain_result
    while leaf:
        state_meta[leaf.id] = {
            "state": leaf.state,
            "info": leaf.info
        }
        leaf = leaf.parent
    state_meta['result'] = "Finished"
    self.update_state(state="SUCCESS", meta=state_meta)

    logger.info("Task 'chainedtask' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def create_directory_layout(self, uuid, workingdir, parameters):

    # create directory for scene
    if not os.path.exists(workingdir):
        os.makedirs(workingdir, 0o2775)

        folders = ['process', 'preprocess', 'simulation', 'export']

        for f in folders:
            os.makedirs(os.path.join(workingdir, f))

    # create ini file for containers
    # in 2.7 ConfigParser is a bit stupid
    # in 3.x configparser has .read_dict()
    config = configparser.SafeConfigParser()
    for section in parameters:
        if not config.has_section(section):
            config.add_section(section)
        for key, value in parameters[section].items():

            # TODO: find more elegant solution for this! ugh!
            if not key == 'units':
                if not config.has_option(section, key):
                    config.set(*map(str, [section, key, value]))

    with open(os.path.join(workingdir, 'input.ini'), 'w') as f:
        config.write(f)  # Yes, the ConfigParser writes to f

    shutil.copyfile(
        os.path.join(workingdir, 'input.ini'),
        os.path.join(os.path.join(
            workingdir, 'preprocess/' 'input.ini'))
    )
    shutil.copyfile(
        os.path.join(workingdir, 'input.ini'),
        os.path.join(os.path.join(
            workingdir, 'simulation/' 'input.ini'))
    )
    shutil.copyfile(
        os.path.join(workingdir, 'input.ini'),
        os.path.join(os.path.join(
            workingdir, 'process/' 'input.ini'))
    )
    # update state with info
    state_meta = {
        "workingdir": workingdir,
        "directory_layout_created": True
    }

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'create_directory_layout' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def preprocess(self, _result_prev_chain_task, uuid, workingdir, parameters):
    """ Chained task which can be aborted. Contains model logic. """

    # # create folders
    inputfolder = os.path.join(workingdir, 'preprocess')
    outputfolder = os.path.join(workingdir, 'simulation')

    # create Preprocess container
    volumes = [
        '{0}:/data/output:z'.format(outputfolder),
        '{0}:/data/input:ro'.format(inputfolder)
    ]

    command = "/data/run.sh /data/svn/scripts/preprocessing/preprocessing.py"

    preprocess_container = DockerClient(
        settings.PREPROCESS_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # start preprocess
    state_meta = {"model_id": self.request.id, "output": ""}

    preprocess_container.start()
    logger.info("Started preprocessing")
    self.update_state(state='STARTED', meta=state_meta)

    log = PersistentLogger(parser="python")

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            preprocess_container.stop()
            self.update_state(state='ABORTED', meta=state_meta)
            break

        # if no abort or revoke: update state
        else:
            state_meta["task"] = self.__name__
            state_meta["log"] = log.parse(preprocess_container.get_log())
            state_meta["container_id"] = preprocess_container.id
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state='PROCESSING', meta=state_meta)

        running = preprocess_container.running()
        time.sleep(2)

    # preprocess_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'preprocess' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def dummy_preprocess(self, uuid, workingdir, parameters):
    """ Chained task which can be aborted. Contains model logic. """

    # # create folders
    inputfolder = os.path.join(workingdir, 'preprocess')
    outputfolder = os.path.join(workingdir, 'simulation')

    # create Preprocess container
    volumes = ['{0}:/data/output:z'.format(outputfolder),
               '{0}:/data/input:ro'.format(inputfolder)]

    command = "python dummy_create_config.py {}".format(3)  # dummy container

    preprocess_container = DockerClient(
        settings.PREPROCESS_DUMMY_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # start preprocess
    state_meta = {"model_id": self.request.id, "output": ""}

    preprocess_container.start()
    logger.info("Started preprocessing")
    self.update_state(state='STARTED', meta=state_meta)

    log = PersistentLogger(parser="python")

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            preprocess_container.stop()
            break

        # if no abort or revoke: update state
        else:
            state_meta["task"] = self.__name__
            state_meta["log"] = log.parse(preprocess_container.get_log())
            state_meta["container_id"] = preprocess_container.id
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state='PROCESSING', meta=state_meta)

        running = preprocess_container.running()
        time.sleep(2)

    # preprocess_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'dummy_preprocess' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def simulation(self, _result_prev_chain_task, uuid, workingdir, parameters):
    """
    TODO Check if processing is still running
    before starting another one.
    TODO Check how we want to log processing
    """
    # create folders
    inputfolder = os.path.join(workingdir, 'simulation')
    outputfolder = os.path.join(workingdir, 'process')

    # create Sim container
    volumes = ['{0}:/data'.format(inputfolder)]
    command = ""

    simulation_container = DockerClient(
        settings.DELFT3D_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # create Process container
    volumes = ['{0}:/data/input:ro'.format(inputfolder),
               '{0}:/data/output:z'.format(outputfolder)]
    command = ' '.join([
        "/data/run.sh ",
        "/data/svn/scripts/postprocessing/channel_network_proc.py",
        "/data/svn/scripts/postprocessing/delta_fringe_proc.py",
        "/data/svn/scripts/postprocessing/sediment_fraction_proc.py",
        "/data/svn/scripts/visualisation/channel_network_viz.py",
        "/data/svn/scripts/visualisation/delta_fringe_viz.py",
        "/data/svn/scripts/visualisation/sediment_fraction_viz.py"
    ])

    env = {"uuid": uuid}

    processing_container = DockerClient(
        settings.PROCESS_IMAGE_NAME,
        volumes,
        '',
        command,
        environment=env
    )

    # start simulation
    state_meta = {"model_id": self.request.id, "output": ""}
    simulation_container.start()
    logger.info("Started simulation")
    self.update_state(state='STARTED', meta=state_meta)

    simlog = PersistentLogger(parser="delft3d")
    proclog = PersistentLogger(parser="python")

    proc_runs = 0

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            processing_container.stop()
            simulation_container.stop()
            self.update_state(state="ABORTED", meta=state_meta)
            break

        # if no abort or revoke: update state
        else:
            # process
            # sim has progress
            if simlog.changed() and not processing_container.running():
                # Create movie which can be zipped later
                directory = os.path.join(workingdir, 'process')

                command_fringe = COMMAND_FRINGE.format(
                    directory, directory)
                command_channel = COMMAND_CHANNEL.format(
                    directory, directory)
                command_sediment = COMMAND_SEDIMENT.format(
                    directory, directory)

                command_line_process = subprocess.Popen(
                    shlex.split(command_fringe),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                process_output, _ = command_line_process.communicate()
                logger.info(process_output)

                command_line_process = subprocess.Popen(
                    shlex.split(command_channel),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                process_output, _ = command_line_process.communicate()
                logger.info(process_output)

                command_line_process = subprocess.Popen(
                    shlex.split(command_sediment),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                process_output, _ = command_line_process.communicate()
                logger.info(process_output)

                logger.info("Started processing, sim progress changed.")
                processing_container.start()
                proc_runs += 1
                logger.info(state_meta["log"])

            # update state
            state_meta["procruns"] = proc_runs
            state_meta["task"] = self.__name__
            state_meta["log"] = [
                simlog.parse(simulation_container.get_log()),
                # TODO This crashes on the get_log part (404)
                proclog.parse(processing_container.get_log())
            ]
            state_meta["container_id"] = {
                "simulation": simulation_container.id,
                "processing": processing_container.id
            }

            # logger.info(state_meta["log"])
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state="PROCESSING", meta=state_meta)

        time.sleep(2)

        running = simulation_container.running()

    # simulation_container.delete()  # Doesn't work on NFS fs
    # processing_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'simulation' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def dummy_simulation(
        self, _result_prev_chain_task, uuid, workingdir, parameters):
    """
    TODO Check if processing is still running
    before starting another one.
    TODO Check how we want to log processing
    docker run -v /data/container/files/ea8b3912-dedc-4da5-aff8-2a9f3591586e
     /simulation/:/data -t dummy_preprocessing python dummy_netcdf_output.py
    """
    # create folders
    inputfolder = os.path.join(workingdir, 'simulation')
    outputfolder = os.path.join(workingdir, 'process')
    # os.makedirs(outputfolder)

    # create Sim container
    volumes = ['{0}:/data/input'.format(inputfolder)]
    command = "python dummy_netcdf_output.py"

    simulation_container = DockerClient(
        settings.DELFT3D_DUMMY_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # create Process container
    volumes = ['{0}:/data/input:ro'.format(inputfolder),
               '{0}:/data/output:z'.format(outputfolder)]
    command = 'python dummy_plot_netcdf.py'
    processing_container = DockerClient(
        settings.PROCESS_DUMMY_IMAGE_NAME,
        volumes,
        '',
        command,
        tail=5
    )

    # start simulation
    state_meta = {"model_id": self.request.id, "output": ""}
    simulation_container.start()
    logger.info("Started simulation")
    self.update_state(state='STARTED', meta=state_meta)

    simlog = PersistentLogger(parser="delft3d")
    proclog = PersistentLogger(parser="python")

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
            # sim has progress
            if simlog.changed() and not processing_container.running():
                logger.info("Started processing, sim progress changed.")
                processing_container.start()
                logger.info(state_meta["log"])

            # update state
            state_meta["task"] = self.__name__
            state_meta["log"] = [
                simlog.parse(simulation_container.get_log()),
                proclog.parse(processing_container.get_log())
            ]
            state_meta["container_id"] = {
                "simulation": simulation_container.id,
                "processing": processing_container.id
            }

            # logger.info(state_meta["log"])
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state="PROCESSING", meta=state_meta)

        time.sleep(2)

        running = simulation_container.running()

    # simulation_container.delete()  # Doesn't work on NFS fs
    # processing_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'dummy_simulation' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def postprocess(self, _result_prev_chain_task, uuid, workingdir, parameters):
    # create folders
    outputfolder = os.path.join(workingdir, 'postprocess')

    # create Postprocess container
    volumes = ['{0}:/data/input:ro'.format(workingdir),
               '{0}:/data/output'.format(outputfolder)]
    command = ""
    postprocessing_container = DockerClient(
        settings.PROCESS_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # start Postprocess
    state_meta = {"model_id": self.request.id, "output": ""}
    postprocessing_container.start()
    logger.info("Started postprocessing")
    self.update_state(state='PROCESSING', meta=state_meta)

    # loop task
    self.update_state(state='STARTED', meta=state_meta)

    log = PersistentLogger(parser="python")

    running = True
    while running:
        if self.is_aborted():
            postprocessing_container.stop()
            break
        else:
            state_meta["task"] = self.__name__
            state_meta["log"] = log.parse(
                postprocessing_container.get_log()
            )
            state_meta["container_id"] = postprocessing_container.id
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state='PROCESSING', meta=state_meta)

        time.sleep(2)

        running = postprocessing_container.running()

    # postprocessing_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'postprocess' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def export(self, _result_prev_chain_task, uuid, workingdir, parameters):
    """ Chained task which can be aborted. Contains model logic. """

    # # create folders
    inputfolder = os.path.join(workingdir, 'simulation')
    outputfolder = os.path.join(workingdir, 'export')

    # create Preprocess container
    volumes = ['{0}:/data/output:z'.format(outputfolder),
               '{0}:/data/input:ro'.format(inputfolder)]

    # dummy container
    command = "/data/run.sh /data/svn/scripts/export/export2grdecl.py"

    preprocess_container = DockerClient(
        settings.EXPORT_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # start preprocess
    state_meta = {"model_id": self.request.id, "output": ""}

    preprocess_container.start()
    logger.info("Started export")
    self.update_state(state='STARTED', meta=state_meta)

    log = PersistentLogger(parser="python")

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            preprocess_container.stop()
            break

        # if no abort or revoke: update state
        else:
            state_meta["task"] = self.__name__
            state_meta["log"] = log.parse(preprocess_container.get_log())
            state_meta["container_id"] = preprocess_container.id
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state='PROCESSING', meta=state_meta)

        running = preprocess_container.running()
        time.sleep(2)

    # preprocess_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'export' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def dummy_export(self, _result_prev_chain_task, uuid, workingdir, parameters):
    """ Chained task which can be aborted. Contains model logic. """

    # # create folders
    inputfolder = os.path.join(workingdir, 'simulation')
    outputfolder = os.path.join(workingdir, 'export')

    # create Preprocess container
    volumes = ['{0}:/data/output:z'.format(outputfolder),
               '{0}:/data/input:ro'.format(inputfolder)]

    command = "python dummy_export.py"  # dummy container

    preprocess_container = DockerClient(
        settings.PREPROCESS_DUMMY_IMAGE_NAME,
        volumes,
        '',
        command
    )

    # start preprocess
    state_meta = {"model_id": self.request.id, "output": ""}

    preprocess_container.start()
    logger.info("Started export")
    self.update_state(state='STARTED', meta=state_meta)

    log = PersistentLogger(parser="python")

    # loop task
    running = True
    while running:

        # abort handling
        if self.is_aborted():
            preprocess_container.stop()
            break

        # if no abort or revoke: update state
        else:
            state_meta["task"] = self.__name__
            state_meta["log"] = log.parse(preprocess_container.get_log())
            state_meta["container_id"] = preprocess_container.id
            # race condition: although we check it in this if/else statement,
            # aborted state is sometimes lost
            if not self.is_aborted():
                self.update_state(state='PROCESSING', meta=state_meta)

        running = preprocess_container.running()
        time.sleep(2)

    # preprocess_container.delete()  # Doesn't work on NFS fs

    self.update_state(state="SUCCESS", meta=state_meta)
    logger.info("Task 'dummy_export' finished (state=SUCCESS)")
    return state_meta


@shared_task(bind=True, base=AbortableTask)
def dummy(self, uuid, workingdir, parameters):
    """
    Chained task which can be aborted. This task is a dummy task to maintain
    chain functionality. An export chain with a single task is not allowed.
    """
    self.update_state(state="SUCCESS", meta={})
    logger.info("Task 'dummy' finished (state=SUCCESS)")
    return {}


# DockerClient

class DockerClient():

    """Class to run docker containers with specific configs.
    TODO kwargs input, integration with wrapper.
    """

    def __init__(self, name, volumebinds, outputfile, command,
                 base_url='unix://var/run/docker.sock',
                 environment=None, tail=1):
        self.name = name
        self.volumebinds = volumebinds
        self.outputfile = outputfile
        self.base_url = base_url
        self.command = command
        self.environment = environment
        self.tail = tail

        self.client = Client(base_url=self.base_url)
        self.config = self.client.create_host_config(binds=self.volumebinds)

        self.container = self.client.create_container(
            self.name,
            host_config=self.config,
            command=self.command,
            environment=self.environment
        )

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
        try:
            self.log = self.client.logs(
                container=self.id,
                stream=False,
                stdout=True,
                stderr=True,
                tail=1
            ).replace('\n', '')
        except:
            self.errlog = "ERROR: Docker client problem: {}.".format(sys.exc_info()[0])
        return self.log

    def get_stderr(self):
        try:
            self.errlog = self.client.logs(
                container=self.id,
                stream=False,
                stdout=False,
                stderr=True,
                tail=self.tail
            ).replace('\n', '')
        except:
            self.errlog = "ERROR: Docker client problem: {}.".format(sys.exc_info()[0])
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
