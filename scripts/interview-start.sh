#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/workspaces/repopilot"
cd "$ROOT"

echo
echo "=========================================="
echo " RepoPilot LOCAL Interview Startup"
echo "=========================================="
echo

fail() {
    echo
    echo "❌ $1"
    exit 1
}

require_env() {
    local name="$1"
    [[ -n "${!name:-}" ]] || fail "Missing Codespaces secret: $name"
}

echo "[1/9] Checking Codespaces secrets..."

for var in \
    POSTGRES_PASSWORD \
    DJANGO_SECRET_KEY \
    AI_API_KEY \
    E2B_API_KEY \
    E2B_TEMPLATE \
    REPOPILOT_APP_ID \
    REPOPILOT_INSTALLATION_ID \
    REPOPILOT_PRIVATE_KEY
do
    require_env "$var"
done

echo "      Secrets: OK"


echo "[2/9] Checking Docker forwarding..."

if sudo iptables-legacy -S FORWARD 2>/dev/null | \
   head -1 | grep -q -- '-P FORWARD DROP'; then
    sudo iptables-legacy -P FORWARD ACCEPT
fi

echo "      Docker forwarding: OK"


echo "[3/9] Preparing LOCAL backend configuration..."

python3 - <<'PY'
from pathlib import Path
import os

path = Path("/workspaces/repopilot/backend/.env")

if not path.exists():
    example = Path("/workspaces/repopilot/backend/.env.example")
    if example.exists():
        path.write_text(example.read_text())
    else:
        path.write_text("")

values = {
    "DJANGO_DEBUG": "true",
    "DJANGO_SECRET_KEY": os.environ["DJANGO_SECRET_KEY"].strip(),

    "DJANGO_ALLOWED_HOSTS":
        "localhost,127.0.0.1",

    "FRONTEND_ORIGINS":
        "http://127.0.0.1:3000",

    "LIVE_EXECUTION_ENABLED": "true",

    "AI_API_KEY":
        os.environ["AI_API_KEY"].strip(),

    "E2B_API_KEY":
        os.environ["E2B_API_KEY"].strip(),

    "E2B_TEMPLATE":
        os.environ["E2B_TEMPLATE"].strip(),

    "GITHUB_APP_ID":
        os.environ["REPOPILOT_APP_ID"].strip(),

    "GITHUB_INSTALLATION_ID":
        os.environ["REPOPILOT_INSTALLATION_ID"].strip(),

    "GITHUB_APP_PRIVATE_KEY": (
        os.environ["REPOPILOT_PRIVATE_KEY"]
        .strip()
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\n")
    ),

    "PUBLISH_ENABLED": "true",

    "TRUST_PROXY_HTTPS": "false",
    "SECURE_HSTS_SECONDS": "0",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": "false",
    "SECURE_HSTS_PRELOAD": "false",
}

old = path.read_text().splitlines()
new = []
seen = set()

for line in old:
    if "=" in line:
        key = line.split("=", 1)[0]

        if key in values:
            value = values[key]

            if key == "GITHUB_APP_PRIVATE_KEY":
                new.append(f'{key}="{value}"')
            else:
                new.append(f"{key}={value}")

            seen.add(key)
            continue

    new.append(line)

for key, value in values.items():
    if key not in seen:
        if key == "GITHUB_APP_PRIVATE_KEY":
            new.append(f'{key}="{value}"')
        else:
            new.append(f"{key}={value}")

path.write_text("\n".join(new) + "\n")
PY

echo "      Backend local mode: OK"


echo "[4/9] Preparing LOCAL frontend configuration..."

cat > frontend/.env.local <<'EOF2'
NEXT_PUBLIC_PORTFOLIO_PREVIEW=false
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
EOF2

echo "      Frontend API: http://127.0.0.1:8000/api"


echo "[5/9] Starting backend stack..."

echo "      Building current API/worker images..."

if ! docker compose build api worker; then
    echo "      Initial Docker build failed. Restarting Docker and retrying..."
    sudo service docker restart >/dev/null 2>&1 || true
    sleep 2
    sudo iptables-legacy -P FORWARD ACCEPT 2>/dev/null || true
    docker compose build api worker
fi

echo "      Backend images: current"

start_stack() {
    docker compose up -d database redis api worker
}

if ! start_stack; then

    echo
    echo "      Docker container state problem detected."
    echo "      Recreating containers WITHOUT deleting volumes..."

    for c in \
        repopilot-api-1 \
        repopilot-worker-1 \
        repopilot-redis-1 \
        repopilot-database-1
    do
        docker rm -f "$c" >/dev/null 2>&1 || true
    done

    docker network rm repopilot_default \
        >/dev/null 2>&1 || true

    if ! docker compose up -d \
        --force-recreate \
        --no-build \
        database redis api worker
    then

        echo
        echo "      Existing backend images unusable."
        echo "      Rebuilding API and worker..."

        docker compose build api worker

        docker compose up -d \
            --force-recreate \
            database redis api worker
    fi
fi

# Reload the interview .env into these two services.
docker compose up -d \
    --force-recreate \
    api worker

echo "      Backend containers: started"

echo "      Applying database migrations..."
docker compose exec -T api python manage.py migrate --noinput
echo "      Database migrations: OK"


echo "[6/9] Waiting for Django API..."

API_OK=false

for i in {1..60}; do
    if curl -fsS \
        http://127.0.0.1:8000/health/ \
        >/dev/null 2>&1
    then
        API_OK=true
        break
    fi

    sleep 1
done

if [[ "$API_OK" != "true" ]]; then
    docker compose ps
    docker compose logs --tail=80 api
    fail "Django API did not become healthy."
fi

echo "      Django API: OK"


echo "[7/9] Building interview frontend..."

cd "$ROOT/frontend"

if [[ ! -d node_modules ]]; then
    echo "      Installing frontend dependencies..."
    npm ci
fi

npm run build

cd "$ROOT"

echo "      Frontend build: OK"


echo "[8/9] Starting static frontend..."

fuser -k 3000/tcp >/dev/null 2>&1 || true

rm -f /tmp/repopilot-frontend.pid

nohup python3 -m http.server 3000 \
    --bind 0.0.0.0 \
    --directory "$ROOT/frontend/out" \
    >/tmp/repopilot-frontend.log 2>&1 &

echo $! >/tmp/repopilot-frontend.pid

FRONTEND_OK=false

for i in {1..30}; do
    if curl -fsS \
        http://127.0.0.1:3000/workspace/ \
        >/dev/null 2>&1
    then
        FRONTEND_OK=true
        break
    fi

    sleep 1
done

if [[ "$FRONTEND_OK" != "true" ]]; then
    cat /tmp/repopilot-frontend.log || true
    fail "Frontend did not become healthy."
fi

echo "      Frontend: OK"


echo "[9/9] Final verification..."

docker compose exec -T api python manage.py shell -c "
from django.conf import settings
from coding_tasks.models import CodingTask
from repositories.models import Repository

print('LIVE:', settings.LIVE_EXECUTION_ENABLED)
print('PUBLISH:', settings.PUBLISH_ENABLED)
print('AI:', 'SET' if settings.AI_API_KEY else 'MISSING')
print('E2B:', 'SET' if settings.E2B_API_KEY else 'MISSING')
print('GITHUB APP:', 'SET' if settings.GITHUB_APP_ID else 'MISSING')
print('TASKS:', CodingTask.objects.count())
print('REPOSITORIES:', Repository.objects.count())
" 2>/dev/null

# Public Codespaces forwarding is not required.
if [[ -n "${CODESPACE_NAME:-}" ]]; then
    gh codespace ports visibility \
        3000:private \
        8000:private \
        -c "$CODESPACE_NAME" \
        >/dev/null 2>&1 || true
fi

echo
echo "=========================================="
echo " RepoPilot LOCAL MODE READY"
echo "=========================================="
echo
echo "Codespace services:"
docker compose ps --format "table {{.Service}}\t{{.Status}}"
echo
echo "Next step on WINDOWS:"
echo
echo "gh codespace ports forward 3000:3000 8000:8000 -c ${CODESPACE_NAME:-YOUR_CODESPACE}"
echo
echo "Then open:"
echo
echo "http://127.0.0.1:3000/workspace/"
echo
echo "Keep the Windows tunnel terminal open."
echo
