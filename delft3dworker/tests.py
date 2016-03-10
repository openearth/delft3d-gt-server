"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os
import re

# django test imports
from django.test import TestCase

# runner imports
from django_coverage.coverage_runner import CoverageRunner
from djcelery.contrib.test_runner import CeleryTestSuiteRunner
from teamcity.django import TeamcityDjangoRunner

from delft3dworker.tasks import donothing
from delft3dworker.tasks import postprocess
from delft3dworker.tasks import process
from delft3dworker.tasks import simulate

from mock import patch


# RUNNERS

class Delft3DGTRunner(CeleryTestSuiteRunner, CoverageRunner):
    pass

class TeamcityDelft3DGTRunner(CeleryTestSuiteRunner, CoverageRunner, 
    TeamcityDjangoRunner):
    pass


# TESTS

class TaskTest(TestCase):

    def testDoNothingTask(self):
        """
        Test that donothing task returns empty info
        """

        with patch('time.sleep') as mocked_sleep:
            result = donothing.delay()
            self.assertEqual(result.info, {})


    def testPostprocessTask(self):
        """
        Test that postprocess task returns empty info
        """

        with patch('time.sleep') as mocked_sleep:
            result = postprocess.delay()

            self.assertTrue('progress' in result.info)
            self.assertEqual(type(result.info['progress']), float)
            self.assertEqual(result.info['progress'], 1.0)
            

    def testProcessTask(self):
        """
        Test that process task returns info with links to images and a logfile
        """

        with patch('time.sleep') as mocked_sleep:
            result = process.delay()

            self.assertTrue('progress' in result.info)
            self.assertEqual(type(result.info['progress']), float)
            self.assertEqual(result.info['progress'], 1.0)

            self.assertTrue('channel_network_image' in result.info)
            is_link_to_png = re.search('\.png$', result.info['channel_network_image'])
            self.assertIsNotNone(is_link_to_png)
            
            self.assertTrue('delta_fringe_image' in result.info)
            is_link_to_png = re.search('\.png$', result.info['delta_fringe_image'])
            self.assertIsNotNone(is_link_to_png)

            self.assertTrue('logfile' in result.info)


    def testSimulateTask(self):
        """
        Test that simulate task returns progress in float format and when task
        is done, progress == 1.0
        """

        with patch('time.sleep') as mocked_sleep:
            result = simulate.delay()

            self.assertTrue('progress' in result.info)
            self.assertEqual(type(result.info['progress']), float)
            self.assertEqual(result.info['progress'], 1.0)


