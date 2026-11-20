import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('speakers',Path(__file__).resolve().parents[1]/'scripts/speakers.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SpeakerTests(unittest.TestCase):
    def test_stable_labels_and_original_preserved(self):
        segments=[dict(start=i,end=i+1,text='会話',speaker='') for i in range(4)]
        result=module.labels_to_segments(segments,[7,3,7,3])
        self.assertEqual([s['speaker'] for s in result],['話者1','話者2','話者1','話者2'])
        self.assertEqual(segments[0]['speaker'],'')
        with self.assertRaises(ValueError):module.labels_to_segments(segments,[1])
