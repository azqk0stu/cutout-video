"""Install a mutually compatible Colab UI/model stack; stop on failure."""
import subprocess
import sys

REQUIREMENTS = [
    'faster-whisper==1.2.1', 'av==16.0.1',
    'sentence-transformers==6.3.0', 'transformers==5.23.0',
    'huggingface-hub>=1.32,<3', 'scikit-learn', 'ipywidgets==7.8.5',
]


def setup_colab():
    print('1/2: 必要なライブラリを準備しています。', flush=True)
    subprocess.run([sys.executable,'-m','pip','install','--upgrade','--quiet',*REQUIREMENTS],check=True)
    print('2/2: 動画・字幕用のツールを準備しています。', flush=True)
    subprocess.run(['apt-get','update','-qq'],check=True)
    subprocess.run(['apt-get','install','-y','-qq','ffmpeg','fonts-noto-cjk'],check=True)
    print('準備完了。ここで必ず「ランタイム → セッションを再起動」を選び、その後②だけ実行してください。①の再実行は不要です。', flush=True)
