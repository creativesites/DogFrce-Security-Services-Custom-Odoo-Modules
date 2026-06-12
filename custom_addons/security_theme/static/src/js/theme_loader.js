/** @odoo-module **/

import { registry } from "@web/core/registry";

const THEMES = [
    'dogforce_navy',
    'corporate_dark',
    'forest_guard',
    'executive_slate',
];

const FONTS = {
    inter: {
        family: "'Inter', system-ui, -apple-system, sans-serif",
        url: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
    },
    plus_jakarta_sans: {
        family: "'Plus Jakarta Sans', system-ui, sans-serif",
        url: "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap",
    },
    dm_sans: {
        family: "'DM Sans', system-ui, sans-serif",
        url: "https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap",
    },
    nunito: {
        family: "'Nunito', system-ui, sans-serif",
        url: "https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700;800&display=swap",
    },
    outfit: {
        family: "'Outfit', system-ui, sans-serif",
        url: "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap",
    },
    manrope: {
        family: "'Manrope', system-ui, sans-serif",
        url: "https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap",
    },
};

function applyFont(fontKey) {
    const cfg = FONTS[fontKey];
    if (!cfg) return;
    if (!document.querySelector(`link[data-dg-font]`)) {
        const preconnect1 = document.createElement('link');
        preconnect1.rel = 'preconnect';
        preconnect1.href = 'https://fonts.googleapis.com';
        document.head.appendChild(preconnect1);

        const preconnect2 = document.createElement('link');
        preconnect2.rel = 'preconnect';
        preconnect2.href = 'https://fonts.gstatic.com';
        preconnect2.crossOrigin = 'anonymous';
        document.head.appendChild(preconnect2);

        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = cfg.url;
        link.setAttribute('data-dg-font', fontKey);
        document.head.appendChild(link);
    }
    document.documentElement.style.setProperty('--dg-font-family', cfg.family);
}

const themeService = {
    dependencies: ['orm'],

    async start(env, { orm }) {
        let theme = 'dogforce_navy';
        let font = 'inter';
        try {
            [theme, font] = await Promise.all([
                orm.call('ir.config_parameter', 'get_param', ['security.theme.active', 'dogforce_navy']),
                orm.call('ir.config_parameter', 'get_param', ['security.theme.ui_font', 'inter']),
            ]);
            theme = theme || 'dogforce_navy';
            font = font || 'inter';
        } catch (_e) {}

        THEMES.forEach(t => document.body.classList.remove('o_theme_' + t));
        document.body.classList.add('o_theme_' + theme);

        if (font !== 'system') {
            applyFont(font);
        }
    },
};

registry.category('services').add('security_theme_loader', themeService);
