from __future__ import absolute_import

from json import dumps

from celery import shared_task
from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from django.core.management import call_command
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from requests.exceptions import HTTPError

logger = get_task_logger(__name__)


@shared_task(bind=True, base=QueueOnce, once={"graceful": True, "timeout": 60})
def delft3dgt_kube_pulse(self):
    """
    This task runs the sync_cluster_state management command.
    This command updates the states of the workflow.

    A lock is implemented to ensure it's only run one at a time
    """
    return call_command("sync_cluster_state")


@shared_task(
    bind=True,
    base=QueueOnce,
    once={"graceful": True, "timeout": 60},
    throws=(HTTPError),
)
def get_argo_workflows(self):
    """
    Retrieve all running argo workflows and return them in
    an array of dictionaries.
    """
    client_api = config.new_client_from_config()
    wf = client_api.call_api(
        "/apis/argoproj.io/v1alpha1/workflows",
        "GET",
        auth_settings=["BearerToken"],
        response_type="V1ConfigMapList",
        _return_http_data_only=True,
    )
    json_wf = dumps(wf.to_dict(), default=str)
    return {"get_argo_workflows": json_wf}


@shared_task(bind=True, throws=(HTTPError))
def get_kube_log(self, wf_id, tail=25):
    """
    Retrieve the log of a container and return container id and log
    """
    client_api = config.new_client_from_config()
    v1 = client.CoreV1Api(client_api)
    log = ""
    pods = v1.list_namespaced_pod(
        "default", label_selector="workflows.argoproj.io/workflow={}".format(wf_id)
    )
    pods_dict = pods.to_dict()
    if "items" in pods_dict:
        for item in pods_dict["items"]:
            name = item["metadata"]["name"]
            try:
                podlog = v1.read_namespaced_pod_log(
                    name, "default", container="main", tail_lines=tail
                )
                log += podlog
            except Exception as e:
                print(e)

    return {"get_kube_log": log}


@shared_task(bind=True, throws=(HTTPError))
def do_argo_create(self, yaml):
    """
    Start a deployment with a specific yaml workflow
    """
    client_api = config.new_client_from_config()
    crd = client.CustomObjectsApi(client_api)
    status = crd.create_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "default", "workflows", yaml
    )

    return {"do_argo_create": status}


@shared_task(bind=True, throws=(HTTPError,))
def do_argo_stop(self, wf_id):
    """
    Stop argo workflow by deleting running pod
    """
    status = {}
    client_api = config.new_client_from_config()
    v1 = client.CoreV1Api(client_api)
    pods = v1.list_namespaced_pod(
        "default", label_selector="workflows.argoproj.io/workflow={}".format(wf_id)
    )
    pods_dict = pods.to_dict()
    for item in pods_dict.get("items", []):
        # Only delete one uncompleted pod
        if (
            item["metadata"]
            .get("labels", {})
            .get("workflows.argoproj.io/completed", "true")
            == "false"
        ):
            name = item["metadata"]["name"]
            try:
                status = v1.delete_namespaced_pod(name, "default").to_dict()
            except ApiException as e:
                logger.error("Exception when deleting a pod: {}\n".format(e))
            break

    return {"do_argo_stop": status}


@shared_task(bind=True, throws=(HTTPError))
def do_argo_remove(self, workflow_id):
    """
    Remove a container with a specific id and return id.
    Try to write the docker log output as well.
    """
    client_api = config.new_client_from_config()
    crd = client.CustomObjectsApi(client_api)
    status = crd.delete_namespaced_custom_object(
        "argoproj.io", "v1alpha1", "default", "workflows", workflow_id
    )

    return {"do_argo_remove": status}
