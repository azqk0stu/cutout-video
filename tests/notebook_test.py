"""Check executable notebook cells and exercise rendering without Colab/network."""
import ast
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NB = json.loads((ROOT / 'notebooks/campus_voice.ipynb').read_text())

class NotebookTests(unittest.TestCase):
    def test_syntax(self):
        for cell in NB['cells']:
            if cell['cell_type'] != 'code': continue
            source = ''.join(cell['source'])
            if not source.startswith('%'): ast.parse(source)

    def test_portable_editor_has_no_external_module(self):
        cell = next(c for c in NB['cells'] if 'portable-editor' in c.get('metadata', {}).get('tags', []))
        source = ''.join(cell['source'])
        tree = ast.parse(source)
        html = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith('<!doctype'))
        self.assertNotIn('src="app.js"', html)
        self.assertNotIn("from './model.js'", html)
        self.assertIn('function validateProject', html)
        self.assertIn('切り抜きをつくる', html)

    def test_render_with_and_without_bgm(self):
        source = next(''.join(c['source']) for c in NB['cells'] if c['cell_type']=='code' and ''.join(c['source']).startswith('start,end='))
        source = source.replace('(1080,1920)', '(180,320)')
        class Files:
            def download(self, name):
                assert Path(name).stat().st_size > 0
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=3','audio.wav'],check=True)
                for bgm in [None, 'audio.wav']:
                    scope = dict(Path=Path, subprocess=subprocess, math=math, files=Files(),audio_path=Path('audio.wav'),bgm=bgm,
                        edit={'start':0.5,'end':2.5,'format':'vertical','bgm_volume':0.12,'segments':[{'start':0,'end':3,'text':'日本語\n字幕テスト','speaker':'A'}]})
                    exec(compile(source,'render-cell','exec'),scope)
                    result = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json','clip.mp4'],capture_output=True,text=True,check=True)
                    self.assertAlmostEqual(float(json.loads(result.stdout)['format']['duration']),2,delta=.15)
                    self.assertIn(r'日本語\N字幕テスト',Path('captions.ass').read_text())
            finally: os.chdir(previous)

if __name__=='__main__': unittest.main()
