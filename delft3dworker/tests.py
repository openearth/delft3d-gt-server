"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os
import re
import uuid

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
from delft3dworker.models import Scene


# RUNNERS

class Delft3DGTRunner(CeleryTestSuiteRunner, CoverageRunner):
    pass


class TeamcityDelft3DGTRunner(CeleryTestSuiteRunner, CoverageRunner,
                              TeamcityDjangoRunner):
    pass


# TESTS

# Skeleton to run Celery & Docker tests.

# class DockerTest(TestCase):

#     def setUp(self):
#         view_parameters = {
#             'name': 'Test Scene',
#             'suid': str(uuid.uuid4()),
#             'info': '{"dt": 20 }'
#         }
#         self.scene = Scene.objects.create(
#             **view_parameters)  # create test scene

#     def tearDown(self):
#         Scene.objects.get(name='Test Scene').delete()  # delete the test Scene

#     def testDocker(self):
#         self.scene.save()
#         # self.scene.start()  # don't actually start containers


# class CeleryTaskModelsTest(TestCase):

#     def setUp(self):
#         view_parameters = {
#             'name': 'Test Scene',
#             'suid': str(uuid.uuid4()),
#             'info': '{"dt": 20 }'
#         }
#         Scene.objects.create(**view_parameters)  # create test scene

#         # create mocked result and store
#         self.result = MagicMock()
#         self.result.id = '8b15e176-210b-4faf-be80-13602c7b4e89'
#         self.result.state = 'SUCCESS'
#         self.result.info = {'progress': 1.0}

#     def tearDown(self):
#         Scene.objects.get(name='Test Scene').delete()  # delete the test Scene

