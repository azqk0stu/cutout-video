import importlib.util
import json
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('edit_input',Path(__file__).resolve().parents[1]/'scripts/edit_input.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class EditInputTests(unittest.TestCase):
    def test_paste_and_file_share_validation(self):
        edit=dict(version=1,audio_name='radio.mp3',start=0,end=40,format='vertical',bgm_volume=.12,segments=[dict(start=0,end=40,text='日本語字幕')])
        self.assertEqual(module.parse_edit(json.dumps(edit),'radio.mp3'),edit)
        for invalid in ['not json', '[]', json.dumps(dict(version=1)),json.dumps(dict(kind='campus-voice-session'))]:
            with self.assertRaises(ValueError):module.parse_edit(invalid,'radio.mp3')
        with self.assertRaises(ValueError):module.parse_edit(json.dumps(edit),'other.mp3')
        for fields in [dict(start=True),dict(end=float('nan')),dict(segments=[]),dict(bgm_volume=2),dict(format='invalid')]:
            with self.assertRaises(ValueError):module.parse_edit(json.dumps(dict(edit,**fields)),'radio.mp3')
