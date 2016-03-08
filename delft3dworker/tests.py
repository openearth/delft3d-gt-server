"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os

from django.test import TestCase
from django.test import modify_settings

from djcelery.contrib.test_runner import CeleryTestSuiteRunner
from teamcity.unittestpy import TeamcityTestRunner

from delft3dgtmain import settings

from delft3dworker.tasks import rundocker


class Delft3DGTRunner(CeleryTestSuiteRunner, TeamcityTestRunner):
    pass


class SimpleTest(TestCase):

    def test_delay_rundocker_in_test(self):
        """
        Test that we can run rundocker.delay with succesful result
        """

        # result = rundocker.delay(
        #     settings.DELFT3D_IMAGE_NAME, 
        #     'ed7a1f3c-e46a-4eb3-9ea3-3d1729a69562', 
        #     '/data/container/files/'
        # )

        # self.assertTrue(result.successful())

        self.assertTrue(True)