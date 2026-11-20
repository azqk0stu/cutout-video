import {validateProject,exportEdit} from './model.js';
const $=id=>document.getElementById(id);
let project,url,stopAt,dirty=false;
function status(message){$('status').textContent=message}
function changed(){dirty=true;$('saveState').textContent='未保存の変更があります'}
function range(start,end){$('start').value=start;$('end').value=end;renderSegments();updateDuration()}
function renderSegments(){
  const root=$('segments');root.replaceChildren();
  for(const s of project.segments){
    if(s.end<=+$('start').value||s.start>=+$('end').value)continue;
    const box=document.createElement('div');box.className='segment';
    const time=document.createElement('small');time.textContent=`${s.start.toFixed(1)}–${s.end.toFixed(1)}秒`;
    const speaker=document.createElement('input');speaker.placeholder='話者名（任意）';speaker.setAttribute('aria-label','話者名');speaker.value=s.speaker||'';
    speaker.oninput=()=>{s.speaker=speaker.value;changed()};
    const text=document.createElement('textarea');text.setAttribute('aria-label',`${s.start.toFixed(1)}秒の字幕`);text.value=s.text;
    text.oninput=()=>{s.text=text.value;changed()};box.append(time,speaker,text);root.append(box);
  }
}
function loadProject(p,selection){
  project=validateProject(p);$('editor').hidden=false;
  renderCandidates();renderSpeakers();
  const c=selection||project.candidates[0]||{start:project.segments[0].start,end:Math.min(project.segments.at(-1).end,project.segments[0].start+60)};
  range(c.start,c.end);$('title').value=c.title||'';$('volume').value=c.bgm_volume??0.12;$('format').value=c.format||'vertical';
  dirty=false;$('saveState').textContent='読み込み済み';
  $('analysisInfo').textContent=project.analysis?.test_seconds ? `冒頭${project.analysis.test_seconds}秒の解析です。全編ではありません。` : (project.analysis?.test_seconds===0 ? '全編を解析したデータです。' : '解析範囲は不明です。');
}
$('project').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  if(dirty&&!confirm('未保存の編集があります。新しいデータを読み込みますか？'))return;
  try{
    const data=JSON.parse(await file.text());
    if(data.kind==='campus-voice-session'){
      validateProject(data.project);
      exportEdit(data.project,data.selection.start,data.selection.end,data.project.segments,data.selection.bgm_volume,data.selection.format);
      loadProject(data.project,data.selection);
    }else loadProject(data);
    status('読み込みました。試聴するには元音声を選択してください。');
  }catch(e){status(e.message)}
};
$('audioFile').onchange=e=>{
  const file=e.target.files[0];if(!file)return;
  if(project&&file.name!==project.audio_name){status(`元音声は「${project.audio_name}」を選んでください。`);e.target.value='';return}
  $('audio').pause();stopAt=null;if(url)URL.revokeObjectURL(url);
  url=URL.createObjectURL(file);$('audio').src=url;status('音声を読み込みました。候補の前後を確認してください。');
};
for(const id of ['start','end'])$(id).onchange=()=>{renderSegments();updateDuration();changed()};
for(const id of ['title','volume','format'])$(id).oninput=changed;
async function listen(context=false){
  try{
    const start=+$('start').value,end=+$('end').value;
    exportEdit(project,start,end,project.segments,+$('volume').value,$('format').value);
    if(!$('audio').src||!Number.isFinite($('audio').duration))throw Error('元音声を読み込み、準備ができるまでお待ちください');
    if(end>$('audio').duration+0.1)throw Error('選択範囲が音声の長さを超えています');
    stopAt=Math.min($('audio').duration,end+(context?10:0));$('audio').currentTime=Math.max(0,start-(context?10:0));
    await $('audio').play();
  }catch(e){status(e.message)}
}
$('listen').onclick=()=>listen();$('context').onclick=()=>listen(true);
$('audio').ontimeupdate=()=>{if(stopAt&&$('audio').currentTime>=stopAt){$('audio').pause();stopAt=null}};
function selection(){const edit=exportEdit(project,+$('start').value,+$('end').value,project.segments,+$('volume').value,$('format').value);edit.title=$('title').value;return edit}
function download(data,name){const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
$('download').onclick=()=>{try{download(selection(),'clip-edit.json');status('Colab用の編集JSONを保存しました。再編集用には「作業全体を保存」も使ってください。')}catch(e){status(e.message)}};
$('saveSession').onclick=()=>{try{download({kind:'campus-voice-session',version:1,project,selection:selection()},'campus-voice-session.json');dirty=false;$('saveState').textContent='作業を保存しました';status('作業全体を保存しました。次回はこのJSONと元音声を読み込むと再開できます。')}catch(e){status(e.message)}};
$('clear').onclick=()=>{
  if(dirty&&!confirm('未保存の編集を破棄して消去しますか？'))return;
  project=null;dirty=false;stopAt=null;$('editor').hidden=true;$('audio').pause();$('audio').removeAttribute('src');$('audio').load();
  if(url)URL.revokeObjectURL(url);url=null;$('project').value='';$('audioFile').value='';$('candidates').replaceChildren();$('segments').replaceChildren();
  status('読み込んだデータを消去しました。端末に保存済みのファイルは別途削除してください。');
};
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue=''}});

function updateDuration(){
  const duration=+$('end').value-+$('start').value;
  $('duration').textContent=Number.isFinite(duration)&&duration>0 ? `${duration.toFixed(1)}秒${duration<30||duration>60?' · おすすめは30〜60秒です':''}` : '開始・終了を確認してください';
}
function renderCandidates(){
  const root=$('candidates');root.replaceChildren();
  if(!project)return;
  const query=$('search').value.trim().toLowerCase();
  const candidates=project.candidates.filter(c=>`${c.title||''} ${c.reason||''} ${project.segments.filter(s=>s.end>c.start&&s.start<c.end).map(s=>s.text).join(' ')}`.toLowerCase().includes(query));
  candidates.sort($('sort').value==='time' ? (a,b)=>a.start-b.start : (a,b)=>(b.score||0)-(a.score||0));
  $('candidateCount').textContent=`${candidates.length}件の候補`;
  if(!candidates.length){const empty=document.createElement('p');empty.textContent='候補がありません。検索を変えるか、開始・終了を手動で指定してください。';root.append(empty)}
  for(const [i,c] of candidates.entries()){
    const card=document.createElement('article');card.className='candidate';
    const heading=document.createElement('h3');heading.textContent=`${i+1}. ${c.title||'候補'}`;
    const detail=document.createElement('small');detail.textContent=`${clock(c.start)}〜${clock(c.end)} · ${(c.end-c.start).toFixed(1)}秒`;
    const reason=document.createElement('p');reason.textContent=c.reason||'前後を聴いて確認してください';
    const select=()=>{range(c.start,c.end);$('title').value=c.title||'';changed()};
    const edit=document.createElement('button');edit.textContent='この範囲を編集';edit.onclick=()=>{select();$('title').focus()};
    const preview=document.createElement('button');preview.className='secondary';preview.textContent='前後を試聴';preview.onclick=()=>{select();listen(true)};
    card.append(heading,detail,reason,edit,preview);root.append(card);
  }
}
function clock(value){return `${Math.floor(value/60)}:${Math.floor(value%60).toString().padStart(2,'0')}`}
$('search').oninput=renderCandidates;$('sort').onchange=renderCandidates;
$('useStart').onclick=()=>{if(Number.isFinite($('audio').duration)){range(Number($('audio').currentTime.toFixed(1)),+$('end').value);changed()}else status('元音声を先に選択してください')};
$('useEnd').onclick=()=>{if(Number.isFinite($('audio').duration)){range(+$('start').value,Number($('audio').currentTime.toFixed(1)));changed()}else status('元音声を先に選択してください')};

function renderSpeakers(){
  const root=$('speakers');root.replaceChildren();
  const speakers=[...new Set(project.segments.map(s=>s.speaker).filter(Boolean))];
  if(!speakers.length){root.textContent='話者は未推定です。字幕ごとの話者欄で入力できます。';return}
  for(const name of speakers){
    const label=document.createElement('label');label.textContent=`${name} の名前`;
    const input=document.createElement('input');input.value=name;input.setAttribute('aria-label',`${name}の名前`);
    const button=document.createElement('button');button.textContent='この話者をまとめて変更';button.className='secondary';
    button.onclick=()=>{const next=input.value.trim();if(!next){status('名前を入力してください');return}for(const s of project.segments){if(s.speaker===name)s.speaker=next}changed();renderSegments();renderSpeakers()};
    label.append(input,button);root.append(label);
  }
}
