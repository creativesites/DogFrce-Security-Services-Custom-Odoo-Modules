FROM odoo:19.0

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=odoo:odoo custom_addons/ /mnt/extra-addons/
COPY --chown=odoo:odoo odoo.conf /etc/odoo/odoo.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER odoo

EXPOSE 8069 8072

CMD ["/entrypoint.sh"]
