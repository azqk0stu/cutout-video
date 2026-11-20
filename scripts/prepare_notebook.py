"""Embed the current static editor into the Colab notebook for a no-deploy trial."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
path = root / 'notebooks/campus_voice.ipynb'
nb = json.loads(path.read_text())
html = (root / 'web/index.html').read_text()
css = (root / 'web/style.css').read_text()
model = (root / 'web/model.js').read_text().replace('export function', 'function')
app = (root / 'web/app.js').read_text().replace("import {validateProject,exportEdit} from './model.js';", '')
html = html.replace('<link rel="stylesheet" href="style.css">', '<style>'+css+'</style>')
html = html.replace('<script type="module" src="app.js"></script>', '<script type="module">'+model+'\n'+app+'</script>')
cell = {'cell_type':'code','metadata':{'tags':['portable-editor']},'execution_count':None,'outputs':[], 'source': ('# Cloudflare公開前でも使える、単体の編集画面です。\nfrom pathlib import Path\nfrom google.colab import files\nPath("campus-voice-editor.html").write_text('+repr(html)+', encoding="utf-8")\nfiles.download("campus-voice-editor.html")\n').splitlines(True)}
nb['cells'] = [c for c in nb['cells'] if 'portable-editor' not in c.get('metadata',{}).get('tags',[])]
nb['cells'].insert(2,cell)
# Keep the ranking implementation executable without repository downloads in Colab.
algorithm = (root / 'scripts/candidates.py').read_text()
for candidate_cell in nb['cells']:
    if 'candidate-ranking' in candidate_cell.get('metadata', {}).get('tags', []):
        source = ''.join(candidate_cell['source'])
        marker = '# 候補だけ再計算する場合は、このセルから実行します。'
        source = source[source.index(marker):]
        candidate_cell['source'] = (algorithm + '\n' + source).splitlines(True)
for speaker_cell in nb['cells']:
    if 'speaker-diarization' in speaker_cell.get('metadata', {}).get('tags', []):
        source = ''.join(speaker_cell['source'])
        marker = '# 話者を自動で推定します。'
        source = source[source.index(marker):]
        speaker_cell['source'] = ((root / 'scripts/speakers.py').read_text() + '\n' + source).splitlines(True)
path.write_text(json.dumps(nb, ensure_ascii=False, indent=2)+'\n')
