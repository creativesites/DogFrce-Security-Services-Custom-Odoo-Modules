/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { imageUrl } from "@web/core/utils/urls";

const userMenuRegistry = registry.category("user_menuitems");

/** Popover content for the rail avatar — a real account menu, not just a
 * shortcut straight to the user's own form view. Built entirely on Odoo's
 * own "user_menuitems" registry (the same one the classic navbar's user
 * menu reads from) rather than hand-rolling logout/preferences links, so
 * it stays correct — right logout route, service-worker notification on
 * sign-out, etc. — and automatically includes whatever any other
 * installed module contributes there (e.g. "Install App"), not just the
 * handful of items this file happens to know about. */
export class ShellProfileCard extends Component {
    static template = "security_shell.ShellProfileCard";
    static props = {
        close: { type: Function, optional: true },
    };

    setup() {
        this.userName = user.name;
        this.userLogin = user.login;
        this.dbName = session.db;
        const { partnerId, writeDate } = user;
        this.avatarUrl = imageUrl("res.partner", partnerId, "avatar_128", { unique: writeDate });
    }

    get items() {
        return userMenuRegistry
            .getAll()
            .map((element) => element(this.env))
            .filter((element) => (element.show ? element.show() : true))
            .sort((a, b) => (a.sequence || 100) - (b.sequence || 100));
    }

    onItemClick(item) {
        item.callback?.();
        this.props.close?.();
    }
}
