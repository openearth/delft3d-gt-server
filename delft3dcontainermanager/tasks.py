from __future__ import absolute_import

import logging
import os
from shutil import rmtree
from six.moves import configparser

from celery import shared_task
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from django.conf import settings
from django.core.management import call_command
from docker import Client
from kubernetes import client, config
from requests.exceptions import HTTPError

config.load_kube_config()
logger = get_task_logger(__name__)


@shared_task(bind=True, base=QueueOnce, once={'graceful': True, 'timeout': 60})
def delft3dgt_pulse(self):
    """
    This task runs the containersync_sceneupdate management command.
    This command updates the states in container and scene model

    A lock is implemented to ensure it's only run one at a time
    """
    call_command('containersync_sceneupdate')
    return


@shared_task(bind=True, base=QueueOnce, once={'graceful': True, 'timeout': 60})
def delft3dgt_latest_svn(self):
    """
    This task runs the get_latest_svn_releases management command.
    This command updates the version_SVN table based on the svn repository

    A lock is implemented to ensure it's only run one at a time
    """
    call_command('get_latest_svn_releases')
    return


@shared_task(bind=True, base=QueueOnce, once={'graceful': True, 'timeout': 60},
             throws=(HTTPError))
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
    # if there are more ignore states we should catch the exception
    # in the inspect call. We filter because Docker Swarm can have disconnected
    # nodes which are seen, but cannot be inspected.
    ignore_states = ['Host Down']
    inspected_containers = []

    client = Client(base_url=settings.DOCKER_URL)
    containers = client.containers(all=True)  # filter here does not work
    filtered_containers = [c for c in containers if c[
        'Status'] not in ignore_states]
    containers_id = [container['Id'] for container in filtered_containers]

    for container_id in containers_id:
        try:
            inspect = client.inspect_container(container_id)
            inspected_containers.append(inspect)
        except Exception, e:
            logging.error("Could not inspect {}: {}".format(
                container_id, str(e)))

    return inspected_containers


@shared_task(bind=True, base=QueueOnce, once={'graceful': True, 'timeout': 60},
             throws=(HTTPError))
def get_argo_wf(self):
    """
    Retrieve all running argo workflows and return them in
    an array of dictionaries. The array looks like this:
    """
    v1 = client.CoreV1Api()
    # --selector=workflows.argoproj.io/workflow=delft3dgt-xxxx
    # pods = v1.list_pod_for_all_namespaces(watch=False, timeout_seconds=59)
    wf = v1.api_client.call_api("/apis/argoproj.io/v1alpha1/workflows",
                                "GET", response_type="V1ConfigMapList", _return_http_data_only=True)
    return wf


@shared_task(bind=True, throws=(HTTPError))
def get_docker_log(self, container_id, stdout=True, stderr=False, tail=5):
    """
    Retrieve the log of a container and return container id and log
    """
    client = Client(base_url=settings.DOCKER_URL)
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
def get_kube_log(self, container_id, tail=5):
    """
    Retrieve the log of a container and return container id and log
    """
    v1 = client.CoreV1Api()
    log = v1.read_namespaced_pod_log(
        container_id, "default", container="wait", tail_lines=tail)
    return log


@shared_task(bind=True, throws=(HTTPError))
def do_docker_create(self, label, parameters, environment, name, image,
                     volumes, memory_limit, folders, command):
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
    client = Client(base_url=settings.DOCKER_URL)
    # We could also pass mem_reservation since docker-py 1.10
    config = client.create_host_config(binds=volumes, mem_limit=memory_limit)
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
    client = Client(base_url=settings.DOCKER_URL)
    client.start(container=container_id)
    return container_id, ""


@shared_task(bind=True, throws=(HTTPError))
def do_argo_create(self, workflow_id, parameters, yaml):
    """
    Start a deployment with a specific id and id
    """
    # with open("delft3dgt-main.yaml") as f:
    # dep = yaml.load(f)

    # Edit Workflow object
    yaml["metadata"] = {"name": workflow_id}
    yaml["spec"]["arguments"]["parameters"] = [{"name": "uuid", "value": "uhsdfaksjhgfe"},
                                               {"name": "parameters", "value": parameters}]

    crd = client.CustomObjectsApi()
    status = crd.create_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "default", "workflows", yaml)

    return status


@shared_task(bind=True, throws=(HTTPError))
def do_docker_stop(self, container_id, timeout=10):
    """
    Stop a container with a specific id and return id
    """
    client = Client(base_url=settings.DOCKER_URL)
    client.stop(container=container_id, timeout=timeout)

    return container_id, ""


@shared_task(bind=True, throws=(HTTPError))
def do_docker_remove(self, container_id, force=False):
    """
    Remove a container with a specific id and return id.
    Try to write the docker log output as well.
    """

    # Commented out removing folders in this task
    # functionality could be moved, therefore not removed

    client = Client(base_url=settings.DOCKER_URL)
    info = client.inspect_container(container=container_id)
    log = client.logs(
        container=str(container_id),
        stream=False,
        stdout=True,
        stderr=True,
        timestamps=True,
    )
    client.remove_container(container=container_id, force=force)

    if isinstance(info, dict):
        try:
            name = info['Name'].split('-')[0].strip('/')  # type
            envs = info['Config']['Env']
            for env in envs:
                key, value = env.split("=")
                if key == 'folder':
                    folder = os.path.split(value)[0]  # root
                    break
            with open(os.path.join(folder,
                                   'docker_{}.log'.format(name)), 'wb') as f:
                f.write(log)
        except:
            logging.error("Failed at writing docker log.")

    return container_id, ""


@shared_task(bind=True, throws=(HTTPError))
def do_argo_remove(self, workflow_id):
    """
    Remove a container with a specific id and return id.
    Try to write the docker log output as well.
    """
    crd = client.CustomObjectsApi()
    crd.delete_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "default", "workflows", workflow_id, {})

    return container_id, ""


@shared_task(bind=True)
def do_docker_sync_filesystem(self, container_id):
    """
    TODO: implement task do_docker_sync_filesystem
    This task should sync the filesystem of a container with a specific id and
    return id
    """
    return container_id, ""
