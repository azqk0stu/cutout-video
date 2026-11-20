import ast
import json
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

class LiveHtmlTests(unittest.TestCase):
    def test_native_callbacks_analysis_and_video_download(self):
        notebook=json.loads((ROOT/'notebooks/campus_voice_live.ipynb').read_text())
        tree=ast.parse(''.join(notebook['cells'][-1]['source']))
        page_text=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('<!doctype'))
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
            page=browser.new_page(accept_downloads=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.evaluate('''() => {
                window.calls=[];window.active='';
                window.google={colab:{kernel:{invokeFunction:async(name,args)=>{
                    const [action,data]=args;window.calls.push({action,data});
                    let response={ok:true};
                    if(action==='hello')Object.assign(response,{audio_name:'radio.wav',bgm:false});
                    if(['analyze','render','preview'].includes(action)){window.active=action;response.job='job';}
                    if(action==='status'){
                        response.done=true;response.messages=['処理完了'];
                        response.result=window.active==='analyze'?{project:{version:1,audio_name:'radio.wav',segments:[{start:0,end:40,text:'試験字幕',speaker:'話者1'}],candidates:[{start:0,end:40,title:'試験候補',summary:'字幕要約',reasons:['時間帯で選出']}],analysis:{test_seconds:0}}}:{mime:'video/mp4',size:3,name:'clip.mp4'};
                    }
                    if(action==='chunk')Object.assign(response,{data:btoa('mp4'),next:3,done:true});
                    return {data:{'application/json':response}};
                }}}};
            }''')
            page.set_content(page_text)
            page.locator('#liveAnalyze').click()
            page.locator('#editor').wait_for(state='visible')
            self.assertIn('字幕要約',page.locator('.candidate-summary').inner_text())
            page.locator('#segments textarea').fill('修正後の字幕')
            page.locator('#liveRender').click()
            page.locator('#liveResult a').wait_for()
            with page.expect_download() as event:page.locator('#liveResult a').click()
            self.assertEqual(event.value.suggested_filename,'clip.mp4')
            calls=page.evaluate('window.calls')
            render=next(c for c in calls if c['action']=='render')
            self.assertEqual(render['data']['edit']['segments'][0]['text'],'修正後の字幕')
            self.assertEqual(errors,[])
            page.on('dialog',lambda dialog:dialog.accept())
            page.evaluate('delete window.google')
            page.locator('#liveAnalyze').click()
            page.wait_for_function("document.getElementById('liveStatus').textContent.includes('Colabへの接続がありません')")
            browser.close()

    def test_notebook_has_no_public_server(self):
        nb=json.loads((ROOT/'notebooks/campus_voice_live.ipynb').read_text())
        for cell in nb['cells']:
            if cell['cell_type']=='code':ast.parse(''.join(cell['source']))
        source=''.join(nb['cells'][-1]['source'])
        self.assertNotIn('from scripts.',source)
        self.assertNotIn('share=True',source)
        self.assertNotIn('ngrok',source)
