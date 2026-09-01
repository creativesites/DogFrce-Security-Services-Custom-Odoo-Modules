/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { NAV_CATALOG, collectActionXmlIds } from "./nav_catalog";

const STORAGE_KEY = "dgs.nav.v1";
const DEFAULT_OPEN_GROUPS = { operations: true, rostering: true };

function loadPersisted() {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function savePersisted(expanded, openGroups, openMenuIds) {
    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ expanded, openGroups, openMenuIds }));
    } catch {
        // localStorage unavailable (private mode, quota) — collapse state just won't persist.
    }
}

export const shellService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        const persisted = loadPersisted();
        const hasStoredPreference = "expanded" in persisted;
        const defaultExpanded = window.innerWidth >= 1280;

        const state = reactive({
            expanded: hasStoredPreference ? persisted.expanded : defaultExpanded,
            openGroups: { ...DEFAULT_OPEN_GROUPS, ...(persisted.openGroups || {}) },
            // Open/closed state for nodes in the LIVE menu tree (shell_nav_panel's
            // flatRows), keyed by real ir.ui.menu id — separate from openGroups
            // above (which only applies to the Home dashboard's curated tile
            // grid). Persisted so a user's expanded sections survive reloads.
            openMenuIds: { ...(persisted.openMenuIds || {}) },
            searchQuery: "",
            resolving: true,
            resolvedActions: {},
            roles: {
                isOwner: false,
                isManager: false,
                isSupervisor: false,
                isHR: false,
                isFinance: false,
            },
            payload: null,
            paletteOpen: false,
            activeGroupKey: null,
            activeLeafKey: null,
            isHome: true,
        });

        function persist() {
            savePersisted(state.expanded, state.openGroups, state.openMenuIds);
        }

        function isMenuNodeOpen(id) {
            return !!state.openMenuIds[id];
        }

        function toggleMenuNode(id) {
            state.openMenuIds[id] = !isMenuNodeOpen(id);
            persist();
        }

        function toggleExpanded() {
            state.expanded = !state.expanded;
            persist();
        }

        function setExpanded(value) {
            state.expanded = value;
            persist();
        }

        function toggleGroup(key) {
            state.openGroups[key] = !isGroupOpen(key);
            persist();
        }

        function isGroupOpen(key) {
            return !!state.openGroups[key];
        }

        function openGroup(key) {
            if (!state.openGroups[key]) {
                state.openGroups[key] = true;
                persist();
            }
        }

        async function resolveActions() {
            const xmlids = collectActionXmlIds();
            if (!xmlids.length) {
                state.resolving = false;
                return;
            }
            const modules = [...new Set(xmlids.map((x) => x.split(".")[0]))];
            const names = xmlids.map((x) => x.split(".").slice(1).join("."));
            try {
                const records = await orm.searchRead(
                    "ir.model.data",
                    [["module", "in", modules], ["name", "in", names]],
                    ["module", "name", "model", "res_id"]
                );
                const map = {};
                for (const rec of records) {
                    map[`${rec.module}.${rec.name}`] = { resModel: rec.model, resId: rec.res_id };
                }
                for (const full of xmlids) {
                    state.resolvedActions[full] = map[full] || null;
                }
            } catch (e) {
                console.warn("DeployGuard Shell: action resolution failed", e);
                for (const full of xmlids) {
                    state.resolvedActions[full] = null;
                }
            } finally {
                state.resolving = false;
            }
        }

        // `st` defaults to this service's own (untracked) reactive state, but
        // callers should pass their own useState()-wrapped `this.shell.state`
        // so the read registers as a dependency of THEIR render — Owl's
        // reactive tracking is per-proxy-instance, not per-target, so a read
        // through this closure's own `state` never triggers a caller's
        // re-render no matter how the underlying value changes.
        function isResolved(xmlid, st = state) {
            if (!xmlid) {
                return false;
            }
            return !!st.resolvedActions[xmlid];
        }

        async function loadPayload(period = "today") {
            try {
                const payload = await orm.call("security.shell.data", "get_home_payload", [period]);
                state.payload = payload;
                if (payload && payload.roles) {
                    Object.assign(state.roles, payload.roles);
                }
                return payload;
            } catch (e) {
                console.warn("DeployGuard Shell: home payload load failed", e);
                return null;
            }
        }

        /** Role- and search-filtered nav tree. Filtering happens here, never
         * in the template (HANDOFF §5.4). `st` should be the caller's own
         * useState()-wrapped state (see isResolved above) so this read
         * registers as a dependency of the caller's own render. */
        function getVisibleCatalog(st = state) {
            const query = (st.searchQuery || "").trim().toLowerCase();
            const isOwner = st.roles.isOwner;

            const filterLeaf = (leaf) => {
                if (leaf.owner && !isOwner) {
                    return false;
                }
                if (query && !leaf.label.toLowerCase().includes(query)) {
                    return false;
                }
                return true;
            };

            const groups = [];
            for (const group of NAV_CATALOG) {
                if (group.owner && !isOwner) {
                    continue;
                }
                const subgroups = [];
                for (const subgroup of group.children) {
                    const leaves = subgroup.children.filter(filterLeaf);
                    if (leaves.length) {
                        subgroups.push({ ...subgroup, children: leaves, leafCount: leaves.length });
                    }
                }
                if (subgroups.length) {
                    const leafCount = subgroups.reduce((n, sg) => n + sg.children.length, 0);
                    groups.push({ ...group, children: subgroups, leafCount });
                }
            }
            return groups;
        }

        /** Best-effort: given the numeric res_id of the action currently
         * showing in the action manager, find which nav leaf/group it
         * belongs to so the rail + nav panel can highlight it. Silently
         * finds nothing for actions outside the curated tree. */
        function findByActionResId(resId) {
            if (!resId) {
                return null;
            }
            for (const group of NAV_CATALOG) {
                for (const subgroup of group.children) {
                    for (const leaf of subgroup.children) {
                        const resolved = leaf.action && state.resolvedActions[leaf.action];
                        if (resolved && resolved.resId === resId) {
                            return { group, subgroup, leaf };
                        }
                    }
                }
            }
            return null;
        }

        function setActiveController(actionResId, actionTag) {
            state.isHome = actionTag === "deployguard.main_command_center";
            const found = state.isHome ? null : findByActionResId(actionResId);
            if (found) {
                state.activeGroupKey = found.group.key;
                state.activeLeafKey = found.leaf.key;
                openGroup(found.group.key);
            } else {
                state.activeGroupKey = null;
                state.activeLeafKey = null;
            }
        }

        resolveActions();

        return {
            state,
            toggleExpanded,
            setExpanded,
            toggleGroup,
            isGroupOpen,
            openGroup,
            isMenuNodeOpen,
            toggleMenuNode,
            isResolved,
            loadPayload,
            getVisibleCatalog,
            setActiveController,
        };
    },
};

registry.category("services").add("deployguard_shell", shellService);
