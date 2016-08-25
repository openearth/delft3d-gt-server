from __future__ import absolute_import

from celery import shared_task
from celery.utils.log import get_task_logger
from docker import Client
from requests.exceptions import HTTPError

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
    return containers


@shared_task(bind=True, throws=(HTTPError))
def get_docker_log(self, container_id, stdout=True, stderr=False, tail=5):
    """
    Retrieve the log of a container and return it in a string
    """
    client = Client(base_url='unix://var/run/docker.sock')
    log = client.logs(
        container=container_id,
        stream=False,
        stdout=stdout,
        stderr=stderr,
        tail=tail,
        timestamps=True,
    ).replace('\n', '')
    return log


@shared_task(bind=True)
def do_docker_create(self, image):
    """
    TODO: implement task do_docker_create
    This task should create a new docker container from a given image and
    return the id of the container
    """
    container_id = None

    return container_id


@shared_task(bind=True, throws=(HTTPError))
def do_docker_start(self, container_id):
    """
    Start a container with a specific id and return whether
    the container is started
    """
    client = Client(base_url='unix://var/run/docker.sock')
    client.start(container=container_id)
    return True


@shared_task(bind=True, throws=(HTTPError))
def do_docker_stop(self, container_id, timeout=10):
    """
    Stop a container with a specific id and return whether
    the container is stopped
    """
    client = Client(base_url='unix://var/run/docker.sock')
    client.stop(container=container_id, timeout=timeout)
    return True


@shared_task(bind=True, throws=(HTTPError))
def do_docker_remove(self, container_id, force=False):
    """
    Remove a container with a specific id and return whether
    the container is removed
    """
    client = Client(base_url='unix://var/run/docker.sock')
    client.remove_container(container=container_id, force=force)
    return True


@shared_task(bind=True)
def do_docker_sync_filesystem(self, container_id):
    """
    TODO: implement task do_docker_sync_filesystem
    This task should sync the filesystem of a container with a specific id and
    return whether the filesystem is synced
    """
    return False

