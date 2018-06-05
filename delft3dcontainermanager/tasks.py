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
from json import dumps
from kubernetes import client, config
from requests.exceptions import HTTPError

logger = get_task_logger(__name__)

@shared_task(bind=True, base=QueueOnce, once={'graceful': True, 'timeout': 60})
def delft3dgt_kube_pulse(self):
    """
    This task runs the sync_cluster_state management command.
    This command updates the states of the workflow.

    A lock is implemented to ensure it's only run one at a time
    """
    call_command('sync_cluster_state')
    return


@shared_task(bind=True, base=QueueOnce, once={'graceful': True, 'timeout': 60},
             throws=(HTTPError))
def get_argo_workflows(self):
    """
    Retrieve all running argo workflows and return them in
    an array of dictionaries. The array looks like this:
    """
    v1 = client.CoreV1Api()
    wf = v1.api_client.call_api("/apis/argoproj.io/v1alpha1/workflows",
                                "GET", response_type="V1ConfigMapList", _return_http_data_only=True)
    json_wf = dumps(wf.to_dict(), default=str)
    return {"get_argo_workflows": json_wf}


@shared_task(bind=True, throws=(HTTPError))
def get_kube_log(self, wf_id, tail=25):
    """
    Retrieve the log of a container and return container id and log
    """
    v1 = client.CoreV1Api()
    log = ""
    pods = v1.list_namespaced_pod("default", label_selector="workflows.argoproj.io/workflow={}".format(wf_id))
    pods_dict = pods.to_dict()
    if "items" in pods_dict:
        for item in pods_dict["items"]:
            name = item["metadata"]["name"]
            try:
                podlog = v1.read_namespaced_pod_log(name, "default", container="main", tail_lines=tail)
                log += podlog
            except Exception as e:
                print(e)

    return {"get_kube_log": log}


@shared_task(bind=True, throws=(HTTPError))
def do_argo_create(self, yaml):
    """
    Start a deployment with a specific id and id
    """
    crd = client.CustomObjectsApi()
    status = crd.create_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "default", "workflows", yaml)

    return {"do_argo_create": status}


@shared_task(bind=True, throws=(HTTPError))
def do_argo_remove(self, workflow_id):
    """
    Remove a container with a specific id and return id.
    Try to write the docker log output as well.
    """
    crd = client.CustomObjectsApi()
    status = crd.delete_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "default", "workflows", workflow_id, {})

    return {"do_argo_remove": status}
