# FreshWise: From Forecasting Quantities to Preserving Preparation Flexibility

**Decision history, proposed product direction and implementation plan**  
**Date:** November 5, 2026  
**Team:** Ari, Silvia and Lan  
**Status:** Ari supports exploring this direction. Team agreement, operational assumptions and the new experiment are still pending.

> Working thesis: FreshWise should not only ask how much to prepare. It should investigate what to prepare now, what to keep flexible, and what to finish after new information becomes available.

## 1. Executive summary

We began by turning weekly meal-order forecasts into preparation quantities. We built and tested a decision engine, integrated a forecasting component in an isolated environment, and evaluated alternative policies on historical order data under simulated stock and cost assumptions.

The first scenario policy performed worse than a simple baseline. Later empirical approaches improved some metrics but increased excess. After several development experiments, we found a small aggregate improvement using a combined forecast and an empirical preparation target. That improvement was selected on the same development data, was uneven across meals, and has not been confirmed on the reserved final period.

These results do not prove that forecasting or inventory optimization cannot work. They show that our tested fixed-commitment policies did not establish a strong, independently verified reduction in excess while maintaining service.

This led to a different hypothesis: instead of only changing how much supply we commit to before demand is known, can we change **which commitments must be made early**?

The proposed extension investigates shared ingredients or intermediate preparations that can be allocated to different meals later. It compares early meal-specific preparation with delayed finalization under the same initial resources, uncertain demand, realistic capacity constraints and explicitly specified information timing.

We are not deleting the existing work. It becomes the evidence trail, reusable calculation infrastructure and baseline family for a second, clearly labelled synthetic operational experiment.

No flexible-preparation model has been implemented or evaluated yet. There are no new waste-reduction results to report.

## 2. Product reference and original question

The submitted team abstract, `FreshWise_Abstract_team41.pdf`, describes an AI-assisted weekly meal-preparation planning system. It combines forecasting, operational decisions, manager knowledge and a tool-connected assistant. It commits to chronological evaluation and explicitly distinguishes simulated outcomes from measured waste reduction.

The mentor, Abir, reinforced the strongest part of the idea: translating forecasts into preparation decisions. The feedback asked us to identify the variable and objective, explain scenario construction, separate model uncertainty from contextual manager adjustments, use tools for calculations, and compare decision quality against a central-forecast baseline.

Our original operational question was:

> How many additional portions should a manager prepare for the following week?

The intended restaurant use case was broader than the actual source data. The Food Demand Forecasting dataset records weekly meal orders at fulfilment centres. It does not supply real recipes, ingredients, preparation stages, expiry, kitchen capacity or food discarded.

That mismatch was disclosed rather than hidden. The first evaluation therefore used historical orders with simulated inventory and penalties.

## 3. What we built before considering the new direction

### 3.1 Preparation and outcome calculations

We implemented:

- A baseline that covers a central forecast after subtracting usable stock, rounding new preparation up to whole portions.
- Evaluation of excess supply and unmet observed orders.
- An explicit overage/underage penalty function.
- Average loss across supplied demand scenarios.
- An exhaustive integer preparation search, retaining the smaller quantity in a tie.
- A manager-adjustment function and crossed comparisons of original/custom plans.
- Input validation and a documented interface for Lan.

The initial objective was:

```text
supply = usable_inventory + new_preparation
excess = max(supply - observed_orders, 0)
unmet = max(observed_orders - supply, 0)
penalty = overage_penalty * excess + underage_penalty * unmet
```

### 3.2 Manager context

A manager can select an anchor scenario B, give a personal demand estimate M and choose an opinion weight w:

```text
custom_anchor = (1 - w) * B + w * M
adjustment = custom_anchor - B
updated_scenario = max(0, original_scenario + adjustment)
```

The system retains the original assumptions and shows both plans under both scenario sets. This weight is a user preference, not measured reliability, and this formula is not Black–Litterman.

### 3.3 Forecast interface

Silvia supplied a next-week forecast component and a four-meal demo scope. Her reviewed branch used `last` as the point forecast and empirical p10/p90 actual/forecast ratios grouped by forecast size for ranges.

Those ranges were calibrated on weeks 116–125. We started the decision comparison at week 126 to avoid applying later calibration information to earlier predictions. Forecast and scenario provenance matter independently.

### 3.4 Reusable empirical preparation policy

We subsequently implemented `recommend_empirical_preparation(forecast, inventory, error_ratios, quantile)`. It constructs possible demand from a method-specific historical ratio sample, takes an explicit empirical quantile and subtracts stock.

The function does not choose the quantile, learn a forecasting model, validate sample dates, apply manager context or guarantee service. A caller must supply the correct history and settings.

The last verified project suite contained **57 passing tests**. A separate integration check reproduced the selected development candidate on all 40 cases and from an archived snapshot. These establish covered calculation behaviour and reproducibility, not business efficacy.

## 4. The development experiment we actually ran

The main historical comparison used:

| Setting | Value |
|---|---|
| Centre | 13 |
| Meals | 2306, 2444, 1198, 2664 |
| Calibration targets | Weeks 116–125 |
| Development evaluation targets | Weeks 126–135 |
| Evaluation cases | 40, with no missing outcomes |
| Observed orders | 13,951 |
| Simulated usable inventory | 40 portions per meal/week |
| Inventory dynamics | Reset for each evaluated case; no carry-over ageing model |
| Overage penalty | 2 assumed units per excess portion |
| Underage penalty | 5 assumed units per unmet order |
| Conversion | One order assumed equal to one portion |
| Manager adjustment | Not applied in these performance comparisons |

All recommendations were computed without using the actual order outcome for the same target week. Actuals were used afterward for evaluation.

The fixed assumptions make comparisons consistent but do not make them representative of a real restaurant. Historical orders are not proven unconstrained demand. Excess portions are a simulated proxy, not measured waste.

## 5. Our experiment sequence and what each result changed

### Attempt A: optimize three equally weighted demand scenarios

We supplied low, central and high demand and assigned one-third weight to each. The optimizer correctly minimized penalty under that discrete representation.

One week initially looked promising: penalty fell from 1,299 to 1,142, while excess increased from 107 to 571. The ten-week comparison then showed a much less favourable picture:

| Policy | Excess | Unmet orders | Penalty |
|---|---:|---:|---:|
| Central-forecast `last` baseline | 1,992 | 2,023 | 14,099 |
| Three equal-weight scenarios | 7,339 | 597 | 17,663 |

Penalty increased by approximately 25.3%. The policy substantially reduced shortages by preparing more, but worsened the sustainability proxy.

**Decision:** stop treating a low/central/high summary as three automatically equiprobable outcomes. Empirical percentiles do not justify equal point masses. Keep the three scenarios as useful communication devices, while revisiting the underlying distribution.

### Attempt B: represent demand through historical forecast errors

We used actual/forecast ratios from calibration, pooled within forecast-size tiers. Each historical error produced a possible demand outcome. For the cost-based candidate we used the newsvendor critical fraction 5/(2+5), comparing integer candidates around the empirical target.

| Policy | Excess | Unmet orders | Penalty |
|---|---:|---:|---:|
| `last` baseline | 1,992 | 2,023 | 14,099 |
| Empirical cost-based policy | 3,173 | 1,456 | 13,626 |

Penalty fell by about 3.4%, but excess increased by about 59%.

**Decision:** distinguish lower penalty from less excess. A cost objective can rationally accept more excess when shortages are more heavily penalized. This result does not satisfy a waste-reduction claim.

### Attempt C: inspect the sustainability/service frontier

We tested common empirical preparation quantiles from 0.1 to 0.9 using `last`.

- The 50th percentile reduced excess to 1,412, but increased unmet orders to 2,567. Fulfilled share fell from 85.50% to 81.60%.
- The 60th percentile reduced unmet orders to 1,959, but increased excess to 2,097.
- None of the nine candidates reduced excess without increasing unmet orders relative to baseline.

**Decision:** expose the trade-off rather than declare a winner by reporting only one metric. Do not silently relax service requirements just to obtain a waste-reduction headline.

### Attempt D: improve the central forecast with a simple combination

We tested `last`, `trailing4`, and a fixed 50/50 blend, all using the same central-forecast preparation rule:

| Forecast | WAPE | Excess | Unmet orders | Penalty |
|---|---:|---:|---:|---:|
| last | 29.07% | 1,992 | 2,023 | 14,099 |
| trailing4 | 33.55% | 2,933 | 1,754 | 14,636 |
| 50/50 blend | 28.09% | 2,243 | 1,672 | 12,846 |

The blend improved forecast error and penalty but still increased excess.

**Decision:** forecast accuracy and decision sustainability must be evaluated separately. Recalibrate the error distribution for the blend rather than reuse errors from `last`.

### Attempt E: select a service-constrained empirical blend policy

After a coarse blend quantile grid also failed to improve both metrics, we explicitly searched quantiles 0.01–0.99 on the same development window. The selection rule was minimum excess subject to aggregate unmet orders no greater than the original baseline.

A common 55th-percentile blend policy was selected:

| Policy | Excess | Unmet orders | Penalty | Fulfilled share |
|---|---:|---:|---:|---:|
| Original `last` baseline | 1,992 | 2,023 | 14,099 | 85.50% |
| Selected blend q0.55 | 1,950 | 1,971 | 13,755 | 85.87% |

That is 42 fewer excess portions, 52 fewer unmet orders and 344 lower penalty: approximately 2.1%, 2.6% and 2.4% improvements respectively.

However:

- The candidate was selected after multiple experiments on these same 40 cases.
- Meal 2444 worsened on both excess and unmet orders.
- Only meal 2306 improved both; the other meals showed trade-offs.
- Penalty improved in five of ten weeks.
- The constraint was aggregate, not a per-meal or future guarantee.
- The selected policy is not the penalty-minimizing 2/5 newsvendor rule.

**Decision:** retain it as a provisional development candidate and preserve the baseline. Do not claim a strong or independently verified sustainability improvement.

## 6. What the evidence supports—and what it does not

### Supported

- The decision module computes and compares specified policies in the covered cases.
- Low/central/high equal weighting can produce undesirable excess under our chosen costs.
- Better forecast error or lower penalty does not necessarily reduce excess.
- We can quantify trade-offs transparently and reproduce the development results.
- Our fixed-commitment experiments did not establish a strong, broadly consistent improvement in excess at maintained service.

### Not supported

- “Our first idea is impossible.” We tested particular methods, assumptions and a small development subset.
- “Silvia's forecasting is the problem.” Forecast error and the decision representation both contribute; some initial choices were ours.
- “All optimization failed.” The optimizer solved its supplied objective; the objective and distribution need to match the intended product value.
- “We reduced real food waste.” The outcomes are simulated.
- “The new approach will work.” It has not been tested.

For the presentation, describe a weak or unsuccessful first result precisely. Do not call all prior work useless, hide the q0.55 candidate or present the modest selected improvement as a decisive success.

## 7. Why we considered another operational lever

The first system changes a quantity while assuming that the commitment must be made in meal-specific form before uncertain demand is realized.

Under that restriction, more protection against shortages often means more excess. We can move along a trade-off without materially improving it.

This motivated a new question:

> Are we committing too early to the final form of the food?

Some menus may share raw ingredients or intermediate preparations. If those resources can remain usable for several meals until better information arrives, the kitchen may be able to postpone allocation rather than guess every meal's final demand in advance.

This is an operational-flexibility hypothesis, not a better forecasting claim. It adds a decision lever: **timing and reversibility of preparation commitments**.

It is also conditional. Some meals cannot be delayed safely or quickly, components may not be interchangeable, and additional work/storage can remove any benefit. These conditions belong inside the experiment.

## 8. New concept: a flexible preparation plan

### User question

> What should I prepare now, what should I keep shared, and what can I finish later without unacceptable delays or shortages?

### Proposed system output

A plan with four explicit parts:

1. **Commit now:** meal-specific portions worth completing before new information.
2. **Prepare shared components:** bases/components usable across more than one permitted recipe.
3. **Keep unallocated:** eligible ingredients/components whose final meal allocation is delayed.
4. **Finish later:** permitted scenario-responsive actions, with time/capacity and expiry limits.

The system shows the same initial plan under low, central and high demand or menu-mix cases. It explains where flexibility helps, which resources become bottlenecks, and when early finalization is safer.

### Illustrative workflow

A manager sees that two meals share a base. A rigid plan commits that base to each final meal in advance. A flexible plan reserves some base for later allocation. Once permitted new information arrives, the kitchen can finish one meal or the other within its remaining capacity.

The assistant might explain:

> “This component remains useful in both demand cases. Completing it as meal A now reduces your ability to respond if demand shifts to meal B. Here is the service and waste consequence of each choice.”

This wording is a desired explanation, not a result already generated by our product.

## 9. A minimal mathematical formulation

The smallest useful version is a two-stage scenario model.

### Inputs

- Meal set M and ingredient/component set J.
- Recipe/component requirements a[j,m] per portion, with consistent units.
- Identical starting stocks for all compared policies.
- Feasible preparation/finishing stages, capacities and processing times.
- Expiry/recoverability rules, horizon and permitted carry-over value.
- Demand scenarios D[m,s] and stated weights p[s]. These represent joint menu demand, not independent per-meal extremes unless explicitly assumed.
- The information observed before later decisions and what it can reveal.
- Waste, unmet-demand, delay and labour/cost measures with stated units.

### First-stage decisions: before new information

- x[m]: final portions of meal m prepared early.
- b[j]: shared component preparation or allocation where technically meaningful.
- Uncommitted usable stock retained for later use.

These decisions must be the same across scenarios with the same information. We cannot let each future outcome choose its own convenient starting plan.

### Later decisions: after an allowed signal

- y[m,h]: finishing quantities based on information state h.
- A feasible allocation of remaining components to meals.
- Fulfilled orders, shortages and terminal waste under each realized demand case.

For every history/information state, finishing must satisfy resource balance, capacity, time and expiry constraints. If two scenarios have the same observed signal, they must receive the same action until distinguishable information arrives. This is the non-anticipativity requirement.

### Demand and service

```text
fulfilled[m,s] <= demand[m,s]
fulfilled[m,s] <= usable completed portions[m,s]
unmet[m,s] = demand[m,s] - fulfilled[m,s]
```

Completing a portion consumes its recipe requirements exactly once. Reusing a shared component does not create more food; a unit allocated to one recipe is unavailable to another.

### Objective and acceptance

For the sustainable-planning hypothesis, report a waste/service frontier or minimize expected terminal waste under an explicitly agreed service constraint. Also report cost/labour/delay rather than hiding them.

Do not combine kilograms, portions and money in a single unscaled score. Terminal waste should be accounted for in a common physical unit where possible. If we use standardized component units in the toy experiment, label them as such rather than kilograms.

Existing overage/underage penalties can support a secondary cost comparison, but the new model must not quietly optimize money and claim it minimized waste.

## 10. Tiny synthetic example to explain the mechanism

This example illustrates possibility under stated assumptions; it is not empirical evidence or a promised demo result.

Assume three hypothetical meals A/B/C each require one identical shared-base unit plus their respective finishing inputs. Ten shared-base units are available. All compared policies have the same sufficient finishing-input stocks. Those finishing inputs do not expire within the example horizon, so their unused quantities are tracked but not counted as newly wasted food.

Three equally weighted synthetic demand cases are:

```text
Case 1: A=10, B=0,  C=0
Case 2: A=0,  B=10, C=0
Case 3: A=0,  B=0,  C=10
```

Total demand is always ten. Meal mix changes; total volume does not.

A rigid example commits the ten base units to 4 A, 3 B and 3 C before knowing the case. It serves 4/3/3 orders, leaving 6/7/7 completed portions unmatched. With no recovery and completed-portions expiry at horizon end, those are waste; otherwise they must be labelled leftovers and aged explicitly. Mean unmatched quantity and unmet orders are both 20/3, approximately 6.67.

An idealized flexible example keeps ten shared-base units unallocated, receives a fully revealing order signal before the promised finishing window, and has capacity to finish ten portions in that window. It can allocate all ten to the requested meal. In that idealized example only, unmatched finished portions and unmet orders are zero.

**Why this is not yet a fair headline:** the demand cases are deliberately extreme and the information is fully revealing. The example isolates a mechanism. It must not be presented as measured restaurant performance or as a universal advantage.

A credible evaluation must also test partial/noisy signals, less extreme mix changes, common total-volume drops, limited finishing capacity, common-base expiry, extra handling costs and meals with no shared components. The rigid comparator must be optimized fairly; it must not be chosen to lose.

At high finishing capacity and useful late information, flexibility may help. At zero finishing capacity, the advantage may disappear. If demand for every meal falls together, shared preparation can still leave unused food. If delay is too costly, early completion may be preferable.

## 11. Fair-comparison requirements

Both policies must receive:

- The same initial ingredient and component stocks, budget and storage conditions.
- The same demand paths and exogenous information signals.
- The same physical preparation technologies, safety assumptions, labour accounting and capacity access.
- The same service deadlines and terminal horizon.
- The same recovery and expiry rules for comparable food states.

The difference is the policy's use of permitted timing/allocation decisions. If flexibility needs extra equipment, labour or late capacity, disclose and cost it or give the comparator equivalent resource access. A fixed policy may be an intentionally restricted benchmark, but its restriction must be named; do not call it the best possible alternative.

Include these controls:

1. A transparent rigid quantity plan from an existing baseline, mapped to the same synthetic recipes.
2. A stronger optimized rigid plan under the same information and resource constraints.
3. The flexible plan, with feasible later actions.
4. Optionally, a perfect-information oracle labelled as an upper bound, not a deployable competitor.

Do not give the flexible plan future demand that a real manager could not observe in time. For a fully revealed second-stage toy, state that this is an idealized information assumption. For a partial-signal demo, define signal generation before comparison and enforce shared actions for indistinguishable cases.

A result of equal performance or worse flexibility is informative. Do not remove such cases, inflate rigidity or change expiry rules after seeing outcomes to manufacture a benefit.

## 12. Minimal scope and data separation

### Recommended minimum experiment

- Two hypothetical meals sharing one base, plus one meal-specific input for each.
- Two decision stages and three explicitly specified demand/menu-mix cases.
- Fixed initial resources and a small integer search space.
- One capacity bottleneck and explicit horizon/expiry rules.
- An idealized fully observed later stage first, labelled as a mechanism test; then at least one partial-information or capacity-limited control.
- One output comparing waste/leftovers, orders fulfilled, unmet orders, later workload and cost assumptions.

Do not start with three real recipes, a full kitchen simulator, live ingredient prices, nutrition, allergen substitutions, deployment or a new agent platform. Allowed recipe allocations must be specified, not invented by an LLM.

### What is observed versus synthetic

| Element | Status |
|---|---|
| Weekly meal-order history | Observed source data; original development experiment |
| Forecast baselines and selected empirical policy results | Implemented/evaluated as documented, with limits |
| Shared recipes and ingredient requirements | New synthetic assumptions unless externally supplied/verified |
| Within-period information, finishing times and capacities | New synthetic assumptions |
| Expiry, safe hold time and recovery permissions | Unvalidated operational assumptions; require real expertise for deployment |
| Flexible-plan performance | Not implemented or measured yet |

Do not map anonymous Kaggle meal IDs to pasta, lasagne or particular ingredients as factual recipes. A synthetic recipe layer can be illustrative, but not treated as recovered dataset information.

Weekly totals do not validate within-week staging or late adaptation. Keep the old historical experiment and the new synthetic mechanism experiment separately labelled throughout the presentation.

## 13. What we keep and what we build

### Preserve unchanged as evidence and baselines

- `src/freshwise/decision.py` and its tests.
- `src/freshwise/empirical.py` and its tests.
- `DECISION_API.md` and `DECISION_EVALUATION.md`.
- All recorded favourable and unfavourable results, including the small q0.55 candidate.
- Original dataset files and prior cumulative recaps.
- The uncommitted notebook work; inspect before any branch change/reset.

No prior work is to be deleted, rewritten as a success or silently replaced.

### New modules, proposed only

| Proposed file | Purpose |
|---|---|
| `src/freshwise/flexible_prep.py` | Resource accounting, feasible actions, rigid/flexible policy comparison |
| `tests/test_flexible_prep.py` | Feasibility, timing, accounting and no-flexibility controls |
| `data/examples/flexible_menu.json` | Tiny synthetic input fixture, if an agreed tracked path is not ignored |
| `docs/flexible_preparation.md` | Assumptions, information structure, units and experiment specification |
| `docs/flexible_results.md` | Results only after the model is implemented and checked |

These files do not exist as a result of this document. The fixture path must be reconciled with `.gitignore` before use. Use a non-ignored examples path if necessary; do not change raw-data exclusion broadly.

Do not modify existing function signatures merely to fit the new experiment. The old module can supply baseline quantities and generic penalty checks; new physical waste/resource accounting needs separate logic.

## 14. Development gates, responsibilities and schedule

There is about one week until the communicated November 12 final date. The team previously budgeted roughly one hour per person per day. This extension is only feasible as a narrow synthetic demonstration. The exact official cutoff and formats still need checking.

### Gate 0 — agree the scope before building, November 5

**All three:** confirm that this is a proposed extension of preparation planning, not a replacement of evidence or an already validated pivot. Read the submitted abstract and official rules to determine whether an update/clarification is needed. Do not claim organizer approval from this document.

Agree the two meals, shared base, units, stages, information timing, capacities, expiry rules, comparator definitions and primary waste/service acceptance criterion. Record who owns the assistant. If no agreement, keep the existing workflow and present the extension as future research.

### Gate 1 — mechanism and physical simulator, November 6

**Ari:** write the resource-balance evaluator and a hand-calculated synthetic fixture. Model one shared-base unit consumed once. Distinguish leftovers from terminal waste. Enforce capacities and permitted completion timing.

**Silvia:** specify the joint demand cases and how to separate total-volume uncertainty from menu-mix uncertainty. Label any probabilities and later signal as synthetic. Forecast improvements may continue independently but should not block the tiny mechanism test.

**Lan:** draft one screen contrasting fixed commitment with delayed allocation. Include observed/synthetic labels and a list of assumptions. Use a fixture while calculation functions are developed.

Acceptance: manual and code accounting agree for one path; infeasible plans are rejected.

### Gate 2 — comparison and controls, November 7

**Ari:** enumerate a small feasible first-stage action set and allowed later actions. Optimize the rigid comparator rather than choosing a poor allocation. Compare on identical scenarios and resources.

**Silvia:** inspect information timing and scenario consistency. Confirm that the flexible model does not use information before it exists.

**Lan:** display every component's allocation and service outcomes; do not independently duplicate numeric calculations in the screen.

Acceptance: a fully explained comparison and at least one no-benefit/control case. If assumptions or implementation do not fit the budget, cut to two meals/one base rather than weakening validation.

### Gate 3 — bounded sensitivity and integration, November 8

Test at least: no shared component; no later finishing capacity; perfect versus imperfect/no useful information; common total-volume drop; component expiry before use. Keep the designed grid fixed rather than testing until a favourable screenshot appears.

Integrate one ordinary path and one manager-context change. Manager input changes assumptions at an explicitly defined time; it does not give the solver future outcomes.

Acceptance: benefit exists only where feasible assumptions support it, and failure cases are visible. If no benefit survives reasonable controls, retain that result and do not invent a success story.

### Gate 4 — freeze and package, November 9–11

**November 9:** freeze the new synthetic experiment specification and core code, if accepted. Decide whether an additional original-policy final evaluation is still useful for the presentation. Preserve its status and do not force both experiments into one statistical claim.

**November 10:** reproduce from documentation on another teammate's machine, rehearse the full demo and prepare a backup allowed by the rules. Verify all displayed numbers, constraints and labels.

**November 11:** obtain all approvals, finalize materials and submit early if possible. Save receipt and exact submitted files. Do not add features after the freeze to rescue the presentation.

**November 12:** submission contingency, subject to the verified official cutoff.

### Immediate next two tasks for Ari's guided session

1. Write the smallest two-meal shared-base example and solve one rigid/flexible outcome by hand. Choose information timing and capacity explicitly; do not code before those are coherent.
2. Create an input/output contract for a pure evaluation function. Then implement accounting and tests before an optimizer or AI explanation.

The new extension has no tutorial step numbers completed yet. Previous completed sequence ended at 214. The November 4 recap had reserved step 215 for coordination; use 215–216 to agree this extension's scope if proceeding, not to imply a simulator already exists.

## 15. Role of the AI assistant in the new concept

The assistant should help the manager explore a defined menu/preparation model:

1. Read validated recipe/component, stock and capacity inputs.
2. Clarify the timing of a contextual claim such as an event or reservations.
3. Call scenario, rigid-plan, flexible-plan and evaluation tools.
4. Explain which commitments remain reversible, which resource binds, and why a recommendation changes.
5. Ask for approval; do not place orders or override constraints.

Calculations and food-state transitions belong in deterministic tools. The LLM must not invent recipes, safe storage periods, substitution permissions, probabilities or quantified benefits. A forecast module remains useful, but the new experiment explores operational decisions in addition to forecasting.

An explanation should include the policy, data/assumption provenance, waste/service trade-off, constraints and a reason the recommendation may fail. It should not present a perfect-information oracle as something the deployed assistant can know.

## 16. Tests required before a persuasive demo

- Resource conservation: no ingredient/component is consumed twice or allocated beyond stock.
- Valid recipes: no meal is completed without all required inputs.
- Same first-stage action across future cases before information is observed.
- Same later action for scenarios that remain indistinguishable under the specified signal.
- Finishing and storage capacity respected; service deadlines respected.
- Expired material cannot be reused; recovery/carry-over handled consistently.
- Remaining recoverable stock separated from terminal waste; no double counting of discarded components and finished meals.
- Identical input resources and demand paths across policies.
- Zero later capacity removes delayed-finalization benefits where the model requires that capacity.
- No shared resource removes cross-meal pooling benefit; any remaining information-timing benefit is identified separately.
- Deterministic known demand can let an optimized rigid plan match the flexible one; no automatic flexibility bonus.
- Extra labour/cost is reported; a food-saving action can still have a cost trade-off.
- Negative or infeasible inputs rejected; no LLM numeric output bypasses the evaluator.

Use a tiny exhaustive search initially. It is understandable and testable. Introduce a solver only if necessary after the fixture and constraints are correct.

## 17. How to tell the story in the presentation

### Slide/segment 1 — the original question

“We started with a straightforward goal: convert weekly demand forecasts into preparation quantities.”

Show the decision variable and explicit excess/shortage objective, not a generic AI diagram.

### Slide/segment 2 — an assumption failed

“Our first three-scenario policy reduced shortages but increased excess substantially and worsened total penalty over ten development weeks.”

Show the 1,992 versus 7,339 excess result with the same stock/cost assumptions. Explain equal scenario weights as the initial modelling assumption, not an error blamed on Silvia.

### Slide/segment 3 — improvement was not enough

“We revised demand representation and forecast combination. The selected candidate improved excess by about 2.1% on development, but the result was small, selected after several experiments and uneven across meals.”

Show the modest candidate, not only failed methods. Say final confirmation is pending. Do not imply a failed test was a deliberate demonstration designed to justify the pivot.

### Slide/segment 4 — the new hypothesis

“We then questioned an operational assumption: why must all preparation be committed to final meals before better information arrives?”

Introduce shared components and delayed finalization as an extra action, not a claim that better forecasting is useless.

### Slide/segment 5 — the flexible plan experiment

Show the same three synthetic demand cases, same starting resources and a timeline of what is known when. Compare the optimized rigid plan with the feasible flexible plan. Put synthetic assumptions and signal quality on screen.

**This segment needs real outputs from the new model before quantified results are inserted.** Until then it is a proposed experiment. If no meaningful benefit appears, report that rather than forcing a pivot-success narrative.

### Slide/segment 6 — honest conclusion

“FreshWise investigates both how much to prepare and which commitments can remain flexible. Historical evaluation exposed limits of our first policies; a separate synthetic experiment tests the value and cost of delayed allocation.”

Add only benefits actually established by the completed experiment, with scope and limits. State what operational data and expert validation would be needed for deployment.

## 18. Presentation-ready narrative draft, before new results exist

> We began by forecasting weekly meal orders and optimizing how many portions to prepare. Our first scenario policy reduced shortages, but it prepared too much: over ten development weeks, simulated excess rose substantially and the total penalty worsened. We replaced the three-point demand approximation with historical error distributions and tested a simple forecast combination. A selected candidate achieved a small aggregate improvement, but the gain was not independently validated and did not hold uniformly across meals.
>
> Rather than claim that a more sophisticated calculation had solved waste, we examined the operational decision itself. Our first model committed supply to finished meals before uncertain demand was known. We therefore proposed an extension: preserve some preparation as shared components, then allocate and finish meals after explicitly defined information arrives, within capacity and expiry constraints.
>
> We are retaining the original models as baselines and evidence. The next experiment compares rigid and flexible preparation under identical synthetic resources and demand scenarios. Its purpose is to test when flexibility can reduce terminal waste without unacceptable service loss, and when its capacity, information or handling requirements remove the benefit.

This is a narrative of the observed process and the proposed next experiment. It does not claim the new model works before it is implemented.

## 19. Evidence and version references

Primary local records reviewed for this document:

- `freshwise/DECISION_EVALUATION.md`: historical development setup, results and limitations.
- `freshwise/DECISION_API.md`, `src/freshwise/decision.py`, `src/freshwise/empirical.py` and their tests: current implementation.
- `output/handoff/FreshWise_Cumulative_Recap_2026-11-04.md`: cumulative chronology and publication evidence.
- Submitted abstract and mentor feedback as read/supplied in this conversation.
- User-supplied terminal tables for the forecast/blend experiments.

Published repository: https://github.com/SilviaDeHoyos3/WAI-Hackaton-2026-

Last inspected local HEAD: `2acdb2e`; main matched cached origin/main, with only the original exploration notebook modified. No new network fetch or publication was performed for this document. This document is shared in the repository for team review. Publication does not establish agreement or approval by Silvia or Lan.

Retain the original records. This strategy document adds a proposed experiment and narrative; it does not rewrite their findings or authorize any external action.
