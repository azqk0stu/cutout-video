import ast
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts.colab_app import create_app

ROOT=Path(__file__).resolve().parents[1]

def descendants(widget):
    yield widget
    for child in getattr(widget,'children',()):yield from descendants(child)

class EasyAppTests(unittest.TestCase):
    def test_notebook_is_self_contained(self):
        nb=json.loads((ROOT/'notebooks/campus_voice_easy.ipynb').read_text())
        source=''.join(next(c['source'] for c in nb['cells'] if 'app' in c.get('metadata',{}).get('tags',[])))
        ast.parse(source)
        self.assertNotIn('from scripts.',source)
        self.assertNotIn('share=True',source)
        self.assertIn('launch_colab_app()',source)

    def test_buttons_edit_save_restore_and_second_video(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'radio.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=5',str(audio)],check=True)
            uploads=[{'radio.wav':audio.read_bytes()}]
            saves=[];renders=[];analyses=[]
            def analyze(path,**options):
                analyses.append(options)
                return dict(version=1,audio_name=path.name,segments=[dict(start=0,end=4,text='元の字幕',speaker='話者1')],candidates=[dict(start=0,end=4,title='候補',summary='抜粋',reasons=['理由'],score=.5)])
            def render(path,edit,bgm):
                renders.append(json.loads(json.dumps(edit)))
                video=Path(directory)/'clip.mp4';video.write_bytes(b'fake video');return video
            app=create_app(lambda:uploads.pop(0),lambda name:saves.append(Path(name).read_bytes()),analyze=analyze,render=render)
            def find(description):return next(w for w in descendants(app) if getattr(w,'description','')==description)
            find('元音声を選ぶ').click()
            find('解析する').click()
            self.assertEqual(len(analyses),1)
            self.assertEqual(analyses[0]['test_seconds'],0)
            find('字幕').value='修正後の字幕'
            find('話者名').value='司会'
            find('作業を保存（次回再開用）').click()
            session=json.loads(saves[-1]);self.assertEqual(session['project']['segments'][0]['text'],'修正後の字幕')
            find('動画を作る').click()
            self.assertEqual(renders[-1]['segments'][0]['speaker'],'司会')
            find('開始（秒）').value=1
            find('動画を作る').click()
            self.assertEqual(len(renders),2)
            self.assertEqual(renders[-1]['start'],1)
            self.assertEqual(len(analyses),1)
            find('解析する').click() # reanalysis must not silently discard edits
            self.assertEqual(len(analyses),1)
            uploads.append({'session.json':saves[0]})
            find('保存した作業を読み込む').click()
            self.assertEqual(find('開始（秒）').value,0)
            self.assertEqual(find('字幕').value,'修正後の字幕')
            self.assertTrue(all(not w.disabled for w in descendants(app) if hasattr(w,'click')))

    def test_controls_are_directly_visible_without_tab_container(self):
        import ipywidgets as widgets
        with patch.object(widgets,'Tab',side_effect=AssertionError('Tab must not be used')):
            app=create_app(lambda:{},lambda name:None)
        descriptions=[getattr(control,'description','') for control in app.children]
        self.assertIn('元音声を選ぶ',descriptions)
        self.assertIn('解析する',descriptions)
        self.assertIn('動画を作る',descriptions)
        self.assertIn('完成MP4を保存',descriptions)

    def test_invalid_action_does_not_leave_buttons_locked(self):
        app=create_app(lambda:{},lambda name:None)
        b=next(w for w in descendants(app) if getattr(w,'description','')=='動画を作る')
        b.click()
        self.assertFalse(b.disabled)

    def test_shared_renderer_produces_mp4(self):
        from scripts.render_clip import render_clip
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'audio.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=2',str(audio)],check=True)
            edit=dict(start=.25,end=1.25,format='vertical',bgm_volume=.1,segments=[dict(start=0,end=2,text='日本語字幕',speaker='司会')])
            output=render_clip(audio,edit)
            result=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(output)],check=True,capture_output=True,text=True)
            self.assertAlmostEqual(float(json.loads(result.stdout)['format']['duration']),1,delta=.15)
            self.assertIn('司会', (output.parent/'captions.ass').read_text())

    def test_external_editor_export_import_and_render_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'radio.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=5',str(audio)],check=True)
            saves=[];renders=[]
            def analyze(path,**options):
                return dict(version=1,audio_name=path.name,segments=[dict(start=0,end=4,text='字幕 </script>',speaker='話者1')],candidates=[dict(start=0,end=4,title='候補')])
            def render(path,edit,bgm):
                renders.append(edit);output=Path(directory)/'clip.mp4';output.write_bytes(b'video');return output
            template='<script type="module">/*editor*/</script>'
            app=create_app(lambda:{'radio.wav':audio.read_bytes()},lambda name:saves.append(Path(name).read_text()),analyze=analyze,render=render,editor_template=template,external_editor=True)
            def find(description):return next(w for w in descendants(app) if getattr(w,'description','')==description)
            find('元音声を選ぶ').click();find('解析する').click()
            self.assertFalse(any(getattr(w,'description','')=='候補を検索' for w in descendants(app)))
            find('編集画面HTMLを保存').click()
            self.assertIn('embeddedProject',saves[-1])
            self.assertNotIn('字幕 </script>',saves[-1])
            find('動画を作る').click();self.assertFalse(renders)
            edit=dict(version=1,audio_name='radio.wav',start=1,end=3,format='square',bgm_volume=.2,segments=[dict(start=0,end=4,text='修正字幕',speaker='司会')])
            find('編集データ').value=json.dumps(edit)
            find('貼り付けた編集データを読み込む').click()
            find('動画を作る').click()
            self.assertEqual(renders[-1]['segments'][0]['text'],'修正字幕')
            self.assertEqual(renders[-1]['format'],'square')
            find('編集データ').value='invalid'
            find('貼り付けた編集データを読み込む').click()
            find('動画を作る').click();self.assertEqual(len(renders),1)
