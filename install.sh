#!/bin/bash
set -e
echo "====================================="
echo " 作業トラッカー セットアップ"
echo "====================================="
if ! command -v brew &>/dev/null; then
  echo "Homebrewをインストール中..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
brew install python 2>/dev/null || true
cd ~
if [ -d "tracker" ]; then
  echo "既存のtrackerを更新中..."
  cd tracker && git pull
else
  git clone https://github.com/yousuke912/tracker.git
  cd tracker
fi
python3 -m venv venv
source venv/bin/activate
pip install -q pyobjc-framework-Cocoa pyobjc-framework-Quartz anthropic flask
echo ""
echo "AnthropicのAPIキーを入力してください"
echo "取得先 → https://console.anthropic.com"
echo ""
read -p "APIキー: " apikey
cat > ~/Library/LaunchAgents/com.omoseka.tracker.plist << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.omoseka.tracker</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$HOME/tracker/start.sh</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ANTHROPIC_API_KEY</key><string>$apikey</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key><string>$HOME/tracker_launchd.log</string>
  <key>StandardErrorPath</key><string>$HOME/tracker_launchd.log</string>
</dict>
</plist>
PLIST
launchctl load ~/Library/LaunchAgents/com.omoseka.tracker.plist
echo ""
echo "====================================="
echo "✅ セットアップ完了！"
echo "ブラウザで開く → http://localhost:5555"
echo "====================================="
