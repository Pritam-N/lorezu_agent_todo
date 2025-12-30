# secret-scout configuration

This repo uses `secret-scout` to prevent accidental commits of secrets (.env files, private keys, tokens, etc.)

## Files

- `config.toml` — scan behavior (max file size, skip dirs, redact)
- `rules.yaml` — repo-specific policy overrides and custom rules

## Typical usage

Local:
```bash
secret-scout scan-path .
```

CI:
```bash
secret-scout scan-path . --fail
```

## Notes
- Built-in rule pack is always loaded (default). rules.yaml can override by reusing the same id.
- Keep redact=true in CI to avoid printing secrets in logs.
