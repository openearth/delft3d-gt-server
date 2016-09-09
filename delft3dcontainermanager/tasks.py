from __future__ import absolute_import

import os
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
    This task runs the containersync_sceneupdate management command.
    This command updates the states in container and scene model
    """
    call_command('containersync_sceneupdate')
    return


@shared_task(bind=True, throws=(HTTPError))
def get_docker_ps(self):
    """
    Retrieve all running docker containers and return them in
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
    containers_id = [container['Id'] for container in containers]
    inspected_containers = [client.inspect_container(
        container_id) for container_id in containers_id]
    return inspected_containers


@shared_task(bind=True, throws=(HTTPError))
def get_docker_log(self, container_id, stdout=True, stderr=False, tail=5):
    """
    Retrieve the log of a container and return container id and log
    """
    client = Client(base_url='unix://var/run/docker.sock')
    log = client.logs(
        container=str(container_id),
        stream=False,
        stdout=stdout,
        stderr=stderr,
        timestamps=True,
        tail=5
    )
    return container_id, log


@shared_task(bind=True, throws=(HTTPError))
def do_docker_create(self, label, parameters, environment, name, image,
                     volumes, folders, command):
    """
    Create necessary directories in a working directory
    for the mounts in the containers.

    Write .ini file filled with given parameters in each folder.

    Create a new docker container from a given image and
    return the id of the container
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
        name=name,
        host_config=config,  # mounts
        command=command,  # command to run
        environment=environment,  # {'uuid' = ""} for cloud fs sync
        labels=label  # type of container
    )
    container_id = container.get('Id')
    return container_id, ""


@shared_task(bind=True, throws=(HTTPError))
def do_docker_start(self, container_id):
    """
    Start a container with a specific id and id
    """
    client = Client(base_url='unix://var/run/docker.sock')
    client.start(container=container_id)
    return container_id, ""


@shared_task(bind=True, throws=(HTTPError))
def do_docker_stop(self, container_id, timeout=10):
    """
    Stop a container with a specific id and return id
    """
    client = Client(base_url='unix://var/run/docker.sock')
    client.stop(container=container_id, timeout=timeout)
    return container_id, ""


@shared_task(bind=True, throws=(HTTPError))
def do_docker_remove(self, container_id, force=False):
    """
    Remove a container with a specific id and return id
    """
    client = Client(base_url='unix://var/run/docker.sock')
    client.remove_container(container=container_id, force=force)
    return container_id, ""


@shared_task(bind=True)
def do_docker_sync_filesystem(self, container_id):
    """
    TODO: implement task do_docker_sync_filesystem
    This task should sync the filesystem of a container with a specific id and
    return id
    """
    return container_id, ""
