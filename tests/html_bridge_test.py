import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from scripts.html_bridge import HtmlBridge

class BridgeTests(unittest.TestCase):
    def wait(self,bridge,job):
        for _ in range(100):
            result=bridge.call('status',dict(job=job))
            if not result['ok'] or result['done']:return result
            time.sleep(.01)
        self.fail('job did not finish')

    def test_jobs_validation_and_chunked_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'audio.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=3',str(path)],check=True)
            def analyze(audio,**kwargs):return dict(audio_name=audio.name,segments=[],candidates=[])
            def render(audio,edit,bgm):
                result=Path(directory)/'clip.mp4';result.write_bytes(b'01234567');return result
            bridge=HtmlBridge(path,analyze=analyze,render=render)
            try:
                self.assertFalse(bridge.call('analyze',dict(speakers=0))['ok'])
                job=bridge.call('analyze')['job'];done=self.wait(bridge,job)
                self.assertEqual(done['result']['project']['audio_name'],'audio.wav')
                self.assertFalse(bridge.call('status',dict(job='wrong'))['ok'])
                edit=dict(version=1,audio_name='audio.wav',start=0,end=2,format='vertical',bgm_volume=.1,segments=[dict(start=0,end=2,text='字幕')])
                job=bridge.call('render',dict(edit=edit))['job'];self.assertTrue(self.wait(bridge,job)['ok'])
                chunk=bridge.call('chunk',dict(job=job,offset=0))
                self.assertTrue(chunk['done']);self.assertEqual(chunk['next'],8)
                self.assertFalse(bridge.call('chunk',dict(job=job,offset=-1))['ok'])
                edit['end']=10
                job=bridge.call('render',dict(edit=edit))['job']
                self.assertFalse(self.wait(bridge,job)['ok'])
            finally:bridge.pool.shutdown()
