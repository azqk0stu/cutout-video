// This extension runs only in a Colab HTML output, never via an exposed server.
const callbackName='__CAMPUS_CALLBACK__';
const liveStatus=$('liveStatus');
let liveBusy=false,previewOffset=0;
async function rpc(action,data={}){
  if(!globalThis.google?.colab?.kernel?.invokeFunction)throw Error('Colabへの接続がありません。このHTMLはColabの出力欄で操作してください。切断時は作業JSONを保存してから再起動します。');
  const reply=await google.colab.kernel.invokeFunction(callbackName,[action,data],{});
  const result=reply.data['application/json'];
  if(!result?.ok)throw Error(result?.error||'Colabが応答しませんでした');
  return result;
}
async function runJob(action,data){
  if(liveBusy)throw Error('前の処理が終わるまでお待ちください');
  liveBusy=true;
  document.querySelectorAll('[data-live]').forEach(b=>b.disabled=true);
  try{
    const {job}=await rpc(action,data);
    for(;;){
      const state=await rpc('status',{job});
      liveStatus.textContent=state.messages?.join('\n')||'処理しています…';
      if(state.done)return {job,result:state.result,blob:state.result?.mime?await receive(job,state.result):null};
      await new Promise(resolve=>setTimeout(resolve,2000));
    }
  }finally{liveBusy=false;document.querySelectorAll('[data-live]').forEach(b=>b.disabled=false)}
}
async function receive(job,result){
  const chunks=[];let offset=0;
  for(;;){
    const part=await rpc('chunk',{job,offset});
    chunks.push(Uint8Array.from(atob(part.data),c=>c.charCodeAt(0)));offset=part.next;
    if(part.done)break;
  }
  return new Blob(chunks,{type:result.mime});
}
function liveError(error){liveStatus.textContent=error.message;status(error.message)}
$('liveAnalyze').onclick=async()=>{
  if(dirty&&!confirm('未保存の編集があります。作業を保存してから解析し直してください。続けますか？'))return;
  try{
    const {result}=await runJob('analyze',{seconds:+$('liveSeconds').value,speakers:+$('liveSpeakers').value,count:+$('liveCount').value,diarize:$('liveDiarize').checked,topics:$('liveTopics').checked});
    loadProject(result.project);liveStatus.textContent='解析完了。候補を選び、前後を試聴して編集してください。';
  }catch(e){liveError(e)}
};
listen=async(context=false)=>{
  try{
    const edit=selection();const start=Math.max(0,edit.start-(context?10:0));
    const {blob}=await runJob('preview',{start,end:edit.end+(context?10:0)});
    if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(blob);
    $('audio').src=url;previewOffset=start;stopAt=null;await $('audio').play();liveStatus.textContent='試聴音声を再生しています。';
  }catch(e){liveError(e)}
};
$('useStart').onclick=()=>{if(Number.isFinite($('audio').duration)){range(previewOffset+$('audio').currentTime,+$('end').value);changed()}};
$('useEnd').onclick=()=>{if(Number.isFinite($('audio').duration)){range(+$('start').value,previewOffset+$('audio').currentTime);changed()}};
$('liveRender').onclick=async()=>{
  try{
    const edit=selection();const {blob}=await runJob('render',{edit,bgm:$('liveBgm').checked});
    // Download immediately: later preview/analysis replaces the backend's last job.
    const link=document.createElement('a');
    const u=URL.createObjectURL(blob);link.href=u;link.download='clip.mp4';link.textContent='完成MP4を保存';
    link.onclick=()=>setTimeout(()=>URL.revokeObjectURL(u),60000);
    $('liveResult').replaceChildren(link);liveStatus.textContent='動画が完成しました。「完成MP4を保存」を押してください。';
  }catch(e){liveError(e)}
};
rpc('hello').then(data=>{$('liveBgm').disabled=!data.bgm;$('liveBgm').checked=data.bgm;liveStatus.textContent=`接続しました。元音声：${data.audio_name}。「解析する」を押してください。`}).catch(liveError);
