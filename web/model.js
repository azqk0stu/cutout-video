export function validateProject(p) {
  if (typeof p?.audio_name !== 'string' || !p.audio_name || !p.segments?.length) throw Error('元音声名と字幕が必要です');
  if (p?.version !== 1 || !Array.isArray(p.segments) || !Array.isArray(p.candidates)) throw Error('対応する解析結果ではありません');
  for (const s of p.segments) if (!Number.isFinite(s.start) || !Number.isFinite(s.end) || s.start < 0 || s.end <= s.start || typeof s.text !== 'string') throw Error('字幕の時刻・内容が不正です');
  for (const c of p.candidates) if (!Number.isFinite(c.start) || !Number.isFinite(c.end) || c.start < 0 || c.end <= c.start) throw Error('候補の時刻が不正です');
  return p;
}
export function exportEdit(project, start, end, segments, bgmVolume, format) {
  if (!['vertical','square','landscape'].includes(format)) throw Error('動画サイズが不正です');
  if (!Number.isFinite(bgmVolume) || bgmVolume < 0 || bgmVolume > 1) throw Error('BGM音量は0〜1にしてください');
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) throw Error('終了時刻は開始時刻より後にしてください');
  if (!segments.some(s => s.end > start && s.start < end)) throw Error('字幕のある範囲を選んでください');
  return {version:1, audio_name:project.audio_name, start,end,segments:segments.filter(s=>s.end>start&&s.start<end),bgm_volume:bgmVolume,format};
}
