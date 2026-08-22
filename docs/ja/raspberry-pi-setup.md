# Raspberry Piのセットアップ

[English](../raspberry-pi-setup.md) | [한국어](../ko/raspberry-pi-setup.md) | [日本語](raspberry-pi-setup.md)

この文書では、Raspberry Pi OSで現在の統合コードを準備する手順を説明します。実際のモーターを接続する前に、[配線ガイド](wiring.md)と安全上の注意事項を確認してください。

## 1. OSとシステムパッケージ

64ビット版のRaspberry Pi OSを用意し、必要な場合に限ってSSHを有効にします。

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip alsa-utils mpg123 ffmpeg libgl1 libglib2.0-0
```

- `alsa-utils`: `arecord`、`aplay`、オーディオデバイスの確認
- `mpg123` と `ffmpeg`: gTTS音声の再生と代替再生経路
- `libgl1` と `libglib2.0-0`: OpenCVの実行に必要となる場合があるシステムライブラリ

Raspberry Pi OSのバージョンとボードによって、GPIOバックエンドの互換性が異なる場合があります。このコードは `RPi.GPIO` インターフェースを使用するため、インストール時にエラーが発生した場合は、使用中のボードとOSに対応する互換パッケージを確認してください。

## 2. リポジトリのクローンと仮想環境

```bash
git clone https://github.com/cora1022/gemini-raspberry-pi-robot.git
cd gemini-raspberry-pi-robot

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

新しいターミナルを開いた場合は、プロジェクトフォルダーで `source .venv/bin/activate` を再度実行します。

## 3. 環境変数

```bash
cp .env.example .env
nano .env
```

最低限必要な設定は次のとおりです。

```dotenv
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash
```

実際のデバイスに合わせて、次の値を確認します。

```dotenv
AUDIO_DEVICE=plughw:3,0
CAMERA_INDEX=1
SAFE_DISTANCE_CM=25
ULTRASONIC_STOP_CM=18
ULTRASONIC_TRIG=23
ULTRASONIC_ECHO=24
COMMAND_LED_PIN=25
```

`.env` はコミットしません。実行前に `git status --ignored` で無視対象になっていることを確認し、キーが漏えいした場合は、ファイルを削除する前にそのキーを失効させます。

## 4. マイクとスピーカーの確認

デバイス番号を確認します。

```bash
arecord -l
aplay -l
```

`.env` の `AUDIO_DEVICE` と同じデバイスを使って短時間録音します。次の例はデフォルト値 `plughw:3,0` を使用しています。設定値を変更した場合は、コマンドのデバイス名も置き換えてください。

```bash
arecord -D plughw:3,0 -f S16_LE -r 48000 -c 1 -d 3 microphone-test.wav
aplay microphone-test.wav
speaker-test -t wav -c 2
```

デバイス番号と対応するサンプルレートは環境によって異なります。音声認識とgTTSはネットワーク接続の影響も受けます。

## 5. カメラの確認

OpenCVを使って `CAMERA_INDEX` が正しいか確認します。次の例はデフォルト値1を使用しています。設定値を変更した場合は、`VideoCapture()` の引数も置き換えてください。

```bash
python - <<'PY'
import cv2
camera = cv2.VideoCapture(1)
ok, frame = camera.read()
print("camera:", ok, None if frame is None else frame.shape)
camera.release()
PY
```

`False` と表示された場合は、`/dev/video*` とUSB接続を確認し、インデックスを0、1、2の順に変更して試します。

## 6. コマンドプランだけをテストする

```bash
python test_case.py
```

このスクリプトはGPIO、カメラ、マイク、モーターのメソッドを呼び出しません。APIキーがある場合はGeminiのJSONプランを確認し、ない場合はルールベースの代替結果を表示します。ハードウェアの安全試験に代わるものではありません。

## 7. 実機ロボットの実行

配線、車輪を浮かせた状態でのモーター試験、距離センサーの値をすべて確認してから実行します。

```bash
python main_brain.py
```

プログラムは起動フレーズを待ち、その後にコマンドをもう一度聞き取ります。終了するには、`종료`、`끝내`、`그만` などの音声コマンドを使用するか、`Ctrl+C` を押します。終了処理ではモーターの停止とGPIOの後処理を試みますが、プログラムとは別に、すぐに切断できるモーター電源スイッチを用意してください。

`python 2main_brain.py` は現在のエントリーポイントではありません。このファイルは、現在のリポジトリには存在しない `robot` オブジェクトを必要とする以前の実験記録であり、そのままでは実行できません。

## 実機での初回テスト手順

1. モーター電源を切り離した状態で、GPIOとセンサーの値を確認します。
2. HC-SR04のECHOから出力される5 VがRaspberry PiのGPIOへ直接入力されないよう、分圧回路またはレベル変換回路を確認します。
3. 車輪を床から浮かせます。
4. APIを使用せず、モーターの方向と停止だけを短時間確認します。
5. 障害物を置き、25 cm以下で前進がブロックされることと、18 cm以下で連続走行が停止することをそれぞれ確認します。
6. センサー異常時の挙動を確認します。現行コードは3回測定し、有効値が1件でもあれば有効値だけの中央値を採用します。有効値がない場合は、ECHOが測定開始時からHIGHのままだった試行が1回でもあれば0 cm、そうでなくタイムアウトした試行が1回でもあれば400 cm、3回とも例外で失敗した場合は0 cmとして扱います。前進処理は0 cmで停止しますが、400 cmでは停止しません。
7. カメラ、マイク、Geminiを順に追加します。
8. 広い場所で、低速かつ短いコマンドから床面走行を始めます。

## よくある問題

- APIエラー: キー、モデルの利用可否、インターネット接続、APIクォータを確認します。
- マイクが反応しない: `AUDIO_DEVICE`、サンプルレート、USBデバイス番号を確認します。
- カメラを認識できない場合: `CAMERA_INDEX`、`/dev/video*`、ほかのプロセスによるデバイスの占有を確認します。
- GPIOテストモード: `RPi.GPIO` のインストール状況と、実行しているボードがRaspberry Piであることを確認します。
- ロボットが直進しない: コードだけでなく、バッテリー電圧、モーターの極性、床の摩擦、左右のモーター差も確認します。
