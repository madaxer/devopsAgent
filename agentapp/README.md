# Agentapp Step 3

Minimal FastAPI service that demonstrates the core action flow:
- receive typed action request,
- set status to `running`,
- execute action asynchronously,
- return status by `request_id`,
- enforce a binary policy gate loaded from YAML.

Current execution behavior:
- `vm.list_path` is implemented as a real read-only action,
- other actions are still mock responses.

Current policy behavior:
- policy is read from `config/policy.yaml`,
- app auto-reloads policy when file changes,
- denied actions return `403` with policy decision metadata,
- runtime environment is set at startup via `AGENT_ENV`.

## Run

From `agentapp/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
AGENT_ENV=dev uvicorn app.main:app --reload --port 8080
```

`AGENT_ENV` must be one of: `dev`, `stage`, `prod`.

## Policy file

Location:

```text
agentapp/config/policy.yaml
```

Structure:

```yaml
version: 1
environments:
  dev:
    allow:
      - "*"
  stage:
    allow:
      - "*"
  prod:
    allow:
      - docker.logs
      - vm.read_file
```

Notes:
- `allow` controls which actions are enabled per environment.
- You can also use `deny` list per environment.
- Changes are picked up automatically on next request; restart is not required.
- Policy status endpoint does not expose local file paths.

## Try it

Health:

```bash
curl -s http://127.0.0.1:8080/v1/health
```

Policy status:

```bash
curl -s http://127.0.0.1:8080/v1/policy/status
```

Example response:

```json
{
  "loaded": true,
  "version": 1,
  "source": "local_yaml",
  "agent_environment": "dev",
  "last_reload_at": "2026-02-16T12:10:00+00:00",
  "error": null
}
```

Execute mock action:

```bash
curl -s -X POST http://127.0.0.1:8080/v1/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "11111111-1111-1111-1111-111111111111",
    "requested_at": "2026-02-15T10:00:00Z",
    "requested_by": "you@example.com",
    "environment": "dev",
    "action": "docker.logs",
    "target": {"container": "api"},
    "params": {"tail": 100}
  }'
```

Execute real `vm.list_path` action:

```bash
curl -s -X POST http://127.0.0.1:8080/v1/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "44444444-4444-4444-4444-444444444444",
    "requested_at": "2026-02-15T10:00:00Z",
    "requested_by": "you@example.com",
    "environment": "dev",
    "action": "vm.list_path",
    "target": {"host": "localhost"},
    "params": {"path": "/var/log"}
  }'
```

Check `vm.list_path` result:

```bash
curl -s http://127.0.0.1:8080/v1/actions/44444444-4444-4444-4444-444444444444
```

The result `summary` contains listed entry count and a preview.

Check status:

```bash
curl -s http://127.0.0.1:8080/v1/actions/11111111-1111-1111-1111-111111111111
```

Policy deny example (write action in prod):

```bash
curl -i -X POST http://127.0.0.1:8080/v1/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "33333333-3333-3333-3333-333333333333",
    "requested_at": "2026-02-15T10:00:00Z",
    "requested_by": "you@example.com",
    "environment": "prod",
    "action": "service.restart",
    "target": {"service": "api"},
    "params": {}
  }'
```

Expected response:
- HTTP `403 Forbidden`
- decision metadata in response body

Enable a write action in prod (example):

```yaml
environments:
  prod:
    allow:
      - service.restart
```

After saving `policy.yaml`, call the endpoint again with a new `request_id`.

## Environment enforcement

The request payload `environment` must match `AGENT_ENV`.

Example mismatch response:

```json
{
  "detail": {
    "code": "environment_mismatch",
    "expected_environment": "dev",
    "provided_environment": "prod"
  }
}
```
