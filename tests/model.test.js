import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateProject,exportEdit} from '../web/model.js';
const p={version:1,audio_name:'radio.mp3',segments:[{start:0,end:10,text:'こんにちは'},{start:10,end:20,text:'次の話題'}],candidates:[{start:0,end:20}]};
test('解析結果を受け取り、選択範囲に重なる字幕を元時刻のまま出力',()=>{validateProject(p);const e=exportEdit(p,11,18,p.segments,.12,'vertical');assert.equal(e.audio_name,'radio.mp3');assert.deepEqual(e.segments,[p.segments[1]]);assert.equal(e.start,11)});
test('不正な字幕時刻と逆転した編集範囲を拒否',()=>{assert.throws(()=>validateProject({...p,segments:[{start:10,end:0,text:'x'}]}));assert.throws(()=>exportEdit(p,20,10,p.segments,.12,'vertical'));assert.throws(()=>exportEdit(p,30,40,p.segments,.12,'vertical'))});
test('空の解析結果・不正なBGM音量・未対応サイズを拒否',()=>{
 assert.throws(()=>validateProject({...p,segments:[]}));
 assert.throws(()=>exportEdit(p,0,10,p.segments,2,'vertical'));
 assert.throws(()=>exportEdit(p,0,10,p.segments,.12,'unknown'));
});
