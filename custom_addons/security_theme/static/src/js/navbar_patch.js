/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { DogForceAppLauncher } from "./dogforce_app_launcher";

patch(NavBar.prototype, {
    toggleDogForceAppLauncher() {
        this.state.showDogForceAppLauncher = !this.state.showDogForceAppLauncher;
    },
    closeDogForceAppLauncher() {
        this.state.showDogForceAppLauncher = false;
    }
});

NavBar.components = {
    ...NavBar.components,
    DogForceAppLauncher,
};
