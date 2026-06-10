/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * PayslipPreviewDialog — renders the payslip QWeb PDF report inside a modal
 * iframe so finance officers can verify figures before printing or confirming.
 *
 * Usage: triggered from the payslip form via the "Preview" button which calls
 * the `action_preview_payslip` Python method returning an ir.actions.client
 * with tag "security_payroll_core.payslip_preview" and context.payslip_id.
 */
class PayslipPreviewDialog extends Component {
    static template = "security_payroll_core.PayslipPreviewDialog";
    static components = { Dialog };
    static props = {
        payslipId: { type: Number },
        close: { type: Function },
    };

    setup() {
        this.state = useState({ loading: true });
    }

    get iframeSrc() {
        return `/report/html/security_payroll_core.report_security_payslip/${this.props.payslipId}`;
    }

    onLoad() {
        this.state.loading = false;
    }
}

/**
 * PayslipPreviewAction — thin client action wrapper that opens the dialog.
 * Registered so ir.actions.client with tag "security_payroll_core.payslip_preview"
 * opens the preview correctly.
 */
class PayslipPreviewAction extends Component {
    static template = "security_payroll_core.PayslipPreviewAction";
    static components = { PayslipPreviewDialog };
    static props = { "*": true };

    setup() {
        this.dialog = useService("dialog");
        const ctx = this.props.action?.context || {};
        const payslipId = ctx.payslip_id;

        onWillStart(() => {
            if (payslipId) {
                this.dialog.add(PayslipPreviewDialog, {
                    payslipId,
                    close: () => this.props.onActionExecuted?.(),
                });
            }
        });
    }
}

registry.category("actions").add(
    "security_payroll_core.payslip_preview",
    PayslipPreviewAction
);
registry.category("dialogs").add(
    "security_payroll_core.PayslipPreviewDialog",
    PayslipPreviewDialog
);
