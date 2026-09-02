/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpcBus } from "@web/core/network/rpc";
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
    dependencies: ["orm", "menu"],

    start(env, { orm, menu }) {
        const persisted = loadPersisted();
        const hasStoredPreference = "expanded" in persisted;
        // Collapsed by default on first-ever load — a narrow rail plus canvas
        // reads calmer than a full sidebar the instant the app appears, and
        // it's one click away. A user's own explicit choice (stored once they
        // toggle) always wins over this default afterward.
        const defaultExpanded = false;

        const state = reactive({
            expanded: hasStoredPreference ? persisted.expanded : defaultExpanded,
            openGroups: { ...DEFAULT_OPEN_GROUPS, ...(persisted.openGroups || {}) },
            // Open/closed state for nodes in the LIVE menu tree (shell_nav_panel's
            // flatRows), keyed by real ir.ui.menu id — separate from openGroups
            // above (which only applies to the Home dashboard's curated tile
            // grid). Persisted so a user's expanded sections survive reloads.
            openMenuIds: { ...(persisted.openMenuIds || {}) },
            // The real ir.ui.menu id of whatever action is currently showing
            // (null if it doesn't match anything in the live tree — e.g. a
            // record form reached by drilling in, not a menu-level screen),
            // plus the chain of ancestor group ids above it. Both the rail
            // and the nav panel derive their active-state highlighting from
            // this — there is no second, hand-maintained active-state map.
            activeMenuId: null,
            activeMenuAncestorIds: [],
            // Reuses security_theme's existing DogForceAppLauncher overlay
            // (search + priority workspace cards + full app grid) rather
            // than a new one-off dropdown — mounted as a shell sibling (see
            // shell_frame.xml) since its original mount point, inside
            // .o_main_navbar, is unreachable once the shell hides that navbar.
            appLauncherOpen: false,
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
            // Count, not a bool: several requests can overlap (e.g. a page's
            // own data load plus the shell's own payload refresh), and the
            // bar should only hide once every one of them has settled.
            pendingRequestCount: 0,
        });

        // Global loading indicator: every RPC in the app funnels through this
        // one bus (core/network/rpc.js), so this is the single place that
        // reliably knows "something is happening" without each screen having
        // to report its own loading state.
        rpcBus.addEventListener("RPC:REQUEST", () => {
            state.pendingRequestCount++;
        });
        rpcBus.addEventListener("RPC:RESPONSE", () => {
            state.pendingRequestCount = Math.max(0, state.pendingRequestCount - 1);
        });

        function persist() {
            savePersisted(state.expanded, state.openGroups, state.openMenuIds);
        }

        function toggleAppLauncher() {
            state.appLauncherOpen = !state.appLauncherOpen;
        }

        function closeAppLauncher() {
            state.appLauncherOpen = false;
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

        /** Given the numeric action id currently showing in the action
         * manager, find its node in the LIVE menu tree (current app) and the
         * chain of group ids above it, by walking the same tree the nav
         * panel renders — no second, hand-maintained map to drift out of
         * sync. Returns nulls if the action isn't menu-level (e.g. a record
         * form reached by drilling into a list, not a menu itself). */
        function findActiveMenuPath(actionResId) {
            const app = menu.getCurrentApp();
            if (!app || !actionResId) {
                return { leafId: null, ancestorIds: [] };
            }
            const tree = menu.getMenuAsTree(app.id);
            let found = null;
            const walk = (nodes, path) => {
                for (const node of nodes) {
                    if (found) {
                        return;
                    }
                    if (node.actionID === actionResId) {
                        found = { leafId: node.id, ancestorIds: [...path] };
                        return;
                    }
                    if (node.childrenTree && node.childrenTree.length) {
                        walk(node.childrenTree, [...path, node.id]);
                    }
                }
            };
            walk(tree.childrenTree || [], []);
            return found || { leafId: null, ancestorIds: [] };
        }

        function setActiveController(actionResId, actionTag) {
            state.isHome = actionTag === "deployguard.main_command_center";
            const { leafId, ancestorIds } = state.isHome
                ? { leafId: null, ancestorIds: [] }
                : findActiveMenuPath(actionResId);
            state.activeMenuId = leafId;
            state.activeMenuAncestorIds = ancestorIds;
            for (const id of ancestorIds) {
                if (!state.openMenuIds[id]) {
                    state.openMenuIds[id] = true;
                }
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
            toggleAppLauncher,
            closeAppLauncher,
            isResolved,
            loadPayload,
            getVisibleCatalog,
            setActiveController,
        };
    },
};

registry.category("services").add("deployguard_shell", shellService);
