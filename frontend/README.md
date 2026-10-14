# Enterprise Knowledge AI - Frontend

The single-page React application for Enterprise Knowledge AI, providing:
- Evidence-grounded chat with sentence-level citation chip navigation (`[S1]`, `[S2]`)
- Dynamic citation inspector drawer showing chunk excerpts, document metadata, and page numbers
- Document management sidebar with multi-select search scoping, upload modal, and chunk preview
- Tenant isolation and Supabase authentication with demo mode fallback
- Graceful UI states for abstention, rate limits, daily quotas, cold starts, and errors

## Tech Stack
- **Framework:** React 18 + TypeScript + Vite
- **Styling:** Tailwind CSS + Lucide React Icons
- **Testing:** Vitest
- **Linting:** ESLint 9 + TypeScript ESLint

## Development Commands
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run type-checking
npx tsc -b

# Run test suite
npm test

# Build for production
npm run build
```
