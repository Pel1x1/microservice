# ПР9, задание 3: user-service в Yandex Cloud Serverless Containers

Конвейер уже содержит работы `push-yc` и `deploy-yc` (`.github/workflows/ci-cd.yml`). Пока не
задана переменная репозитория `YC_ENABLED=true`, они пропускаются. Ниже — что сделать в облаке,
чтобы их включить.

**Почему user-service.** Бессерверный контейнер выключается, когда нет запросов, поэтому
в нём не могут жить постоянные подписчики RabbitMQ (inventory, order, payment, delivery, catalog).
user-service только отвечает на HTTP и публикует события, поэтому подходит. Данные хранятся
во внешней PostgreSQL, сам контейнер ничего не хранит.

## 1. Облако

1. **Container Registry** → реестр группы `ikbo-65-23` (если его нет — создать). ID реестра → секрет `YC_REGISTRY_ID`.
2. **Сервисные аккаунты** → `sa-cicd` → «Создать новый ключ» → «Авторизованный ключ», в описании —
   фамилия. Скачанный JSON целиком → секрет `YC_KEYS`. ID аккаунта → `YC_SA_ID`.
3. **Managed Service for PostgreSQL** → кластер (самый маленький класс, публичный доступ к хосту),
   база `automarket_users`. Строка подключения → секрет `ENV_POSTGRES_URL`:
   `postgresql://user:password@rc1a-xxxx.mdb.yandexcloud.net:6432/automarket_users?sslmode=require`
4. Брокер: учебный RabbitMQ курса → секрет `ENV_AMQP_URL` = `amqp://guest:guest123@51.250.26.59:5672/`.
5. **Serverless Containers** → «Создать контейнер» с именем `kiselev-user-service`
   (имя начинается с фамилии) → секрет `YC_CONTAINER_NAME`. ID каталога → `YC_FOLDER_ID`.

## 2. GitHub

```bash
gh secret set YC_KEYS < authorized_key.json
gh secret set YC_REGISTRY_ID --body crp...
gh secret set YC_FOLDER_ID --body b1g...
gh secret set YC_SA_ID --body aje...
gh secret set YC_CONTAINER_NAME --body kiselev-user-service
gh secret set ENV_POSTGRES_URL --body 'postgresql://...'
gh secret set ENV_AMQP_URL --body 'amqp://guest:guest123@51.250.26.59:5672/'
gh variable set YC_ENABLED --body true
```

После следующего push в `main` конвейер:
1. `push-yc` — загружает протестированный образ в `cr.yandex/<YC_REGISTRY_ID>/user-service:<sha>`;
2. `deploy-yc` — создаёт ревизию контейнера (1 vCPU, 20 %, 512 МБ, до 4 одновременных запросов,
   таймаут 30 с, переменные `POSTGRES_URL`, `AMQP_URL`), делает контейнер публичным и проверяет
   `https://<container_id>.containers.yandexcloud.net/health`.

Сервис слушает порт из переменной `PORT` (Serverless Containers передаёт 8080), логи пишет в stdout
в JSON — Cloud Logging разбирает поля `level` и `message` автоматически.

## 3. Локальная репетиция (без доступа к облаку)

```bash
docker compose up -d                          # нужен RabbitMQ
bash deploy/yandex-cloud/yc_local_deploy.sh   # реестр → образ → «ревизия» → smoke test
bash deploy/yandex-cloud/yc_local_deploy.sh --down
```

Скрипт выполняет те же шаги, что и `push-yc`/`deploy-yc`, но вместо облака использует локальный
реестр `registry:2`, отдельный контейнер PostgreSQL вместо Managed PostgreSQL и `docker run`
с теми же ограничениями ресурсов и `PORT=8080`.
