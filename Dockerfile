# ─────────────────────────────────────────────────────────────────────────────
# DogForce Security Services – Production Dockerfile
# Base: official Odoo 19.0 image
# Target: Render (any Docker host)
# ─────────────────────────────────────────────────────────────────────────────

FROM odoo:19.0

LABEL maintainer="winston@cvmworldwide.com" \
      org.opencontainers.image.title="DogForce Security Platform" \
      org.opencontainers.image.description="Custom Odoo 19 ERP for security companies"

# ── System dependencies ────────────────────────────────────────────────────────
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# ── Copy custom addons ─────────────────────────────────────────────────────────
COPY --chown=odoo:odoo custom_addons/ /mnt/extra-addons/

# ── Drop back to the odoo user ─────────────────────────────────────────────────
USER odoo

# Odoo uses 8069 by default; longpolling on 8072
EXPOSE 8080 8072

# The official Odoo image already defines a correct ENTRYPOINT + CMD.
# We do NOT override them – Render will pass its own PORT if you set it,
# but we'll avoid that and let Odoo use its default.
