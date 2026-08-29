# Generated OpenAI REST surface

`codexloop api …` is a **generated** 1:1 CLI over the installed `openai`
Python SDK resource tree. Commands are discovered by walking
`cached_property` descriptors on resource classes — no live client and no
credentials are required to render `--help`.

## Usage

```bash
codexloop api --help
codexloop api models list --help
codexloop api chat completions create --json '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
```

### Common options

| Option | Meaning |
|---|---|
| `--provider openai\|azure\|custom` | Select the SDK client class |
| `--base-url URL` | Override the API base URL |
| `--json '{…}'` | Inline JSON object merged into the call kwargs |
| `--json-file PATH` | JSON file; contents may start with `@/other/path` |
| `--raw` | Use `with_raw_response` |
| `--stream` | Use `with_streaming_response` |
| `--max-items N` | Auto-paginate list endpoints up to N items |

Scalar SDK parameters (strings, ints, floats, bools) are also exposed as
typed `--kebab-case` options. Nested TypedDict bodies stay in `--json`.

## Drift gate

`tests/infrastructure/api/test_drift.py` asserts:

1. Every discovered SDK method has a registered CLI command.
2. The discovered method set matches the committed
   `api_baseline.json` (additions *and* removals fail CI).
3. Local helpers (`parse` / `stream` / `webhooks.unwrap` / …) are
   individually enumerated — no silent omissions.

After upgrading `openai`, regenerate the baseline only when the new surface
is intentional:

```bash
python -c "from codexloop.infrastructure.api.introspect import *; ..."  # or re-run the M4 freeze script
```

## Webhook signature verification

`codexloop api webhooks unwrap` and `codexloop api webhooks verify-signature`
mirror the OpenAI SDK's local `webhooks` helper — there is no `webhooks`
HTTP endpoint; these validate and parse webhook deliveries you already
received (e.g. from a small HTTP server you run), using the signing secret
from your OpenAI webhook configuration.

Both need the raw request body and the signature-bearing headers
(`webhook-id`, `webhook-timestamp`, `webhook-signature`) exactly as
received — re-serializing the body first will change the payload and break
verification.

```bash
codexloop api webhooks verify-signature \
  --payload "$(cat request-body.json)" \
  --headers '{"webhook-id":"...","webhook-timestamp":"...","webhook-signature":"..."}' \
  --secret "$OPENAI_WEBHOOK_SECRET"
# Raises / exits 2 on an invalid signature; prints nothing on success.

codexloop api webhooks unwrap \
  --payload "$(cat request-body.json)" \
  --headers '{"webhook-id":"...","webhook-timestamp":"...","webhook-signature":"..."}' \
  --secret "$OPENAI_WEBHOOK_SECRET"
# Verifies the signature, then prints the parsed, typed webhook event.
```

`--secret` defaults to the `OPENAI_WEBHOOK_SECRET` environment variable when
omitted, same as the underlying SDK helper. Like every other leaf command,
both accept `--json`/`--json-file` as an alternative to individual flags.

## Providers

- **openai** — first-party `OpenAI` client (`OPENAI_API_KEY`).
- **azure** — `AzureOpenAI` (`AZURE_OPENAI_*` / `OPENAI_API_VERSION`).
- **custom** — `OpenAI` with `--base-url` or `OPENAI_BASE_URL`.

The binder always reflects the **class tree** of the selected client. Today
Azure inherits the full OpenAI resource tree; if a future client exposes a
smaller surface, only that surface is mounted.
