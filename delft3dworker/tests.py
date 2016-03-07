"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os

from djcelery.contrib.test_runner import CeleryTestSuiteRunner
from teamcity.unittestpy import TeamcityTestRunner

from django.test import TestCase
from django.test import modify_settings

from delft3dgtmain.settings import BASE_DIR


class Delft3DGTRunner(CeleryTestSuiteRunner, TeamcityTestRunner):
    pass


class SimpleTest(TestCase):

    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)