/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class RosterGrid extends Component {
    static template = "security_shift_planner.RosterGrid";
    static props = {
        mode: { type: String, optional: true }, // "full" or "light"
        dates: Array,
        sites: Array,
        slots: Array,
        selectedSlotId: { optional: true },
        onSelectSlot: { type: Function, optional: true },
        onSlotContextMenu: { type: Function, optional: true },
        onDropSlot: { type: Function, optional: true },
    };

    static defaultProps = {
        mode: "full",
        selectedSlotId: null,
    };

    setup() {
        this.state = useState({
            dragOverSlotId: null,
        });
    }

    getPostsForSite(siteId) {
        const siteSlots = this.props.slots.filter((s) => s.site_id === siteId);
        const postMap = new Map();
        for (const s of siteSlots) {
            if (s.post_id && !postMap.has(s.post_id)) {
                postMap.set(s.post_id, s.post_name || `Post #${s.post_id}`);
            }
        }
        return Array.from(postMap.entries()).map(([id, name]) => ({ id, name }));
    }

    getSlotsForCell(siteId, postId, dateStr) {
        return this.props.slots.filter(
            (s) => s.site_id === siteId && s.post_id === postId && s.shift_date === dateStr
        );
    }

    isToday(dateStr) {
        const today = new Date().toISOString().slice(0, 10);
        return dateStr === today;
    }

    isWeekend(dateStr) {
        const day = new Date(dateStr + "T00:00:00").getDay();
        return day === 0 || day === 6;
    }

    formatDateShort(dateStr) {
        if (!dateStr) return "";
        const parts = dateStr.split("-");
        if (parts.length < 3) return dateStr;
        return `${parts[2]}/${parts[1]}`;
    }

    dayName(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr + "T00:00:00");
        return d.toLocaleDateString("en-US", { weekday: "short" });
    }

    onDragStartAssignedSlot(slot, ev) {
        if (!slot.employee_id) return;
        ev.dataTransfer.setData(
            "text/plain",
            JSON.stringify({
                guardId: slot.employee_id,
                guardName: slot.employee_name,
                sourceSlotId: slot.id,
            })
        );
        ev.dataTransfer.effectAllowed = "move";
    }

    onDragOverSlot(slot, ev) {
        if (slot.state === "cancelled") return;
        ev.preventDefault();
        this.state.dragOverSlotId = slot.id;
        ev.dataTransfer.dropEffect = "move";
    }

    onDragLeaveSlot() {
        this.state.dragOverSlotId = null;
    }

    onDropSlot(slot, ev) {
        ev.preventDefault();
        this.state.dragOverSlotId = null;
        if (this.props.onDropSlot) {
            this.props.onDropSlot(slot, ev);
        }
    }

    selectSlot(slot) {
        if (this.props.onSelectSlot) {
            this.props.onSelectSlot(slot);
        }
    }

    onSlotContextMenu(slot, ev) {
        if (this.props.onSlotContextMenu) {
            ev.preventDefault();
            this.props.onSlotContextMenu(slot, ev);
        }
    }
}
