/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class HelpPortal extends Component {
    static template = "security_help.HelpPortal";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.companyCountryCode = "";
        this.state = useState({
            categories: [],
            articles: [],
            activeCatId: null,
            activeArticleId: null,
            activeArticle: null,
            searchQuery: "",
            searchResults: [],
            searching: false,
        });
        this._searchTimer = null;

        onWillStart(async () => {
            this.companyCountryCode = await this.orm.call(
                "security.help.article",
                "get_company_country_code",
                []
            );
            await this._loadCategories();
        });
    }

    _countryDomain() {
        // Show categories/articles with no country restriction OR matching this company's country.
        return ["|", ["country_code", "=", false], ["country_code", "=", this.companyCountryCode]];
    }

    async _loadCategories() {
        const cats = await this.orm.searchRead(
            "security.help.category",
            this._countryDomain(),
            ["id", "name", "icon", "color", "article_count"],
            { order: "sequence asc, name asc" }
        );
        this.state.categories = cats;
    }

    async selectCategory(catId) {
        this.state.activeCatId = catId;
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
        this.state.searchQuery = "";
        this.state.searching = false;
        this.state.searchResults = [];

        const domain = [["category_id", "=", catId], ...this._countryDomain()];
        const arts = await this.orm.searchRead(
            "security.help.article",
            domain,
            ["id", "title", "summary"],
            { order: "sequence asc, title asc" }
        );
        this.state.articles = arts;
    }

    async openArticle(articleId) {
        this.state.activeArticleId = articleId;
        this.state.activeArticle = null;

        const [art] = await this.orm.read("security.help.article", [articleId], [
            "id", "title", "summary", "body", "category_id",
        ]);
        this.state.activeArticle = art;
    }

    goBack() {
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
    }

    onSearchInput(ev) {
        const q = ev.target.value;
        this.state.searchQuery = q;
        clearTimeout(this._searchTimer);
        if (!q.trim()) {
            this.state.searching = false;
            this.state.searchResults = [];
            return;
        }
        this._searchTimer = setTimeout(() => this._runSearch(q), 300);
    }

    onSearchKeydown(ev) {
        if (ev.key === "Escape") {
            this.state.searchQuery = "";
            this.state.searching = false;
            this.state.searchResults = [];
        }
    }

    async _runSearch(q) {
        if (!q.trim()) return;
        this.state.searching = true;
        this.state.activeCatId = null;
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
        const results = await this.orm.call(
            "security.help.article",
            "search_articles",
            [q, this.companyCountryCode]
        );
        this.state.searchResults = results;
    }
}

registry.category("actions").add("security_help.HelpPortal", HelpPortal);
