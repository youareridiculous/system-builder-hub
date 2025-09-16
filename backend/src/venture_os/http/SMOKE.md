# SMOKE Test Documentation

## Troubleshooting

- If you encounter issues, check the logs for errors.

## Persisting data with JSONL (optional)
Run the server with:

```sh
VOS_STORE=jsonl VOS_STORE_PATH=data/venture_os.jsonl PYTHONPATH=src python -m src.server
```
