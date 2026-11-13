"""Package only static assets for Cloudflare Pages Direct Upload."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root = Path(__file__).resolve().parents[1]
output = root.parent / 'campus-voice-cloudflare.zip'
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for name in ['index.html', 'app.js', 'model.js', 'style.css', '_headers']:
        archive.write(root / 'web' / name, name)
print(output)
