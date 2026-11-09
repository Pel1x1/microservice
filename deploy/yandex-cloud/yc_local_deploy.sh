#!/usr/bin/env bash
# ПР9, задание 3: локальная репетиция развёртывания user-service в Serverless Containers.
#
# Повторяет шаги работ push-yc и deploy-yc из .github/workflows/ci-cd.yml, заменяя облачные
# ресурсы локальными аналогами (доступа к облаку курса на момент выполнения не было):
#
#   Яндекс.Облако                          локально
#   Container Registry  cr.yandex/<id>     registry:2 на localhost:5050
#   Managed PostgreSQL                     контейнер postgres:16 в отдельной сети
#   RabbitMQ по внешнему адресу            брокер из docker compose через host.docker.internal
#   ревизия контейнера (1 vCPU, 20 %,      docker run --cpus 0.2 --memory 512m, PORT=8080,
#     512 МБ, PORT=8080, env из секретов)    переменные окружения как в revision-env
#
# Запуск:  bash deploy/yandex-cloud/yc_local_deploy.sh          (нужен запущенный docker compose up)
# Удаление: bash deploy/yandex-cloud/yc_local_deploy.sh --down
set -euo pipefail
cd "$(dirname "$0")/../.."

REGISTRY=localhost:5050/ikbo-65-23            # аналог cr.yandex/${YC_REGISTRY_ID}
CONTAINER=kiselev-user-service                # имя начинается с фамилии студента (методичка)
NETWORK=yc-local
PORT=8090                                     # аналог https://<id>.containers.yandexcloud.net
TAG=$(git rev-parse HEAD 2>/dev/null || echo local)

if [[ "${1:-}" == "--down" ]]; then
  docker rm -f "$CONTAINER" yc-local-postgres yc-local-registry >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  echo "Локальное окружение Serverless удалено"
  exit 0
fi

step() { printf '\n\033[1m[%s] %s\033[0m\n' "$1" "$2"; }

docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" >/dev/null

step 1/5 "Container Registry: реестр образов группы"
if ! docker ps --format '{{.Names}}' | grep -qx yc-local-registry; then
  docker run -d --name yc-local-registry -p 5050:5000 registry:2.8.3 >/dev/null
  sleep 2
fi
echo "реестр: $REGISTRY"

step 2/5 "build + push: docker-образ user-service с тегом коммита"
docker build --quiet --tag "$REGISTRY/user-service:$TAG" --tag "$REGISTRY/user-service:latest" user-service
docker push --quiet "$REGISTRY/user-service:$TAG"
docker push --quiet "$REGISTRY/user-service:latest"
curl -s "http://localhost:5050/v2/ikbo-65-23/user-service/tags/list"; echo

step 3/5 "Managed PostgreSQL: внешняя БД (адрес передаётся секретом ENV_POSTGRES_URL)"
if ! docker ps --format '{{.Names}}' | grep -qx yc-local-postgres; then
  docker run -d --name yc-local-postgres --network "$NETWORK" -e POSTGRES_PASSWORD=yc-secret postgres:16 >/dev/null
fi
until docker exec yc-local-postgres pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
echo "postgresql://postgres:***@yc-local-postgres:5432/postgres — готова"

step 4/5 "deploy: новая ревизия контейнера $CONTAINER из образа реестра"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker image rm "$REGISTRY/user-service:$TAG" >/dev/null 2>&1 || true   # образ берётся из реестра, как в облаке
docker pull --quiet "$REGISTRY/user-service:$TAG"
docker run -d --name "$CONTAINER" --network "$NETWORK" \
  --add-host host.docker.internal:host-gateway \
  --cpus 0.2 --memory 512m \
  -p "$PORT:8080" \
  -e PORT=8080 \
  -e POSTGRES_URL=postgresql://postgres:yc-secret@yc-local-postgres:5432/postgres \
  -e AMQP_URL=amqp://guest:guest@host.docker.internal:5672/ \
  -e ENVIRONMENT=yandex-cloud-local \
  "$REGISTRY/user-service:$TAG" >/dev/null
docker ps --filter "name=^${CONTAINER}$" --format 'контейнер {{.Names}}  образ {{.Image}}  {{.Status}}'
docker inspect "$CONTAINER" --format 'ресурсы: {{.HostConfig.NanoCpus}} nanoCPU, {{.HostConfig.Memory}} байт памяти'

step 5/5 "smoke test: /health и регистрация пользователя через развёрнутый контейнер"
URL="http://localhost:$PORT"
for _ in $(seq 1 30); do
  curl --fail --silent "$URL/health" && break
  sleep 1                                                   # «холодный старт»
done
echo
EMAIL="yc-$(date +%s)@automarket.ru"
curl --fail --silent -X POST "$URL/api/users" -H 'Content-Type: application/json' \
  -d "{\"email\": \"$EMAIL\", \"name\": \"Покупатель из облака\", \"role\": \"buyer\"}"
echo
echo
echo "Сервис доступен: $URL/docs   (в облаке: https://<container_id>.containers.yandexcloud.net/docs)"
echo "Логи ревизии (JSON, в облаке — Cloud Logging):"
docker logs --tail 3 "$CONTAINER"
