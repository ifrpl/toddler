__author__ = 'michal'

from toddler_webapp.webapp import auth
import unittest
import uuid
import os

class TestAuth(unittest.TestCase):

    def __init__(self, *args, **kwargs):

        self.auth_config = {}
        self.test_user = "admin:test"
        self.test_password = "supposed to b e super secret"

        super(TestAuth, self).__init__(*args, **kwargs)

    def setUp(self):

        self.auth_config = {
            "passwordFile": "./testpasswords.s",
            "secret": str(uuid.uuid4())
        }

        auth.add_user(self.auth_config, self.test_user, self.test_password)

    def testPassword(self):
        auth.auth_user(self.auth_config, self.test_user, self.test_password)

    def tearDown(self):
        # os.remove(self.auth_config['passwordFile'])
        pass
