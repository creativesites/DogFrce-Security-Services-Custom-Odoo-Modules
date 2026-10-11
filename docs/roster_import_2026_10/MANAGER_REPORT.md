# Roster import & auto-roster — change report for the Operations Manager
Date: 11 Oct 2026 · Source: "GUARD ROASTER 21 AUGUST -20 SEPT 2026.xlsx" (sheets headed 21 Sept – 20 Oct 2026)
Production DB: `dogforce_prod`. Backup taken before any change: `/root/backups/dogforce_prod_pre_roster_import_20261011_1704.dump` (server 199.192.23.46).

## 1. What was done
1. **Regular guard pools** imported from the sheet into 25 contract sites (merge only, nothing removed). Mode = *Site only*, source = "DogForce Guard Roaster 21 Aug - 20 Sep 2026". Each site's chatter lists the imported guards and the names that could NOT be matched.
2. **Guard matching.** 211 name rows. Matched automatically (exact / name-order / partial / spelling) or by reviewed spelling variant (`scripts/assisted_matches.py`): 158. **53 not matched** — see `guard_match_reconciliation.csv`. No employee was created; unmatched names need HR review (probably new hires or misspelt names).
3. **Auto-roster, cycle 21 Sep – 20 Oct 2026.** Only guards from each site's regular pool were used. No relief, no guard outside the pool. 1,244 of 1,700 slots filled across the sites below; the rest are marked *critical gap* with a reason.
4. **New contracts created** for roster sections with no contract in Odoo (all with **no rates / monthly value / end date** — please complete): Emerincia Plot, Unigas, New Era (2 sites), Scrap Southern (client Scrap Salvage). New partners created: *Emerincia Plot*, *New Era*. Night+Sun/PH sites = night every day, day shift Sunday & public holidays only; 24h sites = 1 day + 1 night.
5. **Bug fixes** (code, deployed): auto-fill crashed for every site (undefined `req_languages`, `post_type_for_docs`, `_logger` in `security_shift_planner.py`).
6. **Stale snapshots reset:** roster batches created before the import held empty pool snapshots (engine then used all guards). Snapshots for the imported sites were reset to the site defaults.

## 2. Left alone on purpose (manual-test sites)
Hochland Service Station, Petrofund, Windhoek Eye Clinic — pools imported, rosters NOT auto-generated. Atta Rentals roster was already confirmed.

## 3. Please verify — these were my judgement calls
| Roster section | Mapped to | Why uncertain |
|---|---|---|
| Eros House & General Veiko Alexander | Alexander & Incorporated Law Firm – Main Site | Alexander also has "Eros" sites on an older draft contract |
| Nantu WHK West | Namibia National Teachers Union – Main Site (Nantu Jenner) | by elimination |
| Robot & New Road, Mandela & Under the Bridge, China Construction | China State Construction – Main Site (one pool of 15) | three sections pooled into one site |
| Afrideca & Over Side Group | Afrideca Plant Hire | Over Side Group (Willowreid Court) is a separate client |
| Oyetweni Clinic & General Veiko Alexander | Oyetweni Dialyses Centre | |
| Dreamland | Pioneerspark (Dream-land contract) | |
| Scrap Southern | new contract under Scrap Salvage | |
Spelling-variant matches (e.g. "Shefika Tiephelus" → Shefika Theophilus Shalongo) are listed in `scripts/assisted_matches.py`; please confirm with HR.

## 4. Remaining gaps (sheet vs. Odoo)
Pool too small because roster names were not found in HR: Oyetweni, New Era Head Office, Waka Academy (pool 1 → 38 gaps each); Namic H3 (33); 8 sites with 16 gaps (pool 2). The sheet allocates 3 officers per 2-post site; Odoo has only the matched ones. Fix = add/repair the missing employees, then use *Reset to Site Defaults* + auto-fill.
Odoo requirement data also differs from the sheet (e.g. China 7th Railway needs 11 guards per sheet, Odoo has 1 post of 1+1). Existing contracts were NOT changed — billing is derived from them.
Past dates (21 Sep – 11 Oct) were filled too and show as already worked.

## 5. How to reverse
- **Pools:** `pool_changelog_pass2.json` / `pass3.json` hold each site's pool before the change (`site_pool_before`, `contract_pool_before`). Pass 1 (all 22 original sites) started from empty pools. Restore with the same `(6,0,ids)` write.
- **New contracts:** `contracts_changelog.json` lists every created record id (partners, contracts, sites, posts, requirements, operational sites). Set the contracts to terminated/cancelled and archive the records, or delete in reverse order.
- **Rosters:** slots touched in the cycle-fill pass for the second fill pass are in `roster_changelog_pass2.json` (also in `/root/backups` on the server). Unassign by clearing `employee_id` on those slots. First-pass slots: all `security.roster.slot` rows in batches dated 2026-09-21 whose `write_date` ≥ 2026-10-11 17:00 and that were unassigned before.
- **Everything:** restore the dump above (loses any work done after 17:04 on 11 Oct).
