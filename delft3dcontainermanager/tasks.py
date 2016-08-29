from __future__ import absolute_import


import os
import shutil
from celery import shared_task
from celery.utils.log import get_task_logger
from docker import Client
from requests.exceptions import HTTPError
from six.moves import configparser
from django.core.management import call_command

logger = get_task_logger(__name__)


@shared_task(bind=True)
def delft3dgt_pulse(self):
    """
    This taks runs the containersync_sceneupdate management command.
    This command updates the states in container and scene model
    """
    call_command('containersync_sceneupdate')

    return


@shared_task(bind=True, throws=(HTTPError))
def get_docker_ps(self):
    """
    This task retrieves all running docker containers and returns them in
    an array of dictionaries. The array looks like this:

    [
      {'Command': '/bin/sleep 30',
      'Created': 1412574844,
      'Id': '6e276c9e6e5759e12a6a9214efec6439f80b4f37618e1a6547f28a3da34db07a',
      'Image': 'busybox:buildroot-2014.02',
      'Names': ['/grave_mayer'],
      'Ports': [],
      'Status': 'Up 1 seconds'},

      {...},
    ]
    """
    client = Client(base_url='unix://var/run/docker.sock')
    containers = client.containers(all=True)
    return containers


@shared_task(bind=True)
def get_docker_log(self, container_id):
    """
    TODO: implement task get_docker_log
    This task should retrieve the log of a container and return it in an object
    """
    return {}


@shared_task(bind=True, throws=(HTTPError))
def do_docker_create(self, image, volumes, folders, command, label, parameters,
                     environment=None):
    """
    Create necessary directories in a working directory 
    for the mounts in the containers.

    Write .ini file filled with given parameters in each folder.

    Create a new docker container from a given image and
    return the id of the container

    This should be in the call from the container model:
        inputfolder = os.path.join(workingdir, 'simulation')
        outputfolder = os.path.join(workingdir, 'export')
        volumes = ['{0}:/data/output:z'.format(outputfolder),
                   '{0}:/data/input:ro'.format(inputfolder)]
        command = "/data/run.sh /data/svn/scripts/export/export2grdecl.py"
    """
    # Create needed folders for mounts
    for folder in folders:
        try:
            os.makedirs(folder, 0o2775)
        # Path already exists, ignore
        except OSError:
            if not os.path.isdir(folder):
                raise

    # Create ini file for containers
    config = configparser.SafeConfigParser()
    for section in parameters:
        if not config.has_section(section):
            config.add_section(section)
        for key, value in parameters[section].items():

            # TODO: find more elegant solution for this! ugh!
            if not key == 'units':
                if not config.has_option(section, key):
                    config.set(*map(str, [section, key, value]))

    for folder in folders:
        with open(os.path.join(folder, 'input.ini'), 'w') as f:
            config.write(f)  # Yes, the ConfigParser writes to f

    # Create docker container
    client = Client(base_url='unix://var/run/docker.sock')
    config = client.create_host_config(binds=volumes)
    container = client.create_container(
        image,  # docker image
        host_config=config,  # mounts
        command=command,  # command to run
        environment=environment,  # {'uuid' = ""} for cloud fs sync
        labels=label  # type of container
    )
    container_id = container.get('Id')
    return container_id


@shared_task(bind=True)
def do_docker_start(self, container_id):
    """
    TODO: implement task do_docker_start
    This task should start a container with a specific id and return whether
    the container is started
    """
    return False


@shared_task(bind=True)
def do_docker_stop(self, container_id):
    """
    TODO: implement task do_docker_stop
    This task should stop a container with a specific id and return whether
    the container is stopped
    """
    return False


@shared_task(bind=True)
def do_docker_remove(self, container_id):
    """
    TODO: implement task do_docker_remove
    This task should remove a container with a specific id and return whether
    the container is removed
    """
    return False


@shared_task(bind=True)
def do_docker_sync_filesystem(self, container_id):
    """
    TODO: implement task do_docker_sync_filesystem
    This task should sync the filesystem of a container with a specific id and
    return whether the filesystem is synced
    """
    return False
