# envdiff

A tiny, dependency-free CLI that compares two `.env`-style files **by key**,
without ever printing secret values to your terminal, CI logs, or
screen-share.

## Why

Every team eventually needs to answer: "does my local `.env` have every
variable that `.env.example` declares?" or "what changed between staging
and production config?". The naive answer — `diff .env .env.example` — works,
but it dumps raw secret values into your shell history and into CI logs.

`envdiff` parses only the **keys**, tells you what's missing, what's extra,
and which keys have *different* values — masked by default (`<set, 12 chars>`)
so you can safely paste the output into a PR, a Slack message, or a bug
report.

## Install

No dependencies beyond Python 3.9+. Just copy `envdiff.py` into your repo or
`PATH`, or clone this repository.

```bash
git clone <this-repo>
cd envdiff
python3 envdiff.py --help
```

## Usage

```bash
python3 envdiff.py .env.example .env
```

Example output:

```
Comparing .env.example -> .env
========================================

Only in .env.example (1):
  - OPTIONAL_FEATURE_FLAG

Only in .env (1):
  + LOCAL_DEBUG_PORT

Different values (1):
  ~ API_BASE_URL: <set, 23 chars> -> <set, 21 chars>

Identical keys: 4
```

Exit codes (useful in CI / pre-commit hooks):

- `0` — no key differences
- `1` — differences found (missing, extra, or changed keys)
- `2` — usage error (file not found, etc.)

### Flags

- `--show-values` — print actual values instead of masked placeholders.
  Only use this on files that contain no secrets, since the whole point of
  the default mode is to avoid leaking secrets.

## Example: CI guard against missing env vars

```bash
python3 envdiff.py .env.example .env || exit 1
```

## Running the tests

```bash
python3 -m unittest tests/test_envdiff.py -v
```

## License

MIT — see [LICENSE](./LICENSE).

## Support this project

This project is funded through [Drips](https://www.drips.network/), a
protocol for streaming and splitting ERC-20 tokens to open-source
maintainers. See [`FUNDING.json`](./FUNDING.json).
