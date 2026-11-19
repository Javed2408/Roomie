# Roomie

A student roommate discovery and shared-accommodation platform, starting with
the residential communities around SRM Kattankulathur.

**Current status:** Phase 6 (accommodation listings, listing authority
verification and photos) is complete. What is real and what is still sample
data:

| Real: saved by the backend | Still sample data (later phases) |
| --- | --- |
| Registration, login, logout, sessions | Messages (Phase 7) |
| Email confirmation and password reset | Reporting and blocking (Phase 8) |
| Onboarding, profile, preferences, preferred societies, profile photos | The landing page's "areas we cover" section and profile preview |
| Identity and student verification submission, with private document upload | |
| The society directory: search, area filter, admin management and history | |
| Discover, compatibility scores, likes, passes, matches and match notifications | |
| Accommodation listings, evidence of listing authority, photos, browsing, interest | |

**The directory has no verified societies yet.** It holds researched
candidates that a person must confirm first (see
[The society directory](#the-society-directory)). Until at least one society
is verified, nobody can finish onboarding in your development database, so
Discover there stays empty too. To try Discover and matching now, use the
[practice database](#trying-the-app-with-fictional-societies-and-students).

Screens that show sample data carry a "Sample data" label. Nothing is ever
shown as verified unless an administrator has really approved it.

See [docs/IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md) for what
comes next.

## How the pieces fit together

```text
Browser ──► Frontend (Next.js, port 3000)
   │
   └──────► Backend (FastAPI, port 8000) ──► PostgreSQL (Docker, port 5432)
```

| Part     | Technology                               | Folder               |
| -------- | ---------------------------------------- | -------------------- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind | `frontend/`          |
| Backend  | Python, FastAPI, SQLAlchemy 2            | `backend/`           |
| Database | PostgreSQL 17                            | `docker-compose.yml` |

## What you need installed

| Tool           | Version used | Check with               |
| -------------- | ------------ | ------------------------ |
| Node.js        | 24           | `node --version`         |
| Python         | 3.11 or newer | `python --version`      |
| Docker Desktop | any recent   | `docker --version`       |
| Git            | any recent   | `git --version`          |

Docker Desktop must be **running** (open it from the Start menu and wait for
"Engine running") before you start the database.

## First-time setup

All commands are written for **PowerShell on Windows**. Open a terminal in
VS Code with `` Ctrl+` ``. Each block says which folder to be in.

### 1. Create your local configuration files

In the project root (`roomie/`):

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env.local
```

Open `.env` and change two values:

- `POSTGRES_PASSWORD`: a long random string of letters and numbers.
- `SECRET_KEY`: 64 random characters. Generate them with
  `python -c "import secrets; print(secrets.token_hex(32))"` and paste the
  result in.

These two files hold your local settings and are ignored by Git — never commit
them. The backend refuses to start if either value is missing.

### 2. Start the database

In the project root:

```powershell
docker compose up -d --wait
```

This downloads PostgreSQL the first time, starts it in the background (`-d`)
and waits until it is ready (`--wait`).

### 3. Set up the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.scripts.directory import
```

- `python -m venv .venv` creates a private Python environment for this project,
  so its packages do not clash with other projects.
- `Activate.ps1` switches this terminal to that environment. Your prompt shows
  `(.venv)` when it is active. **Run it again in every new terminal.**
- `pip install` downloads the packages the backend needs.
- `alembic upgrade head` creates the database tables by applying every
  migration. Run it again whenever you pull new code; it only applies what is
  missing and never deletes data.
- `directory import` adds the **candidate** localities and societies around
  SRM, all **unverified** and hidden from students. It is safe to run again;
  it never adds a duplicate or changes an existing record.

Create an administrator account. You need one to verify directory records
and to review verification submissions:

```powershell
python -m app.scripts.create_admin you@example.com
```

It asks for the password at a hidden prompt. There is no way to become an
administrator through the website.

Students see a society only after an administrator has confirmed it and
marked it verified (see [Verifying a record](#verifying-a-record)). To try
onboarding before any real record is confirmed, use the
[practice database with fictional societies](#trying-the-app-with-fictional-societies-and-students).

### 4. Set up the frontend

In a **second** terminal:

```powershell
cd frontend
npm install
npx playwright install chromium
```

`npm install` downloads the frontend's packages. The last command downloads the
browser used by the end-to-end tests.

## Running the app

You need three things running. The database runs in the background; the
backend and frontend each need their own terminal.

**Database** (project root — only needed if it is not already running):

```powershell
docker compose up -d --wait
```

**Terminal 1 — backend:**

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

**Terminal 2 — frontend:**

```powershell
cd frontend
npm run dev
```

Then open:

| Address                                    | What you should see                            |
| ------------------------------------------ | ---------------------------------------------- |
| <http://localhost:3000>                    | The public landing page                        |
| <http://localhost:3000/register>           | Create a real account (also `/login`, `/forgot-password`) |
| <http://localhost:3000/onboarding>         | The six-step profile setup; each step is saved as you go |
| <http://localhost:3000/dashboard>          | The signed-in app (also `/profile`, `/profile/edit`, `/profile/verification`, `/discover`, `/matches`, `/messages`, `/accommodation`) |
| <http://localhost:3000/accommodation/new>  | Post a listing (also `/accommodation/mine` for review statuses) |
| <http://localhost:3000/terms>              | Draft Terms of Use (also `/privacy`) |
| <http://localhost:3000/status>             | Two green "Connected" rows: the API and the database |
| <http://localhost:8000/api/v1/health>      | `{"status":"ok", ...}`                         |
| <http://localhost:8000/api/v1/health/db>   | `{"status":"ok","database":"connected"}`       |
| <http://localhost:8000/docs>               | Interactive API documentation                  |

The public pages (landing, terms, privacy) work with the frontend alone.
Everything that involves an account needs the backend and the database.

To stop: press `Ctrl+C` in each terminal, then run `docker compose stop` in the
project root. Your database data is kept.

## Accounts, email and documents

### Signing in

Register at <http://localhost:3000/register>. You are signed in straight away
and taken to onboarding. Signed-in pages send you to the login page if your
session has ended.

- **Sessions** last up to 14 days, or end after 3 days without use, whichever
  comes first. Logging out ends the session on the server, not just in the
  browser. Resetting a password logs that account out everywhere.
- The session is a cookie the page's own scripts cannot read (`HttpOnly`).
  Every change also needs an anti-forgery token, which the frontend handles
  for you.

### Email in development

By default (`EMAIL_BACKEND=console`) **no email is sent**. Each one is saved as
a text file in `backend/var/outbox/`. To confirm your address or reset a
password while developing:

1. Do the action in the browser (register, or "Forgot your password?").
2. Open the newest file in `backend/var/outbox/` in VS Code.
3. Copy the link from it into your browser.

To send real email, set `EMAIL_BACKEND=smtp` and the `SMTP_*` values in `.env`.
Production refuses to start with the console setting.

### Verification documents

Upload identity and student documents at
<http://localhost:3000/profile/verification>.

- Files are saved in `backend/var/private-storage/` under random names. This
  folder is never served by any web server and is ignored by Git.
- Only PDF, JPEG and PNG are accepted, up to 5 MB. The type is decided by the
  file's actual contents, not its name.
- A file can be downloaded only by the person who uploaded it and by
  administrators. Anyone else gets "not found".
- **Nothing is approved automatically.** Every submission waits for an
  administrator. The admin review endpoints exist and are covered by the
  automated tests; the admin screens arrive in Phase 8. (The interactive page
  at <http://localhost:8000/docs> lists them, but it cannot be used to make
  changes: the anti-forgery protection refuses requests from that page.)

### Environment variables

All live in the root `.env` file; `.env.example` lists them with comments.

| Variable | Purpose | Default |
| --- | --- | --- |
| `POSTGRES_*` | Database connection | see `.env.example` |
| `SECRET_KEY` | Signs anti-forgery tokens. **Required**, 32+ characters | none |
| `FRONTEND_URL` | Used to build links in emails | `http://localhost:3000` |
| `CORS_ALLOWED_ORIGINS` | Websites allowed to call the API with cookies | `http://localhost:3000` |
| `EMAIL_BACKEND` | `console` (save to files) or `smtp` (send) | `console` |
| `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Real email sending | unset |
| `STORAGE_DIR` | Folder for private documents | `backend/var/private-storage` |
| `MAX_UPLOAD_BYTES` | Upload size limit | 5 MB |
| `SESSION_LIFETIME_HOURS`, `SESSION_IDLE_HOURS` | Session expiry | 336, 72 |
| `SESSION_COOKIE_SAMESITE` | `lax` normally; `none` if frontend and API are on unrelated domains | `lax` |

The frontend has one setting, in `frontend/.env.local`:
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

## The society directory

Students pick their preferred societies from a directory that administrators
look after. Members cannot add to it.

- A **locality** is an area: Potheri, SRM Nagar, Kattankulathur,
  Guduvanchery. A **society** is one named apartment complex or villa
  community inside a locality. The directory keeps the two separate.
- Every record starts **unverified**. A society is shown to students only
  when the society **and** its locality are both verified and active.
  Anything else is invisible: it is not in search results and its page
  answers "not found".
- **Verified** means a person has confirmed the record is accurate (for
  example by visiting) and written down how. It does **not** mean Roomie has
  any agreement with the society, and the app says so under the picker.
- Every change is kept in a history: who, what, when and why.
- Records are switched off, never deleted, so members' saved choices are
  kept. A member whose saved society is switched off sees it marked "No
  longer available"; it stops counting towards a complete profile.

### What is in the directory now: candidates, none verified

`backend/app/scripts/data/srm_ktr_directory_candidates.json` lists records
found on public property-listing and developer web pages on 17 November
2026. **Nothing in it has been confirmed on the ground, and nothing is
verified.** Each entry keeps its source links and what still needs checking.
Those details are also saved in each record's private source note, which
administrators can read through the admin API.

The four localities (Potheri, SRM Nagar, Kattankulathur, Guduvanchery) are
all unverified. Decide before verifying them:

- What the "city" field should hold. It currently says
  "Chengalpattu district" for all four.
- Whether SRM Nagar is used locally as its own area name, or should be
  merged into Potheri.
- One spelling for Guduvanchery (listing sites also use "Guduvancheri").
- Kattankulathur has no candidate society yet.

| Society | Listed in | Type per sources | Must be confirmed before verifying |
| --- | --- | --- | --- |
| SRM Green Pearl | Potheri | Apartment complex | That it is occupied today; some listing data is years old. "SRM" is the builder's name, not a link with the university. |
| Lancor Abode Valley | Potheri | Apartment complex | The name used locally (also listed as "Abode Valley"). |
| Arun Excello Estancia | Potheri | Apartment complex | Whether "Arun Estancia" and "Arun Excello Estancia Mini" are the same complex, and whether it is in Potheri or SRM Nagar. |
| VGN Tranquil | Potheri | Apartment complex | The locality. Sources say Potheri, "opposite SRM", and Guduvanchery. |
| DAC Urban Park | Potheri | Apartment complex | The locality (Potheri or Guduvanchery), and that it is finished and lived in. |
| Travancore Residency | Potheri | **Unknown** | That it is a named complex, not a single building, and its type. Only rental listings mention it. |
| DK Apartments | SRM Nagar | **Unknown** | Complex or single building, its locality and its type. Only a map listing mentions it. |
| Lancor Lumina | Guduvanchery | Apartment complex | That every block is finished. Its RERA number (TN/01/Building/0281/2018, from a blog) has not been checked against the Tamil Nadu RERA register. |
| Urbanrise Jubilee Residences | Guduvanchery | Apartment complex | That it is a practical distance from SRM for students. |
| Spkya Bliss | Guduvanchery | Apartment complex | That it exists, is finished and is spelled correctly. Only one source, a property blog. |

Found during research but **deliberately not added**: Gurudev Apartments
and Shriram Shankari (listed in Perumattunallur, not one of the chosen
areas), VGN Southern Meadows / Southern Avenue and Purva Vanam (plots of
land, not homes), Aishwarya Apartment (too generic to identify), Jmm Bell
Flower Apartments (no page describing it could be found) and Eben Residency
(a hotel).

No descriptions were written. Whoever verifies a record writes its
description from what they confirmed.

### Directory commands

In `backend/` with `.venv` active:

```powershell
python -m app.scripts.directory status          # every record, its state, and how many people chose it
python -m app.scripts.directory import          # add the candidates from the file, unverified
python -m app.scripts.directory retire-samples  # remove the old Phase 2 "(sample)" societies
```

- `import` never adds a duplicate and never changes an existing record.
  Running it twice adds nothing the second time.
- `retire-samples` is only needed in a database where the old `seed_dev`
  script was run. It deletes the invented "(sample)" societies that nobody
  chose. Samples somebody did choose are switched off and kept, so that
  person's saved data is not removed without their knowledge.

### Verifying a record

Verify a record **only after you have confirmed it**: visited it, checked it
with its residents' association, or checked its RERA registration. The note
is required and is kept in the history.

```powershell
python -m app.scripts.directory verify locality "Potheri" --admin you@example.com --note "<how you confirmed it>"
python -m app.scripts.directory verify society "Lancor Abode Valley" --admin you@example.com --note "<how and when you confirmed it>"
```

- `--admin` must be an administrator account, and is recorded in the
  history.
- A society's type must be known before it can be verified. Travancore
  Residency and DK Apartments have none yet; set it through the admin API
  (below) once you know it.
- Changing a verified record's core details makes it unverified again, so it
  must be checked once more. Core details are a locality's name, city or
  state, and a society's name, locality, type or address.

Switching records off and on, or withdrawing a verification:

```powershell
python -m app.scripts.directory deactivate society "<name>" --admin you@example.com --note "<why>"
python -m app.scripts.directory activate society "<name>" --admin you@example.com
python -m app.scripts.directory unverify society "<name>" --admin you@example.com --note "<what was wrong>"
```

### Adding or changing records: the admin API

Adding a society, setting its type, correcting a name or writing a
description goes through the admin API. (The admin screens arrive in
Phase 8.) All paths start with `/api/v1/admin/directory`.

| Method and path | What it does |
| --- | --- |
| `GET /localities` | Every locality, including hidden ones |
| `POST /localities` | Add a locality (starts unverified) |
| `GET /localities/{id}` | One locality, with its history |
| `PATCH /localities/{id}` | Change only the fields sent |
| `GET /societies` | Every society. Filters: `q`, `locality_id`, `verification_status`, `is_active` |
| `POST /societies` | Add a society (starts unverified) |
| `GET /societies/{id}` | One society, with its history and how many people chose it |
| `PATCH /societies/{id}` | Change only the fields sent |
| `POST /localities/{id}/verify` (or `/societies/...`) | Body `{"note": "..."}`; the note is required |
| `POST .../unverify` | The note is required |
| `POST .../activate`, `POST .../deactivate` | The note is optional |

Every request needs a signed-in administrator, and every change also needs
the anti-forgery token. A name that duplicates an existing record (ignoring
capitals and punctuation, anywhere in the directory) is refused with a
message naming the existing one. A society's address and coordinates, and
every source note, are visible to administrators only.

The public endpoints are `GET /api/v1/localities`,
`GET /api/v1/societies?q=&locality_id=&limit=&offset=` and
`GET /api/v1/societies/{id}`. They return only verified, active records.

**Using the admin API from PowerShell.** Start the backend first. Then, in
another PowerShell window:

```powershell
# 1. Sign in. Your password goes into a pop-up box, not into the command.
$api = "http://localhost:8000/api/v1"
$json = "application/json; charset=utf-8"
$cred = Get-Credential -UserName "you@example.com" -Message "Roomie administrator"
$body = @{ email = $cred.UserName; password = $cred.GetNetworkCredential().Password } | ConvertTo-Json
$login = Invoke-RestMethod -Method Post "$api/auth/login" -ContentType $json -Body $body -SessionVariable roomie
Remove-Variable body, cred
$csrf = @{ "X-CSRF-Token" = $login.csrf_token }

# 2. List the unverified societies, with their ids.
Invoke-RestMethod "$api/admin/directory/societies?verification_status=UNVERIFIED" -WebSession $roomie | Format-Table id, name, locality_name, community_type -AutoSize

# 3. Set a society's type once you know it. ("VILLA_COMMUNITY" is the other type.)
$id = "<the society's id from step 2>"
$change = @{ community_type = "APARTMENT_COMPLEX"; note = "<how you know>" } | ConvertTo-Json
Invoke-RestMethod -Method Patch "$api/admin/directory/societies/$id" -ContentType $json -Body $change -Headers $csrf -WebSession $roomie

# 4. Add a new society. Find the locality's id with:
#    Invoke-RestMethod "$api/admin/directory/localities" -WebSession $roomie | Format-Table id, name
$new = @{ locality_id = "<locality id>"; name = "<exact name>"; community_type = "APARTMENT_COMPLEX"; source_note = "<where the information came from>" } | ConvertTo-Json
Invoke-RestMethod -Method Post "$api/admin/directory/societies" -ContentType $json -Body $new -Headers $csrf -WebSession $roomie

# 5. Read a record's history.
(Invoke-RestMethod "$api/admin/directory/societies/$id" -WebSession $roomie).history | Format-Table action, actor_email, note, created_at -AutoSize

# 6. Sign out when finished.
Invoke-RestMethod -Method Post "$api/auth/logout" -Headers $csrf -WebSession $roomie
```

If a request is refused, PowerShell shows the API's message in red, for
example that a society with that name already exists.

To add **several candidates at once**, add entries to the candidates file in
the same format (each with `sources` and `notes`, and no `description`), then
run `python -m app.scripts.directory import`. To change a record that already
exists, use the API: the import never overwrites anything.

### Trying the app with fictional societies and students

To try onboarding and Discover before any real society is verified, run the
backend against a separate practice database filled with obviously
fictional societies ("Alpha Fixture Residency" and so on) and six fictional
students ("Asha (practice)", "Rahul (practice)", ...):

```powershell
cd backend
.venv\Scripts\Activate.ps1
$env:POSTGRES_DB = "roomie_sandbox_test"
python -m app.scripts.prepare_database --practice-students
uvicorn app.main:app --reload
```

- `$env:POSTGRES_DB` applies to this terminal only. Your real `roomie`
  database is not touched, and accounts you create here exist only in the
  practice database.
- Every practice student's name says "(practice)", their college is
  "Practice College" and their bio says they are not a real person. Nobody
  can sign in as them; they are there to be discovered and liked.
- Add `--reset` to start the practice database again from empty.
- To go back, stop the backend (`Ctrl+C`), close the terminal, and start the
  backend normally in a new one.
- These options only work on a database whose name ends in `_test` or
  `_e2e`, so fictional records can never end up in your real data.

## Discovery and matching

Discover shows one student at a time with a compatibility score. You like
or pass; when two people like each other, they match.

### Who appears in Discover

A student appears to you only if **all** of these are true:

- it is not you;
- their account is active (not suspended or deleted) and is a member
  account (not an administrator);
- they have **confirmed their email address**;
- their profile is **published** (complete);
- neither of you has blocked the other;
- you have not already liked or passed on them.

Student and identity verification are **not** required to appear. The PRD
asks only for a confirmed email before "full discovery access" (PRD 8.1).
Each card still shows both checks by name, truthfully: "Identity: not
verified" until an administrator approves it.

To use Discover yourself your profile must be published. Before you
confirm your email you can look, but not like or pass, and nobody can see
you yet.

What a card shows: name, college and course, bio, budget, move-in date,
room type, preferred societies (only ones still in the directory), some
habits, the two verification checks and the score with its reasons. It
never shows an email address, date of birth, a gender the student chose
to hide, or any address.

### The order

The PRD says discovery *prioritises* people whose accommodation
preferences overlap. So the deck shows:

1. people who chose at least one of the same societies as you,
2. then people who chose the same area (locality),
3. then everyone else,

with the highest score first inside each group. People looking elsewhere
are not hidden, but they are never mixed in silently: their card says
"Looking in another area", and a note says when you have seen everyone who
shares your societies.

### The compatibility score

The scoring lives in one file, `backend/app/services/compatibility.py`. It
reads nothing from the database and is fully unit-tested
(`tests/test_compatibility.py`). Each factor is scored 0 to 100 by its own
function:

| Factor | Weight | How it is scored |
| --- | --- | --- |
| Budget | 25% | Ranges, not exact amounts. Overlapping: 70 to 100, depending on how much of the narrower range is shared. Separate: 60 falling to 0 as the gap reaches 30% of the lower budget. |
| Societies | 25% | A shared society scores 60 to 100: both ranking it first is 100, and each place lower for either person costs 10. Same area, different societies: 40. Nothing in common: 0. Only societies currently in the directory count. |
| Lifestyle | 20% | The average over the habits **both** answered (sleep, tidiness, social, guests, smoking, drinking). Same: 100, one step apart: 50, opposite: 0. Sleep: a flexible sleeper with anyone is 75, an early bird with a night owl is 0. |
| Move-in date | 15% | Within 7 days: 100, 14: 85, 30: 70, 60: 40, 90: 20, more: 0. |
| Room type | 10% | Same: 100, one with no preference: 80, private against shared: 30. |
| Food | 5% | Same: 100, vegetarian and vegan: 70, vegetarian and non-vegetarian: 30, vegan and non-vegetarian: 20. |

**Overall score** = the weighted average of the factors that could be
judged, rounded (half up) to a whole number:

```text
score = round( Σ weight × factor score  /  Σ weight )      over judged factors only
```

A factor that cannot be judged (someone did not answer, or one of you has
no society in the directory) is **left out**, not counted as a mismatch,
and its weight is spread over the rest. The response lists it as "could not
compare". If nothing at all can be compared, there is no score.

**Example 1.** Ananya: ₹8,000–12,000, 10 Jan, private room, vegetarian,
early riser, tidy, quiet, rarely has guests, does not smoke or drink;
societies A (1st) and B (2nd). Rahul: ₹10,000–14,000, 30 Jan, no room
preference, non-vegetarian, night owl, tidy, balanced, sometimes has
guests, does not smoke, drinks occasionally; society B (1st).

| Factor | Score | Why |
| --- | --- | --- |
| Budget | 85 | Overlap ₹10,000–12,000, half of the narrower range |
| Societies | 90 | Both chose B; Ananya ranks it 2nd |
| Lifestyle | 58 | Sleep 0, tidiness 100, social 50, guests 50, smoking 100, drinking 50 |
| Move-in | 70 | 20 days apart |
| Room | 80 | Rahul has no preference |
| Food | 30 | Vegetarian and non-vegetarian |

(25×85 + 25×90 + 20×58 + 15×70 + 10×80 + 5×30) ÷ 100 = 75.35 → **75**.
Summary: "Strong compatibility in budget and room type. You both prefer
Society B. Main differences: food."

**Example 2.** The same Ananya and someone whose only society has been
switched off, who answered just one habit. Societies cannot be compared,
so its 25% is shared out: budget then counts 33.3%, lifestyle 26.7%,
move-in 20%, room 13.3% and food 6.7%. Lifestyle says "Based on 1 of 6
habits".

The score is a guide, not a guarantee, and every screen that shows it says
so.

**Changing the weights.** They are in one place, the backend settings.
Set `COMPATIBILITY_WEIGHTS` in `.env` as JSON with all six factors adding
up to 100, for example
`{"budget": 30, "societies": 25, "lifestyle": 20, "move_in": 10, "room": 10, "food": 5}`.
The backend refuses to start if the weights are incomplete, negative or do
not add up to 100.

### Likes, passes and matches

- A decision is **final**. Sending the same one again changes nothing;
  switching a like to a pass (or back) is refused.
- Nobody is told that you passed, and nobody can find out who liked them.
  A like only becomes visible when it is mutual.
- When the second person likes back, the same request creates the match,
  its conversation (for messaging in Phase 7) and a "new match"
  notification for each person. Both see the match in **Matches**. The
  dashboard shows unread notifications. Nothing is emailed or pushed.
- Blocked, suspended, unpublished and unconfirmed accounts cannot be liked
  or passed on: the request answers "not found", exactly like a profile
  that does not exist.
- A match stays visible to both people unless one blocks the other or an
  account is suspended.

**Two people liking each other at the same moment.** Each request locks
that *pair of people* in PostgreSQL (a transaction advisory lock) before
it looks for the other person's like, so the second request waits for the
first to commit and then sees it. Without the lock, a test showed only 1 of
20 simultaneous mutual pairs getting a match. On top of the lock, the
database itself refuses duplicates: one decision per person per target,
one match per pair (stored smallest id first), one conversation per match
and one "new match" notification per person per match. Every insert says
"if it already exists, do nothing".

### API

All need a signed-in member. Changes also need the anti-forgery token.

| Method and path | What it does |
| --- | --- |
| `GET /api/v1/discovery?limit=10&cursor=...` | The next people, best first. Returns `items`, `next_cursor` (pass it back for the next page) and `remaining` |
| `GET /api/v1/students/{id}` | A full profile, the score with every factor, your own decision and the match id if you matched |
| `POST /api/v1/discovery/{id}/like` | Like. Returns `{"decision", "matched", "match_id"}` |
| `POST /api/v1/discovery/{id}/pass` | Pass |
| `GET /api/v1/matches` | Your matches, newest first |
| `GET /api/v1/matches/{id}` | One of your matches, with their profile and current score |
| `GET /api/v1/notifications?unread_only=false` | Your notifications and how many are unread |
| `POST /api/v1/notifications/{id}/read` | Mark one as read |
| `POST /api/v1/notifications/read-all` | Mark all as read |

Errors you may see: `profile_incomplete` (publish your profile first),
`email_not_verified` (confirm your email before liking or passing), `404`
(the person cannot be seen), `409` (you already decided differently),
`429` (more than 300 decisions in 10 minutes).

### Trying it by hand

You need two accounts, so use two browsers (or one normal window and one
private window). In the practice database above:

1. In each browser, register at <http://localhost:3000/register> and
   complete onboarding (choose at least one fixture society).
2. Confirm each email: open the newest file in `backend/var/outbox/` and
   paste its link into **that** browser.
3. In browser 1, open **Discover**: the practice students and your other
   account appear, people sharing your societies first. Like your other
   account (or open its full profile and press Like).
4. In browser 2, like the first account. A "You matched with ..." message
   appears. Both browsers now show the match under **Matches**, and the
   dashboard shows a "New match" notification.
5. Try a pass, then reload Discover: that person does not come back.

## Accommodation listings

There are two kinds of post, kept clearly apart everywhere:

- **Room available** (`EXISTING_ACCOMMODATION`): a real room. Posted by
  the owner, a current tenant, or an agent the owner has authorised.
  Unauthorised brokers cannot publish.
- **Let's find a place together** (`LOOKING_TO_RENT_TOGETHER`): students
  without a flat looking for people to rent with. Not a property, so no
  ownership claims, evidence or brokerage.

### How a room listing goes live

1. Save a draft at **Accommodation > Post a listing**. It is private.
2. On its management page, upload the evidence for your role and add
   photos. The page lists what is still missing.
3. Submit it for review.
4. An administrator checks the evidence and approves or rejects the
   listing (with a reason you see). Only then is it public.

| You are           | You upload                                   | Also needed |
| ----------------- | -------------------------------------------- | ----------- |
| Property owner    | Proof of ownership                           | Verified identity |
| Current tenant    | Rental agreement (still running)             | The landlord's written permission, unless the agreement allows sharing |
| Authorised agent  | The owner's written authorisation, plus the owner's name and contact | Verified identity, and Roomie confirming with the owner directly |

**Owning or renting is not the same as being allowed to take someone
in.** A genuine rental agreement proves tenancy only. When approving a
tenant, the reviewer records *why* sharing is permitted (the agreement
allows it, or the landlord gave written permission) and when the
agreement ends; the listing is hidden automatically after that date.

**Two statuses.** *Lifecycle* (draft, active, filled, closed) is yours.
*Review* (pending, approved, rejected, suspended) is Roomie's: the API
never accepts a review status from a creator. A listing is public only
when it is active **and** approved, its society is in the directory, and
its creator's account is active. Editing a live listing, or changing its
photos or brokerage, sends it back for review.

**Brokerage** is always stated, including "No brokerage". When it
applies, the amount and who receives it are shown before anyone can
express interest, and students must tick that they understand it first.
Only an authorised agent may collect brokerage themselves. Every change
is recorded. Roomie never handles any payment.

**Photos** (profile and listing): JPEG, PNG or WebP up to 8 MB. The
backend checks the file really is an image, refuses oversized "image
bombs", re-encodes it as a fresh JPEG (removing all metadata, including
GPS location), and stores it under a random name in
`backend/var/photo-storage/`, separate from verification documents. The
browser only ever gets API addresses such as
`/api/v1/listings/{id}/photos/{photo_id}`, which check on every request
that you may see that listing or profile.

### Approving a listing by hand (until the Phase 8 admin screens)

Sign in to the admin API from PowerShell exactly as in step 1 of
"Using the admin API from PowerShell" above (that gives you `$api`,
`$json`, `$csrf` and `$roomie`). Then:

```powershell
# 1. Submitted listings waiting for review, with their ids.
Invoke-RestMethod "$api/admin/listings" -WebSession $roomie | Format-Table id, title, creator_type, authority_status -AutoSize

# 2. One listing: what is still outstanding, and its evidence check's id.
$id = "<the listing's id from step 1>"
$detail = Invoke-RestMethod "$api/admin/listings/$id" -WebSession $roomie
$detail.authority_requirements
$check = $detail.authority_verification_id

# 3a. Approve the evidence (owner or agent).
$review = @{ status = "APPROVED" } | ConvertTo-Json
# 3b. For a TENANT, also say why sharing is allowed and when the agreement ends:
# $review = @{ status = "APPROVED"; tenant_permission_basis = "AGREEMENT_PERMITS_SHARING"; rental_agreement_valid_until = "2027-06-30" } | ConvertTo-Json
Invoke-RestMethod -Method Post "$api/admin/verifications/listing-authority/$check/review" -ContentType $json -Body $review -Headers $csrf -WebSession $roomie

# 4. Approve the listing, or reject it with a reason the creator will see.
$decision = @{ status = "APPROVED" } | ConvertTo-Json
# $decision = @{ status = "REJECTED"; note = "<what to fix>" } | ConvertTo-Json
Invoke-RestMethod -Method Post "$api/admin/listings/$id/moderation" -ContentType $json -Body $decision -Headers $csrf -WebSession $roomie
```

The documents themselves can be downloaded only by their uploader and
administrators, from `GET /api/v1/verification-documents/{id}/content`.

### Listing API

| Method and path | What it does |
| --- | --- |
| `GET /api/v1/listings` | Approved, active listings. Filters: `type`, `society_id`, `locality_id`, `min_rent`, `max_rent`, `available_by`, `q`; `sort` (`newest`, `rent_low`, `available_soon`); `limit`, `offset` |
| `GET /api/v1/listings/{id}` | One public listing, with your interest status |
| `POST`/`DELETE /api/v1/listings/{id}/interest` | Express or withdraw interest |
| `GET /api/v1/me/interests` | Your interests and their replies |
| `GET`/`POST /api/v1/me/listings` | Your listings; create a draft |
| `GET`/`PUT`/`DELETE /api/v1/me/listings/{id}` | Read, edit, delete an unsubmitted draft |
| `POST /api/v1/me/listings/{id}/submit` | Submit or resubmit for review |
| `POST /api/v1/me/listings/{id}/lifecycle` | Mark filled, reopen or close |
| `POST /api/v1/me/listings/{id}/photos`, `DELETE .../photos/{photo_id}` | Add or remove photos |
| `POST /api/v1/me/listings/{id}/authority-verification` | Upload evidence |
| `GET /api/v1/me/listings/{id}/interests`, `POST .../interests/{interest_id}` | See interested students; accept or decline |
| `PUT`/`DELETE /api/v1/me/profile/photo` | Your profile photo |

## Running the checks

**Backend** (in `backend/`, with `.venv` active; the database must be running):

```powershell
pytest                 # run the tests
ruff check .           # look for mistakes and risky code
ruff format .          # tidy the formatting
```

`pytest -m "not integration"` runs only the tests that do not need the database.

The tests use their own database, `roomie_test`, which they create and
rebuild automatically. They never touch the data in your `roomie` database.

| Area | Test file |
| --- | --- |
| Directory | `tests/test_directory_api.py` |
| Compatibility scoring (no database needed) | `tests/test_compatibility.py` |
| Discovery: who appears, order, paging, privacy, full profiles | `tests/test_discovery_api.py` |
| Likes, passes, matches, notifications, database guarantees | `tests/test_matching_api.py` |
| Two people liking each other at the same moment | `tests/test_matching_concurrency.py` |
| Practice data scripts and their safety guards | `tests/test_practice_data.py` |

`test_matching_concurrency.py` uses real, separate database connections
(the only way to show a race between two transactions) and empties the test
database afterwards. Run just the scoring rules with
`pytest tests/test_compatibility.py`.

### Database migrations

The table structure is changed only through Alembic migrations, in
`backend/alembic/versions/`. From `backend/` with `.venv` active:

```powershell
alembic current                 # which migration the database is on
alembic upgrade head            # apply everything not yet applied
alembic downgrade -1            # undo the most recent migration
alembic history                 # list all migrations
```

To change the structure: edit the models in `app/models/`, then run
`alembic revision --autogenerate -m "what changed"`, **read the generated
file**, and apply it with `alembic upgrade head`. One test fails if the
models and the migrations ever disagree.

**Frontend** (in `frontend/`):

```powershell
npm run lint           # look for mistakes
npm run typecheck      # check TypeScript types
npm run format         # tidy the formatting
npm run build          # make sure a production build succeeds
npm run test:e2e       # browser tests, on a desktop and a phone screen size
```

The browser tests need only PostgreSQL running (`docker compose up -d --wait`).
Playwright starts its **own** backend (port 8010) and frontend (port 3100)
with their own database, `roomie_e2e`, so the tests never touch your
development servers or your accounts. That database is **rebuilt from empty
at the start of every run** and holds only the fictional directory records
from `backend/app/scripts/seed_test_fixtures.py` plus the accounts the
tests create. The first run takes a minute or two because it builds the
frontend first. The society picker tests are in
`frontend/e2e/directory.spec.ts`; Discover, likes and matches are in
`frontend/e2e/discovery.spec.ts`.

## Project structure

```text
roomie/
├── backend/
│   ├── alembic/           Database migrations (versions/ holds each one)
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py    Sign-in, anti-forgery and admin checks for routes
│   │   │   └── v1/        HTTP routes: auth, me, societies (public directory),
│   │   │                  admin_directory, discovery (+ students, like, pass),
│   │   │                  matches (+ notifications), verifications, admin
│   │   ├── core/          Settings, security, error format, logging, rate limits
│   │   ├── db/            Database connection and the model base class
│   │   ├── models/        Database tables, one class each (25 tables)
│   │   ├── repositories/  Database queries: public listings, public directory,
│   │   │                  who may see whom in discovery
│   │   ├── schemas/       Shapes of API requests and responses (allow-lists)
│   │   ├── scripts/       create_admin, directory (the directory command),
│   │   │                  prepare_database, seed_test_fixtures
│   │   │   └── data/      Candidate directory records, with their sources
│   │   ├── services/      Business rules: auth, account, directory,
│   │   │                  compatibility (scoring), discovery, matching,
│   │   │                  notifications, verification, moderation, email,
│   │   │                  private storage
│   │   └── main.py        Creates the FastAPI app
│   ├── var/               Created when running: outbox/ and private-storage/
│   │                      (Git-ignored)
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/                    Pages and layouts (Next.js App Router)
│   │   ├── (auth)/             login, register, forgot-password, reset-password,
│   │   │                       verify-email
│   │   ├── (dashboard)/        dashboard, discover, students/[id], matches,
│   │   │                       messages (+ [id]), accommodation (+ new, mine,
│   │   │                       [id]), profile (+ edit, verification)
│   │   ├── onboarding/         Profile setup after registering
│   │   ├── terms/, privacy/    Draft legal pages
│   │   ├── status/             API and database check (from Phase 0)
│   │   ├── globals.css         Design tokens: colours, fonts, radius, shadows
│   │   ├── layout.tsx          Root layout and fonts
│   │   └── page.tsx            Landing page
│   ├── components/
│   │   ├── ui/                 Design system: button, text field, select,
│   │   │                       textarea, choice pills, checkbox, dialog, card,
│   │   │                       badge, avatar, alert, loading/empty/error states
│   │   ├── marketing/          Landing page sections, header and footer
│   │   ├── auth/               Sign-in forms and their shared frame
│   │   ├── app-shell/          Sidebar, bottom tab bar, header, profile menu
│   │   ├── discovery/          Discover deck, profile card, score and its
│   │   │                       breakdown, full profile, match dialog
│   │   ├── matches/            The matches list
│   │   ├── listings/           Listing card, directory, create form, review
│   │   │                       status badge, interest button
│   │   ├── profile/            Profile fields, editor, onboarding, society picker
│   │   ├── messages/           Chat thread
│   │   ├── safety/             Report and block
│   │   ├── session/            RequireSession: loads the signed-in account
│   │   ├── dashboard/          The home page overview
│   │   └── verification/       Verification labels and the upload page
│   ├── e2e/                    Playwright browser tests (fixtures.ts creates
│   │                           test accounts; settings.ts holds test ports)
│   ├── hooks/                  Reusable React hooks (forms, society directory,
│   │                           like/pass)
│   ├── lib/                    Helpers: formatting, validation, navigation,
│   │                           profile-form and listing-form rules
│   │   └── mock/               SAMPLE DATA for features not built yet
│   ├── services/               Calls to the backend API (api-client, auth,
│   │                           account, directory, discovery), and
│   │                           mock-api.ts for later phases
│   └── types/                  Shared TypeScript types
├── docs/                  Product and engineering specifications
├── .github/workflows/     Automated checks run by GitHub
├── docker-compose.yml     Local PostgreSQL
└── .env.example           Template for local configuration
```

## Troubleshooting

| Problem | Likely cause and fix |
| --- | --- |
| `failed to connect to the docker API` | Docker Desktop is not running. Open it and wait for "Engine running". |
| `Set POSTGRES_PASSWORD in the .env file` | You have not created `.env` yet. Do step 1 of the setup. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again. |
| `uvicorn` or `pytest` is "not recognized" | The virtual environment is not active. Run `.venv\Scripts\Activate.ps1` in `backend/`. |
| Backend error mentioning `postgres_password` / `Field required` | `.env` is missing from the project root. |
| Backend error mentioning `secret_key` | Add `SECRET_KEY` to `.env` (see step 1 of the setup). |
| No email arrives | In development none is sent. Look in `backend/var/outbox/`. |
| Every signed-in page goes back to the login page | The backend is not running, or `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` does not point at it. |
| "This request did not come from the Roomie website" | The frontend's address is not in `CORS_ALLOWED_ORIGINS`. |
| Onboarding says "No societies are in the directory yet" | No society **and** its locality are both verified yet. Run `python -m app.scripts.directory status` in `backend/` to see what is missing. Verify only records you have confirmed ([Verifying a record](#verifying-a-record)), or try the [practice database](#trying-the-app-with-fictional-societies-and-students). |
| A saved society shows "No longer available" | An administrator switched it off or withdrew its verification. It stays saved; remove it or choose another in **Edit profile**. |
| `Not done: ... already exists` from the directory command | A record with that name (ignoring capitals and punctuation) is already in the directory. Run `status` to find it. |
| `... is not an administrator account` | Create one with `python -m app.scripts.create_admin you@example.com`, or check the email spelling. |
| `ModuleNotFoundError: No module named 'app.scripts.seed_dev'` | That script was removed in Phase 4. Use `python -m app.scripts.directory import` instead. |
| Discover says "Finish your profile first" | Your profile is not published, or an edit removed something required (budget, move-in date or a society still in the directory). Open **Continue setting up** on the dashboard. |
| Like and Pass are greyed out | Your email address is not confirmed yet. Open the newest file in `backend/var/outbox/` and follow its link. |
| Discover says "You're all caught up" straight away | Nobody else has a published profile and a confirmed email yet. Use a second browser to make another account, or the [practice database](#trying-the-app-with-fictional-societies-and-students) with `--practice-students`. |
| `no unique or exclusion constraint matching the ON CONFLICT specification` | The database is missing migration `0004`. Run `alembic upgrade head` in `backend/`. |
| Backend will not start: `COMPATIBILITY_WEIGHTS ...` | The weights in `.env` must name all six factors, none negative, adding up to 100. Remove the line to use the defaults. |
| "Too many attempts" | The rate limit for that action was reached. Wait a few minutes, or restart the backend (limits are kept in memory). |
| `relation "..." does not exist` | The tables have not been created. Run `alembic upgrade head` in `backend/`. |
| Page shows API "Unavailable" | The backend is not running (terminal 1), or it is not on port 8000. |
| Page shows Database "Unavailable" | The database container is stopped. Run `docker compose up -d --wait`. |
| `password authentication failed` | You changed the password in `.env` after the database was first created. PostgreSQL keeps the original. To start fresh (this **deletes all local data**): `docker compose down -v`, then `docker compose up -d --wait`. |
| `port is already allocated` / `address already in use` | Another program is using port 3000, 8000 or 5432. Close it, or for the database change `POSTGRES_PORT` in `.env`. |
| Database calls take 5 seconds | `POSTGRES_HOST` is set to `localhost`. Use `127.0.0.1` (see the note in `.env.example`). |
| VS Code underlines Python imports | Press `Ctrl+Shift+P`, choose "Python: Select Interpreter", and pick `backend\.venv`. |

## Phase 6 decisions

- **Drafts first, then evidence, then review.** A listing is saved as a
  private draft so evidence and photos can be attached to it; it cannot
  be submitted until nothing required is missing, and only an
  administrator can approve it.
- **Tenants need a recorded permission basis.** A rental agreement proves
  tenancy, not permission to take someone in. The reviewer records which
  of the two allowed bases they saw, plus the agreement's end date.
- **Changes are re-reviewed.** Edits, photo changes and brokerage changes
  hide a live listing until approved again; a new society or creator
  type reopens the authority check. Every change is logged in
  `listing_changes` (migration `0005`).
- **Photos are re-encoded, never stored as uploaded.** That is the only
  reliable way to remove hidden metadata and anything that is not an
  image.
- **No new tables for photos or interest.** The existing
  `listing_images`, `listing_interests` and `profile_photo_key` were
  extended instead.
- **Messaging after an accepted interest waits for Phase 7.** The student
  is notified and told messaging is coming; nothing pretends to work.
- **The admin screens are Phase 8.** The review and moderation APIs exist
  and are tested; the browser tests use them as the fixture administrator,
  whose password is set only for the throwaway `_e2e` database.

## Phase 5 decisions

- **A confirmed email is the only check needed to appear in Discover.** PRD
  8.1 asks for a verified email "before full discovery access"; it does not
  ask for student or identity verification. Before confirming, a student
  can look at Discover but cannot like, pass or be seen.
- **Overlap comes first; nobody is hidden for wanting another area.** The
  PRD says discovery *prioritises* overlapping preferences, and the
  scoring rules require a real "no overlap" score. So the deck orders by
  shared society, then shared area, then score, and labels people looking
  elsewhere. The deck says clearly when you move past people who share your
  societies, so the search never broadens silently (USER_FLOWS 4).
- **Unknown is not a mismatch.** A factor that cannot be judged is left out
  and its weight spread over the rest. Retired, switched-off and unverified
  societies are never compared.
- **Decisions are final.** Repeating the same one is harmless; changing it
  is refused. There is no undo in the MVP. Incoming likes are never shown.
- **One lock per pair, plus database rules.** A PostgreSQL advisory lock on
  the pair stops two simultaneous likes from missing each other; unique
  constraints stop duplicates even if code goes wrong.
- **One small migration (`0004`).** A unique partial index so a person can
  never get two "new match" notifications for one match, and
  `matches.compatibility_score` may now be empty rather than invented.
- **Conversations are created with each match, messaging is not built.**
  The conversation row exists so Phase 7 can use it; Messages stays sample
  data until then. The Report and Block buttons are still the labelled
  preview from Phase 1 (Phase 8), but discovery already honours blocks
  stored in the database.
- **Swipe, but buttons first.** Cards can be dragged on touch screens and
  with a mouse; the Like and Pass buttons do the same thing, stay in reach
  at the bottom of the screen, and are what keyboard and screen-reader
  users get.
- **The browser-test database is rebuilt for each run**, so Discover in one
  run never shows accounts from an earlier run. `--reset` refuses any
  database whose name does not end in `_test` or `_e2e`.

## Phase 4 decisions

- **Verified and active are separate switches, and both start safe.** New
  records are unverified, so nothing reaches students until a person has
  confirmed it. An accurate record can still be switched off.
- **A society is public only if its locality is too.** One change hides a
  whole area, and no society appears under an area nobody has checked.
- **Duplicates are stopped by the database.** Names are compared in a
  normalised form (lower case, punctuation ignored), and society names are
  unique across the whole directory because neighbouring areas overlap.
  Genuinely different spellings still need a person to spot them.
- **Editing a verified record's core details unverifies it**, so a changed
  record is never shown under an earlier approval.
- **Researched candidates, not invented ones.** The candidates file records
  where each name came from and what is still uncertain. Nothing was marked
  verified, because nobody has confirmed anything on the ground yet. No
  descriptions were written, and records that turned out to be plots, hotels
  or outside the chosen areas were left out.
- **The old sample societies were retired without deleting anyone's data.**
  Unused samples were deleted. Samples someone had chosen were switched off
  and kept, and the app shows them as "No longer available".
- **History has its own table** (`directory_events`), with a sequence number
  so changes made in the same instant still read in order.
- **A command-line tool as well as an API.** Until the admin screens arrive
  in Phase 8, `python -m app.scripts.directory` covers the common jobs. It
  goes through the same rules and records the same history as the API.
- **Tests use fictional records only.** `seed_test_fixtures` refuses to run
  on any database whose name does not end in `_test` or `_e2e`. The old
  `seed_dev` script was removed.
- **The sample listing form kept its own static society list** until the
  listings API was built in Phase 6 (it now uses the directory).

## Phase 3 decisions

- **Server-side sessions in an HttpOnly cookie, not JWTs.** A random token
  sits in a cookie scripts cannot read; the database stores only its SHA-256
  hash. Logging out or a password reset revokes sessions immediately, which a
  self-contained JWT cannot do.
- **Anti-forgery (CSRF) protection in two layers.** Changes from an unknown
  website are refused by their `Origin`, and every change must also carry a
  token tied to the session, which only our own frontend can read.
- **Argon2id password hashing**, with a dummy check for unknown emails so the
  response time does not reveal who has an account.
- **Emailed links are single-use, short-lived and stored only as hashes.**
  Asking again cancels the previous link.
- **Every `/me` route acts on the signed-in person only.** No route accepts
  a user id, so one person cannot change another's profile. Someone else's
  document or listing answers "not found", the same as one that does not
  exist.
- **Private storage behind an interface.** Files go to a local folder now;
  an S3-compatible store can replace it at deployment by implementing the
  same three methods (`save`, `read`, `delete`).
- **Rate limits are kept in the API's memory.** Correct while the API runs as
  one process; they move to a shared store (such as Redis) if it is ever run
  as several.
- **Onboarding saves each step as you go** and resumes at the first unfinished
  step, so closing the browser halfway loses nothing.
- **Profile completion is decided by the backend.** Publishing requires a
  name, college, budget, move-in date and at least one society. Removing one
  of those later un-publishes the profile.
- **Browser tests run their own isolated stack** (ports 3100 and 8010, database
  `roomie_e2e`), so they can create real accounts without touching yours.

## Phase 2 decisions

- **Three verification tables, not one.** Identity, student and listing
  authority are separate tables with separate statuses. No record means "not
  verified". Listing authority belongs to a listing, not a person.
- **Two status columns on a listing.** `lifecycle_status` (the creator's)
  and `moderation_status` (administrators'). A listing is public only when
  it is `ACTIVE` and `APPROVED`; that rule is written once, on the model.
- **A property cannot be approved without verified listing authority.** This
  is what keeps unauthorised brokers out.
- **Rules live in the database where possible.** Constraints reject invalid
  rows (for example a property with no brokerage disclosure) whichever code
  writes them.
- **Fixed sets of values are text plus a CHECK constraint**, not PostgreSQL
  enum types, because they are much easier to change in a migration.
- **Documents are never stored in the database**, only a private storage
  reference and metadata. Public response shapes are allow-lists that cannot
  include those references.
- **No public API routes for listings yet.** Listing routes are built in
  Phase 6, on top of the Phase 3 sign-in.

## Frontend conventions

- **Use the design tokens.** Colours, radius and shadows are named once in
  `frontend/app/globals.css` and used as classes such as `bg-primary`,
  `text-muted` and `rounded-card`. Avoid raw colour values in components.
- **Build from `components/ui/`.** Buttons, fields, cards and the loading,
  empty and error states live there so every screen stays consistent.
- **Label sample data.** Anything that reads from `lib/mock/` must show the
  `SampleDataBadge`. Never show something as verified unless it really is.
- **Verification is always specific.** Use `VerificationStatus`, which names
  the check ("Identity", "Listing authority"). There is no generic "Verified"
  badge, so one check can never be mistaken for another.
- **Pages stay in memory after you leave them.** This version of Next.js hides
  the previous page instead of discarding it, so its state survives. Sign-in
  forms opt out with `resetWhenHidden` so a typed password never lingers. In
  browser tests, prefer `getByRole(...)`, which ignores hidden pages; add
  `.filter({ visible: true })` to `getByLabel(...)`.

## Phase 1 decisions

- **Dark mode follows the device setting.** There is no in-app switch. It
  works because components use the design tokens; the dark values live in one
  block in `globals.css`.
- **Forms for later phases validate but do not save.** Listing, report and
  chat forms run real validation, then call stand-in services in
  `services/mock-api.ts` that say plainly nothing was saved. (Sign-in and
  profile forms became real in Phase 3.)
- **Terms and Privacy are plain-language drafts**, marked as such on the page.
  They need legal review before launch.
- **Pages with an id in the address** (a student, a listing, a conversation)
  read that id inside `<Suspense>`, as this version of Next.js requires.

- **Teal as the brand colour, rose as a small accent.** Teal reads as calm and
  trustworthy; rose is reserved for "like" moments so the product does not look
  like a dating app.
- **`lucide-react` is the only new dependency**, for icons.
- **A `/dashboard` overview was added** alongside the sections listed in
  USER_FLOWS.md. On phones the bottom bar holds five items and Profile is
  reached from the header menu.
- **The Phase 0 status page moved from `/` to `/status`** to make room for the
  landing page.
- **Listings carry two separate statuses**: one set by the creator (draft,
  active, filled, closed) and one set by admin review (pending, approved,
  rejected, suspended). Adopted in the documents in Phase 2.

## Phase 0 decisions

- **Health endpoints live under `/api/v1/health`.** The roadmap mentions both
  `/health` and `/api/v1/health`; the versioned path is used because the PRD
  requires versioned API routes.
- **One `.env` in the project root** is shared by Docker Compose and the
  backend so database credentials exist in one place. The frontend has its own
  `frontend/.env.local` because Next.js only reads env files from its folder.
- **Only PostgreSQL runs in Docker.** The frontend and backend run directly on
  your machine so code changes reload instantly.
- **End-to-end tests are not part of CI yet.** CI runs backend lint and tests,
  and frontend lint, type check and build. Browser tests join CI in Phase 9.

## Documentation

- [docs/PRD.md](docs/PRD.md) — product requirements and MVP scope
- [docs/USER_FLOWS.md](docs/USER_FLOWS.md) — user journeys and screens
- [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) — tables and constraints
- [docs/IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md) — phases and milestones
