from __future__ import absolute_import

import os
import sys
from time import time

from django.test import TestCase
from fakeredis import FakeStrictRedis
from mock import MagicMock, Mock, patch

from delft3dcontainermanager.tasks import (
    delft3dgt_kube_pulse,
    do_argo_create,
    do_argo_remove,
    do_argo_stop,
    get_argo_workflows,
    get_kube_log,
)


class AsyncTaskTest(TestCase):
    mock_options = {}

    def setUp(self):
        self.get_redis = patch("celery_once.backends.redis.get_redis")
        self.mocked_redis = self.get_redis.start()

        self.redis = FakeStrictRedis()
        self.mocked_redis.return_value = self.redis

    @patch("delft3dcontainermanager.tasks.call_command")
    def test_delft3dgt_kube_pulse(self, mockCall):
        """
        Assert that de delft3dgt_kube_pulse task
        calls the sync_cluster_state() only once.
        """
        delft3dgt_kube_pulse.delay()

        # Set redis key with TTL 100 seconds from now
        # so subsequent tasks won't run
        self.redis.set(
            "qo_delft3dcontainermanager.tasks.delft3dgt_kube_pulse", int(time()) + 100
        )

        delft3dgt_kube_pulse.delay()
        delft3dgt_kube_pulse.delay()

        mockCall.assert_called_with("sync_cluster_state")
        self.assertEqual(mockCall.call_count, 1)

    def tearDown(self):
        self.redis.flushall()
        self.get_redis.stop()


class TaskTest(TestCase):
    mock_options = {}

    def setUp(self):
        self.get_redis = patch("celery_once.backends.redis.get_redis")
        self.mocked_redis = self.get_redis.start()

        self.redis = FakeStrictRedis()
        self.mocked_redis.return_value = self.redis

    @patch("delft3dcontainermanager.tasks.client", **mock_options)
    @patch("delft3dcontainermanager.tasks.config", **mock_options)
    def test_get_argo_workflows(self, mockConfig, mockClient):
        """
        Assert that the get_argo_workflows task
        calls the kubernetes v1.api_client.call_api function.
        """

        # Mock return of all workflows
        mockConfig.new_client_from_config.return_value = Mock()
        get_argo_workflows.delay()
        mockConfig.new_client_from_config().call_api.assert_called_with(
            "/apis/argoproj.io/v1alpha1/workflows",
            "GET",
            auth_settings=["BearerToken"],
            response_type="V1ConfigMapList",
            _return_http_data_only=True,
        )

    @patch("delft3dcontainermanager.tasks.client", **mock_options)
    @patch("delft3dcontainermanager.tasks.config", **mock_options)
    def test_get_kube_log(self, mockConfig, mockClient):
        """
        Assert that the argo_log task
        calls the kubernetes read_namespaced_pod_log function.
        """

        wf_id = "id"
        pod_id = "foo"

        # Mock return of all pods
        pods = Mock()
        pods.to_dict.return_value = {"items": [{"metadata": {"name": pod_id}}]}
        mockClient.CoreV1Api().list_namespaced_pod.return_value = pods

        # Check that all pods are requested
        # and the logs for each individual pod
        get_kube_log.delay(wf_id)
        mockClient.CoreV1Api().list_namespaced_pod.assert_called_with(
            "default", label_selector="workflows.argoproj.io/workflow={}".format(wf_id)
        )
        mockClient.CoreV1Api().read_namespaced_pod_log.assert_called_with(
            pod_id, "default", container="main", tail_lines=25
        )

    @patch("delft3dcontainermanager.tasks.client", **mock_options)
    @patch("delft3dcontainermanager.tasks.config", **mock_options)
    def test_do_argo_create(self, mockConfig, mockClient):
        """
        Assert that the do_argo_create task
        calls the kubernetes create_namespaced_custom_object function.
        """
        yaml = "---"

        do_argo_create.delay(yaml)
        mockClient.CustomObjectsApi().create_namespaced_custom_object.assert_called_with(
            "argoproj.io", "v1alpha1", "default", "workflows", yaml
        )

    @patch("delft3dcontainermanager.tasks.client", **mock_options)
    @patch("delft3dcontainermanager.tasks.config", **mock_options)
    def test_do_argo_stop(self, mockConfig, mockClient):
        """
        Assert that the argo_remove task
        calls the kubernetes delete_namespaced_custom_object function
        """

        wf_id = "id"
        pod_id = "foo"

        # Mock return of all pods
        pods = Mock()
        pods.to_dict.return_value = {
            "items": [
                {
                    "metadata": {
                        "name": pod_id,
                        "labels": {"workflows.argoproj.io/completed": "false"},
                    }
                }
            ]
        }
        mockClient.CoreV1Api().list_namespaced_pod.return_value = pods

        do_argo_stop.delay(wf_id)
        mockClient.CoreV1Api().list_namespaced_pod.assert_called_with(
            "default", label_selector="workflows.argoproj.io/workflow={}".format(wf_id)
        )
        mockClient.CoreV1Api().delete_namespaced_pod.assert_called_with(
            pod_id, "default"
        )

    @patch("delft3dcontainermanager.tasks.client", **mock_options)
    @patch("delft3dcontainermanager.tasks.config", **mock_options)
    def test_do_argo_remove(self, mockConfig, mockClient):
        """
        Assert that the argo_remove task
        calls the kubernetes delete_namespaced_custom_object function
        """
        wf_id = "id"
        do_argo_remove.delay(wf_id)
        mockClient.CustomObjectsApi().delete_namespaced_custom_object.assert_called_with(
            "argoproj.io", "v1alpha1", "default", "workflows", wf_id, {}
        )
