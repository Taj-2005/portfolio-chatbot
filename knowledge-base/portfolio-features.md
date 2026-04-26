# PRD — Shaik Tajuddin Portfolio (Knowledge Base for RAG)

This document describes **all pages, tabs, sections, and features** in the portfolio web app, including UX behavior, data sources, and backend APIs. It is written as a **RAG-friendly knowledge base** (explicit names, paths, and responsibilities).

---

## Product overview

- **Product name**: Shaik Tajuddin — Software Engineer Portfolio
- **Purpose**: Showcase projects, experience, certifications, skills, and provide multiple ways to contact (book a call, email, message form) plus an on-site chat assistant.
- **Platform**: Web (Next.js App Router)

---

## Tech stack (implementation)

- **Framework**: Next.js (App Router) — `src/app/`
- **Language**: TypeScript / React
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Email**: Nodemailer (server route)
- **Scheduling**: Cal.com (server route)
- **Chat**: Client widget calling a server proxy route that forwards to an external chatbot backend

---

## Information architecture (tabs / navigation)

The app has **4 top-level navigation tabs** (desktop navbar) and modals/features accessible from buttons and the command palette.

### Tabs (top-level routes)

1. **Home** — `/`
2. **Projects** — `/projects`
3. **Experience** — `/experience`
4. **Certifications** — `/certifications`

### Global actions (not routes)

- **Book a Call** (opens contact modal directly into booking flow)
- **Command Palette** (keyboard-first navigation modal)
- **Resume Modal** (PDF preview + download + external full-screen link)
- **Chat Widget** (floating assistant across the entire site)

---

## Pages and sections (route-by-route)

### Home page — `src/app/page.tsx` (`/`)

**Primary sections**
- **Navbar**: `src/app/components/main/Navbar.tsx`
- **Hero**: `src/app/components/main/Hero.tsx`
  - Uses:
    - `src/app/components/HeroBackground.tsx`
    - `src/app/components/HeroSection.tsx`
- **Skills / Tech Stack grid**: `src/app/components/main/Skills.tsx`
  - Data source: `src/data/tech-constants.ts` (`TECH_STACK`)
- **Home projects parallax**: `src/app/components/sub/HomeProjects.tsx`
  - Uses `src/constants/data/Hero.ts` (`courses`) for parallax thumbnails/links
  - Renders with `src/app/components/sub/HeroParallax.tsx`
- **Footer**: `src/app/components/main/Footer.tsx`

**Behavior**
- Layout is vertically stacked: Hero → Skills → HomeProjects → Footer.

---

### Projects page — `src/app/projects/page.tsx` (`/projects`)

**Primary sections**
- **Navbar**
- **Projects listing**: `src/app/components/main/Projects.tsx`
  - Data source: `src/constants/data/music_courses.json`
  - Each project renders as a 3D card:
    - `src/app/components/sub/3dCard.tsx`
  - Tech badges are rendered using:
    - `src/app/components/sub/TechList.tsx`
  - Buttons per project (if present in data):
    - GitHub repo link
    - API Docs link
    - Live Link
- **Footer**

**Data model (projects)**
- Stored in `src/constants/data/music_courses.json` under `courses[]` (and also `prev[]`).
- Typical fields include:
  - `title`, `description`, `image`
  - `github`, `livelink`, optional `apiDocs`
  - `tech[]` items: `{ name, icon }`

---

### Experience page — `src/app/experience/page.tsx` (`/experience`)

**Primary sections**
- **Navbar**
- **Experience section header** (“Professional Journey”)
- **Experience timeline/cards**: `src/app/components/sub/ExperienceCard.tsx`
- **Footer**

**Data model (experience)**
- Experience entries are currently **defined inside** `src/app/components/sub/ExperienceCard.tsx` as an array named `experiences`.
- Entries are grouped by company title, then displayed in a **timeline-like card layout**.
- Each entry includes:
  - `date`, `title` (company), `role`, `location`
  - `description` (company description)
  - `highlights[]` (pill tags)
  - `features[]` (bullet list of achievements)
  - `tech[]` (icons via `TechList`)
  - Optional links: `offerLetter`, `experienceLetter`, `website`

---

### Certifications page — `src/app/certifications/page.tsx` (`/certifications`)

**Primary sections**
- **Navbar**
- **Certifications list** (timeline-like cards)
  - Certifications data is **embedded inside** `src/app/certifications/page.tsx` as `certifications[]`
  - Each item includes:
    - `title`, `issuer`, `logo`, `date`
    - `description`
    - `features[]`
    - `credentialLink`
- **Footer**

---

## Global layout and site-wide components

### Root layout — `src/app/layout.tsx`

**Always-on site elements**
- Background visuals: `BackgroundBeams` (`src/app/components/sub/BackgroundBeams.tsx`) mounted at layout level.
- Global chat widget: `ChatWidget` (`src/app/components/chat/ChatWidget.tsx`) mounted at layout level (appears on every route).

**SEO**
- Metadata for OpenGraph/Twitter/keywords and JSON-LD person schema is defined here.

---

### Navbar — `src/app/components/main/Navbar.tsx`

**Desktop navigation**
- Home, Projects, Experience, Certifications routes.

**Desktop actions**
- **Book a Call** button opens `ContactModal` directly into the booking view (`initialView="book-call"`).
- **Command Palette** button (grid/command icon) opens `CommandPalette`.

**Mobile behavior**
- Entire navbar becomes a single button that opens the command palette (menu).

**Greeting**
- Home page shows a short animated greeting for ~3 seconds then transitions into the standard navbar.

---

### Command Palette — `src/app/components/sub/CommandPalette.tsx`

**Purpose**
- Keyboard-first navigation and quick actions.

**Items included**
- Home, Projects, Experience, Certifications
- Book a Call (opens contact modal)
- Resume (opens resume modal)

**Keyboard controls**
- ArrowUp / ArrowDown: navigate items
- Enter: select
- Esc: close

---

## Contact features (Book a Call, Email, Message)

### Contact modal hub — `src/app/components/sub/ContactModal.tsx`

This modal acts like a **multi-view wizard**:

- `main`: choose one of 3 actions
  - Book a Call
  - Email Me (mailto)
  - Message Me (in-app message form)
- `book-call`: date/time selection
- `review`: attendee info + notes + confirmation submit
- `success`: booking confirmation view + calendar actions
- `message`: message form

---

### Book a Call flow (UI)

**1) Date/time selection** — `src/app/components/sub/BookCallModal.tsx`
- Shows calendar month picker and time slots.
- Time slots differ for weekdays vs weekends (in IST).
- Prevents selecting past dates/times using IST-based comparisons.

**2) Review & confirm** — `src/app/components/sub/ReviewBookingModal.tsx`
- Captures:
  - Name (validated)
  - Email (validated; blocks obvious fake/test patterns)
  - Notes (optional)
- Submits to server API:
  - `POST /api/book-call`

**3) Success screen** — `src/app/components/sub/BookingSuccess.tsx`
- Displays booking date/time, attendee, notes.
- Provides calendar actions:
  - **Download `.ics`**
  - **Add to Google Calendar**

---

### Book a Call backend API — `src/app/api/book-call/route.ts`

**Purpose**
- Creates an actual booking through **Cal.com API v2**.

**Endpoint**
- `POST /api/book-call`

**Request body**
```json
{
  "dateTime": "2026-04-22T19:20:00.000Z",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "notes": "Optional message"
}
```

**Dependencies / env vars**
- `CAL_API_KEY`
- `CAL_EVENT_TYPE_ID`

**External call**
- `POST https://api.cal.com/v2/bookings`
- Headers include:
  - `Authorization: Bearer <CAL_API_KEY>`
  - `cal-api-version: 2026-02-25`

**Response**
- On success, returns:
  - `booking.id`, `booking.uid` (if provided by Cal.com)
  - `startTime`, `endTime`
  - `attendee` details

---

### Email Me (mailto)

**Location**
- Contact modal main view: `ContactModal.tsx`

**Behavior**
- Uses a `mailto:` link with subject prefilled.

---

### Message Me (in-app email form)

**UI**
- `src/app/components/sub/MessageModal.tsx`
- Validates name, email, message length (10–1000 chars).
- Submits to:
  - `POST /api/send-message`

**Backend**
- `src/app/api/send-message/route.ts`
- Sends an email via Nodemailer using SMTP configuration.

**Required env vars**
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `FROM_EMAIL`
- `TO_EMAIL`

---

## Chat assistant

### UI — `src/app/components/chat/ChatWidget.tsx`

**Behavior**
- Floating button opens a chat window.
- Maintains in-memory message history for the current session.
- Sends questions to:
  - `POST /api/chat`

### Chat window — `src/app/components/chat/ChatWindow.tsx`

**Includes**
- Message list + typing indicator
- Suggested questions when there is no history:
  - `src/app/components/chat/SuggestedQuestions.tsx`

### Backend proxy — `src/app/api/chat/route.ts`

**Purpose**
- Proxies chat requests to an external chatbot backend (e.g., Python/Vercel serverless).

**Required env vars**
- `CHATBOT_API_URL` (preferred) OR `NEXT_PUBLIC_CHATBOT_API_URL`

**External call**
- `POST <CHATBOT_API_URL>/api/question` with `{ question }`

---

## Resume feature

### Resume modal — `src/app/components/sub/ResumeModal.tsx`

**Capabilities**
- In-modal PDF preview (iframe)
- Download PDF (local asset)
- Open full-screen (external Google Drive link)

**Assets**
- PDF expected at: `/public/Shaik_Tajuddin_Resume.pdf`

---

## Visual system & effects (high-level)

These components create the “space / beams / glow” aesthetic:
- `src/app/components/sub/BackgroundBeams.tsx`
- `src/app/components/sub/Beams.tsx`
- `src/app/components/main/StarBackground.tsx`
- `src/app/components/HeroBackground.tsx`

---

## Data sources summary (where content lives)

- **Home parallax projects**: `src/constants/data/Hero.ts`
- **Projects page**: `src/constants/data/music_courses.json`
- **Experience page**: currently embedded in `src/app/components/sub/ExperienceCard.tsx`
- **Certifications page**: currently embedded in `src/app/certifications/page.tsx`
- **Skills grid**: `src/data/tech-constants.ts`

---

## Environment variables (all)

### Scheduling (Cal.com)
- `CAL_API_KEY`
- `CAL_EVENT_TYPE_ID`

### Contact email (SMTP / Nodemailer)
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `FROM_EMAIL`
- `TO_EMAIL`

### Chat
- `CHATBOT_API_URL` (or `NEXT_PUBLIC_CHATBOT_API_URL`)

---

## Non-goals / notes

- This PRD focuses on **what is present in the current repo** and how it behaves.
- Several datasets are **hardcoded in components**; a future improvement could move them to `src/constants/data/` for easier maintenance and RAG ingestion.

