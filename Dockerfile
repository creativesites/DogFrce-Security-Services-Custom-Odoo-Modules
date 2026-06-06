FROM odoo:19.0

LABEL maintainer="winston@cvmworldwide.com" \
      org.opencontainers.image.title="DogForce Security Platform" \
      org.opencontainers.image.description="Custom Odoo 19 ERP for security companies"

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=odoo:odoo custom_addons/ /mnt/extra-addons/
COPY --chown=odoo:odoo odoo.conf /etc/odoo/odoo.conf

USER odoo

EXPOSE 8069 8072

CMD ["odoo", "--config=/etc/odoo/odoo.conf"]
