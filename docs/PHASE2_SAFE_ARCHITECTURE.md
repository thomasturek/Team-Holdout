# Phase 2 - Safe Candidate-Ranking Architecture

This document starts **only after V1 is integrated, tested, merged, and preserved as a working
submission**. Phase 2 must never put the working V1 at risk.

The objective is to reduce failures on suppliers or negotiation situations that differ substantially
from the training distribution. Instead of allowing ML to construct unrestricted decisions, plain
code generates safe candidate actions, ML ranks them, an uncertainty detector chooses between ML
and the deterministic fallback, and the LLM only communicates the selected decision.

## 0. Entry gate: confirm that V1 is protected

Do not begin Phase 2 until all of the following are true:

- [ ] V1 completes every local simulator case without human intervention.
- [ ] V1 completes a full final rehearsal with parallel waves.
- [ ] At least one complete hosted practice run has succeeded.
- [ ] The deterministic Policy V0 works when ML or the LLM is disabled.
- [ ] Must-haves and alternatives are checked before every acceptance.
- [ ] Standard terms from the supplier quote are included in every cost calculation.
- [ ] LLM timeout and deterministic email fallback are tested.
- [ ] Crash recovery and deadline closing are tested.
- [ ] All tests pass from a clean checkout.
- [ ] The exact final run command is documented.
- [ ] V1 is merged and tagged, for example `v1-working`.

Create Phase 2 on a separate branch. Do not modify or delete the V1 path.

```text
feature/safe-candidate-policy
```

Add a runtime switch from the beginning:

```text
BUYER_POLICY=v1
BUYER_POLICY=v2
BUYER_POLICY=shadow
```

`v1` must remain the default until Phase 2 passes its activation gate.

## 1. Target architecture

```text
Case + supplier profile + thread history
                    |
                    v
        Safe candidate generation in code
                    |
                    v
       Costing, validity and dominance filter
                    |
                    v
        ML ranking + uncertainty detection
              /                 \
        confident              uncertain/OOD
            |                       |
       ML selection          deterministic Policy V0
              \                 /
                    v
          Decision selected by code
                    |
                    v
       LLM/template writes the email only
                    |
                    v
        Final validation, logging and send
```

The invariant is:

> Code owns numbers and safety. ML ranks safe choices. The LLM never changes the decision.

## 2. Interfaces to add

Agree on these interfaces before implementation. If they change an interface in `AGENTS.md`, update
that file deliberately with agreement from the affected roles.

```python
@dataclass
class CandidateAction:
    candidate_id: str
    kind: str                         # send | accept | walk
    supplier_id: str
    term_sheets: list[dict]
    claims: list[Claim]
    questions: list[str]
    intent: str
    buyer_cost: float | None
    saving_vs_open: float | None
    improvement_vs_alternative: float | None
    supplier_value_estimate: float | None
    features: dict[str, float | int | str | bool]
    valid: bool
    rejection_reasons: list[str]


@dataclass
class PolicySelection:
    decision: Decision
    policy_source: str                # v2_ml | v0_fallback | deadline
    confidence: float
    ood_reasons: list[str]
    ranked_candidates: list[dict]
```

Every decision log must contain `policy_source`, `confidence`, `ood_reasons`, candidate costs, the
selected candidate, and the reason it was selected.

## 3. Work packages by role

The four roles can work in parallel after the interfaces above are agreed.

### THE SCOUT - safe candidate inputs and safety shield

Owns the exact facts and euro calculations used by the candidate generator and validator.

#### S1. Expose complete candidate-cost features

- [ ] Return total buyer cost for every complete term sheet.
- [ ] Return cost deltas for each negotiable lever.
- [ ] Include supplier standard terms in every calculation.
- [ ] Return alternative cost and whether a candidate beats it.
- [ ] Return must-have validity and uncovered-need cost.
- [ ] Return the supplier-value and relationship-cost estimate where applicable.
- [ ] Attach confidence and provenance to floor, cash-rate, and supplier-health estimates.

#### S2. Implement the safety shield

Create a single validator that rejects a candidate when:

- [ ] A term is missing or outside `term_options`.
- [ ] A must-have is broken.
- [ ] The candidate accidentally leaves expensive uncovered need.
- [ ] Acceptance costs more than the alternative.
- [ ] The supplier standing offer or term-sheet ID is stale.
- [ ] A claim has an unknown ID, incorrect figure, invalid window, or has already been used.
- [ ] Strategic/bottleneck supplier-health risk exceeds the configured safe limit.

The Analyst must not duplicate these rules.

#### S3. Provide uncertainty inputs

- [ ] Mark missing or low-confidence supplier features explicitly.
- [ ] Provide normalized numeric features with stable names and units.
- [ ] Provide indicators for unseen negotiable fields, unknown archetypes, and absent documents.
- [ ] Add controlled perturbations for uncertain floor and cash-rate estimates so the Analyst can
      test decision sensitivity.

#### S4. Tests

- [ ] Every generated claim passes the local fact checker.
- [ ] Invalid and dominated term sheets are correctly identified.
- [ ] No accepted candidate can break a must-have or lose to the alternative.
- [ ] Cost features match `arena_kit.total_cost` exactly.

### THE ANALYST - candidate generation, ranking and OOD fallback

Owns all strategic choices after consuming Scout outputs.

#### A1. Implement deterministic candidate generation

Generate a bounded set of complete candidate actions from:

- [ ] The supplier's current standing terms.
- [ ] Allowed `term_options` and fixed terms.
- [ ] Policy V0 anchor and concession schedule.
- [ ] Buyer reference terms and the alternative.
- [ ] Supplier floor, cash pressure, capacity, quality, and archetype estimates.
- [ ] Previous supplier reactions and concession history.
- [ ] Remaining rounds and wave time.

Candidate families should include:

- [ ] Reference payment terms with several safe price steps.
- [ ] Faster payment traded for a lower price when cash pressure is plausible.
- [ ] Longer commitment or volume traded for price/capacity when permitted.
- [ ] Later effective date traded against price increases.
- [ ] Lead-time and quality variants for capacity/quality cases.
- [ ] Index-clause variants for raw-material cases.
- [ ] Accept and walk-away candidates when legally/economically available.

Filter candidates through the Scout's safety shield. Remove duplicates and candidates dominated on
buyer cost and supplier value. Keep the set small enough to rank quickly.

#### A2. Build the ML ranker

The model ranks `CandidateAction` objects; it does not generate prices or terms.

- [ ] Define a fixed state/candidate feature schema.
- [ ] Train multiple small models with different seeds or bootstrap samples.
- [ ] Output expected negotiation value for every candidate.
- [ ] Record the complete ranking, not only the winner.
- [ ] Keep inference comfortably below one second.

Prefer a small, interpretable model or parameterized policy over a large model that is difficult to
validate during the hackathon.

#### A3. Implement uncertainty/OOD detection

Combine several independent signals:

- [ ] Distance to the nearest normalized training states.
- [ ] Disagreement between ensemble members.
- [ ] Instability under Scout-provided feature perturbations.
- [ ] Missing critical supplier/case information.
- [ ] Unseen case type, category goal, negotiable field, or supplier archetype.
- [ ] Predicted actions that disagree strongly with Policy V0.

Do not trust the model's probability alone. Produce `confidence` and explicit `ood_reasons`.

#### A4. Route uncertain states safely

- [ ] High confidence: use the ML-ranked safe candidate.
- [ ] Medium confidence: restrict ML to conservative candidate families.
- [ ] Low confidence/OOD: use deterministic Policy V0.
- [ ] Deadline near: use deterministic closing policy regardless of ML confidence.
- [ ] Acceptance and walk-away remain protected by the Scout safety shield.

#### A5. Train for robustness

- [ ] Use wide domain randomization for floors, margins, patience, authority, cash pressure,
      capacity, concession curves, claim sensitivity, and final-offer behavior.
- [ ] Include suppliers that ignore valid arguments or behave inconsistently.
- [ ] Optimize mean score, 10th-percentile score, zero-score rate, bad accepts, and timeouts.
- [ ] Validate with leave-one-supplier, leave-one-archetype, and leave-one-case-type-out splits.
- [ ] Add range-extrapolation and missing-data stress tests.
- [ ] Verify that withheld case types trigger safe fallback instead of confident ML control.

#### A6. Tests

- [ ] Every selected candidate came from the validated candidate set.
- [ ] OOD examples reliably activate Policy V0.
- [ ] Deadline always overrides normal ranking.
- [ ] V2 matches or beats V1 on held-out cases without increasing zero scores.

### THE DIPLOMAT - parallel understanding and decision-safe writing

Owns language understanding and generation, never commercial decisions.

#### D1. Separate analysis from final writing

While the Scout and Analyst prepare candidates, run the LLM reader concurrently to extract:

- [ ] Tone and irritation.
- [ ] Cash, capacity, approval, quality, or logistics signals.
- [ ] Supplier asks and objections.
- [ ] Accepted/rejected arguments.
- [ ] Final-offer language.
- [ ] Questions that still require answers.

The LLM may prepare offer-independent wording, but it must not commit to a price, concession,
acceptance, or walk-away before `PolicySelection` exists.

#### D2. Implement decision-safe final assembly

- [ ] The final writer receives the selected `Decision`, not the candidate list.
- [ ] Claims are inserted verbatim.
- [ ] All commercial numbers come from the selected decision.
- [ ] Accept/counter/walk wording matches the selected action exactly.
- [ ] A code validator rejects foreign numbers, unknown IDs, and contradictory commitment language.
- [ ] Deterministic templates cover send, accept, walk, final offer, RFQ, quality, and capacity.

#### D3. Avoid unnecessary second LLM calls

Prefer deterministic assembly of:

```text
prepared relationship language
+ selected intent
+ verified claims
+ selected questions
+ term-sheet summary
+ closing language
```

Only make a final LLM call if time permits and the deterministic version is insufficient. The
template path must always remain available.

#### D4. Tests

- [ ] Generated prose cannot change the selected action or terms.
- [ ] No email contains a number or ID that did not come from the decision/profile.
- [ ] Template fallback works for every action and case type.
- [ ] Parallel reader latency remains inside the Operator's per-move budget.

### THE OPERATOR - feature flags, concurrency, shadow mode and observability

Owns runtime safety and evidence for deciding whether V2 is ready.

#### O1. Add policy modes

- [ ] `v1`: current working architecture.
- [ ] `v2`: safe candidate generation + ML ranking + OOD fallback.
- [ ] `shadow`: V1 controls the real negotiation; V2 decides and logs but is never sent.
- [ ] One environment-variable change returns the system to V1.

#### O2. Parallelize the safe work

On each supplier reply, run concurrently where dependencies allow:

- [ ] Attachment parsing and data/profile updates.
- [ ] Fast rule-based signal extraction.
- [ ] LLM signal extraction and offer-independent language preparation.
- [ ] Candidate generation that does not depend on new LLM signals.

After all required signals are available, perform final ranking, selection, assembly, validation,
and send. The Operator enforces the total move deadline.

#### O3. Implement shadow mode

For every real V1 decision:

- [ ] Run V2 on the same state without sending it.
- [ ] Log V1 and V2 decisions, buyer cost, confidence, OOD reasons, and latency.
- [ ] Record whether V2 would accept, counter, or walk.
- [ ] Record the estimated opportunity or risk of the disagreement.
- [ ] Ensure shadow computation cannot delay the real V1 move.

#### O4. Extend logging and reports

Create a comparison report containing:

- [ ] Mean and 10th-percentile score.
- [ ] Zero-score and bad-accept rates.
- [ ] V1/V2 action disagreement rate.
- [ ] OOD/fallback frequency by case type.
- [ ] Candidate-generation, ML, LLM, and total decision latency.
- [ ] Timeouts and API/runtime errors.
- [ ] Cases where perturbing uncertain inputs changed the selected action.

#### O5. Failure handling

- [ ] Any V2 exception immediately falls back to V1/Policy V0.
- [ ] Empty candidate set activates Policy V0.
- [ ] ML timeout activates Policy V0.
- [ ] LLM timeout uses a deterministic template.
- [ ] Approaching deadline activates deterministic closing.
- [ ] Crash resume restores the same policy mode and logs.

#### O6. Tests

- [ ] Shadow mode cannot send the V2 decision.
- [ ] Kill-and-restart works in all three modes.
- [ ] Ten parallel cases stay within API and time limits.
- [ ] V2 failures never stop another case or thread.

## 4. Integration sequence

Integrate in this order so each merge leaves the branch runnable:

1. [ ] Agree on `CandidateAction` and `PolicySelection` interfaces.
2. [ ] Merge Operator feature flags and empty shadow-mode plumbing.
3. [ ] Merge Scout cost features, confidence fields, and safety shield.
4. [ ] Merge Analyst deterministic candidate generator without ML.
5. [ ] Run candidate generation in shadow mode against V1.
6. [ ] Merge Analyst ML ranker.
7. [ ] Merge OOD detection and Policy V0 routing.
8. [ ] Merge Diplomat parallel reader and decision-safe assembly.
9. [ ] Run complete local, sandbox, and hosted shadow validation.
10. [ ] Review the activation gate as a team and choose V1 or V2.

After each merge:

- [ ] Rebase or update from the shared integration branch.
- [ ] Run unit and integration tests.
- [ ] Run at least one complete simulator negotiation.
- [ ] Verify that `BUYER_POLICY=v1` still behaves exactly as before.
- [ ] Record important findings in `docs/LEARNINGS.md`.

## 5. Validation matrix

| Test | Required result |
|---|---|
| Normal familiar supplier | V2 selects a valid competitive candidate |
| Unseen supplier | V2 either generalizes safely or falls back |
| Unseen case type | OOD detector activates Policy V0 |
| Unknown negotiable field | Candidate generator handles it generically or falls back |
| Low-confidence floor estimate | Conservative candidate or fallback |
| Missing quote/document | No unsafe acceptance; request information or fallback |
| Incorrect LLM signal | Safety shield prevents invalid commercial action |
| Supplier `final_offer` | Controlled push or safe close according to time/value |
| Good alternative | Never accept a worse deal |
| Broken must-have candidate | Candidate rejected before ranking |
| Approaching wave cap | Deterministic closing move |
| ML/LLM exception | Policy V0/template fallback |
| Crash and restart | Session resumes without duplicate/invalid actions |

## 6. Activation gate

V2 may control hosted/final negotiations only if every item below is true:

- [ ] All V1 tests still pass.
- [ ] V1 remains selectable through one configuration change.
- [ ] V2 produces no invalid term sheets in simulator, sandbox, practice, or stress tests.
- [ ] V2 never accepts a must-have violation or a deal worse than the alternative.
- [ ] V2 matches or beats V1 on held-out real practice cases.
- [ ] V2 does not increase the zero-score rate.
- [ ] Leave-one-supplier and leave-one-case-type tests pass or correctly trigger fallback.
- [ ] Shadow-mode disagreements have been reviewed by the team.
- [ ] OOD thresholds are calibrated and frozen.
- [ ] Full parallel rehearsal finishes without our own timeouts.
- [ ] Total decision latency remains safely below the move deadline.
- [ ] The final frozen commit, parameters, environment variables, and run command are documented.

If any critical item fails, run V1 in the final. Phase 2 remains useful as a demonstrated prototype
and future improvement; it must not weaken the reliable submission.

## 7. Final team review

Before activating V2, hold one short review with all four roles:

- **SCOUT:** Are every candidate's numbers, claims, standard terms, and constraints correct?
- **ANALYST:** Does ML improve decisions, and does uncertainty reliably cause fallback?
- **DIPLOMAT:** Can the language layer ever contradict the selected decision?
- **OPERATOR:** Can V2 fail without delaying, crashing, or corrupting the negotiation?

Record the decision in `docs/LEARNINGS.md`:

```text
Chosen final policy: v1 | v2
Frozen commit:
Frozen parameter version:
Validation evidence:
Known limitations:
Rollback command:
```

The final principle is simple:

> V2 is activated only when it is demonstrably safer and better. A reliable V1 always remains the
> fallback and a valid final submission.
