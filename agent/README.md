# Service Startup

## Requirements

- Python `>=3.11`
- `uv` installed

## deploy
uv sync

## Start in Development

Use this command:

```bash
uv run python main.py
```

Behavior:

- Reads `.env` automatically
- `APP_ENV=dev` (default) enables auto reload
- Default address: `0.0.0.0:8000`

## Start in Production

修改`.env` APP_ENV=prod 
```bash
uv run python main.py
```

## Environment Variables

- `APP_ENV`: `dev` / `prod` (default: `dev`)
- `HOST`: default `0.0.0.0`
- `PORT`: default `8000`

## 运行
curl -s http://127.0.0.1:8000/list_agents | python -m json.tool
curl -s -X POST http://127.0.0.1:8000/run_agent -H "Content-Type: application/json" -d '{"agent": "ops-agent","message": "你好，用一句话介绍你自己"}'