import unittest
import os
import sys
import re
import shutil
current_path = os.path.realpath(__file__)
sys.path.append(os.path.join(os.path.dirname(current_path), os.pardir))
os.chdir(os.path.dirname(current_path))
from log_analyzer import main


class TestAnalyzer(unittest.TestCase):

    
    def test_when_success_main(self):
        """

        Проверка выходных результатов при успешном завершении скрипта, настроенном
        на входном конфиге test_config.txt: создание выходной 
        директории/файла отчета и его содержания; наличие выходного лога. 
        
        """
        main(['--config','./tests/test_success_config.txt'])
        current_path = os.path.realpath(__file__)
        os.chdir(os.path.dirname(current_path))
        self.assertTrue(os.path.exists(r'./test_success_logs/test_success_log.log'))
        self.assertTrue(os.path.exists(r'./test_success_reports/report-2019.11.11.html'))
        with open(r'./test_success_reports/report-2019.11.11.html', 'r') as f:
            report_text = f.read()
        self.assertIsNotNone(re.findall("var table = \[(\{('\w+': [^\{\}]*){8}\}(, )*){42}\]", report_text))
        if os.path.exists(r'./test_success_logs'):
            shutil.rmtree(r'./test_success_logs')
        if os.path.exists(r'./test_success_reports'):
            shutil.rmtree(r'./test_success_reports')


    @unittest.skip('reason')
    def test_when_failure_main(self):
        """

        Проверка выходных результатов при неудачном завершении скрипта, вызванное
        низким значением FAIL_PERC в файле конфига test_failure_config.txt. Проверяется
        создание выходного лога, а также его содержания.
        
        """
        main(['--config','./tests/test_failure_config.txt'])
        current_path = os.path.realpath(__file__)
        os.chdir(os.path.dirname(current_path))
        self.assertTrue(os.path.exists(r'./test_failure_logs/test_failure_log.log'))
        with open(r'./test_failure_logs/test_failure_log.log') as f:
            log_text = f.readlines()
        self.assertTrue('что выше допустимого' in log_text[-2])
        if os.path.exists(r'./test_failure_logs'):
            shutil.rmtree(r'./test_failure_logs')
        if os.path.exists(r'./test_failure_reports'):
            shutil.rmtree(r'./test_failure_reports')


if __name__ == '__main__':
    unittest.main()

