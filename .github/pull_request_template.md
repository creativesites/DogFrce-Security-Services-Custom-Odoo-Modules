## Summary

<!-- What changed and why? 1–3 sentences focused on the business or technical outcome. -->

## Type of change

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor / chore
- [ ] Documentation
- [ ] Test only

## Related issue / backlog item

<!-- Link issue, Linear ticket, or docs/IMPLEMENTATION_BACKLOG.md priority if applicable. -->

Fixes #

## Modules affected

<!-- e.g. security_attendance, security_mobile, mobile -->

-

## Test plan

<!-- Checklist of steps a reviewer can follow to verify the change. -->

- [ ] `./scripts/start.sh` — stack starts without errors
- [ ] Module installs/upgrades cleanly on `dogforce_dev`
- [ ] Manual scenario verified (describe below)
- [ ] Automated tests run (if applicable)

**Manual verification steps:**

1.
2.

**Test commands run:**

```bash
# e.g. odoo -d dogforce_dev --test-enable -i security_payroll_core --stop-after-init
```

## Screenshots / recordings

<!-- UI or mobile changes only. -->

## Checklist

- [ ] Branch name follows convention (`feature/…`, `bugfix/…`, etc.)
- [ ] Scope is limited to the task — no unrelated refactors
- [ ] Access rules updated (`ir.model.access.csv`) for new/changed models
- [ ] Payroll/statutory logic includes or updates tests (if applicable)
- [ ] Demo data updated if new required master data was added (optional: `security_demo_data`)
- [ ] Documentation updated if setup, API, or architecture changed
- [ ] No secrets, `.env`, or credentials committed

## Notes for reviewers

<!-- Optional: trade-offs, follow-up work, migration steps. -->
