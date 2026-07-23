/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class FleetDashboard extends Component {
    static template = "security_fleet.FleetDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            data: null,
            filterState: "all",
            searchQuery: "",
            activeTab: "vehicles", // "vehicles" | "runs" | "fuel"
            selectedVehicle: null,
            selectedRun: null,
            modalRun: {
                open: false,
                vehicle_id: "",
                route_id: "",
                driver_id: "",
                scheduled_departure: "",
                saving: false,
            },
            modalFuel: {
                open: false,
                vehicle_id: "",
                driver_id: "",
                fuel_date: new Date().toISOString().slice(0, 10),
                litres: 0,
                cost_per_litre: 0,
                total_cost: 0,
                odometer_at_fueling: 0,
                saving: false,
            },
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "security.fleet.dashboard",
                "get_dashboard_data",
                [],
                { state_filter: this.state.filterState }
            );
            this.state.data = data;

            // Maintain selection if previously selected item exists
            if (this.state.selectedVehicle) {
                const updatedV = data.vehicles.find(v => v.id === this.state.selectedVehicle.id);
                this.state.selectedVehicle = updatedV || null;
            }
            if (this.state.selectedRun) {
                const updatedR = data.today_runs.find(r => r.id === this.state.selectedRun.id);
                this.state.selectedRun = updatedR || null;
            }
        } finally {
            this.state.loading = false;
        }
    }

    // ── Filter & Search Handlers ──

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

    get filteredVehicles() {
        if (!this.state.data?.vehicles) return [];
        const q = this.state.searchQuery;
        if (!q) return this.state.data.vehicles;
        return this.state.data.vehicles.filter(
            v => v.name.toLowerCase().includes(q) ||
                 v.plate.toLowerCase().includes(q) ||
                 v.driver.toLowerCase().includes(q)
        );
    }

    get filteredRuns() {
        if (!this.state.data?.today_runs) return [];
        const q = this.state.searchQuery;
        if (!q) return this.state.data.today_runs;
        return this.state.data.today_runs.filter(
            r => r.vehicle.toLowerCase().includes(q) ||
                 r.route.toLowerCase().includes(q) ||
                 r.driver.toLowerCase().includes(q) ||
                 r.name.toLowerCase().includes(q)
        );
    }

    // ── Selection & Inspector ──

    selectVehicle(vehicle) {
        this.state.selectedRun = null;
        this.state.selectedVehicle = vehicle;
    }

    selectRun(run) {
        this.state.selectedVehicle = null;
        this.state.selectedRun = run;
    }

    closeInspector() {
        this.state.selectedVehicle = null;
        this.state.selectedRun = null;
    }

    // ── Quick Actions ──

    async changeVehicleState(vehicleId, newState) {
        const ok = await this.orm.call(
            "security.fleet.dashboard",
            "action_update_vehicle_state",
            [vehicleId, newState]
        );
        if (ok) {
            this.notification.add(`Vehicle status updated to ${newState}.`, { type: "success" });
            await this.loadData();
        }
    }

    async changeRunState(runId, newState) {
        const ok = await this.orm.call(
            "security.fleet.dashboard",
            "action_update_run_state",
            [runId, newState]
        );
        if (ok) {
            this.notification.add(`Shuttle run status updated to ${newState}.`, { type: "success" });
            await this.loadData();
        }
    }

    async assignDriver(vehicleId, driverId) {
        const ok = await this.orm.call(
            "security.fleet.dashboard",
            "action_quick_assign_driver",
            [vehicleId, parseInt(driverId) || false]
        );
        if (ok) {
            this.notification.add("Primary driver assigned successfully.", { type: "success" });
            await this.loadData();
        }
    }

    // ── Modal Handlers ──

    openRunModal() {
        this.state.modalRun = {
            open: true,
            vehicle_id: this.state.data?.vehicles[0]?.id || "",
            route_id: this.state.data?.routes[0]?.id || "",
            driver_id: this.state.data?.drivers[0]?.id || "",
            scheduled_departure: "",
            saving: false,
        };
    }

    closeRunModal() {
        this.state.modalRun.open = false;
    }

    async submitCreateRun() {
        const m = this.state.modalRun;
        if (!m.vehicle_id || !m.driver_id || !m.route_id) {
            this.notification.add("Please select Vehicle, Driver, and Route.", { type: "warning" });
            return;
        }
        m.saving = true;
        try {
            await this.orm.call("security.fleet.dashboard", "action_quick_create_run", [{
                vehicle_id: parseInt(m.vehicle_id),
                driver_id: parseInt(m.driver_id),
                route_id: parseInt(m.route_id),
                scheduled_departure: m.scheduled_departure || false,
                shift_date: new Date().toISOString().slice(0, 10),
            }]);
            this.notification.add("Shuttle run created successfully.", { type: "success" });
            this.closeRunModal();
            await this.loadData();
        } finally {
            m.saving = false;
        }
    }

    openFuelModal() {
        this.state.modalFuel = {
            open: true,
            vehicle_id: this.state.data?.vehicles[0]?.id || "",
            driver_id: this.state.data?.drivers[0]?.id || "",
            fuel_date: new Date().toISOString().slice(0, 10),
            litres: 0,
            cost_per_litre: 0,
            total_cost: 0,
            odometer_at_fueling: 0,
            saving: false,
        };
    }

    closeFuelModal() {
        this.state.modalFuel.open = false;
    }

    onFuelCalc() {
        const m = this.state.modalFuel;
        if (m.litres > 0 && m.cost_per_litre > 0) {
            m.total_cost = Math.round(m.litres * m.cost_per_litre * 100) / 100;
        }
    }

    async submitCreateFuel() {
        const m = this.state.modalFuel;
        if (!m.vehicle_id || !m.driver_id || m.litres <= 0 || m.total_cost <= 0) {
            this.notification.add("Please fill all fuel details correctly.", { type: "warning" });
            return;
        }
        m.saving = true;
        try {
            await this.orm.call("security.fleet.dashboard", "action_quick_create_fuel", [{
                vehicle_id: parseInt(m.vehicle_id),
                driver_id: parseInt(m.driver_id),
                fuel_date: m.fuel_date,
                litres: parseFloat(m.litres),
                cost_per_litre: parseFloat(m.cost_per_litre),
                total_cost: parseFloat(m.total_cost),
                odometer_at_fueling: parseFloat(m.odometer_at_fueling),
            }]);
            this.notification.add("Fuel slip log registered successfully.", { type: "success" });
            this.closeFuelModal();
            await this.loadData();
        } finally {
            m.saving = false;
        }
    }

    openVehicleForm(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.vehicle",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRunForm(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.shuttle.run",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    fmt(amount) {
        return "N$ " + (amount || 0).toLocaleString("en-NA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    stateBadgeClass(state) {
        return {
            available: "fd-badge fd-badge-available",
            in_transit: "fd-badge fd-badge-in_transit",
            in_service: "fd-badge fd-badge-in_service",
            scrapped: "fd-badge fd-badge-scrapped",
        }[state] || "fd-badge fd-badge-scrapped";
    }

    runStateClass(state) {
        return {
            draft: "fd-badge fd-badge-draft",
            boarding: "fd-badge fd-badge-boarding",
            in_transit: "fd-badge fd-badge-in_transit",
            completed: "fd-badge fd-badge-completed",
            cancelled: "fd-badge fd-badge-cancelled",
        }[state] || "fd-badge fd-badge-draft";
    }
}

registry.category("actions").add("security_fleet.fleet_dashboard", FleetDashboard);
