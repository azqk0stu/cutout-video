"""Validate pasted/file edits before replacing the current Colab edit."""
import json
import math


def parse_edit(text, audio_name):
    try:
        edit = json.loads(text)
    except (ValueError, TypeError) as error:
        raise ValueError('編集画面の「Colabへコピー」からコピーしたJSONを貼り付けてください') from error
    if not isinstance(edit, dict):
        raise ValueError('編集JSONが必要です')
    if edit.get('kind') == 'campus-voice-session':
        raise ValueError('作業全体のJSONではなく、編集画面の「Colabへコピー」を使ってください')
    def number(value):
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)
    start, end = edit.get('start'), edit.get('end')
    if edit.get('version') != 1 or not number(start) or not number(end) or not 0 <= start < end or end-start > 600:
        raise ValueError('開始・終了を含む編集JSONが必要です（最大600秒）。解析JSONは使えません')
    if edit.get('audio_name') != audio_name:
        raise ValueError('解析時と同じ元音声を選択してください')
    segments = edit.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ValueError('字幕が含まれていません')
    for segment in segments:
        if not isinstance(segment,dict) or not number(segment.get('start')) or not number(segment.get('end')) or not 0 <= segment['start'] < segment['end'] or not isinstance(segment.get('text'),str):
            raise ValueError('字幕の時刻・内容が不正です')
    volume = edit.get('bgm_volume', .12)
    if not number(volume) or not 0 <= volume <= 1:
        raise ValueError('BGM音量は0〜1にしてください')
    if edit.get('format') not in ('vertical','square','landscape'):
        raise ValueError('動画サイズが不正です')
    return edit
