#!/usr/bin/env bash
#
# 로컬 Ollama 개발 환경 준비 (ADR-0012). all_total_vue_student/sh/setup_ollama.sh를 줄여서 옮겼다.
# - ollama serve가 없으면 백그라운드로 띄운다 (이미 떠 있으면 그대로 쓴다)
# - 모델이 없으면 받는다 (qwen3:8b는 약 5GB)
# - 한 번 불러서 메모리에 올려 둔다 (첫 요청이 느리지 않게)
#
# 실행:
#   bash scripts/setup_ollama.sh
#   OLLAMA_MODEL=qwen3:14b bash scripts/setup_ollama.sh   # 다른 모델로 (.env의 LLM_MODEL_*도 같이 바꾼다)
#
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen3:8b}"
URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

command -v ollama >/dev/null 2>&1 \
    || { echo "ERROR: ollama가 없습니다. brew install ollama 또는 https://ollama.com 에서 설치하세요."; exit 1; }

if ! curl -s --max-time 2 "$URL/api/tags" >/dev/null 2>&1; then
    echo "ollama serve를 백그라운드로 띄웁니다 (로그: /tmp/ollama_serve.log)"
    nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
    for _ in $(seq 1 30); do
        curl -s --max-time 2 "$URL/api/tags" >/dev/null 2>&1 && break
        sleep 0.5
    done
fi
curl -s --max-time 2 "$URL/api/tags" >/dev/null 2>&1 || { echo "ERROR: ollama serve 기동 실패"; exit 1; }

if ollama list | grep "^${MODEL}" >/dev/null; then
    echo "이미 받아져 있어 그대로 씁니다: $MODEL"
else
    echo "모델 받는 중: $MODEL (몇 분 걸릴 수 있습니다)"
    ollama pull "$MODEL"
fi

echo "모델을 메모리에 올리는 중..."
curl -s "$URL/api/generate" \
    -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false,\"think\":false,\"options\":{\"num_predict\":1}}" >/dev/null

cat <<EOF

Ollama 준비 완료: $MODEL ($URL)
.env에 아래 값이 있는지 확인한 뒤 ai-server와 backend를 다시 띄우세요.
  LLM_PROVIDER=ollama
  LLM_MODEL_FAST=ollama:$MODEL
  LLM_MODEL_QUALITY=ollama:$MODEL
EOF
