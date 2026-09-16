/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const REFRESH_INTERVAL_MS = 20000;
let gmapsLoaderPromise = null;

/** Injects the Google Maps JS SDK once per page, however many times the
 * map component itself gets mounted/unmounted (switching screens and
 * back shouldn't re-request the script). */
function loadGoogleMaps(apiKey) {
    if (window.google && window.google.maps) {
        return Promise.resolve(window.google.maps);
    }
    if (gmapsLoaderPromise) {
        return gmapsLoaderPromise;
    }
    gmapsLoaderPromise = new Promise((resolve, reject) => {
        const callbackName = "__dgArmedResponseGmapsReady";
        window[callbackName] = () => {
            delete window[callbackName];
            resolve(window.google.maps);
        };
        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&callback=${callbackName}&loading=async`;
        script.async = true;
        script.defer = true;
        script.onerror = () => reject(new Error("Failed to load the Google Maps script."));
        document.head.appendChild(script);
    });
    return gmapsLoaderPromise;
}

/** Reads a design-token color as a literal string, since Google Maps
 * marker/icon options need real color values, not CSS custom properties. */
function token(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

const STATUS_COLOR = {
    available: () => token("--ds-success", "#0D7A4E"),
    dispatched: () => token("--ds-warning", "#92400E"),
    on_scene: () => token("--ds-danger", "#991B1B"),
    returning: () => token("--ds-info", "#1D5FA4"),
    off_duty: () => token("--ds-text-subtle", "#64748B"),
};

export class LiveCalloutMap extends Component {
    static template = "security_armed_response.LiveCalloutMap";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.mapContainerRef = useRef("mapContainer");

        this.state = useState({
            loading: true,
            error: null,
            apiKeyMissing: false,
            data: { units: [], dispatches: [] },
        });

        this.map = null;
        this.markers = [];
        this.refreshTimer = null;

        onWillStart(async () => {
            await this.fetchData();
        });

        onMounted(async () => {
            if (this.state.apiKeyMissing || this.state.error) {
                return;
            }
            try {
                await loadGoogleMaps(this.apiKey);
                this.initMap();
                this.renderMarkers();
                this.refreshTimer = setInterval(() => this.refreshData(), REFRESH_INTERVAL_MS);
            } catch (err) {
                this.state.error = err.message;
            }
        });

        onWillUnmount(() => {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
            }
            this.clearMarkers();
        });
    }

    async fetchData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("security.response.map", "get_map_data", []);
            this.apiKey = data.api_key;
            this.state.apiKeyMissing = !data.api_key;
            this.state.data = { units: data.units || [], dispatches: data.dispatches || [] };
        } catch (err) {
            this.state.error = "Could not load map data.";
        } finally {
            this.state.loading = false;
        }
    }

    async refreshData() {
        try {
            const data = await this.orm.call("security.response.map", "get_map_data", []);
            this.state.data = { units: data.units || [], dispatches: data.dispatches || [] };
            if (this.map) {
                this.renderMarkers();
            }
        } catch {
            // Silent — a single missed refresh isn't worth surfacing an error banner over.
        }
    }

    initMap() {
        const el = this.mapContainerRef.el;
        if (!el || this.map) {
            return;
        }
        const first = this.state.data.units[0] || this.state.data.dispatches[0];
        const center = first ? { lat: first.lat, lng: first.lng } : { lat: -22.5597, lng: 17.0832 }; // Windhoek fallback
        this.map = new window.google.maps.Map(el, {
            center,
            zoom: first ? 12 : 6,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false,
        });
    }

    clearMarkers() {
        for (const marker of this.markers) {
            marker.setMap(null);
        }
        this.markers = [];
    }

    renderMarkers() {
        if (!this.map) {
            return;
        }
        this.clearMarkers();
        const gmaps = window.google.maps;
        const bounds = new gmaps.LatLngBounds();

        for (const dispatch of this.state.data.dispatches) {
            const marker = new gmaps.Marker({
                position: { lat: dispatch.lat, lng: dispatch.lng },
                map: this.map,
                title: `${dispatch.site_name} — ${dispatch.name}`,
                icon: {
                    path: gmaps.SymbolPath.BACKWARD_CLOSED_ARROW,
                    scale: 6,
                    rotation: 180,
                    fillColor: dispatch.priority === "critical" || dispatch.priority === "high"
                        ? token("--ds-danger", "#991B1B") : token("--ds-info", "#1D5FA4"),
                    fillOpacity: 1,
                    strokeWeight: 1,
                    strokeColor: "#FFFFFF",
                },
            });
            marker.addListener("click", () => this.openDispatch(dispatch.id));
            this.markers.push(marker);
            bounds.extend(marker.getPosition());
        }

        for (const unit of this.state.data.units) {
            const colorFn = STATUS_COLOR[unit.status] || STATUS_COLOR.off_duty;
            const marker = new gmaps.Marker({
                position: { lat: unit.lat, lng: unit.lng },
                map: this.map,
                title: `${unit.name} (${unit.status}${unit.is_stale ? " — stale" : ""})`,
                icon: {
                    path: gmaps.SymbolPath.CIRCLE,
                    scale: 8,
                    fillColor: colorFn(),
                    fillOpacity: unit.is_stale ? 0.4 : 1,
                    strokeWeight: 2,
                    strokeColor: "#FFFFFF",
                },
            });
            if (unit.active_dispatch_id) {
                marker.addListener("click", () => this.openDispatch(unit.active_dispatch_id));
            } else {
                marker.addListener("click", () => this.openUnit(unit.id));
            }
            this.markers.push(marker);
            bounds.extend(marker.getPosition());
        }

        if (this.markers.length > 1) {
            this.map.fitBounds(bounds);
        }
    }

    openDispatch(dispatchId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.response.dispatch",
            res_id: dispatchId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openUnit(unitId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.response.unit",
            res_id: unitId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSettings() {
        this.action.doAction("base_setup.action_general_configuration");
    }
}

registry.category("actions").add("security_armed_response.LiveCalloutMap", LiveCalloutMap);
