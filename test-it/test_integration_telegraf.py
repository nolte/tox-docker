import os
import unittest


class ToxDockerIntegrationTelegrafTest(unittest.TestCase):
    # TODO: These tests depend too heavily on what's in tox.ini,
    # but they're better than nothing
    def test_it_sets_automatic_env_vars(self):
        # the telegraf image we use exposes UDP port 8092
        self.assertIn("TELEGRAF_8092_UDP", os.environ)
