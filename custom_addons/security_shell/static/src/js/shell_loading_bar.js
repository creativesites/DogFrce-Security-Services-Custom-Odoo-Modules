/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/** A slim top-edge progress bar that appears while any RPC is in flight —
 * the same "something is happening" signal a normal SaaS app gives you,
 * which the shell doesn't get for free once the classic navbar (and its
 * own loading affordances) are hidden. Purely presentational: all the
 * actual counting lives in shellService, tracked off Odoo's own rpcBus so
 * this never has to be told by each screen individually. */
export class ShellLoadingBar extends Component {
    static template = "security_shell.ShellLoadingBar";
    static props = { "*": true };

    setup() {
        const shellService = useService("deployguard_shell");
        this.shell = { ...shellService, state: useState(shellService.state) };
    }

    get isLoading() {
        return this.shell.state.pendingRequestCount > 0;
    }
}
