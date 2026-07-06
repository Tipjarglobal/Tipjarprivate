# Auth Testing (TipJar)

Auth uses JWT Bearer tokens (returned in response body, stored client-side in localStorage). No httpOnly cookies.

## Endpoints
- POST /api/auth/register {email, password, username, timezone, language} -> {token, user}
- POST /api/auth/login {email, password} -> {token, user}
- GET /api/auth/me (Authorization: Bearer <token>) -> {user}
- PUT /api/auth/profile {username?, timezone?, language?} (auth) -> {user}

## Admin
Seeded on startup: admin@tipjar.com / TipJarAdmin2026! (role=admin, username TipJarAdmin)

## curl
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" -d '{"email":"t@t.com","password":"secret1","username":"tester","timezone":"UTC","language":"en"}'
TOKEN=... ; curl -s "$API/api/auth/me" -H "Authorization: Bearer $TOKEN"
