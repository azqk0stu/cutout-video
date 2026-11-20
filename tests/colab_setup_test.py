import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch
from scripts.colab_setup import setup_colab, REQUIREMENTS

class SetupTests(unittest.TestCase):
    def test_failure_stops_before_false_success(self):
        output=io.StringIO()
        with patch('scripts.colab_setup.subprocess.run',side_effect=subprocess.CalledProcessError(1,'pip')) as run,contextlib.redirect_stdout(output):
            with self.assertRaises(subprocess.CalledProcessError):setup_colab()
        self.assertEqual(run.call_count,1)
        self.assertNotIn('準備完了',output.getvalue())

    def test_restart_instruction_after_success(self):
        output=io.StringIO()
        with patch('scripts.colab_setup.subprocess.run') as run,contextlib.redirect_stdout(output):setup_colab()
        self.assertEqual(run.call_count,3)
        self.assertTrue(all(call.kwargs['check'] for call in run.call_args_list))
        self.assertIn('セッションを再起動',output.getvalue())
        self.assertIn('sentence-transformers==6.3.0',REQUIREMENTS)
        self.assertIn('huggingface-hub>=1.32,<3',REQUIREMENTS)
