# Venture OS — HTTP API Smoke

This document outlines a smoke checklist to verify that the Venture OS HTTP API works end-to-end with the in-memory repository. The expected server URL is [http://localhost:5001](http://localhost:5001), and it uses the in-memory repository inside `venture_os/http/api.py`.

## Headers Used in Examples

- **X-Tenant-ID**: `demo_tenant` (required)
- **X-User-Role**: `admin`|`viewer` (optional; admin required for seeding)

## 1) Seed Demo Data (Admin-Only)

Use the following curl command to seed demo data:

```bash
curl -sS -X POST http://localhost:5001/api/venture_os/seed/demo \
  -H 'X-Tenant-ID: demo_tenant' \
  -H 'X-User-Role: admin' | jq
```

### Expected Shape (Example JSON Snippet)

```json
{ "ok": true, "seeded": true, "ids": { "company": "c_1", "contact": "p_1", "deal": "d_1" } }
```

## 2) List Entities

To list entities, use:

```bash
curl -sS 'http://localhost:5001/api/venture_os/entities?limit=100' \
  -H 'X-Tenant-ID: demo_tenant' | jq '.items | length, .[0]'
```

Note that “Acme Corporation” should appear after seeding.

## 3) Search Entities (Text)

To search for entities by text, use:

```bash
curl -sS 'http://localhost:5001/api/venture_os/search?q=acme' \
  -H 'X-Tenant-ID: demo_tenant' | jq '.items | map(.name)'
```

## 4) Filter by Kind

To filter entities by kind, use:

```bash
curl -sS 'http://localhost:5001/api/venture_os/entities?kind=deal' \
  -H 'X-Tenant-ID: demo_tenant' | jq '.items | map(.name)'
```

## 5) Company Summary

To get a summary of a company, use:

```bash
curl -sS 'http://localhost:5001/api/venture_os/companies/c_1/summary' \
  -H 'X-Tenant-ID: demo_tenant' | jq
```

### Expected Keys

- `company`
- `contacts[]`
- `deals[]`

### Viewer vs Admin Note

Without `X-User-Role: admin`, you are treated as a viewer; seeding requires admin, but reads are fine as a viewer.

## Troubleshooting

- **401/403 or {error:"forbidden"}**: Ensure `X-User-Role: admin` for seed; viewer is read-only.
- **400 “missing tenant”**: Add `-H 'X-Tenant-ID: demo_tenant'`.
- **Empty results after seed**: Confirm server restart isn’t resetting in-memory repo; re-run seed.
- **Server not reachable**: Check it’s running on [http://localhost:5001](http://localhost:5001) and that Venture OS blueprint is mounted (log line: “Venture OS API mounted at /api/venture_os”).

## Appendix

One-liner to quickly pretty-print without jq:

```bash
| python -m json.tool
```