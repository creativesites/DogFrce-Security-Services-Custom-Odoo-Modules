/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class EquipmentDashboard extends Component {
    static template = "security_equipment.EquipmentDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            data: null,
            filterCategory: "all",
            filterState: "all",
            searchQuery: "",
            activeTab: "allocations", // "allocations" | "stock" | "overdue" | "damages"
            selectedAllocation: null,
            selectedStockItem: null,
            modalIssue: {
                open: false,
                employee_id: "",
                equipment_type_id: "",
                quantity: 1,
                expected_return_date: "",
                saving: false,
            },
            modalDamage: {
                open: false,
                employee_id: "",
                equipment_type_id: "",
                severity: "minor",
                cost_estimate: 0,
                saving: false,
            },
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "security.equipment.dashboard",
                "get_dashboard_data",
                [],
                {
                    category_filter: this.state.filterCategory,
                    state_filter: this.state.filterState,
                }
            );
            this.state.data = data;

            if (this.state.selectedAllocation) {
                const updatedA = data.allocations.find(a => a.id === this.state.selectedAllocation.id);
                this.state.selectedAllocation = updatedA || null;
            }
        } finally {
            this.state.loading = false;
        }
    }

    // ── Filter & Search Handlers ──

    onCategoryFilterChange(ev) {
        this.state.filterCategory = ev.target.value;
        this.loadData();
    }

    onStateFilterChange(ev) {
        this.state.filterState = ev.target.value;
        this.loadData();
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value.toLowerCase().trim();
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    // ── Filtered Getters ──

    get filteredAllocations() {
        if (!this.state.data?.allocations) return [];
        const q = this.state.searchQuery;
        if (!q) return this.state.data.allocations;
        return this.state.data.allocations.filter(
            a => a.guard.toLowerCase().includes(q) ||
                 a.equipment.toLowerCase().includes(q) ||
                 a.item_serial.toLowerCase().includes(q) ||
                 a.name.toLowerCase().includes(q)
        );
    }

    get overdueAllocations() {
        if (!this.state.data?.allocations) return [];
        return this.state.data.allocations.filter(a => a.is_overdue);
    }

    get filteredStock() {
        if (!this.state.data?.inventory_stock) return [];
        const q = this.state.searchQuery;
        if (!q) return this.state.data.inventory_stock;
        return this.state.data.inventory_stock.filter(
            s => s.name.toLowerCase().includes(q) ||
                 s.category.toLowerCase().includes(q)
        );
    }

    // ── Selection & Inspector ──

    selectAllocation(alloc) {
        this.state.selectedStockItem = null;
        this.state.selectedAllocation = alloc;
    }

    selectStockItem(item) {
        this.state.selectedAllocation = null;
        this.state.selectedStockItem = item;
    }

    closeInspector() {
        this.state.selectedAllocation = null;
        this.state.selectedStockItem = null;
    }

    // ── Quick Actions ──

    async quickReturnAsset(allocId) {
        const ok = await this.orm.call(
            "security.equipment.dashboard",
            "action_quick_return",
            [allocId]
        );
        if (ok) {
            this.notification.add("Equipment marked as returned.", { type: "success" });
            await this.loadData();
        }
    }

    async quickAcknowledgeAsset(allocId) {
        const ok = await this.orm.call(
            "security.equipment.dashboard",
            "action_quick_acknowledge",
            [allocId]
        );
        if (ok) {
            this.notification.add("Allocation acknowledged by guard.", { type: "success" });
            await this.loadData();
        }
    }

    // ── Modals ──

    openIssueModal() {
        this.state.modalIssue = {
            open: true,
            employee_id: this.state.data?.guards[0]?.id || "",
            equipment_type_id: this.state.data?.equipment_types[0]?.id || "",
            quantity: 1,
            expected_return_date: "",
            saving: false,
        };
    }

    closeIssueModal() {
        this.state.modalIssue.open = false;
    }

    async submitIssue() {
        const m = this.state.modalIssue;
        if (!m.employee_id || !m.equipment_type_id) {
            this.notification.add("Please select Guard and Equipment Type.", { type: "warning" });
            return;
        }
        m.saving = true;
        try {
            await this.orm.call("security.equipment.dashboard", "action_quick_issue", [{
                employee_id: parseInt(m.employee_id),
                equipment_type_id: parseInt(m.equipment_type_id),
                quantity: parseInt(m.quantity) || 1,
                expected_return_date: m.expected_return_date || false,
                issue_date: new Date().toISOString().slice(0, 10),
            }]);
            this.notification.add("Equipment issued successfully.", { type: "success" });
            this.closeIssueModal();
            await this.loadData();
        } finally {
            m.saving = false;
        }
    }

    openDamageModal() {
        this.state.modalDamage = {
            open: true,
            employee_id: this.state.selectedAllocation?.guard_id || this.state.data?.guards[0]?.id || "",
            equipment_type_id: this.state.selectedAllocation?.equipment_type_id || this.state.data?.equipment_types[0]?.id || "",
            severity: "minor",
            cost_estimate: 0,
            saving: false,
        };
    }

    closeDamageModal() {
        this.state.modalDamage.open = false;
    }

    async submitDamage() {
        const m = this.state.modalDamage;
        if (!m.employee_id || !m.equipment_type_id) {
            this.notification.add("Please fill Guard and Equipment Type.", { type: "warning" });
            return;
        }
        m.saving = true;
        try {
            await this.orm.call("security.equipment.dashboard", "action_quick_report_damage", [{
                employee_id: parseInt(m.employee_id),
                equipment_type_id: parseInt(m.equipment_type_id),
                severity: m.severity,
                cost_estimate: parseFloat(m.cost_estimate) || 0.0,
                damage_date: new Date().toISOString().slice(0, 10),
            }]);
            this.notification.add("Damage report submitted.", { type: "warning" });
            this.closeDamageModal();
            await this.loadData();
        } finally {
            m.saving = false;
        }
    }

    openAllocationForm(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.equipment.allocation",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    stateBadgeClass(state) {
        return {
            issued: "eq-badge eq-badge-issued",
            acknowledged: "eq-badge eq-badge-acknowledged",
            returned: "eq-badge eq-badge-returned",
            damaged: "eq-badge eq-badge-damaged",
            lost: "eq-badge eq-badge-lost",
        }[state] || "eq-badge eq-badge-issued";
    }

    severityColor(daysOverdue) {
        if (daysOverdue > 30) return "text-danger fw-bold";
        if (daysOverdue > 7) return "text-warning fw-semibold";
        return "text-secondary";
    }
}

registry.category("actions").add("security_equipment.equipment_dashboard", EquipmentDashboard);
