# Data Admin Frontend

A lightweight, config-driven admin UI for any REST-ish backend. No build step.

## Features
- Config-driven resources and forms via `config.json`
- List view with search, pagination, and sorting
- Create/Edit/Delete with basic validation
- Optional Bearer token auth via localStorage

## Getting Started

1) Update `config.json` with your backend base URL and resources.

2) Serve the `frontend/` directory with any static server. Examples:

```bash
# Python
python3 -m http.server 8080 --directory frontend

# Node
npx http-server frontend -p 8080 --cors
```

3) Open `http://localhost:8080` in your browser.

## Configuration

`frontend/config.json` example:

```json
{
  "baseUrl": "http://localhost:3000",
  "auth": { "type": "bearer", "localStorageKey": "data_admin_token" },
  "resources": [
    {
      "name": "users",
      "label": "Users",
      "idKey": "id",
      "columns": [ { "key": "id" }, { "key": "name" }, { "key": "email" } ],
      "fields": [ { "name": "name", "required": true }, { "name": "email", "required": true } ]
    }
  ]
}
```

- `baseUrl`: API root. Ex: `GET /users`, `POST /users`, `GET /users/:id`, `PUT /users/:id`, `DELETE /users/:id`.
- `auth.type`: Set to `bearer` to send `Authorization: Bearer <token>`.
- `auth.localStorageKey`: Storage key for token.
- `resources[*].columns`: Columns for list table.
- `resources[*].fields`: Form fields; types: `text|number|date|select|textarea`.

## API Response Shapes

- List endpoint: `{ items: any[], total: number }` or raw `any[]`.
- Item endpoints: JSON object.

## Customization

- Styles: `styles.css`
- Routes: `router.js`, `app.js`
- Components: `components/`

## Deploy

Serve statically (S3+CloudFront, Vercel static, Netlify, Nginx). Ensure CORS allows your origin.

## License
MIT