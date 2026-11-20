"""Colab speaker clustering using a public WavLM speaker embedding model.

Labels are estimates per transcript segment, not overlapping-source separation.
"""

def labels_to_segments(segments, labels):
    if len(segments) != len(labels):
        raise ValueError('話者ラベルと字幕の件数が一致しません')
    names = {}
    result = []
    for segment, label in zip(segments, labels):
        if label not in names:
            names[label] = f'話者{len(names)+1}'
        result.append(dict(segment, speaker=names[label]))
    return result


def diarize_segments(audio_path, segments, num_speakers=2):
    """Cluster per-segment embeddings. Requires the expected speaker count.

    Uses at most 6 seconds of each utterance to bound model memory use. Short
    utterances and speaker changes within one subtitle are inherently uncertain.
    """
    import subprocess
    import tempfile
    from pathlib import Path
    import numpy as np
    import torch
    from transformers import AutoFeatureExtractor, AutoModelForAudioXVector
    from sklearn.cluster import AgglomerativeClustering

    if not isinstance(num_speakers, int) or not 1 <= num_speakers <= 10:
        raise ValueError('話者数は1〜10の整数にしてください')
    if len(segments) < num_speakers:
        raise ValueError('字幕数より話者数が多いため、話者数を減らしてください')
    if num_speakers == 1:
        return labels_to_segments(segments, [0]*len(segments))
    model_id = 'microsoft/wavlm-base-plus-sv'
    extractor = AutoFeatureExtractor.from_pretrained(model_id)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    speaker_model = AutoModelForAudioXVector.from_pretrained(model_id).to(device).eval()
    embeddings = []
    # Disk-backed PCM avoids loading an entire 50-minute waveform into RAM.
    with tempfile.TemporaryDirectory() as directory:
        pcm = Path(directory)/'voice.f32'
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(audio_path),'-vn','-ar','16000','-ac','1','-f','f32le',str(pcm)],check=True)
        audio = np.memmap(pcm, dtype='float32', mode='r')
        try:
            for i, segment in enumerate(segments):
                start = int(segment['start']*16000)
                end = min(len(audio), int(segment['end']*16000), start+6*16000)
                if end <= start:
                    raise ValueError('字幕時刻が元音声の範囲を超えています')
                clip = np.array(audio[start:end])
                if len(clip) < 16000:
                    clip = np.pad(clip, (0,16000-len(clip)))
                inputs = extractor(clip, sampling_rate=16000, return_tensors='pt', padding=True)
                with torch.inference_mode():
                    vector = speaker_model(**{k:v.to(device) for k,v in inputs.items()}).embeddings
                    vector = torch.nn.functional.normalize(vector, dim=-1)
                embeddings.append(vector[0].cpu().numpy())
                if (i+1)%25 == 0:
                    print(f'話者解析: {i+1}/{len(segments)}字幕')
        finally:
            del audio
    labels = AgglomerativeClustering(n_clusters=num_speakers, metric='cosine', linkage='average').fit_predict(np.stack(embeddings))
    del speaker_model
    if device == 'cuda':
        torch.cuda.empty_cache()
    return labels_to_segments(segments, labels.tolist())
