#!/usr/bin/env bash
# 개발용: Postgres + ai-server + backend + frontend를 한 터미널에서 띄운다 (기술 ADR-0026).
#
#   bash scripts/dev.sh
#
# - 로그는 [ai] [api] [web] 접두어를 붙여 이 터미널에 보이고, .dev-logs/<이름>.log 에도 남는다 (Claude가 읽어 확인한다).
# - 저장하면 자동 반영: ai-server는 uvicorn --reload, frontend는 Vite HMR,
#   backend는 [build]가 바뀐 Java를 계속 컴파일하고 devtools가 재시작한다.
# - Ctrl+C 한 번이면 전부 끈다. Postgres 컨테이너는 남겨 둔다 (docker compose down 으로 끈다).
# - 의존성(pyproject.toml, package.json, build.gradle)을 바꿨으면 이 스크립트를 다시 실행한다.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.dev-logs"
mkdir -p "$LOG_DIR"

say() { printf '\033[1m[dev]\033[0m %s\n' "$*"; }

cleanup() {
  trap - INT TERM EXIT
  say "끄는 중..."
  kill 0 2>/dev/null  # 이 스크립트가 띄운 프로세스 전부
  wait 2>/dev/null
}
trap cleanup INT TERM EXIT

# 이름, 폴더, 명령 → 접두어를 붙여 화면에 보이고 .dev-logs/<이름>.log 에 남긴다
run() {
  local name="$1" dir="$2"
  shift 2
  : > "$LOG_DIR/$name.log"
  (cd "$ROOT/$dir" && "$@" 2>&1) | tee -a "$LOG_DIR/$name.log" | awk -v p="[$name] " '{ print p $0; fflush() }' &
}

wait_for() {  # 이름, URL, 최대 초
  local name="$1" url="$2" limit="$3"
  for _ in $(seq "$limit"); do
    curl -sf -o /dev/null "$url" && { say "$name 준비됨 ($url)"; return 0; }
    sleep 1
  done
  say "$name 이(가) ${limit}초 안에 뜨지 않았어요. .dev-logs/$name.log 를 보세요"
  return 1
}

# 0. 미리 확인
docker info > /dev/null 2>&1 || { say "Docker가 꺼져 있어요. Docker Desktop을 켜고 다시 실행하세요"; exit 1; }
for port in 8000 8080 5173; do
  if lsof -iTCP:"$port" -sTCP:LISTEN > /dev/null 2>&1; then
    say "포트 $port 를 이미 쓰고 있어요 (이미 띄운 서버가 있나요?): $(lsof -iTCP:$port -sTCP:LISTEN -Fc | sed -n 's/^c//p' | head -1)"
    exit 1
  fi
done
curl -sf -o /dev/null http://localhost:11434/api/tags || say "주의: Ollama가 꺼져 있어요. LLM·임베딩 호출이 실패합니다 (ollama serve)"

# 1. Postgres
say "Postgres 시작"
docker compose -f "$ROOT/docker-compose.yml" up -d --wait postgres > /dev/null || { say "Postgres를 띄우지 못했어요"; exit 1; }

# 2. 의존성 (바뀐 게 없으면 금방 끝난다)
(cd "$ROOT/ai-server" && uv sync -q)
[ -d "$ROOT/frontend/node_modules" ] || (cd "$ROOT/frontend" && npm install --silent)

# 3. 세 서비스
run ai ai-server uv run uvicorn app.main:app --reload --port 8000
run api backend ./gradlew bootRun --console=plain
run web frontend npm run dev -- --strictPort

wait_for ai http://localhost:8000/health 60
wait_for api http://localhost:8080/actuator/health 180 && \
  run build backend ./gradlew -t classes -q --console=plain  # bootRun이 뜬 뒤에 시작해야 build/ 폴더를 두고 다투지 않는다
wait_for web http://localhost:5173 60

say "준비 끝: http://localhost:5173  (Ctrl+C로 전부 종료)"
wait
