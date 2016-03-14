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

        with patch('time.sleep') as mocked_sleep:  # mocking sleep in task (stub)
            result = donothing.delay()  # start the task
            self.assertEqual(result.info, {})  # check if returnvalue is as expected


    def testPostprocessTask(self):
        """
        Test that postprocess task returns progress info as float [0.0 - 1.0]
        """

        with patch('time.sleep') as mocked_sleep:  # mocking sleep int task
            result = postprocess.delay()  # start the task

            self.assertTrue('progress' in result.info)  # check if progress is in returnval
            self.assertEqual(type(result.info['progress']), float)  # check if progress is in float format
            self.assertEqual(result.info['progress'], 1.0)  # check that the (final) returnvalue is 1


    def testProcessTask(self):
        """
        Test that process task returns info with
            - progress info as float [0.0 - 1.0]
            - links to images
            - links to a logfile
        """

        with patch('time.sleep') as mocked_sleep:  # mocking sleep in task (stub)
            result = process.delay()  # start the task

            self.assertTrue('progress' in result.info)  # check if progress is in returnval
            self.assertEqual(type(result.info['progress']), float)  # check if progress is in float format
            self.assertEqual(result.info['progress'], 1.0)  # check that the (final) returnvalue is 1

            self.assertTrue('channel_network_images' in result.info)  # check if channel network image is in returnval
            self.assertTrue('location' in result.info['channel_network_images'])  # check if the location of images is defined
            self.assertTrue('images' in result.info['channel_network_images'])  # check if an array of network images is defined
            self.assertTrue(type(result.info['channel_network_images']['images']) == list)  # check if an array of network images is a list
            is_link_to_png = re.search('\.png$', result.info['channel_network_images']['images'][0])  # check if the first element is an image
            self.assertIsNotNone(is_link_to_png)

            self.assertTrue('delta_fringe_images' in result.info)  # check if delta fringe image is in returnval
            self.assertTrue('location' in result.info['delta_fringe_images'])  # check if the location of images is defined
            self.assertTrue('images' in result.info['delta_fringe_images'])  # check if an array of network images is defined
            self.assertTrue(type(result.info['delta_fringe_images']['images']) == list)  # check if an array of network images is a list
            is_link_to_png = re.search('\.png$', result.info['delta_fringe_images']['images'][0])  # check if the first element is an image
            self.assertIsNotNone(is_link_to_png)

            self.assertTrue('logfile' in result.info)  # check if the logfile in returnval


    def testSimulateTask(self):
        """
        Test that simulate task returns progress in float format and when task
        is done, progress == 1.0
        """

        with patch('time.sleep') as mocked_sleep:  # mocking sleep in task (stub)
            result = simulate.delay()  # start the task

            self.assertTrue('progress' in result.info)  # check if progress is in returnval
            self.assertEqual(type(result.info['progress']), float)  # check if progress is in float format
            self.assertEqual(result.info['progress'], 1.0)  # check that the (final) returnvalue is 1


# TESTS

class CeleryTaskModelsTest(TestCase):

    def setUp(self):
        Scene.objects.create(name='Test Scene')  # create test scene

        # create mocked result and store
        self.result = MagicMock()
        self.result.id = '8b15e176-210b-4faf-be80-13602c7b4e89'
        self.result.state = 'SUCCESS'
        self.result.info = {'progress': 1.0}

    # TODO: mock celery.result.AsyncResult to enable successfully the tearDown test
    # def tearDown(self):
    #     json = self.task.serialize()  # serialize this task
    #     self.assertEqual(json, {
    #         'state': 'SUCCESS',
    #         'state_meta': {'progress': 1.0},
    #         'uuid': '8b15e176-210b-4faf-be80-13602c7b4e89'
    #     })  # check if format is as expected for front-end
    #     Scene.objects.get(name='Test Scene').delete()  # delete the test Scene

    def testCeleryTask(self):
        """
        Test that running this model calls donothing.delay once
        """

        with patch('delft3dworker.tasks.donothing.delay', autospec=True) as mocked_donothing_delay:  # mock the task delay
            mocked_donothing_delay.return_value = self.result  # set the task return to mocked result
            # with patch('celery.result.AsyncResult') as mocked_asyncresult:
            #     # mocked_asyncresult.return_value = self.result
            self.task = CeleryTask()  # create celery task
            self.task.run()  # run celery task
            mocked_donothing_delay.assert_called_once_with()  # verify that the donothing task was started once



    def testPostprocessingTask(self):
        """
        Test that running this model calls postprocess.delay once
        """

        with patch('delft3dworker.tasks.postprocess.delay', autospec=True) as mocked_postprocess_delay:  # mock the task delay
            mocked_postprocess_delay.return_value = self.result  # set the task return to mocked result

            self.task = PostprocessingTask()  # create celery task
            self.task.scene = Scene.objects.get(name='Test Scene')  # assign test Scene so task can save
            self.task.run()  # run celery task
            mocked_postprocess_delay.assert_called_once_with()  # verify that the donothing task was started once



    def testProcessingTask(self):
        """
        Test that running this model calls process.delay once
        """

        with patch('delft3dworker.tasks.process.delay', autospec=True) as mocked_process_delay:  # mock the task delay
            mocked_process_delay.return_value = self.result  # set the task return to mocked result

            self.task = ProcessingTask()  # create celery task
            self.task.scene = Scene.objects.get(name='Test Scene')  # assign test Scene so task can save
            self.task.run()  # run celery task
            mocked_process_delay.assert_called_once_with()  # verify that the donothing task was started once


    def testSimulationTask(self):
        """
        Test that running this model calls simulate.delay once
        """

        with patch('delft3dworker.tasks.simulate.delay', autospec=True) as mocked_simulate_delay:  # mock the task delay
            mocked_simulate_delay.return_value = self.result  # set the task return to mocked result

            self.task = SimulationTask()  # create celery task
            self.task.scene = Scene.objects.get(name='Test Scene')  # assign test Scene so task can save
            self.task.run()  # run celery task
            mocked_simulate_delay.assert_called_once_with()  # verify that the donothing task was started once


class SceneTest(TestCase):

    def testSceneSimulate(self):
        """
        Test that simulating a scene creates two tasks
        """

        with patch.object(SimulationTask, 'run', return_value=None) as simulation_run_mock_method:  # mock the simulation task run
            with patch.object(ProcessingTask, 'run', return_value=None) as processing_run_mock_method:  # mock the processing task run
                scene = Scene.objects.create(name='My Test Scene')  # create Scene
                scene.start()  # start Scene simulation
                scene.start()  # start Scene simulation again
                scene.start()  # start Scene simulation again

                simulation_run_mock_method.assert_called_once_with()  # verify simulation task was started only once
                processing_run_mock_method.assert_called_once_with()  # verify processing task was started only once
