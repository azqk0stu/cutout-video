# Campus Voice 開発引き継ぎ

更新日: 2026-11-13（日本時間）

## 最新の中断地点（2026-11-13）

ユーザーから「動画できた」と報告あり。ユーザーのColabと単体HTML編集画面を使い、動画生成まで到達した。生成動画自体はこの開発環境で検査していない。解析対象が冒頭180秒か全編か、BGMの有無、画質・字幕品質は未確認。今日はここで終了し、追加の開発・公開は進めない。

### 次回ユーザーが再開する手順

1. PCに保存したcampus-voice-editor.htmlを開く。
2. 「作業全体を保存」で得たcampus-voice-session.jsonと元MP3を読み込む。作業JSONがない場合はanalysis.jsonから再開できるが、字幕修正や選択範囲は保存されていない可能性がある。
3. できた動画の字幕・音量・範囲を確認し、修正または2本目の作成へ進む。全編解析はTEST_SECONDS=0で別途実行する（実施済みかは次回確認）。
4. 動画生成が必要なときだけGitHubのノートブックをColabで開く。ランタイムが切れていたら依存インストールと元MP3のアップロードをやり直す。既存のclip-edit.jsonで動画だけ再生成するなら文字起こしの再実行は不要。元音声アップロード後、編集JSON/BGM読み込みセルと動画生成セルへ進む。

手元に残すもの: 元MP3、campus-voice-editor.html、analysis.json、campus-voice-session.json、clip-edit.json、生成MP4、使ったBGM。これらのユーザーデータをこちらで保存・取得できたわけではない。ブラウザを閉じる前に編集画面で「作業全体を保存」を押すよう案内する。Colabの一時領域は消えるため唯一の保存先にしない。

### 今回のエラーと対処

- Colab Python 3.13.18、faster-whisper 1.2.1、av 19.0.2で `TypeError: open() got an unexpected keyword argument 'metadata_errors'` が発生。依存条件はav>=11で上限なしだった。
- `%pip install -q --force-reinstall "av==16.0.1"` とセッション再起動を案内。ユーザーは再起動後、最終的に動画生成成功を報告。再起動後のavバージョンの再取得はしていない。
- 再発防止としてリポジトリのインストールセルにもav==16.0.1を指定した。新しい組み合わせをこの開発環境で文字起こし実行したわけではない。
- 編集JSONセルの `KeyError: 'start'` は、start/endを持たないJSONを選んだことによる。analysis.jsonや作業全体のJSONではなく、編集画面の「Colab用の編集JSONを保存」で得たclip-edit.jsonを選ぶ。
- 元音声は解析JSONのaudio_nameと同名が必要。画面には `JJ_Campus_Voice_2026-10-04 (1).mp3` と表示されていた。PCで見つからない場合はColabで `files.download(str(audio_path))` により取得できる。自動で付いた番号には注意する。

## 今回の回収と保存

新環境 /workspace には旧ソースが存在しなかった。GitHub azqk0stu/cutout-video は git ls-remote と clone でブランチのない空リポジトリと確認した。
旧環境の起動を再試行せず、旧チャット「cutout-videoをセットアップ」（01a1677b-a08c-704e-b1dd-908a4951c098）の実装履歴からファイル作成・修正コマンドを回収し、時系列に適用した。旧ディスクの直接コピーではないため、履歴に記録されていない変更の有無は確認できない。

回収対象: web/ の5ファイル、notebooks/campus_voice.ipynb、scripts/ の2ファイル、tests/ の3ファイル、package.json、.gitignore、README.md、docs/CLOUDFLARE.md。本書を追加し、GitHubへ通常のpushで保存する。force pushは使用しない。保存コミットはGit履歴で確認すること。旧環境は削除していない。

## 目的と設計

個人用の学内ラジオ切り抜きアプリ。月1本・約50分の音声から30〜60秒の動画を2本ほど作る。目標は文字起こし、意味による話題分け、話者分離後の名前入力、笑いや会話の活発さから5〜10候補を提示し、人が前後を試聴して字幕・範囲を修正し最終決定すること。

無課金を優先し、メモリの少ないPCに重い処理をさせない。
- Cloudflare Pages: 静的な編集画面（web/、ビルド不要）
- Google Colab: 文字起こし・解析・動画生成
- JSONを手動で受け渡す。Colabを常設APIにしない。

## 回収した実装

- faster-whisper smallによる日本語文字起こし、無音境界と発話密度による候補抽出。
- 元音声のローカル試聴、前後10秒試聴、範囲・字幕・話者欄・タイトル編集。
- 作業全体のJSON保存・再読み込み（kind=campus-voice-session、projectとselectionを保持）、Colab用clip-edit.json出力、未保存警告、読み込みデータ消去。
- FFmpegによる単色背景、ASS字幕、任意BGM（音量・フェード）付きMP4。9:16、1:1、16:9。
- Colab初回はTEST_SECONDS=180。0に変えると全編。途中字幕checkpointあり。
- Colabから単体HTML編集画面を取得でき、Cloudflare公開前でも利用可能。

未実装: 意味による話題分析、自動話者分離、笑い声検出、背景画像選択、動画へのタイトル表示。現在の話者欄は手入力のみ。候補は意味や笑いを理解して選んでいるわけではない。

## 今回の検証

回収後の新環境で成功:
- npm test: JSモデルテスト3件。
- python -m unittest discover -s tests -p '*_test.py': Pythonテスト4件。ノートブック構文、単体HTMLの依存埋め込み、実Chromiumで字幕・話者修正→作業保存→再読み込み→編集JSON出力、合成音声でBGMあり／なしのMP4生成。
- ローカルHTTP配信、app.js/model.js/style.cssの応答、JS構文確認。

回収時点では実ラジオ音声・実Colab・Cloudflare本番は未検証だった。その後ユーザーがColabで動画生成成功を報告した（上記参照）。Cloudflare本番配信は引き続き未検証。

## 開発と再開手順

```sh
cd /workspace/cutout-video
npm test
python -m unittest discover -s tests -p '*_test.py'
npm run dev
```

Node.jsとPython 3を利用。PythonテストにはFFmpeg/ffprobe、Python Playwright、/usr/bin/chromiumが必要。今回の環境には存在し、追加インストールなしで実行できた。

webを変更したら `python scripts/prepare_notebook.py` でノートブックの単体HTMLにも反映する。配布ZIPは `python scripts/package_cloudflare.py`。ZIPはリポジトリの親に生成され、Git保存対象外。

次は実音声でColabの冒頭180秒を試し、字幕・候補・動画を確認する。その後TEST_SECONDS=0で全編を解析し、Cloudflare公開と未実装機能の追加を進める。

## Cloudflare

未認証・未公開。旧環境ではログイン開始時にdash.cloudflare.comへの通信が403で失敗。旧設定の許可候補はdash.cloudflare.com、api.cloudflare.com、*.pages.devだった。今回の環境はnetwork policyがunrestricted/enforcedと観測されたが、Cloudflare認証・接続自体は再検証していない。旧設定や認証が引き継がれたと仮定しない。

ログイン候補は `wrangler login --device --browser=false`。ユーザーのブラウザ承認が必要。秘密情報をチャットへ貼るよう要求しない。公開はユーザー許可済み。詳しいPages設定はCLOUDFLARE.mdを参照。

## データ

実音源はJJ_Campus_Voice_2026-10-04.mp3。旧添付は32MiB超で開発環境へ取得できなかった。ユーザー側Colabではその後動画生成まで到達した。ユーザーがColabで元MP3を選択する必要がある。

音声・動画・解析結果・字幕データ・認証情報をGitHubへ含めない。ColabはDriveへ自動保存しない。編集画面のファイルはブラウザ内で処理する。保存JSONと元音声は別管理。Colab上のデータはランタイム削除、手元のファイルは個別削除する。
