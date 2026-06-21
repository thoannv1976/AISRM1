# packages/shared

Reserved for cross-app shared artifacts (generated enums/types, OpenAPI client).

In this build the canonical contracts are:
- Backend enums: `apps/api/app/core/enums.py`
- Backend OpenAPI: served at `/api/v1/openapi.json` (generate a typed client here)
- Frontend types: `apps/web/src/lib/types.ts`

To regenerate a typed TS client from the live API:
```bash
npx openapi-typescript http://localhost:8000/api/v1/openapi.json -o packages/shared/api.d.ts
```
