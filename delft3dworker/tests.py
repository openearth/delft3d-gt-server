"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os

# django test imports
from django.test import TestCase
from django.test import modify_settings

# runner imports
from django_coverage.coverage_runner import CoverageRunner
from djcelery.contrib.test_runner import CeleryTestSuiteRunner
from teamcity.django import TeamcityDjangoRunner

# mock imports
from mock import patch, MagicMock
from docker import Client

from delft3dgtmain import settings
from delft3dworker.tasks import rundocker


# RUNNERS

class Delft3DGTRunner(CeleryTestSuiteRunner, CoverageRunner):
    pass

class TeamcityDelft3DGTRunner(CeleryTestSuiteRunner, CoverageRunner, TeamcityDjangoRunner):
    pass


# TESTS

class SimpleTest(TestCase):
    def testDelayRundockerInTest(self):
        """
        Test that we can run rundocker.delay with succesful result
        """

        container = MagicMock()
        container.get.return_value = 'id'

        with patch('docker.Client') as MockClient:
            MockClient.create_client.return_value = container

            # TODO: Make this delay task work with the mocked docker Client

            # result = rundocker.delay(
            #     settings.DELFT3D_IMAGE_NAME, 
            #     'ed7a1f3c-e46a-4eb3-9ea3-3d1729a69562', 
            #     '/data/container/files/'
            # )

            # MockClient.create_client.assert_called_once_with()
            self.assert_(True)
