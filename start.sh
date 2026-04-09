#!/bin/bash
cd "$(dirname "$0")"
echo "====================================="
echo " 作業トラッカー 起動"
echo "====================================="
source venv/bin/activate
echo "▶ 監視デーモン 起動中..."
python3 tracker.py &
TRACKER_PID=$!
sleep 1
echo "▶ ダッシュボード 起動中..."
python3 dashboard.py &
DASHBOARD_PID=$!
echo ""
echo "✅ 起動完了: http://localhost:5555"
echo "停止するには Ctrl+C"
echo "====================================="
trap "kill $TRACKER_PID $DASHBOARD_PID 2>/dev/null; exit 0" INT TERM
wait
