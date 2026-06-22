# Authentication Module

JWT-based authentication with database-backed refresh tokens.

## Design

- **Password hashing**: bcrypt via `passlib`. Plaintext passwords are never
  stored; `User.hashed_password` holds the bcrypt hash only.
- **Access tokens**: short-lived JWTs (default 30 min, `ACCESS_TOKEN_EXPIRE_MINUTES`),
  signed with HS256 using `SECRET_KEY`. Stateless — not stored in the DB.
- **Refresh tokens**: longer-lived JWTs (default 30 days,
  `REFRESH_TOKEN_EXPIRE_DAYS`). Each issued refresh token is persisted in the
  `refresh_tokens` table, keyed by its `jti` (JWT ID claim), along with a
  SHA-256 hash of the raw token and an `expires_at`/`revoked` flag. The raw
  token itself is never stored, so a database leak alone can't be used to
  forge valid sessions.
- **Rotation**: every call to `/auth/refresh` revokes the refresh token used
  and issues a brand new access/refresh pair. This limits the blast radius
  of a leaked refresh token to a single use.
- **Logout**: `/auth/logout` revokes the given refresh token in the DB. The
  paired access token remains valid until it naturally expires (it's
  stateless by design) — for true immediate revocation of access tokens
  you'd add a deny-list, which is out of scope here.
- **Uniqueness**: `users.email` has a DB-level `UNIQUE` constraint (not just
  an app-level check), so concurrent registration attempts can't create
  duplicate accounts. Violations surface as `409 Conflict`.

## Data model

```
users
├── id (UUID, PK)
├── email (unique, indexed)
├── hashed_password
├── full_name (nullable)
├── is_active
├── is_superuser
├── created_at / updated_at

refresh_tokens
├── id (UUID, PK)
├── user_id (FK -> users.id, ON DELETE CASCADE)
├── jti (unique, indexed)        -- JWT ID claim
├── token_hash                   -- SHA-256 of the raw refresh JWT
├── revoked
├── expires_at
├── created_at
```

## Endpoints (under `/api/v1/auth`)

| Method | Path        | Auth required | Description |
|--------|-------------|----------------|--------------|
| GET    | `/health`   | No  | Router liveness check |
| POST   | `/register` | No  | Create a new user. `409` if email is taken. |
| POST   | `/login`    | No  | Exchange email+password for an access/refresh token pair. `401` on bad credentials. |
| POST   | `/refresh`  | No (refresh token in body) | Rotate a refresh token for a new pair. `401` if invalid/expired/revoked. |
| POST   | `/logout`   | No (refresh token in body) | Revoke a refresh token. `204` on success. |
| GET    | `/me`       | Yes (Bearer access token) | Return the authenticated user. |

### Example flow

```bash
# Register
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"S3curePassw0rd!","full_name":"Alice"}'

# Login
curl -X POST localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"S3curePassw0rd!"}'
# -> {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

# Call a protected endpoint
curl localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh
curl -X POST localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Logout
curl -X POST localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Using `get_current_user` in other routers

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/notes")
async def list_notes(current_user: User = Depends(get_current_user)):
    ...
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | HS256 signing key. **Must** be set to a long random value in any non-local environment. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime. |

## Known limitations / next steps

- No email verification or password-reset flow.
- No rate limiting on `/login` or `/register` (recommend adding via Redis,
  e.g. a sliding-window counter, since Redis is already wired up).
- Access tokens can't be revoked before they expire (stateless by design);
  add a Redis-backed deny-list keyed by `jti` if immediate revocation is
  required.
- No role-based authorization beyond the `is_superuser` flag and the
  `get_current_active_superuser` dependency stub.
