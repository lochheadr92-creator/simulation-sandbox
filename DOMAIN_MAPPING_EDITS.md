## memory/DOMAIN_MAPPING.md — Required edits

### Edit 1: Emotion row (re-assign)

Locate the Emotion row (or the unassigned-cognition section where Emotion is listed).  
Change:

```diff
- Emotion          | unassigned | —
+ Emotion          | Phase 3    | REVISED-DOMAIN-ROADMAP.md; contract pending at Session A
```

If the row uses a different column format, preserve the table alignment and update only the status / pointer cells.

---

### Edit 2: Unassigned-cognition pointer (append)

Locate the unassigned-cognition section (around lines 138–158 per the plan).  
Append the following paragraph after the existing unassigned list, or in the nearest notes / pointer block:

```
Family (partial), Animals, Weather, and Social-interaction extensions are now phased
by REVISED-DOMAIN-ROADMAP.md: Phases 4 (Kinship & Households), 5 (Animal & Ecology
Renewal), 6 (Weather–Behaviour Coupling), and 7 (Social Queue Leg 1). No row in this
table is created or removed until its phase reaches Session A.
```

---

### Edit 3: No other rows touched

Confirm no other status or assignment cells are modified. If Animals, Weather, or
Social-interaction rows exist with "unassigned" or placeholder text, leave them as-is —
the pointer in Edit 2 is the single source of truth for their scheduling.
