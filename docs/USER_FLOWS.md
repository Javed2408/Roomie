# ROOMIE --- User Flows and Screen Requirements

**Version:** 1.3\
**Date:** 17 November 2026

**Changes in 1.3:** Flow B (section 4) describes Discover as built: card
order, the email confirmation step, final decisions, the match moment and
how each empty state appears.

**Changes in 1.2:** the society directory edge cases in Flow A (section 3).

**Changes in 1.1:** three listing creator types, two independent listing
statuses and three independent verification types. See sections 1, 5, 9
and 11.

## 1. Roles

-   **Visitor:** can view public landing and product information.
-   **Member:** an account with a verified email. A member may be a
    student (with a student profile), a property owner or an authorised
    agent. Students use discovery and matching; any member may create a
    listing if they can prove the right to.
-   **Administrator:** manages societies, reports, accounts, listings
    and verification reviews.

Email verification proves only that the email address works. Identity,
student status and listing authority are three further, separate
verifications (section 9).

## 2. Primary navigation

Suggested student navigation:

-   Discover
-   Matches
-   Messages
-   Accommodation
-   Saved (optional later)
-   Profile

On mobile, use a compact bottom navigation. On desktop, use a sidebar or
top navigation.

## 3. Flow A --- Registration and onboarding

``` mermaid
flowchart TD
    A([Open Roomie]) --> B[Register with email and password]
    B --> C[Verify email]
    C --> D[Enter student details]
    D --> E[Upload profile photo]
    E --> F[Set budget and move-in date]
    F --> G[Select preferred societies]
    G --> H[Set lifestyle preferences]
    H --> I[Review profile and privacy]
    I --> J[Publish profile]
    J --> K([Open Discover])
```

### Screens and requirements

1.  **Register**
    -   Email, password, confirm password.
    -   Terms and privacy acknowledgement.
    -   Inline validation and clear errors.
2.  **Verify email**
    -   Explain that the verification link/code was sent.
    -   Allow resend with rate limits.
    -   Handle expired and already-used tokens.
3.  **Student details**
    -   Name, college, course, department, year.
    -   Only collect data needed for the product.
    -   Do not expose date of birth by default.
4.  **Profile photo and bio**
    -   Upload image.
    -   Validate file type and size.
    -   Allow skip if product policy permits.
5.  **Accommodation preferences**
    -   Minimum/maximum monthly budget.
    -   Move-in date.
    -   Room type.
    -   Select multiple societies.
6.  **Lifestyle preferences**
    -   Structured choices for food, smoking, alcohol, sleep,
        cleanliness, social preference and guests.
    -   Explain why these questions help compatibility.
7.  **Review**
    -   Preview what other students can see.
    -   Let user edit privacy settings.
    -   Publish.

### Edge cases

-   Email already registered.
-   Verification link expired.
-   User closes browser mid-onboarding.
-   Society directory has no suitable society. Say so plainly; the
    student cannot type in a society of their own.
-   The directory has no verified societies at all. Explain that each one
    is added only after being checked.
-   A society the student saved is later switched off. Keep the choice,
    mark it "No longer available", and ask them to choose another.
-   The student tries to choose more societies than allowed (five).
-   User skips optional fields.
-   Profile is incomplete.

Save onboarding progress so a student can continue later.

## 4. Flow B --- Discover and swipe

``` mermaid
flowchart TD
    A([Open Discover]) --> B[Fetch eligible student profiles]
    B --> C[Exclude self, blocked, suspended and processed profiles]
    C --> D[Apply society and eligibility filters]
    D --> E[Calculate compatibility]
    E --> F[Display profile card]
    F --> G{Student action}
    G -->|View profile| H[Open full profile]
    H --> F
    G -->|Pass| I[Save pass decision]
    G -->|Like| J[Save like decision]
    J --> K{Reciprocal active like?}
    K -->|Yes| L[Create unique match]
    K -->|No| M[Continue discovery]
    I --> M
    L --> N[Notify both students]
    N --> O[Enable conversation]
    M --> F
```

### Discovery card

Display: - Profile photo - Name and permitted age display -
College/course - Budget range - Preferred society/locality - Move-in
date - A few lifestyle preferences - Compatibility score - Short
explanation such as "Same preferred society" or "Overlapping budget"

### Rules

-   A user cannot swipe on themselves.
-   One active decision per actor/target pair.
-   Repeated requests should be idempotent.
-   A blocked relationship removes both users from each other's
    discovery.
-   Passing should not be treated as a match.
-   Do not expose a user's incoming likes in the MVP.

As built (Phase 5):

-   **Order.** People who share a society come first, then people in the
    same area, then everyone else; the best score first in each group.
    Each card is labelled "Shares your societies", "Same area as you" or
    "Looking in another area".
-   **Deciding.** Pass and Like buttons sit under the card and stay in
    reach at the bottom of the screen. A card can also be dragged: right
    to like, left to pass. The next card then appears in place, with the
    person's name brought back into view.
-   **Final decisions.** A like or pass cannot be changed. Someone you
    passed on is not told and does not come back.
-   **Match moment.** If the other person already liked you, a "You
    matched with ..." dialog appears straight away, with a link to
    Matches. Both people get a "New match" notification on the dashboard,
    and the match is marked "New match" on the Matches page until seen.
-   **Before email confirmation.** Discover can be browsed, but Like and
    Pass are disabled with an explanation, and the student does not
    appear to anyone.

### Empty states

-   No profiles match current societies.
-   No new profiles remain.
-   Profile setup is incomplete.
-   Network error.
-   User needs to broaden society preferences.

Offer a clear way to edit society preferences without silently
broadening the search.

As built: an incomplete profile shows "Finish your profile first" with a
link to onboarding. An empty deck shows "You're all caught up" with "Check
again". A failed load shows the reason with "Try again". When the deck
reaches people who share none of the student's societies or areas, a note
says so and links to editing societies. If none of the student's own
societies is still in the directory, a note explains that societies are
not being compared and links to choosing them again.

## 5. Flow C --- Existing accommodation

``` mermaid
flowchart TD
    A([Accommodation]) --> B[Create listing]
    B --> C[Choose Existing Accommodation]
    C --> C1[State creator type: owner, tenant or agent]
    C1 --> D[Select society]
    D --> E[Enter rent, deposit, brokerage and room details]
    E --> F[Enter availability date]
    F --> G[Add description and photos]
    G --> H[Preview listing]
    H --> I[Submit for review]
    I --> I1[Provide listing authority evidence]
    I1 --> I2{Authority verified and listing approved?}
    I2 -->|No| I3[Rejected with a reason; fix and resubmit]
    I3 --> I1
    I2 -->|Yes| J[Listing is public: receive listing interests]
    J --> K[Review interested profiles]
    K --> L[Choose a student to connect with]
    L --> M[Start or request authorized conversation]
    M --> N[Discuss details and arrange viewing]
    N --> O{Room filled?}
    O -->|Yes| P[Mark listing filled]
    O -->|No| J
```

### Listing form

Required: - Listing type - Creator type (owner, existing tenant or
authorised agent) - Society - Rent per person - Whether brokerage
applies, and the amount if it does - Availability date - Description -
Number of available spaces - Confirmation that the creator has the right
to list the property

Optional/conditional: - Total rent - Deposit - Bedrooms - Furnishing -
Photos - Approximate location - Current occupancy

### Listing detail

Show: - Society and locality - Rent and deposit clearly labelled -
Brokerage, stated either way ("No brokerage" or the amount) -
Availability - Room and furnishing details - Photos - Who posted it and
their creator type - The poster's identity verification and the
listing's authority verification, as two separately named labels

Do not display an exact unit number or private address publicly.

### Listing authority evidence

| Creator type | Evidence required before approval |
| --- | --- |
| Property owner | Proof of ownership |
| Existing tenant | Valid rental agreement; landlord's permission where required |
| Authorised agent | Approved identity verification; the owner's written authorisation; confirmation obtained by Roomie directly from the owner |

Evidence is uploaded privately and is visible only to the uploader and
to authorised administrators. An agent's own paperwork is never enough:
an administrator must reach the owner independently.

### Listing statuses

A listing has two separate statuses, shown separately in "My listings":

-   **Lifecycle**, set by the creator: draft, active, filled, closed.
-   **Moderation**, set by administrators: pending, approved, rejected,
    suspended.

Other people can find a listing only while it is **active and
approved**. A pending, rejected or suspended listing is visible only to
its creator and to administrators. The creator is shown the reason for a
rejection or suspension.

Nobody may request or collect any payment in Roomie's name, and the
interface must say so wherever money is mentioned.

## 6. Flow D --- Find a flat together

``` mermaid
flowchart TD
    A([Accommodation]) --> B[Create search]
    B --> C[Choose Find Together]
    C --> D[Select preferred societies]
    D --> E[Set per-person budget]
    E --> F[Set flat configuration]
    F --> G[Set current group size]
    G --> H[Set additional people needed]
    H --> I[Set move-in date and preferences]
    I --> J[Publish search]
    J --> K[Browse compatible search posts and students]
    K --> L[Express interest or like]
    L --> M[Connect after required mutual consent]
    M --> N[Discuss group requirements]
    N --> O[Coordinate flat search]
    O --> P([Update or close search])
```

### Important product rule

A joint accommodation search is a requirement post, not a property
listing. The interface must label it clearly so nobody mistakes it for a
confirmed available flat.

For MVP, group coordination can happen through a listing-interest flow
and one-to-one conversations. Full group chat and group membership
management are later features.

## 7. Flow E --- Match and chat

``` mermaid
flowchart TD
    A([Mutual like]) --> B[Create match transactionally]
    B --> C[Create or enable conversation]
    C --> D[Notify both users]
    D --> E[Open Matches]
    E --> F[Open conversation]
    F --> G[Send and receive messages]
    G --> H{User action}
    H -->|Continue| G
    H -->|Unmatch| I[Deactivate match]
    H -->|Block| J[Block user and restrict access]
    H -->|Report| K[Create report for moderation]
```

### Chat rules

-   Only participants of the match can access its conversation.
-   Verify authorization on every message read/write.
-   Store messages persistently.
-   Realtime delivery must not bypass authorization.
-   Blocking should prevent further contact.
-   Unmatching should disable new messages; retention/deletion policy
    must be documented.
-   Reported content should be available to authorized moderators under
    a defined policy.

## 8. Flow F --- Report and block

1.  Student opens profile, listing or conversation menu.
2.  Student selects Report or Block.
3.  Report form asks for a category and optional details.
4.  Backend records the report.
5.  Block takes effect immediately.
6.  Admin reviews report.
7.  Admin may dismiss, warn, remove listing or suspend account.
8.  Record moderator action in an audit log.

Never promise instant human review unless an operational process exists.

## 9. Administrator flows

### Society management

-   Create locality.
-   Add society.
-   Edit name/address/approximate coordinates.
-   Mark society active/inactive.
-   Review duplicate suggestions.

### Listing moderation

-   Review the queue of pending listings.
-   Approve, reject or suspend a listing; a reason is required to reject
    or suspend.
-   An existing-accommodation listing can be approved only after its
    listing authority verification is approved.
-   View reported listings and inspect listing and report context.
-   Every decision is recorded with who made it, when and why.

### User moderation

-   Review reports.
-   Inspect relevant account history.
-   Warn, suspend or restore account.
-   Keep an audit trail.

### Verification

There are three separate review queues, one per verification type:

-   **Identity:** check a government identity document against the
    account.
-   **Student:** check current enrolment (college email, student ID or
    enrolment proof).
-   **Listing authority:** check the evidence for the listing's creator
    type. For an authorised agent, contact the owner directly using
    independently checked details and record the outcome.

For each: approve, reject or request resubmission, with a note. Approving
one type never changes another. Document access is restricted to
authorised administrators. Evidence is deleted according to a documented
retention policy, and every decision is recorded.

## 10. Screen inventory

  Screen                    Purpose                               MVP
  ------------------------- ------------------------------------- -----
  Landing page              Explain Roomie and signup             Yes
  Register/login            Account access                        Yes
  Email verification        Verify email                          Yes
  Onboarding                Collect profile/preferences           Yes
  Discover                  Browse roommate profiles              Yes
  Full profile              Inspect details                       Yes
  Matches                   View mutual connections               Yes
  Chat                      Message matches                       Yes
  Accommodation directory   Browse both listing types             Yes
  Create listing            Create either listing type            Yes
  Listing detail            Inspect accommodation/search          Yes
  My listings               Manage own listings                   Yes
  Profile/settings          Edit details and privacy              Yes
  Report/block              Safety controls                       Yes
  Admin dashboard           Moderation and directory management   P1

## 11. Global UX rules

-   Mobile-first responsive layouts.
-   Show loading, empty, success and error states.
-   Confirm destructive actions.
-   Avoid exposing exact addresses.
-   Explain compatibility factors.
-   Keep existing-flat listings distinct from joint-search posts.
-   Never use a verification badge to imply a different kind of
    verification. Always name the check: identity, student or listing
    authority.
-   Show brokerage on every property listing, including when there is
    none.
-   Never show a listing publicly unless it is both active and approved.
-   Never suggest that Roomie collects or handles payments.
-   Preserve user input when validation fails.
