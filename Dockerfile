# ─────────────────────────────────────────────────────────────────────────────
# DogForce Security Services — Production Dockerfile
# Base: official Odoo 19.0 image
# Targets: Fly.io (primary), any Docker host
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
# Copies the entire custom_addons directory into the extra-addons mount point
COPY --chown=odoo:odoo custom_addons/ /mnt/extra-addons/

# ── Copy Fly.io entrypoint ─────────────────────────────────────────────────────
COPY deploy/fly-entrypoint.sh /fly-entrypoint.sh
RUN chmod +x /fly-entrypoint.sh

# ── Drop back to the odoo user ─────────────────────────────────────────────────
USER odoo

EXPOSE 10000 8072

ENTRYPOINT ["/fly-entrypoint.sh"]
CMD ["start"]
