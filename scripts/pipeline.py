"""Analysis used by the Colab button UI. No persistent server or external API."""
import gc
import json
import subprocess
import tempfile
from pathlib import Path
from scripts.candidates import suggest_candidates
from scripts.speakers import diarize_segments


def analyze_audio(audio_path, test_seconds=0, speakers=2, use_speakers=True, use_topics=True, count=10, report=print):
    from faster_whisper import WhisperModel
    import torch
    audio_path=Path(audio_path)
    work=Path(tempfile.mkdtemp(prefix='campus-analysis-'))
    source=audio_path
    if test_seconds:
        source=work/'trial.wav'
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(audio_path),'-t',str(test_seconds),'-ar','16000','-ac','1',str(source)],check=True)
    gpu=torch.cuda.is_available()
    report('文字起こしを準備しています。初回はモデルをダウンロードします。')
    model=WhisperModel('small',device='cuda' if gpu else 'cpu',compute_type='float16' if gpu else 'int8')
    segments=[]
    try:
        stream,info=model.transcribe(str(source),language='ja',vad_filter=True,beam_size=5)
        for item in stream:
            if not item.text.strip():continue
            segments.append(dict(start=item.start,end=item.end,text=item.text.strip(),speaker=''))
            (work/'transcript-checkpoint.json').write_text(json.dumps(dict(audio_name=audio_path.name,segments=segments),ensure_ascii=False))
            if len(segments)%25==0:report(f'文字起こし: {item.end/60:.1f}分まで完了')
    except Exception:
        report(f'途中字幕を保存しました: {work / "transcript-checkpoint.json"}')
        raise
    finally:
        del model
        gc.collect()
        if gpu:torch.cuda.empty_cache()
    if not segments:raise ValueError('発話を検出できませんでした。元音声を確認してください。')
    speaker_status=dict(success=False,requested_speakers=speakers)
    if use_speakers:
        report('話者を推定しています。')
        try:
            segments=diarize_segments(source,segments,speakers)
            speaker_status.update(success=True,method='wavlm-utterance-clustering')
        except Exception as error:
            speaker_status['error']=str(error)
            report(f'話者推定を利用できませんでした。名前は手入力できます: {error}')
    embeddings=None
    if use_topics:
        report('話題の区切りを調べています。')
        try:
            from sentence_transformers import SentenceTransformer
            topic_model=SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',device='cpu')
            embeddings=topic_model.encode([s['text'] for s in segments],normalize_embeddings=True).tolist()
            del topic_model
        except Exception as error:
            report(f'話題モデルを利用できないため、他の指標で候補を選びます: {error}')
    candidates=suggest_candidates(segments,embeddings,count)
    project=dict(version=1,audio_name=audio_path.name,segments=segments,candidates=candidates,analysis=dict(test_seconds=test_seconds,speaker_diarization=speaker_status['success'],speaker_details=speaker_status,topic_analysis=embeddings is not None,laughter_detection=False,candidate_method='time-balanced-topic-tempo-v3'))
    report(f'完了: {len(segments)}字幕・{len(candidates)}候補。次の「候補と編集」へ進んでください。')
    return project
