from django.test import TestCase
from delft3dgtmain.wsgi import check_password
from django.contrib.auth.models import User


class WsgiTestCase(TestCase):

    def setUp(self):
        User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')

    def test_wsgi_auth(self):
        """Test if our check_password function works correctly"""

        self.assertEqual(check_password({}, 'john', 'johnpassword'), True)
        self.assertEqual(check_password({}, 'john', 'wrongpassword'), False)
        self.assertEqual(check_password({}, 'notexist', 'johnpassword'), None)