from __future__ import absolute_import

from celery import shared_task
from celery.utils.log import get_task_logger
from docker import Client
from requests.exceptions import HTTPError

logger = get_task_logger(__name__)


@shared_task(bind=True, throws=(HTTPError))
def get_docker_ps(self):
    """
    This task retrieves all running docker containers and return them in
    an array of dictionaries. Array looks like this:

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


@shared_task(bind=True)
def do_docker_create(self, image):
    """
    TODO: implement task do_docker_create
    This task should create a new docker container from a given image and
    return the id of the container
    """
    container_id = None

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
