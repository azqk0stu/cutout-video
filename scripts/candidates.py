"""Candidate ranking; optional embeddings are computed in Colab, never the editor."""
import math
import re


def summarize_excerpt(segments, max_chars=220):
    """Extract representative sentences; never invent claims or paraphrase ASR.

    Character bigrams work without Japanese tokenizers. Keep selected sentences
    in chronological order; the UI explicitly labels this as an extractive summary.
    """
    sentences = []
    for segment in segments:
        for sentence in re.split(r'(?<=[。！？!?])', segment['text']):
            sentence = sentence.strip()
            if sentence and sentence not in sentences:
                sentences.append(sentence)
    if not sentences:
        return ''
    def grams(text):
        text = re.sub(r'\s+', '', text)
        return set(text[i:i+2] for i in range(len(text)-1))
    features = [grams(t) for t in sentences]
    weights = {}
    for feature in features:
        for gram in feature:
            weights[gram] = weights.get(gram, 0) + 1
    ranking = sorted(range(len(sentences)), key=lambda i: sum(weights[g] for g in features[i])/max(1,len(features[i])) + min(len(sentences[i]),80)/160, reverse=True)
    selected = []
    for i in ranking:
        if any(len(features[i]&features[j])/max(1,len(features[i]|features[j]))>.8 for j in selected):
            continue
        selected.append(i)
        if len(selected)==2:
            break
    text = ' … '.join(sentences[i] for i in sorted(selected))
    return text if len(text)<=max_chars else text[:max_chars-1]+'…'


def suggest_candidates(segments, embeddings=None, limit=10):
    """Rank 30–60s windows with topic, tempo and transcript reaction cues.

    Embeddings must align with segments. Reaction words are not laughter detection.
    Short recordings return fewer candidates rather than duplicating intervals.
    """
    if embeddings is not None and len(embeddings) != len(segments):
        raise ValueError('字幕と埋め込みの件数が一致しません')
    if not segments:
        return []
    boundaries = set()
    if embeddings is not None:
        for i in range(1, len(segments)):
            a, b = embeddings[i - 1], embeddings[i]
            norm = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
            similarity = sum(x*y for x, y in zip(a, b)) / norm if norm else 1
            if similarity < .45:
                boundaries.add(i)
    windows = []
    for i, first in enumerate(segments):
        # A long individual subtitle cannot make a 30–60s candidate safely.
        selected = []
        for j in range(i, len(segments)):
            if segments[j]['end'] - first['start'] > 60:
                break
            selected.append(segments[j])
            duration = segments[j]['end'] - first['start']
            if duration < 30:
                continue
            gap = segments[j+1]['start']-segments[j]['end'] if j+1 < len(segments) else 2
            clean_end = gap >= .8 or j+1 in boundaries or j == len(segments)-1
            text = ''.join(s['text'] for s in selected)
            speech = sum(s['end']-s['start'] for s in selected)
            density = min(1, speech / duration)
            tempo = min(1, len(selected) / duration * 5)
            reactions = len(re.findall(r'すごい|面白|おもしろ|まさか|なるほど|[!！]|[（(]笑[)）]', text))
            topic = i in boundaries or i == 0
            score = .4*density + .25*tempo + .15*min(1,reactions/3) + .1*topic + .1*clean_end
            reasons = [f'発話密度 {density:.0%}', f'発話区間 {len(selected)}件']
            if topic and embeddings is not None:
                reasons.append('話題の区切りから開始')
            if reactions:
                reasons.append(f'反応語 {reactions}件（文字情報）')
            if clean_end:
                reasons.append('区切りで終了')
            windows.append(dict(start=first['start'], end=segments[j]['end'],
                                title=first['text'][:40], reason=' / '.join(reasons),
                                score=round(score,4), density=round(density,3),
                                reactions=reactions, topic_start=bool(topic and embeddings is not None),
                                tempo=round(tempo,3), clean_end=clean_end, opening=topic))
    chosen = []
    ranked = sorted(windows, key=lambda c: c['score'], reverse=True)
    def compatible(candidate):
        return not any(max(0,min(candidate['end'], c['end'])-max(candidate['start'],c['start'])) /
                       min(candidate['end']-candidate['start'],c['end']-c['start']) > .25 for c in chosen)
    # Reserve one eligible candidate per time band before filling by quality.
    # Use actual timestamps, including long silences, rather than subtitle count.
    if ranked:
        first = segments[0]['start']
        span = max(1, segments[-1]['end']-first)
        bands = min(5, limit)
        for band in range(bands):
            pool = [c for c in ranked if min(bands-1,int(((c['start']+c['end'])/2-first)/span*bands)) == band]
            candidate = next((c for c in pool if compatible(c)), None)
            if candidate is not None:
                candidate['selection_basis'] = f'解析範囲の第{band+1}/{bands}時間帯から、得点上位の重複しない候補を確保'
                chosen.append(candidate)
    for candidate in ranked:
        if len(chosen) >= limit:
            break
        if compatible(candidate):
            candidate['selection_basis'] = '時間帯別の候補を確保した後、得点順で重複しない候補を追加'
            chosen.append(candidate)
    for candidate in chosen:
        selected = [s for s in segments if s['end']>candidate['start'] and s['start']<candidate['end']]
        candidate['summary'] = summarize_excerpt(selected)
        candidate['summary_method'] = 'extractive-v1'
        candidate['reasons'] = [
            f"発話密度 {candidate['density']:.0%}：無音が少ない区間を加点",
            f"発話テンポ指標 {candidate['tempo']:.0%}：字幕区間数／秒から計算（話者交代数ではありません）",
            candidate['selection_basis'],
        ]
        if candidate['topic_start']:
            candidate['reasons'].append('話題の開始位置と推定されたため加点（先頭または隣接字幕の意味の変化）')
        elif candidate['opening']:
            candidate['reasons'].append('解析範囲の先頭から始まるため加点（意味による判定ではありません）')
        if candidate['reactions']:
            candidate['reasons'].append(f"驚き・反応の文字表現 {candidate['reactions']}件を加点（音声の笑い検出ではありません）")
        if candidate['clean_end']:
            candidate['reasons'].append('無音・話題境界・解析末尾のいずれかで終わるため加点')
    return sorted(chosen, key=lambda c:c['score'], reverse=True)
