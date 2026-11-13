import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import urllib.request
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=subprocess.Popen(['python','-m','http.server','5189','--directory',str(ROOT/'web')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                urllib.request.urlopen('http://127.0.0.1:5189/').close(); return
            except OSError: time.sleep(.1)
        raise RuntimeError('server failed')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate();cls.server.wait()

    def test_edit_save_resume_and_export(self):
        with sync_playwright() as p, tempfile.TemporaryDirectory() as directory:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
            page=browser.new_page(accept_downloads=True)
            errors=[];page.on('pageerror',lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:5189/')
            project={'version':1,'audio_name':'radio.wav','segments':[{'start':0,'end':10,'text':'最初の字幕'},{'start':10,'end':20,'text':'二番目の字幕'}],'candidates':[{'start':0,'end':20,'title':'テスト候補'}]}
            page.locator('#project').set_input_files({'name':'analysis.json','mimeType':'application/json','buffer':json.dumps(project).encode()})
            page.locator('#segments textarea').first.fill('修正した字幕')
            page.locator('#segments input').first.fill('話者A')
            page.locator('#title').fill('保存するタイトル')
            page.locator('#format').select_option('landscape')
            with page.expect_download() as event: page.locator('#saveSession').click()
            saved=Path(directory)/'session.json';event.value.save_as(saved)
            data=json.loads(saved.read_text())
            self.assertEqual(data['project']['segments'][0]['text'],'修正した字幕')
            page.reload()
            page.locator('#project').set_input_files(saved)
            self.assertEqual(page.locator('#segments textarea').first.input_value(),'修正した字幕')
            self.assertEqual(page.locator('#title').input_value(),'保存するタイトル')
            self.assertEqual(page.locator('#format').input_value(),'landscape')
            with page.expect_download() as event: page.locator('#download').click()
            clip=Path(directory)/'clip.json';event.value.save_as(clip)
            self.assertEqual(json.loads(clip.read_text())['segments'][0]['speaker'],'話者A')
            page.locator('#volume').fill('2')
            page.locator('#download').click()
            self.assertIn('BGM音量は',page.locator('#status').inner_text())
            page.on('dialog',lambda dialog: dialog.accept())
            page.locator('#clear').click()
            self.assertFalse(page.locator('#editor').is_visible())
            self.assertEqual(errors,[])
            browser.close()

if __name__=='__main__': unittest.main()
