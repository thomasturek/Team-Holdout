# V3 - Robustness, Adversarial Validation, and Calibrated Fallback

## Purpose

V3 does not replace the V2 safe candidate-ranking architecture. It proves that V2 behaves safely
when a negotiation differs from its training distribution and improves the mechanisms that decide
when ML may be trusted.

The central objective is:

> Familiar states may use ML ranking. Unfamiliar, unstable, or poorly understood states must
> automatically use a deterministic fallback without violating commercial constraints.

V3 focuses on tests, uncertainty calibration, adversarial cases, and measurable robustness. It
must not weaken the working V1 or V2 paths.

## Entry gate

Do not start V3 until:

- [ ] V1 is merged, tested, and tagged as a working submission.
- [ ] V2 generates candidate offers in deterministic code.
- [ ] Every V2 candidate passes must-have, alternative, completeness, and cost checks.
- [ ] ML ranks candidates instead of generating unrestricted terms.
- [ ] Policy V0 remains available as a deterministic fallback.
- [ ] V2 has `v1`, `v2`, and `shadow` runtime modes.
- [ ] V2 decisions log candidate features, ranking, confidence, and policy source.
- [ ] A full parallel rehearsal finishes without timeouts caused by the buyer.

If an entry requirement is missing, fix V2 first.

## Non-negotiable invariants

V3 must preserve these properties under every generated or mutated test:

1. Never accept a term sheet that violates a must-have.
2. Never accept a deal that costs more than the valid alternative.
3. Never send an incomplete or API-invalid term sheet.
4. Never cite an unknown or incorrectly calculated data ID.
5. Never let LLM prose modify the selected action, terms, claims, or IDs.
6. Never start a long negotiation step when the deadline requires closing.
7. Never allow an ML/OOD/LLM exception to stop another case or thread.
8. Increasing uncertainty must not increase confidence.

## Target pipeline

```text
Valid parent case
       |
       v
Programmatic and LLM-proposed mutations
       |
       v
Schema validation
       |
       v
Economic-consistency validation
       |
       v
Novelty classification: ID / near-OOD / far-OOD
       |
       v
Property and oracle assignment
       |
       v
V1, V2, V3, and Policy V0 execution
       |
       v
Confidence calibration and failure analysis
```

LLMs propose creative tests. Deterministic code decides whether a case is valid and whether its
objective properties pass.

## Shared test-case record

Agree on a stable representation before role-specific work starts:

```python
@dataclass
class AdversarialCase:
    case_id: str
    parent_case_id: str | None
    generator: str                 # programmatic | llm | human
    generator_version: str
    seed: int
    mutations: list[str]
    distribution: str              # in_distribution | near_ood | far_ood
    case: dict
    scripted_responses: list[dict]
    expected_properties: list[str]
    expected_policy: str | None     # ml | conservative_ml | fallback | deadline
    validation: dict
```

Every retained test must be reproducible from its seed or stored as a versioned fixture.

## Test portfolio

Aim for this distribution:

| Test class | Share | Purpose |
|---|---:|---|
| Property and boundary tests | 40% | Catch objective commercial and numerical failures |
| Near-OOD mutations | 30% | Catch confidently wrong generalization |
| Conflicting-signal cases | 15% | Test supplier interpretation and belief reliability |
| Missing-data cases | 10% | Verify confidence reduction and fallback |
| Extreme opposite cases | 5% | Verify far-OOD detection and system survival |

Do not allow extreme cases to dominate. Subtle near-OOD cases are usually more dangerous.

## Mutation catalog

### Boundary mutations

- Alternative cost EUR 0.01 above or below the proposed deal.
- Must-have exactly at, immediately above, and immediately below its boundary.
- Contract coverage just below, exactly at, and above the buyer horizon.
- Payment at 59, 60, and 61 days when 60 is the reference.
- Lead time immediately around the required lead time.
- Supplier margin immediately around the sustainable margin.
- Deadline immediately around the closing threshold.
- Index deadband immediately around expected movement.

### Preference reversals

- Cash-stressed supplier rejects early-payment packages.
- Financially strong supplier strongly values early payment.
- Family-owned supplier uses a strict approval ladder.
- Group supplier can approve large concessions immediately.
- Capacity-constrained supplier rejects long commitments.
- Supplier with available capacity demands a long contract.

### Familiar-looking traps

- Low unit price but expensive uncovered need.
- Cheap EXW offer that loses to DAP after freight.
- Attractive price with poor PPM commitment and high defect cost.
- Familiar price-increase case where effective date dominates price.
- Normal-looking renewal where walking away is optimal.
- Accepted evidence that produces no commercial concession.

### Conflicting signals

- Profile indicates cash pressure while correspondence denies it.
- Strong historical quality with a new severe quality event.
- Warm tone combined with a credible walk-away boundary.
- `final_offer` language followed by a further concession.
- Supplier requests volume but responds more strongly to payment.
- Supplier changes package preference between rounds.

### Missing and corrupted context

- No should-cost record.
- Unknown supplier archetype.
- Missing or incomplete quote standard terms.
- Missing correspondence and notes.
- New market index series.
- Unseen negotiable-field combination.
- One low-confidence or contradictory supplier-profile feature.

### Negotiation-sequence mutations

- No concession for several rounds followed by a large move.
- Very slow supplier response near the wave cap.
- One RFQ thread reaches `final_offer` while another is still opening.
- Supplier contradicts an earlier statement.
- Supplier becomes irritated after duplicate arguments.
- Best apparent supplier unexpectedly walks away.

## Quality gates for generated tests

### Gate 1 - Schema validity

Deterministic validation must confirm:

- [ ] Documented case type and category goal.
- [ ] Valid buyer, fixed-term, negotiable, and option fields.
- [ ] Valid dates, units, identifiers, and must-have operators.
- [ ] Complete term sheets and valid supplier statuses.
- [ ] Internally consistent supplier messages and standing offers.

### Gate 2 - Economic consistency

Use the official cost function to confirm:

- [ ] Opening, alternative, need, coverage, and horizon are coherent.
- [ ] At least one valid action exists, unless the intended solution is no-deal.
- [ ] Price units and quantities are plausible.
- [ ] The intended trap is real in total-cost terms.
- [ ] Supplier parameters permit the scripted behavior.

### Gate 3 - Objective properties

Each test must have one or more machine-checkable expectations, for example:

```text
must_not_accept
must_fallback
must_close_before_deadline
must_rank_A_above_B
confidence_must_decrease
must_not_use_claim_twice
must_select_lower_total_cost_when_supplier_value_is_equal
```

Do not keep a test solely because an LLM says it is difficult.

### Gate 4 - Novelty classification

Calculate:

- Standardized distance to training states.
- Unseen categorical combinations.
- Range violations.
- New supplier/case/term combinations.

Label the case as in-distribution, near-OOD, or far-OOD. Review cases whose measured novelty does
not match the intended mutation.

### Gate 5 - Independent criticism

A second model or prompt may criticize realism, hidden contradictions, and triviality. This is an
additional filter only; deterministic validators remain authoritative.

## Role plan

### THE SCOUT

Mission: build objective validity, economic consistency, and property oracles.

- [ ] Implement the schema validator for generated cases and responses.
- [ ] Implement the economic-consistency validator using official costing.
- [ ] Create boundary and metamorphic transformations.
- [ ] Define machine-checkable commercial invariants.
- [ ] Generate uncertain-input perturbations for floor, cash rate, quality, and capacity.
- [ ] Validate every claim and ID used in adversarial fixtures.
- [ ] Report why a generated test was rejected.

Metamorphic properties should include:

- Raising EXW freight cannot make an otherwise identical EXW offer more attractive.
- Improving the alternative cannot make accepting a worse deal more appropriate.
- Raising defect cost cannot improve a high-PPM candidate's ranking.
- Reducing remaining time cannot increase willingness to start a long probe.
- Removing reliable evidence cannot increase confidence.

Definition of done:

- Zero retained cases with invalid economics or unsupported claims.
- Every retained test has at least one objective property.

### THE ANALYST

Mission: build adversarial mutations, calibrated uncertainty, and robust policy evaluation.

- [ ] Implement near-OOD and far-OOD mutation operators.
- [ ] Train an ensemble of small rankers using independent seeds/bootstrap samples.
- [ ] Measure ensemble disagreement for every candidate ranking.
- [ ] Implement nearest-training-state distance.
- [ ] Test action stability under Scout-provided perturbations.
- [ ] Combine disagreement, distance, missingness, and instability into confidence/OOD reasons.
- [ ] Define high-, medium-, and low-confidence routing.
- [ ] Optimize mean score, 10th percentile, zero-score rate, bad accepts, and timeouts.
- [ ] Run leave-one-supplier, leave-one-archetype, and leave-one-case-type-out evaluation.

Suggested routing structure:

```python
if deadline_near:
    return deterministic_closing()
if confidence >= high_threshold:
    return ml_ranked_candidate()
if confidence >= medium_threshold:
    return conservative_candidate_ranking()
return policy_v0()
```

Thresholds must be selected on the development set, never on the locked evaluation set.

Definition of done:

- Far-OOD states usually fall back.
- Near-OOD unsafe decisions are materially lower than V2.
- Normal-case performance is not materially degraded.

### THE DIPLOMAT

Mission: adversarially test signal extraction and guarantee decision-safe language.

- [ ] Generate supplier emails containing conflicting, indirect, and misleading signals.
- [ ] Include polite final offers, irritated non-final offers, approval ambiguity, and bluffing.
- [ ] Create expected `Signals` fixtures for selected adversarial messages.
- [ ] Measure reader precision/recall for cash, capacity, approval, finality, asks, and tone.
- [ ] Confirm incorrect signals cannot bypass the candidate safety shield.
- [ ] Test that final prose cannot introduce foreign numbers, IDs, or commitments.
- [ ] Test deterministic templates on every adversarial action.

Definition of done:

- Language failures may reduce strategy quality but cannot create an invalid commercial action.
- Template fallback succeeds for every case/action combination.

### THE OPERATOR

Mission: create the reproducible harness, dataset partitions, reports, and runtime stress tests.

- [ ] Build one command that runs V1, V2, V3, and Policy V0 on the same suite.
- [ ] Store seeds, generator versions, fixtures, decisions, latencies, and results.
- [ ] Enforce separate training, development, and locked evaluation sets.
- [ ] Prevent training code from reading the locked evaluation directory.
- [ ] Add parallel-load, deadline, retry, crash-resume, and timeout tests.
- [ ] Produce automated comparison reports.
- [ ] Add failure clustering by mutation, case type, archetype, and OOD reason.

Required metrics:

- Mean, median, 10th-percentile, and worst-case score.
- Zero-score rate.
- Invalid-offer and bad-accept rate.
- Correct walk-away rate.
- OOD detection recall and false-fallback rate.
- Confidence calibration error.
- V1/V2/V3 disagreement rate.
- Candidate generation, ranking, LLM, and total latency.
- Buyer-caused timeouts and runtime failures.

Definition of done:

- Test runs are reproducible.
- Shadow or evaluation failures cannot affect a real negotiation.
- Reports allow the team to decide objectively whether V3 is safer.

## Dataset discipline

Maintain three isolated sets:

```text
tests/generated/train/
tests/generated/development/
tests/generated/locked/
```

- Training failures may be added to training after review.
- Development failures may guide thresholds, prompts, and features.
- Locked failures must not be used to tune or retrain the evaluated version.
- Create a new locked suite only for a later, clearly versioned evaluation cycle.

## Confidence calibration

Produce reliability tables:

| Confidence band | Count | Correct safe action | Unsafe action | Fallback rate |
|---|---:|---:|---:|---:|
| 0.0-0.2 | | | | |
| 0.2-0.4 | | | | |
| 0.4-0.6 | | | | |
| 0.6-0.8 | | | | |
| 0.8-1.0 | | | | |

Confidence is useful only if higher confidence corresponds to greater observed reliability.

## Integration order

1. [ ] Agree on `AdversarialCase` and objective property vocabulary.
2. [ ] Merge the Operator harness and dataset isolation.
3. [ ] Merge Scout schema/economic validators and property generators.
4. [ ] Add deterministic boundary and metamorphic tests.
5. [ ] Add Analyst novelty metrics and OOD reports without changing routing.
6. [ ] Add LLM-proposed near-OOD mutations behind quality gates.
7. [ ] Add ensemble disagreement and perturbation stability.
8. [ ] Calibrate routing thresholds on the development set.
9. [ ] Run the locked evaluation exactly once for the release candidate.
10. [ ] Review results as a four-person team and freeze or reject V3.

## Activation gate

V3 may replace V2 as the default only if:

- [ ] All V1 and V2 safety tests still pass.
- [ ] Zero invalid term sheets are sent.
- [ ] Zero must-have violations are accepted.
- [ ] Zero deals worse than the alternative are accepted.
- [ ] Far-OOD fallback recall meets the agreed target.
- [ ] Near-OOD unsafe decisions are significantly lower than V2.
- [ ] Confidence is measurably calibrated.
- [ ] False fallback does not materially destroy normal-case performance.
- [ ] Mean score is acceptable and 10th-percentile/worst-case results improve.
- [ ] Full parallel rehearsal introduces no buyer-caused timeouts.
- [ ] V1 and V2 remain available through configuration flags.

If V3 fails this gate, run V2 or V1. Keep the test suite and findings for later work.

## Final deliverables

- Versioned adversarial-case schema and mutation catalog.
- Programmatic boundary and metamorphic test generator.
- Quality-controlled LLM mutation generator.
- Schema and economic-consistency validators.
- Ensemble/OOD/confidence implementation.
- Isolated training, development, and locked suites.
- V1/V2/V3 comparison report.
- Documented thresholds, known limitations, and rollback command.

