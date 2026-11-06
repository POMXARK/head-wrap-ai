#!/bin/sh
# Снимок страницы панели для проверки глазами (headless Chrome): ./shot.sh [путь] [ширина] [высота] [файл]
# По умолчанию /pipeline 1300x2400 -> /tmp/panel.png. Панель должна работать (python3 app.py --port 8770).
P=${1:-/pipeline}; W=${2:-1300}; H=${3:-2400}; O=${4:-/tmp/panel.png}
google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=$W,$H \
  --virtual-time-budget=${BUDGET:-6000} --screenshot="$O" "http://127.0.0.1:${PORT:-8770}$P" >/dev/null 2>&1
echo "$O"
