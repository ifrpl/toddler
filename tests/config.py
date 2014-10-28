__author__ = 'michal'

import os
import unittest
import json
import toddler.config as cfg


class ConfigTest(unittest.TestCase):

    def testIncludes(self):

        config_dir_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "config")

        cfg.parse_config_dir(config_dir_path)

        with open(os.path.join(config_dir_path, 'toddler.conf')) as cfg_file:
            test_cfg = json.load(cfg_file)
            # -1 because of includes themselves
            self.assertEqual(
                len(test_cfg['includes'])+len(test_cfg)-1,
                len(cfg.configs)
            )
