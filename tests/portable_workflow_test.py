import ast
import json
from pathlib import Path
import tempfile
import unittest
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

class PortableWorkflowTests(unittest.TestCase):
    def test_embedded_project_and_manual_copy_when_clipboard_denied(self):
        nb=json.loads((ROOT/'notebooks/campus_voice.ipynb').read_text())
        cell=next(c for c in nb['cells'] if 'portable-editor' in c.get('metadata',{}).get('tags',[]))
        tree=ast.parse(''.join(cell['source']))
        # Execute generated writer without requiring the Colab package.
        tree.body=[node for node in tree.body if not (isinstance(node,ast.ImportFrom) and node.module=='google.colab')]
        class Files:
            def download(self,name):pass
        scope={'files':Files()}
        exec(compile(tree,'portable-cell','exec'),scope)
        project=dict(version=1,audio_name='radio.mp3',segments=[dict(start=0,end=40,text='要約 </script><script>window.injected=true</script>')],candidates=[dict(start=0,end=40,title='候補')])
        with tempfile.TemporaryDirectory() as directory:
            # Replace Path only for writer output, keeping the caller's cwd intact.
            scope['Path']=lambda name:Path(directory)/name
            scope['save_editor'](project)
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
                page=browser.new_page()
                page.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('denied'))}})")
                page.set_content((Path(directory)/'campus-voice-editor.html').read_text())
                page.locator('#editor').wait_for(state='visible')
                self.assertTrue(page.locator('#editor').is_visible())
                self.assertEqual(page.locator('#segments textarea').input_value(),project['segments'][0]['text'])
                self.assertIsNone(page.evaluate('window.injected'))
                page.locator('#copyEdit').click()
                page.locator('#copyFallback').wait_for(state='visible')
                edit=json.loads(page.locator('#copyText').input_value())
                self.assertEqual(edit['audio_name'],'radio.mp3')
                self.assertEqual(edit['end'],40)
                page.on('dialog',lambda d:d.accept())
                page.locator('#clear').click()
                self.assertEqual(page.locator('#copyText').input_value(),'')
                browser.close()
