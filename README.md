# Pilota

Basque Pelota results and statistics tracking application.

## Project Structure

- `frontend/` — Angular 18+ application
- `backend/` — API server
- `api/` — Additional API services

## Development

```bash
cd frontend
npm install
npm run dev
```

## Test Mode (Development Only)

⚠️ **WARNING**: Test mode endpoints are for development/testing ONLY. Never enable in production.

To enable test mode, set one of these environment variables:
```bash
TEST_MODE=true
# or
DEV_MODE=true
```

### Available Test Endpoints

#### POST /api/test/purge-database

Drops all database tables and re-runs migrations. Use for clean test resets.

**Rate limiting**: 1 request per minute per IP.

**Example**:
```bash
curl -X POST http://localhost:3000/api/test/purge-database
```

**Response**:
```json
{
  "success": true,
  "message": "Database purged and migrations re-run successfully",
  "warning": "⚠️ This endpoint is for test mode only and will be removed"
}
```

#### GET /api/test/status

Check current test mode status.

```bash
curl http://localhost:3000/api/test/status
```


## Accessibility Guidelines

### Images and Alt Text

All images must include descriptive alt text:

```html
<img [src]="imageUrl" [alt]="imageDescription" />
```

**Rules:**
- Decorative images: use `alt=""` (empty string)
- Informative images: describe the content and purpose
- Avoid "image of" or "picture of" prefixes
- Keep alt text concise but meaningful

### ARIA Labels

- All interactive elements must have accessible names
- Use `aria-label` for icon-only buttons
- Use `aria-describedby` for additional context
- Use `role` attributes where semantic HTML is insufficient

### Focus States

- All interactive elements have visible focus indicators
- Skip link provided for keyboard navigation
- Focus order follows visual layout

### Color Contrast

- Text meets WCAG AA contrast requirements (4.5:1 for normal text)
- Interactive elements have distinct hover/focus states

## UI/UX Improvements Log

See `UI-UX-AUDIT-REPORT.md` for the full audit and implementation status.
