# ROOMIE --- Product Requirements Document

**Version:** 1.3\
**Date:** 17 November 2026\
**Product:** Roomie\
**Initial market:** Student accommodation communities around SRM
Kattankulathur (KTR)

**Changes in 1.3:** clarifications made while building discovery and
matching (Phase 5), marked "Clarified in 1.3" in sections 8.5, 8.6 and
8.7. They interpret existing requirements; none removes or adds a feature.

**Changes in 1.2:** directory records must be verified by an administrator
before members can see them, every directory change is recorded, and
members' saved choices survive a society being switched off. See
section 8.4.

**Changes in 1.1:** three listing creator types (owner, tenant, authorised
agent) are part of the MVP; listings have two independent statuses
(lifecycle and moderation); verification is three independent checks
(identity, student, listing authority). See sections 4, 8.9 and 8.11.

## 1. Product summary

Roomie is a student-focused roommate discovery and shared-accommodation
platform. It helps students find compatible people to live with, whether
they already have a room or flat and need a roommate, or they want to
find people before renting a place together.

Roomie is **society-first**: students choose residential societies or
communities they are interested in, and discovery prioritizes people
whose accommodation preferences overlap.

**Product promise:** Find compatible people first, then make it easier
to find a place together.

## 2. Problem statement

Students looking for accommodation around SRM KTR commonly rely on
informal WhatsApp groups, friends, brokers and scattered listings. These
channels do not reliably answer important roommate questions:

-   Is the other person's budget compatible?
-   Do they want to live in the same society or locality?
-   Are their move-in dates close?
-   Are their routines, cleanliness expectations and lifestyle
    preferences compatible?
-   Does one person already have a flat, or are both still looking?
-   Is the profile or property information trustworthy?

Roomie brings these needs into one structured platform.

## 3. Goals and non-goals

### Goals

1.  Let students create useful, privacy-conscious profiles.
2.  Organize discovery around a curated society directory near SRM KTR.
3.  Help users assess budget, location, timing and lifestyle
    compatibility.
4.  Support mutual matching and private communication.
5.  Support two accommodation scenarios:
    -   **Existing accommodation:** a student has a room/flat and needs
        a roommate.
    -   **Find together:** a student or group wants to find compatible
        people before renting.
6.  Provide basic safety, reporting and moderation tools.
7.  Build a product that can later expand to other college clusters.

### Non-goals for the first MVP

-   Rent collection, deposits or payment processing.
-   Legal rental agreements.
-   Guaranteed background checks.
-   Brokerage or commission processing.
-   Native Android/iOS applications.
-   AI personality analysis.
-   Automated property availability verification.
-   Complex group swipe matching.

## 4. Target users

### Persona A: Student seeking a roommate

A student has found or already rents a flat near campus and wants
another student to share rent and living responsibilities.

### Persona B: Student seeking a flat together

A student has no accommodation yet. They want to find one or more
compatible people, agree on a budget and society, then search for a flat
together.

### Persona C: Existing group seeking another member

Two students already plan to live together and want to find another
compatible person or fill a vacant room.

### Listing creators

A room or flat may be listed by one of three kinds of people. They are
not necessarily students, and each must prove their right to list:

-   **Property owner:** owns the property.
-   **Existing tenant:** rents it and has permission to bring in a
    roommate.
-   **Authorised agent or broker:** acts for the owner, with the owner's
    written authorisation, which Roomie confirms with the owner directly.

Unauthorised brokers are not permitted to publish listings.

**Eligibility:** The initial audience is students. The launch market is
accommodation around SRM KTR; the product should not be hardcoded to
only SRM students. Students from nearby colleges may use it if they are
looking in the supported communities.

## 5. Product principles

-   **People before properties:** roommate compatibility is the main
    differentiator.
-   **Society-first discovery:** users choose specific residential
    communities.
-   **Trust without false guarantees:** identity, student status and
    listing authority are three separate checks, never one "verified"
    badge.
-   **No payments through Roomie:** Roomie never collects rent, deposits
    or brokerage, and nobody may collect payments in Roomie's name.
-   **Privacy by default:** never expose exact residential addresses
    publicly.
-   **Two accommodation journeys:** existing-flat sharing and finding a
    flat together both matter.
-   **Explainable matching:** show the factors behind compatibility.
-   **Modular monolith:** keep the first architecture straightforward
    and maintainable.

## 6. Geographic scope

Initial coverage should be curated around SRM Kattankulathur. Candidate
areas include:

-   Potheri
-   SRM Nagar
-   Kattankulathur
-   Guduvanchery
-   Nearby residential communities along GST Road

These are candidate localities, not a claim that every society or
property in them has been verified. An administrator should create and
maintain the society directory. Each society record should include its
locality, display name, approximate map location and active status.

## 7. Core user journeys

1.  Register, verify email and complete a student profile.
2.  Select one or more preferred societies.
3.  Set budget, move-in date, room and lifestyle preferences.
4.  Discover compatible student profiles.
5.  Like or pass a profile.
6.  Create a match after mutual likes.
7.  Chat with a match.
8.  Create or browse accommodation listings.
9.  Express interest in a listing and contact its owner through an
    authorized conversation flow.
10. Block or report users and listings when necessary.

## 8. Functional requirements

### 8.1 Authentication and account

-   Register with email and password.
-   Verify email before full discovery access.
-   Login, logout and password reset.
-   Secure token/session handling.
-   Account status: active, suspended or deleted.
-   Roles: member and administrator. A member may be a student, a
    property owner or an authorised agent; which one is established by
    their profile and verifications, not by the role.

Email verification does not automatically mean the person's student
status has been verified.

### 8.2 Student profile

Profile fields:

-   Full name
-   Date of birth or age display (privacy controlled)
-   Profile photo
-   College/university
-   Course, department and academic year
-   Short bio
-   Optional gender field, with visibility controls

Students must be able to edit their profile and control visibility of
sensitive fields.

### 8.3 Roommate preferences

Structured preference fields should include:

-   Minimum and maximum monthly budget
-   Expected move-in date
-   Preferred room type
-   Food preference
-   Smoking preference
-   Alcohol preference
-   Sleep and wake schedules
-   Cleanliness expectations
-   Social/quiet preference
-   Guest frequency

Use enumerated values or controlled options where matching depends on
the field. Do not infer sensitive characteristics from photos or free
text.

### 8.4 Society directory

-   Admin-managed localities and societies.
-   Search societies by name and locality.
-   Select multiple preferred societies.
-   Set preference priority.
-   View society details and associated listings.
-   Show approximate location only in public views.

The MVP should not allow arbitrary user-created society names to become
canonical directory entries.

-   A locality (an area) and a society (one named apartment complex or
    villa community) are different records. Plotted layouts and hotels
    are not societies.
-   New records start unverified. Members see a society only after an
    administrator has confirmed its details and verified it, and only
    while both the society and its locality are active.
-   Verification means the details were confirmed. It does not mean
    Roomie has any partnership or arrangement with the society, and the
    product must not suggest otherwise.
-   Every directory change is recorded with who made it, when and why.
-   Duplicate records (the same name written with different capitals or
    punctuation) are refused.
-   Switching a society off never removes members' saved choices. They
    see it marked as no longer available, and it stops counting towards
    a complete profile.
-   Exact addresses and the sources behind a record are visible to
    administrators only.

### 8.5 Discovery

Each discovery card may show:

-   Profile photo
-   Name and age where permitted
-   College
-   Budget range
-   Preferred society/locality
-   Move-in date
-   Selected lifestyle information
-   Compatibility score and a short explanation

Actions: like, pass and view profile.

Rules: - Users cannot like themselves. - A user's decision for a target
should not create duplicate records. - Blocked, suspended and ineligible
accounts must not appear. - Already processed profiles should be
excluded from the normal queue. - A mutual like creates one match. - Do
not reveal incoming likes unless a deliberate product decision enables
that feature.

Clarified in 1.3:

-   "Full discovery access" (8.1) is read as: before confirming their
    email, a student may look at Discover but cannot like or pass, and does
    not appear to others. Student and identity verification are not
    required to take part; each card names both checks truthfully.
-   Eligible means: an active member account, a confirmed email, a
    published profile, and no block in either direction.
-   "Prioritizes people whose accommodation preferences overlap" (section
    1) is read as ordering, not filtering: people sharing a society first,
    then the same locality, then everyone else, by score within each
    group. Cards say when someone is looking elsewhere, so the search is
    never broadened silently.
-   A decision is final in the MVP: repeating it is harmless, changing it
    is refused, and there is no undo.

### 8.6 Compatibility engine

Initial configurable weights:

  Factor                        Weight
  ------------------------- ----------
  Budget compatibility             25%
  Society compatibility            25%
  Lifestyle compatibility          20%
  Move-in date                     15%
  Room preference                  10%
  Food preference                   5%
  **Total**                   **100%**

Each factor returns a normalized score from 0 to 100. The final score is
the weighted sum, rounded to an integer.

The scoring service must: - Compare overlapping budget ranges, not just
exact equality. - Score society overlap and preference priority. -
Compare structured lifestyle choices. - Account for reasonable move-in
date differences. - Treat missing values as unknown, not automatically
as a perfect match. - Be deterministic and unit-tested. - Keep weights
configurable. - Explain the main positive and negative factors.

The score is a decision aid, not a guarantee that two people will be
good roommates.

Clarified in 1.3:

-   A factor that cannot be judged (missing answers, or no society still
    in the directory on one side) is left out, and the remaining weights
    are scaled up in proportion. It is reported as "could not compare".
-   Only societies that are verified and active, in a verified and active
    locality, are compared. Retired or unverified societies never raise a
    score.
-   The weights are one setting (`COMPATIBILITY_WEIGHTS`), validated to
    cover all six factors and add up to 100. The exact per-factor rules
    are in the README ("The compatibility score").

### 8.7 Mutual matching

-   A match is created when two users have active likes toward each
    other.
-   Create the match transactionally.
-   Enforce a uniqueness constraint on the normalized user pair.
-   Notify both users.
-   Enable a conversation for the match.
-   Allow unmatch, block and report actions.

Clarified in 1.3: the match, its conversation and both notifications are
created in the same transaction as the second like. Simultaneous likes
are serialised by a lock on the pair of people, and the database refuses
a second match, conversation or match notification for the same pair.
Notifications are in-app only. Unmatching arrives with messaging (roadmap
Phase 7), and the block and report actions with roadmap Phase 8.

### 8.8 Messaging

MVP messaging: - Text messages. - Persistent message history. - Realtime
delivery using WebSockets. - Timestamps. - Unread counts. - Read status
if implemented reliably. - Access restricted to participants of an
active match.

Images, attachments, voice notes and group chat are later features.

### 8.9 Accommodation listings

Two listing types:

**A. Existing accommodation** - Society - Description - Rent and rent
per person - Deposit, if known - Bedroom count and available rooms -
Furnishing - Availability date - Approximate location - Photos - Current
occupancy - Roommate requirements

**B. Looking to rent together** - Preferred societies (one or more) -
Budget per person - Desired configuration/bedroom count - Current group
size - Number of additional roommates needed - Move-in date -
Preferences and description

Listings must clearly distinguish a search request from an available
property. A listing is not a verified property listing merely because it
appears on Roomie.

**Who may list a property.** Every existing-accommodation listing states
its creator type, and the creator must provide evidence before the
listing can be approved:

| Creator type | Must provide |
| --- | --- |
| Property owner | Proof of ownership |
| Existing tenant | A valid rental agreement, and the landlord's permission where the agreement requires it |
| Authorised agent or broker | Identity verification, written authorisation from the owner, and independent confirmation from the owner obtained by Roomie |

Unauthorised brokers must not be able to publish listings. Joint-search
posts are requests from students and have no creator type.

**Brokerage.** Every existing-accommodation listing must state upfront
whether brokerage applies and, if so, how much. Roomie does not process
it.

**No payments in Roomie's name.** Nobody may ask for or collect rent,
deposits, brokerage or any other payment under Roomie's name.

**Two independent statuses.** Each listing has:

-   a **lifecycle status** controlled by its creator: draft, active,
    filled, closed;
-   a **moderation status** controlled by administrators: pending,
    approved, rejected, suspended.

A listing is publicly discoverable **only** when its lifecycle status is
active **and** its moderation status is approved. Pending, rejected and
suspended listings never appear in public discovery. The two statuses
are kept separate and are never merged into one.

### 8.10 Listing interest

-   Users can express interest in a listing.
-   Listing owners can review interested profiles.
-   Prevent duplicate interests by the same user.
-   Provide a safe route to start a conversation.
-   Owners can close or mark listings as filled.

### 8.11 Safety and administration

-   Block and unblock users.
-   Report users, messages or listings.
-   Admin review queue.
-   Suspend accounts and moderate listings.
-   Rate-limit authentication, likes and messaging.
-   Keep audit records for administrative actions.
-   Provide privacy controls.
-   Never display exact residential addresses publicly.
-   Restrict access to verification documents.

**Three independent verifications.** These are separate records with
separate statuses and are never combined into one generic "verified"
state:

1.  **Identity verification** confirms the person's identity.
2.  **Student verification** confirms the person is currently enrolled at
    an educational institution.
3.  **Listing authority verification** confirms the person has the right
    to list one specific property.

Examples: a property owner may pass identity and listing authority
without being a student; a student may pass identity and student
verification without any right to list a property; an authorised agent
may pass identity and listing authority without being a student.

Every label shown to users must name the check it refers to. Verification
documents are private: only authorised administrators and the person who
uploaded them may access them. Every review decision is recorded.

## 9. Non-functional requirements

### Security

-   Hash passwords using a modern password-hashing algorithm.
-   Validate all inputs on the server.
-   Enforce authorization on every private endpoint.
-   Protect refresh tokens and session cookies.
-   Restrict message access to conversation participants.
-   Rate-limit sensitive endpoints.
-   Keep secrets out of source control.
-   Use HTTPS in production.

### Performance

-   Paginate discovery, messages and listings.
-   Optimize and resize images.
-   Add indexes for common filters and foreign keys.
-   Avoid loading full message histories in one request.
-   Set practical API response-time targets after baseline testing.

### Reliability

-   Use transactions for match creation and other multi-step writes.
-   Prevent duplicate likes, matches and listing interests.
-   Add database backups.
-   Log application errors and important security events.

### Usability

-   Mobile-first responsive design.
-   Clear onboarding progress.
-   Accessible labels and form validation.
-   Useful empty states.
-   Explain compatibility factors.
-   Avoid exposing unnecessary personal information.

### Maintainability

-   Modular monolith.
-   Separate API, schema, model, repository and service concerns.
-   Version API routes.
-   Use database migrations.
-   Add automated tests and a CI workflow.

## 10. MVP priority

**P0 --- required for first usable release** - Authentication and email
verification - Student profile and preferences - Locality and society
directory - Society selection - Discovery and like/pass - Compatibility
scoring - Mutual matches - Basic private chat - Both listing types -
Listing browsing and interest - Block/report - Listing creator types with
listing authority verification - Identity and student verification -
Listing moderation with the two-status visibility rule - Brokerage
disclosure

**P1 --- important follow-up** - Fuller admin dashboard - Notifications -
More detailed profile visibility controls - Improved discovery filters

**Later** - Group matching - Map-based
discovery - Reviews - Push notifications - Payment or rent-splitting
integrations

## 11. Success metrics

Track: - Registration completion rate - Email-verified student rate -
Profile completion rate - Active users by locality/society - Likes per
active user - Mutual match rate - Match-to-chat conversion - Listing
interest rate - Listings marked filled - User-reported successful
roommate connections - Reports per active user and moderation response
time

Do not optimize only for swipes. The meaningful outcome is successful,
safe roommate connections.

## 12. MVP acceptance criteria

The MVP is ready for a controlled pilot when:

1.  Two separate students can register and verify their email.
2.  Each can create and edit a profile.
3.  Each can select multiple societies.
4.  Discovery returns eligible profiles and excludes blocked or
    processed users.
5.  Compatibility scores are reproducible and covered by tests.
6.  Mutual likes create exactly one match.
7.  Matched users can exchange persistent messages.
8.  A user can create an existing-accommodation listing.
9.  A user can create a joint-accommodation search listing.
10. Users can browse listings and express interest.
11. Users can block and report.
12. Admins can review reports and moderate listings.
    -   An owner, a tenant and an authorised agent can each submit a
        listing with the evidence their creator type requires.
    -   A listing with no approved listing authority cannot be approved,
        and a listing that is not both active and approved never appears
        in public discovery.
    -   Identity, student and listing authority verification are shown
        and stored as three separate things.
13. Core flows work on mobile and desktop.
14. Critical user journeys pass automated end-to-end tests.

## 13. Risks and assumptions

-   The real inventory of societies and available accommodation must be
    researched and curated.
-   Student willingness to share lifestyle information needs validation.
-   A new platform may initially have too few users for useful matches.
-   Property details may be inaccurate or become outdated.
-   Email domains may not cover all eligible colleges.
-   Users may interpret a compatibility percentage as a guarantee.
-   Moderation and verification require operational effort.

Mitigation: start with a narrow pilot, label unverified information
clearly, provide reporting tools, and interview students before
expanding.
