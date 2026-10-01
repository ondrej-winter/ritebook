# Launch Planning Examples

These are illustrative structures, not operational defaults. Replace every
cohort, window, threshold, command, and time target with a value justified by the
release risk, service objectives, observed baseline, traffic, detection delay,
and recovery capability. Remove any step or control that does not apply.

## Example rollout sequence

Tailor cohort sizes and observation windows to traffic volume, release risk,
time-to-detection, and how quickly recovery can complete. Use runtime release
controls only when they materially improve safety. Do not advance merely because
an observation window elapsed; advance when the defined evidence is sufficient.

1. Verify the release in the most production-like pre-production environment.
   - Run the applicable automated checks.
   - Smoke test critical flows.
2. Deploy to the smallest safe production exposure: `<initial_exposure>`.
   - Apply the chosen runtime control only if the release plan requires one.
   - Verify deployment health and the release-specific signals.
3. Expand to `<internal_or_canary_cohort>` when that cohort provides useful evidence.
   - Observe for `<representative_observation_window>`.
   - Compare rollout signals against the pre-launch baseline.
4. Increase exposure through `<cohort_sequence>`.
   - Repeat the same monitoring and decision process at each stage.
   - Retain the selected recovery or containment capability while risk remains.
5. Complete the rollout when `<stabilization_criteria>` pass.
   - Continue monitoring through `<stabilization_window>`.
   - Remove temporary release controls according to `<cleanup_owner_and_deadline>`.

## Rollout decision threshold template

Define conditions from project evidence before launch, then decide whether to
advance, hold, or execute the recovery strategy at each stage:

| Signal                      | Advance condition              | Hold condition              | Recovery condition              |
| --------------------------- | ------------------------------ | --------------------------- | ------------------------------- |
| Error or failure rate       | `<advance_error_condition>`    | `<hold_error_condition>`    | `<recover_error_condition>`     |
| Latency or processing time  | `<advance_latency_condition>`  | `<hold_latency_condition>`  | `<recover_latency_condition>`   |
| New failure modes           | `<advance_failure_condition>`  | `<hold_failure_condition>`  | `<recover_failure_condition>`   |
| Product or workflow outcome | `<advance_outcome_condition>`  | `<hold_outcome_condition>`  | `<recover_outcome_condition>`   |
| Data or security signal     | `<advance_safety_condition>`   | `<hold_safety_condition>`   | `<recover_safety_condition>`    |

Execute the recovery strategy when any defined recovery condition is met. Include
immediate triggers for unacceptable data-integrity or security impact even when
traffic is too low for statistical thresholds.

## Recovery strategy template

Every deployment needs an explicit recovery strategy before it happens. Select
rollback, disablement, roll-forward, compensation, or documented irreversibility
according to the release risk and system capabilities.

```markdown
## Recovery Strategy for <feature_or_release>

### Chosen Strategy

- Strategy: <rollback | disablement | roll-forward | compensation | documented irreversibility>
- Rationale: <why this strategy fits the change and operating environment>
- Decision owner: <role_or_owner>
- Recovery or containment target: <project_derived_target>

### Trigger Conditions

- Error or failure condition: <release_specific_condition>
- Latency or capacity condition: <release_specific_condition>
- Product or workflow condition: <release_specific_condition>
- Data-integrity or security condition: <release_specific_condition>

### Execution Steps

1. Confirm the trigger using <signal_or_dashboard>.
2. Execute <recovery_command_or_runbook>.
3. Verify <health_and_user_outcome_checks>.
4. Communicate through <incident_or_release_channel>.

### Data and State Considerations

- State affected by the release: <data_schema_configuration_or_workflow_state>
- Preservation, restoration, reconciliation, or compensation plan: <plan_or_runbook>
- Verification after recovery or containment: <checks>

### If the Change Is Irreversible

- Reason reversal is impossible or riskier than proceeding: <reason>
- Risk accepted by: <owner_or_governance_process>
- Blast-radius limits and safeguards: <limits_and_controls>
- Preserved evidence, backup, checkpoint, or audit trail: <artifact_or_not_applicable_with_reason>
- Containment, repair, and communication path: <runbook>

### Timing Targets

- Detection target: <project_derived_target>
- Decision target: <project_derived_target>
- Recovery or containment target: <project_derived_target>
```
