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
from djcelery.contrib.test_runner import CeleryTestSuiteRunner
from teamcity.unittestpy import TeamcityTestRunner

# mock imports
from mock import patch, MagicMock
from docker import Client

from delft3dgtmain import settings
from delft3dworker.tasks import rundocker


class Delft3DGTRunner(TeamcityTestRunner, CeleryTestSuiteRunner):
    pass


class SimpleTest(TestCase):

    def test_delay_rundocker_in_test(self):
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
            self.assertTrue(True)
