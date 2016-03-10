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

# mock
from mock import MagicMock
from mock import patch

# the delft3dworker elements to be tested
from delft3dworker.tasks import donothing
from delft3dworker.tasks import postprocess
from delft3dworker.tasks import process
from delft3dworker.tasks import simulate

from delft3dworker.models import CeleryTask
from delft3dworker.models import PostprocessingTask
from delft3dworker.models import ProcessingTask
from delft3dworker.models import Scene
from delft3dworker.models import SimulationTask

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


# TESTS

class CeleryTaskModelsTest(TestCase):

    def setUp(self):
        Scene.objects.create(name='Test Scene')

        self.result = MagicMock()
        self.result.id = '8b15e176-210b-4faf-be80-13602c7b4e89'
        self.result.state = 'PENDING'
        self.result.info = {}

    def tearDown(self):
        json = self.task.serialize()            
        self.assertEqual(json, {
            'state': 'SUCCESS',
            'state_meta': {'progress': 1.0},
            'uuid': '8b15e176-210b-4faf-be80-13602c7b4e89'
        })
        Scene.objects.get(name='Test Scene').delete()

    def testCeleryTask(self):
        """
        Test that running this model calls donothing.delay once
        """

        with patch('delft3dworker.tasks.donothing.delay', autospec=True) as mocked_donothing_delay:
            mocked_donothing_delay.return_value = self.result

            self.task = CeleryTask()
            self.task.run()
            mocked_donothing_delay.assert_called_once_with()
            
            

    def testPostprocessingTask(self):
        """
        Test that running this model calls postprocess.delay once
        """

        with patch('delft3dworker.tasks.postprocess.delay', autospec=True) as mocked_postprocess_delay:
            mocked_postprocess_delay.return_value = self.result

            self.task = PostprocessingTask()
            self.task.scene = Scene.objects.get(name='Test Scene')
            self.task.run()
            mocked_postprocess_delay.assert_called_once_with()
            
            

    def testProcessingTask(self):
        """
        Test that running this model calls process.delay once
        """

        with patch('delft3dworker.tasks.process.delay', autospec=True) as mocked_process_delay:
            mocked_process_delay.return_value = self.result

            self.task = ProcessingTask()
            self.task.scene = Scene.objects.get(name='Test Scene')
            self.task.run()
            mocked_process_delay.assert_called_once_with()
                        

    def testSimulationTask(self):
        """
        Test that running this model calls simulate.delay once
        """

        with patch('delft3dworker.tasks.simulate.delay', autospec=True) as mocked_simulate_delay:
            mocked_simulate_delay.return_value = self.result

            self.task = SimulationTask()
            self.task.scene = Scene.objects.get(name='Test Scene')
            self.task.run()
            mocked_simulate_delay.assert_called_once_with()


class SceneTest(TestCase):

    def testSceneSimulate(self):
        """
        Test that simulating a scene creates two tasks
        """
        
        with patch.object(SimulationTask, 'run', return_value=None) as simulation_run_mock_method:
            with patch.object(ProcessingTask, 'run', return_value=None) as processing_run_mock_method:
                scene = Scene.objects.create(name='My Test Scene')
                scene.simulate()

                simulation_run_mock_method.assert_called_once_with()
                processing_run_mock_method.assert_called_once_with()  
