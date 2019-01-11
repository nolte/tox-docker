import os
import unittest

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


class ToxDockerIntegrationNginxTest(unittest.TestCase):
    # TODO: These tests depend too heavily on what's in tox.ini,
    # but they're better than nothing
    def test_it_sets_specific_env_vars(self):
        self.assertEqual("env-var-value", os.environ["ENV_VAR"])

    def test_it_sets_automatic_env_vars(self):
        # the nginx image we use exposes port 80
        self.assertIn("NGINX_80_TCP", os.environ)

        # the nginx running host ip like 172.17.0.1
        self.assertIn("NGINX_HOST", os.environ)

    def test_it_exposes_the_port(self):
        # the nginx image we use exposes port 80
        url = "http://{host}:{port}/".format(host=os.environ["NGINX_HOST"], port=os.environ["NGINX_80_TCP"])
        response = urlopen(url)
        self.assertEqual(200, response.getcode())

        # ceck the mapped content, from the 'test-index.html'
        self.assertIn("custom text from monted html", str(response.read()))
