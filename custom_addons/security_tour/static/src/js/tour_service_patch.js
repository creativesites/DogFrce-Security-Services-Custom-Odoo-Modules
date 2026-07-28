/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";

// Register custom tour launcher handler
export const deployguardTourAutoStarter = {
    dependencies: ["orm", "action"],
    async start(env, { orm, action }) {
        // Wait briefly for main interface to load
        setTimeout(async () => {
            try {
                const res = await orm.call("res.users", "get_pending_user_tour", []);
                if (res && res.pending_tour) {
                    if (window.__deployguard_tour_runner__) {
                        window.__deployguard_tour_runner__.startTour(res.pending_tour);
                    } else {
                        const tourService = env.services.tour_service;
                        if (tourService && typeof tourService.startTour === 'function') {
                            tourService.startTour(res.pending_tour);
                        }
                    }
                }
            } catch (_e) {
                // Ignore auto-start error
            }
        }, 2000);
    }
};

registry.category("services").add("deployguard_tour_auto_starter", deployguardTourAutoStarter);
