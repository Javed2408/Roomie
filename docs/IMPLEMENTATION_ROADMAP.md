# ROOMIE --- Implementation Roadmap

**Version:** 1.1\
**Date:** 13 November 2026\
**Approach:** Incremental delivery, modular monolith, test each
milestone before moving forward.

**Changes in 1.1:** listing creator types, the two listing statuses and
the three verification types are MVP requirements. Their database
foundation is built in Phase 2; their screens and APIs are spread across
Phases 3, 6 and 8 as noted below.

## 1. Recommended technology stack

  Layer                Technology
  -------------------- ----------------------------------
  Frontend             Next.js 16, React 19, TypeScript
  Styling              Tailwind CSS
  Backend              FastAPI
  Database             PostgreSQL
  ORM                  SQLAlchemy 2.x
  Migrations           Alembic
  Authentication       Secure session/JWT strategy
  Realtime messaging   WebSockets
  Image storage        S3-compatible object storage
  Testing              Pytest and Playwright
  Containers           Docker Compose
  Frontend hosting     Vercel or equivalent
  Backend hosting      Render/Railway or equivalent

Use a modular monolith. Do not split the application into microservices
for the MVP. Redis is optional and should be introduced only when a
concrete need exists.

## 2. Repository structure

``` text
roomie/
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/
│   │   │   ├── discover/
│   │   │   ├── matches/
│   │   │   ├── messages/
│   │   │   ├── accommodation/
│   │   │   └── profile/
│   │   ├── societies/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── types/
│   └── public/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── docs/
│   ├── PRD.md
│   ├── USER_FLOWS.md
│   ├── DATABASE_SCHEMA.md
│   └── IMPLEMENTATION_ROADMAP.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## 3. Phase 0 --- Product and engineering foundation

### Tasks

-   Create GitHub repository.
-   Add the four product/engineering documents.
-   Create frontend and backend applications.
-   Configure environment variables and `.env.example`.
-   Configure Docker Compose for PostgreSQL.
-   Add FastAPI health endpoint.
-   Add frontend base layout.
-   Establish formatting and linting.
-   Add README with setup instructions.
-   Add basic CI for linting and tests.

### Deliverables

-   Repository runs locally.
-   Frontend and backend start independently.
-   Backend can connect to PostgreSQL.
-   `/health` endpoint returns a successful response.
-   No secrets are committed.

### Exit criteria

A new developer can clone the repository, follow the README and run the
application locally.

## 4. Phase 1 --- Frontend foundation

### Tasks

-   Define typography, colors, spacing and reusable components.
-   Build landing page.
-   Build login and registration screens.
-   Build dashboard shell and navigation.
-   Build profile editor shell.
-   Build discovery card shell using mock data.
-   Build matches and messages shells.
-   Build accommodation directory and listing forms.
-   Add responsive mobile layouts.
-   Add loading, empty and error states.

### Deliverables

A navigable responsive frontend with mock data.

### Exit criteria

All main routes work on mobile and desktop. Forms have client-side
validation, but backend integration is not yet required.

## 5. Phase 2 --- Backend and database foundation

### Tasks

-   Create FastAPI application structure.
-   Configure SQLAlchemy sessions.
-   Add Alembic.
-   Implement initial models and migrations, including the three
    verification types, verification documents, review history, listing
    creator types and the two listing statuses.
-   Add Pydantic request/response schemas that never expose private
    fields.
-   Implement the listing visibility rule, listing moderation and
    verification review as services (no public routes yet; those need
    authentication from Phase 3).
-   Add centralized error handling.
-   Add structured logging.
-   Add API version prefix `/api/v1`.
-   Add database health check.
-   Add Pytest configuration.

### Deliverables

Persistent database and tested backend foundation.

### Exit criteria

A clean database can be created from migrations, and health/database
tests pass. Tests prove the visibility rule, the independence of the
three verification types and the database constraints.

## 6. Phase 3 --- Authentication and student profiles

### Tasks

-   Registration.
-   Email verification.
-   Login/logout.
-   Secure refresh/session handling.
-   Password reset.
-   Current-user endpoint.
-   Profile create/read/update.
-   Profile photo upload.
-   Profile completion rules.
-   Authorization dependencies.
-   Submitting identity and student verification, with private document
    upload.
-   The API for submitting listing authority evidence (owner, tenant and
    agent), and administrator review endpoints for all three verification
    types, including recording independent owner confirmation. Their
    screens follow in Phases 6 and 8.

### Deliverables

Two independent student accounts can register and maintain separate
profiles.

### Exit criteria

Authentication tests pass, private routes reject unauthenticated
requests, and one user cannot modify another user's profile.

## 7. Phase 4 --- Localities, societies and preferences

### Tasks

-   Admin locality CRUD.
-   Admin society CRUD.
-   Seed verified/carefully curated initial locality and society
    records. (Done as researched candidates imported **unverified**,
    with their sources. Each must be confirmed by a person and verified
    before students can see it; see the README.)
-   Change history for every directory record.
-   Society search API.
-   User multi-society preference API.
-   Preference ordering.
-   Profile display of preferred societies.
-   Validation for inactive societies.

### Deliverables

Students can select and manage multiple preferred societies.

### Exit criteria

A student can select several societies and the backend persists the
choices accurately.

## 8. Phase 5 --- Discovery and compatibility

### Tasks

-   Implement discovery eligibility filters.
-   Exclude self, blocked, suspended and already processed profiles.
-   Add pagination.
-   Implement compatibility scoring as a standalone service.
-   Add configurable weights.
-   Add unit tests for every scoring factor and missing-data cases.
-   Implement like/pass endpoints.
-   Implement reciprocal-like detection.
-   Create matches transactionally.
-   Prevent duplicate matches.
-   Add match notifications.

Done in Phase 5 as above, with these notes: weights are one validated
setting; simultaneous likes are serialised by a lock on the pair of people;
a conversation row is created with each match (its messaging is Phase 7);
notifications are in-app only (email and push are later, PRD 10). Block
and report screens remain Phase 8, but discovery already honours blocks.

### Deliverables

Two accounts can discover one another, like each other and create
exactly one match.

### Exit criteria

Matching tests cover reciprocal likes, repeated requests, concurrent
requests, self-like prevention, blocks and score calculation.

## 9. Phase 6 --- Accommodation listings

### Tasks

-   Create existing-accommodation listing form and API.
-   Create joint-search listing form and API.
-   Add listing-society preference relation.
-   Add photo storage.
-   Add browse/search/filter endpoints.
-   Add listing detail screen.
-   Add owner listing management.
-   Add listing-interest endpoint and owner view.
-   Add listing lifecycle status transitions (creator-controlled).
-   Collect creator type, brokerage disclosure and listing authority
    evidence when a property is listed.
-   Enforce the visibility rule on every public listing query: active
    and approved only.
-   Show the creator their listing's moderation status and any reason.

### Deliverables

Both accommodation use cases work with persisted data.

### Exit criteria

A student can publish either listing type, another student can browse it
and express interest, and the owner can manage it.

### Status (19 November 2026): complete

Built: both listing types with create, edit, draft deletion, submission
and resubmission; evidence upload per creator type; tenant permission
basis and agreement end date; brokerage disclosure with payee and change
history; profile and listing photos (validated, re-encoded, metadata
removed, privately stored, served through access-checked routes);
browsing with filters, sorting and pages; listing detail; "My listings",
a management page per listing, "My interests"; interest with brokerage
acknowledgement, accept and decline; listing notifications; admin
moderation and review APIs (the admin screens are Phase 8). Messaging
after an accepted interest arrives with Phase 7.

## 10. Phase 7 --- Matches and messaging

### Tasks

-   Conversation model and APIs.
-   Conversation participant authorization.
-   Message persistence.
-   WebSocket authentication.
-   Realtime message broadcast.
-   Unread counts.
-   Read receipts if reliable.
-   Unmatch behavior.
-   Block behavior integrated with chat.

### Deliverables

Matched users can exchange persistent realtime messages.

### Exit criteria

Unauthorized users cannot retrieve or send messages. Messages remain
available after reconnecting.

## 11. Phase 8 --- Safety and admin

### Tasks

-   Block/unblock APIs and UI.
-   Report user/listing APIs.
-   Admin report queue.
-   Admin listing moderation (approve, reject, suspend) with reasons.
-   Account suspension.
-   Admin review queues for identity, student and listing authority
    verification, including independent owner confirmation for agents.
-   Audit logs.
-   Rate limits.
-   Privacy settings.
-   Verification evidence access controls.

### Deliverables

A basic operational safety and moderation system.

### Exit criteria

A user can block/report, an administrator can review a report and
moderation actions are recorded.

## 12. Phase 9 --- Testing, deployment and pilot

### Testing

-   Unit tests for services and scoring.
-   API integration tests.
-   Database constraint tests.
-   Authentication and authorization tests.
-   WebSocket authorization tests.
-   Playwright critical-path tests.
-   Responsive testing.
-   Upload validation tests.
-   Abuse/rate-limit tests.

### Deployment

-   Configure production environment variables.
-   Deploy frontend and backend.
-   Provision managed PostgreSQL.
-   Configure object storage.
-   Configure HTTPS and allowed origins.
-   Run migrations.
-   Set up database backups.
-   Configure logs and error monitoring.
-   Test account recovery and email delivery.

### Pilot

Start with a controlled student pilot around SRM KTR. Recruit a small
group, validate society names and listing quality, observe onboarding
completion and collect feedback. Do not claim product-market fit based
only on signups or swipes.

### Exit criteria

The two main user journeys work in production: 1. Existing-flat tenant
finds and connects with a potential roommate. 2. Students create a joint
accommodation search, match and coordinate.

## 13. Testing strategy

  -----------------------------------------------------------------------
  Area                                Test examples
  ----------------------------------- -----------------------------------
  Authentication                      Duplicate email, invalid password,
                                      expired verification

  Profiles                            Ownership, required fields,
                                      visibility

  Societies                           Inactive society, duplicate
                                      preference

  Matching                            Reciprocal likes, duplicate match,
                                      block, missing data

  Messaging                           Nonparticipant access, inactive
                                      match, reconnect

  Listings                            Invalid type-specific fields,
                                      closed listing

  Interests                           Duplicate interest, owner
                                      self-interest

  Safety                              Block enforcement, report
                                      submission, admin permissions

  Frontend                            Onboarding, discovery, listing
                                      creation, chat

  Deployment                          Environment config, migrations,
                                      backups
  -----------------------------------------------------------------------

## 14. Suggested Git workflow

-   `main`: stable, deployable code.
-   `develop`: integration branch if the team needs it.
-   `feature/<name>`: isolated feature branches.
-   Use small commits with meaningful messages.
-   Open pull requests for major modules.
-   Require tests to pass before merging.
-   Never commit `.env`, API keys or personal verification documents.

## 15. Milestone tracking

  Milestone   Definition of done
  ----------- -----------------------------------------
  M0          Local development environment works
  M1          Main frontend routes work
  M2          Database and API foundation work
  M3          Students can register and edit profiles
  M4          Society preferences persist
  M5          Discovery and mutual matching work
  M6          Both listing types work
  M7          Matched users can chat
  M8          Safety and admin flows work
  M9          Production pilot passes critical tests

## 16. Scope guardrails

Do not add these before the core flows work: - AI matching or
embeddings. - Payment gateway. - Rent splitting. - Microservices. -
Complex group chat. - Native mobile apps. - Payment handling of any kind
(Roomie never collects rent, deposits or brokerage).

A feature should be added only when it supports a validated user need or
removes a real blocker.

## 17. First development session checklist

-   [ ] Create repository named `roomie`.
-   [ ] Create `frontend/` and `backend/`.
-   [ ] Initialize Next.js with TypeScript and Tailwind.
-   [ ] Initialize FastAPI.
-   [ ] Add PostgreSQL to Docker Compose.
-   [ ] Add `.env.example`.
-   [ ] Connect FastAPI to PostgreSQL.
-   [ ] Add `/api/v1/health`.
-   [ ] Add a simple frontend page that calls the health endpoint.
-   [ ] Commit the working foundation.

**First milestone:** A browser page successfully calls the Roomie
backend, and the backend confirms database connectivity.
