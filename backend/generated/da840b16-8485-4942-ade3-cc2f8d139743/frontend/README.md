# CRM Frontend

This is a Vite + React + TypeScript frontend for the CRM application.

## Development

### Prerequisites
- Node.js 16+ 
- npm

### Setup
```bash
npm install
```

### Start Development Server
```bash
npm run dev -- --port 3000
```

The app will be available at http://localhost:3000

### SBH Integration
This frontend is designed to work with System Builder Hub (SBH):

- **Local Development**: Run `npm run dev -- --port 3000` manually
- **SBH Auto-start**: Use `POST /serve/<build_id>/start-frontend` to auto-start
- **SBH Proxy**: Access via `http://localhost:5001/serve/<build_id>/`

### Build
```bash
npm run build
```

### Preview
```bash
npm run preview
```

## Tech Stack
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS + shadcn/ui
- **Icons**: Lucide React
- **Routing**: React Router DOM
