/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ResourceInspectorModal extends Component {
    static template = "security_shift_planner.ResourceInspectorModal";
    static props = {
        slot: Object,
        closeModal: Function,
        onResourceUpdated: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            saving: false,
            resources: [],
            availableVehicles: [],
            availableEquipment: [],
        });

        onWillStart(async () => {
            await this.loadResourceData();
        });
    }

    async loadResourceData() {
        this.state.loading = true;
        try {
            const slotId = this.props.slot.id;
            const resources = await this.orm.searchRead(
                "security.roster.slot.resource",
                [["slot_id", "=", slotId]],
                ["id", "resource_category", "name", "qty_required", "qty_allocated", "is_mandatory", "is_fulfilled", "vehicle_id", "equipment_ids", "notes"]
            );

            const [vehicles, equipment] = await Promise.all([
                this.orm.searchRead("security.vehicle", [["active", "=", true]], ["id", "name", "license_plate", "status"]),
                this.orm.searchRead("security.equipment", [["active", "=", true]], ["id", "name", "serial_number", "category_id"]),
            ]);

            this.state.resources = resources;
            this.state.availableVehicles = vehicles;
            this.state.availableEquipment = equipment;
        } catch (err) {
            console.error("Error loading slot resources:", err);
            this.notification.add("Failed to load shift resource allocations.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async allocateVehicle(resourceId, vehicleId) {
        try {
            await this.orm.write("security.roster.slot.resource", [resourceId], {
                vehicle_id: vehicleId ? parseInt(vehicleId) : false,
            });
            await this.loadResourceData();
            if (this.props.onResourceUpdated) {
                await this.props.onResourceUpdated();
            }
            this.notification.add("Patrol vehicle allocated to shift slot.", { type: "success" });
        } catch (err) {
            console.error("Vehicle allocation failed:", err);
            this.notification.add("Failed to allocate vehicle.", { type: "danger" });
        }
    }

    async allocateEquipment(resourceId, equipmentId) {
        try {
            const res = this.state.resources.find((r) => r.id === resourceId);
            const currentEqIds = res ? res.equipment_ids : [];
            const newEqId = parseInt(equipmentId);
            if (!currentEqIds.includes(newEqId)) {
                await this.orm.write("security.roster.slot.resource", [resourceId], {
                    equipment_ids: [[4, newEqId]],
                });
                await this.loadResourceData();
                if (this.props.onResourceUpdated) {
                    await this.props.onResourceUpdated();
                }
                this.notification.add("Equipment unit allocated.", { type: "success" });
            }
        } catch (err) {
            console.error("Equipment allocation failed:", err);
            this.notification.add("Failed to allocate equipment.", { type: "danger" });
        }
    }

    getCategoryIcon(cat) {
        const icons = {
            guard: "fa-user-shield",
            supervisor: "fa-user-tie",
            vehicle: "fa-car",
            firearm: "fa-crosshairs",
            radio: "fa-walkie-talkie",
            bodycam: "fa-video",
            keys: "fa-key",
            dog: "fa-dog",
            generator: "fa-bolt",
            uniform: "fa-vest",
            ppe: "fa-hard-hat",
            mobile: "fa-mobile-alt",
        };
        return icons[cat] || "fa-cubes";
    }
}
