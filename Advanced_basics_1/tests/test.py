import unittest
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from log_analyzer import main


class TestAnalyzer(unittest.TestCase):

    def test_main_function_(self):
        main(['--config','tests\test_config.txt'])