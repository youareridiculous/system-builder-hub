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

### GitHub Pages

1) Push the `frontend/` folder to a GitHub repository.
2) In repo Settings → Pages, set Source to `Deploy from a branch`, and select branch `main` (or your default) and folder `/ (root)` if the repo only contains `frontend`, or select `/docs` and place the files there.
3) Add `404.html` (already included) for SPA routing.
4) Set `spaBasePath` in `config.json` to your Pages subpath:

```json
{"spaBasePath":"/YOUR_REPO_NAME"}
```

5) Access the app at `https://YOUR_USER.github.io/YOUR_REPO_NAME/`.

## License
MIT