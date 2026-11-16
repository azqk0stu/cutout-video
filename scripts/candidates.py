"""Candidate ranking; optional embeddings are computed in Colab, never the editor."""
import math
import re


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
                                reactions=reactions, topic_start=bool(topic and embeddings is not None)))
    chosen = []
    for candidate in sorted(windows, key=lambda c: c['score'], reverse=True):
        # Prevent near-duplicates while allowing a short shared lead-in.
        if any(max(0,min(candidate['end'], c['end'])-max(candidate['start'],c['start'])) /
               min(candidate['end']-candidate['start'],c['end']-c['start']) > .25 for c in chosen):
            continue
        chosen.append(candidate)
        if len(chosen) >= limit:
            break
    return chosen
