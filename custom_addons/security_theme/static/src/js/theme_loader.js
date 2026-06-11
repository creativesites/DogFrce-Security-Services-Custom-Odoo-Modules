/** @odoo-module **/

import { registry } from "@web/core/registry";

const THEMES = [
    'dogforce_navy',
    'corporate_dark',
    'forest_guard',
    'executive_slate',
];

const themeService = {
    dependencies: ['orm'],

    async start(env, { orm }) {
        let theme = 'dogforce_navy';
        try {
            theme = await orm.call(
                'ir.config_parameter',
                'get_param',
                ['security.theme.active', 'dogforce_navy']
            ) || 'dogforce_navy';
        } catch (_e) {
            // Fallback silently
        }

        THEMES.forEach(t => document.body.classList.remove('o_theme_' + t));
        document.body.classList.add('o_theme_' + theme);
    },
};

registry.category('services').add('security_theme_loader', themeService);
