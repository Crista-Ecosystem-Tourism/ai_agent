# API performance smoke

`ops/load_smoke.py` provides a small, repeatable HTTP smoke for an Agent API
instance. It concurrently calls `/health` and `/ready`, reports JSON latency
and status aggregates, and exits non-zero when requests fail. It uses only the
Python standard library and never prints response bodies.

Run it against a controlled local or staging origin after the service reports
ready. Do not put credentials, query strings, or fragments in the URL; the
script rejects them to keep its JSON report safe to share.

```bash
python3 ops/load_smoke.py https://api.staging.example --requests 100 --concurrency 10
```

Set thresholds only after the environment and expected traffic are agreed. The
example below fails if p95 is above 500 ms or more than 1% of requests fail:

```bash
python3 ops/load_smoke.py https://api.staging.example \
  --requests 500 --concurrency 20 --max-p95-ms 500 --max-error-rate 0.01
```

The smoke confirms the API's liveness and readiness endpoints under a bounded
burst. It does not establish production capacity, database saturation limits,
autoscaling behaviour, or user journey performance. Record the JSON output,
service revision, environment, request parameters, and any active background
jobs with the release evidence.
