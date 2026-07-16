# Gate Namba One

Автономный FastAPI-сервис интеграции с Merchant Web API Namba One.

Сервис реализует методы:

- `sale_without_card` — создание одноразовой платёжной ссылки;
- `status` — получение статуса платежа;
- `invoice_notification` — обработка webhook `PAYMENT_ORDER`;
- `refund` — инициация возврата;
- `refund_status` — получение статуса возврата.

Закрытые зависимости исходного cookiecutter-шаблона (`gate_lib`, `utils`, `cds_client`, `sbank_client`) заменены локальными моделями, HTTP-клиентом и обработчиками ошибок.

## Архитектура

```text
FastAPI routes
      |
      v
GateNambaOne service
      |
      v
NambaOneClient
      |
      v
Merchant Web API Namba One
```

Разделение ответственности:

- `src/api/` — HTTP-маршруты и зависимости FastAPI;
- `src/gate_nambaone/gate_nambaone.py` — бизнес-логика интеграции;
- `src/provider_client.py` — подпись и HTTP-взаимодействие с Namba One;
- `src/models.py` — входные и выходные Pydantic-модели;
- `src/terminal_data.py` — настройки конкретного терминала;
- `src/const.py` — внутренние статусы и их сопоставление;
- `src/tests/` — модульные и API-тесты.

## Поддерживаемые маршруты

| Метод | Маршрут | Назначение |
|---|---|---|
| `GET` | `/v2/ping` | Проверка доступности сервиса |
| `POST` | `/v2/sale_without_card` | Создание одноразовой платёжной ссылки |
| `POST` | `/v2/status` | Получение статуса платежа |
| `POST` | `/v2/refund` | Инициация возврата |
| `POST` | `/v2/refund_status` | Получение статуса возврата |
| `POST` | `/notifications/invoice` | Приём webhook платежа |

Swagger UI доступен по адресу `/api/openapi`.

## Подпись Namba One

Исходящие запросы подписываются согласно документации Namba One:

```text
message = request_uri + exact_json_body + salt
signature = Base64(HMAC-SHA512(secret, message))
```

Заголовки:

```text
x-merchant-api-salt
x-merchant-api-signature
```

Для `GET`-запросов тело в строке подписи является пустой строкой.

JSON сериализуется один раз, после чего одна и та же строка используется и для подписи, и как фактическое тело HTTP-запроса. Это исключает расхождение подписи из-за пробелов или порядка сериализации.

## Денежные суммы

Внутренний API принимает суммы в основных единицах валюты:

```text
10.50 KGS
```

Namba One получает сумму в тыйынах:

```text
1050
```

Интеграция поддерживает валюту `KGS`.

## Локальный запуск

Требуется Python 3.12 или новее.

Создать виртуальное окружение:

```powershell
py -m venv .venv
```

Установить зависимости:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" httpx pydantic pydantic-settings python-multipart pytest pytest-asyncio pytest-httpx ruff
```

Запустить сервис:

```powershell
.\.venv\Scripts\python.exe src\main.py
```

Проверка:

```text
http://localhost:8000/v2/ping
http://localhost:8000/api/openapi
```

## Запуск через Docker Compose

Сервис собирается и запускается без GitLab-токенов и других ручных действий:

```bash
docker compose up --build
```

После запуска:

```text
http://localhost:8000/v2/ping
http://localhost:8000/api/openapi
```

Для реального обращения к Namba One передаются настройки терминала во входном запросе. Для проверки подписи входящего webhook используются переменные окружения:

```dotenv
NAMBAONE_BASE_URL=https://merchant-api.example
NAMBAONE_MERCHANT_ID=merchant-account-guid
NAMBAONE_SECRET=merchant-secret
```

## Тесты

Запуск всех тестов:

```powershell
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m pytest -v
```

Проверяемые сценарии для методов интеграции:

- успешный ответ;
- отказ провайдера;
- невалидный входящий запрос;
- невалидный JSON провайдера;
- пустой ответ провайдера;
- таймаут;
- преобразование статусов;
- преобразование денежных сумм;
- формирование HMAC-SHA512/Base64-подписи;
- обработка успешного и неуспешного webhook.

Проверка стиля:

```powershell
.\.venv\Scripts\python.exe -m ruff check src
```

## Конфигурация терминала

Пример `terminal_data`:

```json
{
  "provider_base_url": "https://merchant-api.example",
  "merchant_account_guid": "159e7e3b-94e1-48c7-bec5-952949f7935f",
  "secret": "merchant-secret",
  "webhook_url": "https://merchant.example/notifications/invoice",
  "refund_webhook_url": "https://merchant.example/notifications/refund",
  "merchant_employee_guid": null,
  "acceptor_merchant_account_guid": null,
  "acceptor_merchant_account_token": null
}
```

## Пример создания платежа

```json
{
  "invoice_id": "invoice-1001",
  "amount": "10.50",
  "currency_code": "KGS",
  "finish_url": "https://merchant.example/success",
  "description": "Order invoice-1001",
  "terminal_data": {
    "provider_base_url": "https://merchant-api.example",
    "merchant_account_guid": "159e7e3b-94e1-48c7-bec5-952949f7935f",
    "secret": "merchant-secret",
    "webhook_url": "https://merchant.example/notifications/invoice"
  }
}
```

## Обработка ошибок

Ошибки Namba One переводятся в стабильный внутренний формат:

```json
{
  "status": "failed",
  "code": "PAYMENT_LINK_EXTERNAL_ID_DUPLICATE_EXCEPTION",
  "message": "External ID already exists"
}
```

Таймауты, сетевые ошибки, пустые ответы и невалидный JSON обрабатываются отдельно. Исключения провайдера не приводят к падению FastAPI-сервиса.

## Особенность документации статуса

В заголовке метода получения платежа по `externalId` указан маршрут:

```text
/public/merchant/payment/v1/{merchantAccountGuid}/one-time/{extId}
```

В одном из примеров документации при этом приведён маршрут `/static/order/{guid}`. Реализация использует маршрут из формального описания метода получения по `externalId`, поскольку именно этот контракт соответствует внутреннему методу `status`. Путь вынесен в `TerminalData` и может быть изменён конфигурацией без изменения бизнес-логики.