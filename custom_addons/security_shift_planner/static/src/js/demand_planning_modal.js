/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DemandPlanningModal extends Component {
    static template = "security_shift_planner.DemandPlanningModal";
    static props = {
        closeModal: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: false,
            saving: false,
            partners: [],
            
            // Inputs
            title: "New Contract Sizing Plan",
            partnerId: null,
            siteName: "Main Facility / Mine Site",
            siteType: "mining",
            postsCount: 24,
            shiftDuration: "12h",
            operatingSchedule: "24_7",
            rotationPattern: "2_2_2",
            reliefFactor: 1.333,
            guardPay: 4500.0,
            supervisorPay: 6500.0,
            vehicleCost: 12000.0,
            billRate: 38.50,

            // Results
            calculated: false,
            results: {
                neededGuards: 32,
                neededSupervisors: 2,
                neededVehicles: 2,
                neededRadios: 14,
                neededTorches: 26,
                neededBodycams: 10,
                neededUniformKits: 38,
                monthlyPostHours: 17498.4,
                monthlyRevenue: 673688.4,
                monthlyPayroll: 157000.0,
                monthlyEquipment: 28160.0,
                monthlyProfit: 488528.4,
                grossMarginPct: 72.5,
            },
        });

        onWillStart(async () => {
            await this.loadPartners();
            this.calculate();
        });
    }

    async loadPartners() {
        try {
            const partners = await this.orm.searchRead(
                "res.partner",
                [["is_company", "=", true]],
                ["id", "name"],
                { order: "name asc", limit: 100 }
            );
            this.state.partners = partners;
            if (partners.length) {
                this.state.partnerId = partners[0].id;
            }
        } catch (e) {
            console.error("Failed to load clients", e);
        }
    }

    calculate() {
        const posts = Math.max(1, parseInt(this.state.postsCount) || 1);
        const shiftDur = this.state.shiftDuration;
        const schedule = this.state.operatingSchedule;
        const rf = parseFloat(this.state.reliefFactor) || 1.333;

        let hoursPerWeek = 168.0;
        let shiftsPerDay = 2.0;
        if (schedule === "day_12" || schedule === "night_12") {
            hoursPerWeek = 84.0;
            shiftsPerDay = 1.0;
        } else if (schedule === "business_8") {
            hoursPerWeek = 40.0;
            shiftsPerDay = 1.0;
        }

        const baseHeadcount = schedule === "24_7" ? posts * 2.0 : posts * 1.0;
        const neededGuards = Math.ceil(baseHeadcount * (schedule === "24_7" ? rf / 2.0 : rf));
        const totalGuards = Math.max(neededGuards, Math.ceil(baseHeadcount * 1.25));

        const supsPerShift = Math.max(1, Math.ceil(posts / 12.0));
        const neededSupervisors = schedule === "24_7" ? Math.ceil(supsPerShift * 2 * 1.25) : supsPerShift;

        let neededVehicles = 0;
        if (["mining", "industrial"].includes(this.state.siteType) || posts >= 15) {
            neededVehicles = Math.ceil(posts / 20.0);
        } else if (posts >= 8) {
            neededVehicles = 1;
        }

        const neededRadios = (["mining", "embassy"].includes(this.state.siteType) ? posts : Math.ceil(posts / 2.0)) + neededSupervisors;
        const neededTorches = ["24_7", "night_12"].includes(schedule) ? posts + neededSupervisors : neededSupervisors;
        const neededBodycams = (["mining", "embassy", "banking"].includes(this.state.siteType) ? Math.ceil(posts / 3.0) : 0) + neededSupervisors;
        const neededUniformKits = Math.ceil((totalGuards + neededSupervisors) * 1.10);

        const monthlyPostHours = Math.round(posts * hoursPerWeek * 4.333 * 10) / 10;
        const monthlyRevenue = Math.round(monthlyPostHours * parseFloat(this.state.billRate) * 100) / 100;
        const guardPayroll = Math.round(totalGuards * parseFloat(this.state.guardPay));
        const supPayroll = Math.round(neededSupervisors * parseFloat(this.state.supervisorPay));
        const totalPayroll = guardPayroll + supPayroll;

        const equipCost = Math.round((neededVehicles * parseFloat(this.state.vehicleCost)) + (neededRadios * 150) + (neededTorches * 80));
        const monthlyProfit = Math.round((monthlyRevenue - totalPayroll - equipCost) * 100) / 100;
        const grossMarginPct = monthlyRevenue > 0 ? Math.round((monthlyProfit / monthlyRevenue * 100) * 10) / 10 : 0;

        this.state.results = {
            neededGuards: totalGuards,
            neededSupervisors,
            neededVehicles,
            neededRadios,
            neededTorches,
            neededBodycams,
            neededUniformKits,
            monthlyPostHours,
            monthlyRevenue,
            monthlyPayroll: totalPayroll,
            monthlyEquipment: equipCost,
            monthlyProfit,
            grossMarginPct,
        };
        this.state.calculated = true;
    }

    async saveDemandPlan() {
        this.state.saving = true;
        try {
            const res = await this.orm.create("security.demand.plan", [{
                name: this.state.title,
                partner_id: this.state.partnerId ? parseInt(this.state.partnerId) : false,
                site_name: this.state.siteName,
                site_type: this.state.siteType,
                posts_count: parseInt(this.state.postsCount),
                shift_duration: this.state.shiftDuration,
                operating_schedule: this.state.operatingSchedule,
                rotation_pattern: this.state.rotationPattern,
                relief_factor: parseFloat(this.state.reliefFactor),
                guard_monthly_pay: parseFloat(this.state.guardPay),
                supervisor_monthly_pay: parseFloat(this.state.supervisorPay),
                vehicle_monthly_cost: parseFloat(this.state.vehicleCost),
                bill_rate_per_post_hour: parseFloat(this.state.billRate),
                state: "estimated",
            }]);

            this.notification.add("Demand Plan saved & estimated successfully!", { type: "success" });
            this.props.closeModal();

            if (res && res.length) {
                this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "security.demand.plan",
                    res_id: res[0],
                    views: [[false, "form"]],
                    target: "current",
                });
            }
        } catch (e) {
            console.error("Failed to save demand plan", e);
            this.notification.add("Failed to save Demand Plan.", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }
}
