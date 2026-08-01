# DeployGuard — Mobile Operations & Production Deployment Guide

**Target System:** DogForce Security Services Production (`https://dogforcesecurityservices.com`)  
**Production Server IP:** `199.192.23.46`  
**SSH User / Password:** `root` / `4Li02oO6R5mCT6Uyhx`  
**Document Version:** 1.0 (August 2026)

---

## 1. Required Mobile Tools & Setup

To manage, monitor, and deploy updates to the production server directly from your iOS or Android mobile device:

### **Recommended SSH Terminal Apps**
* **iOS (iPhone/iPad):**
  * **[Termius](https://termius.com)** *(Recommended — supports saved snippets, touch ID/Face ID login, and quick command buttons)*
  * **Prompt 3** *(Panic Transmit)*
* **Android:**
  * **[Termius](https://termius.com)** *(Recommended)*
  * **JuiceSSH**

### **Server Connection Profile Settings**
In your mobile SSH app, create a new host entry with these details:

| Setting | Value |
|---|---|
| **Host / IP** | `199.192.23.46` |
| **Port** | `22` |
| **Username** | `root` |
| **Password** | `4Li02oO6R5mCT6Uyhx` |
| **Label / Name** | `DogForce Production VPS` |

---

## 2. One-Tap Snippets & Saved Commands

In **Termius** (or your SSH app's Snippets section), save the following quick-action buttons for 1-tap mobile execution:

### **📱 Snippet 1: Update All Modules & Production Code**
> **Snippet Name:** `1. Update Production`
```bash
cd /opt/dogforce && git pull origin main && ./scripts/promote_staging_to_prod.sh security_suite
```
* **What it does:** Pulls the latest tested code from GitHub, executes an automated pre-deploy rollback snapshot, updates all `security_suite` modules, and runs a health check.

---

### **📱 Snippet 2: Upgrade Specific Module Only (e.g. `security_operations`)**
> **Snippet Name:** `2. Upgrade Operations`
```bash
cd /opt/dogforce && ./scripts/promote_staging_to_prod.sh security_operations
```

---

### **📱 Snippet 3: Check Live Production Logs**
> **Snippet Name:** `3. View Production Logs`
```bash
docker logs --tail 100 -f dogforce-prod-odoo
```
* **Tip on Mobile:** Press `Ctrl + C` in Termius to exit log tailing.

---

### **📱 Snippet 4: Quick Server Health Check**
> **Snippet Name:** `4. Health Check`
```bash
curl -I http://localhost:8069/web/health
```
* **Expected Output:** `HTTP/1.0 200 OK` or `303 SEE OTHER`.

---

### **📱 Snippet 5: Emergency Container Restart**
> **Snippet Name:** `5. Restart Odoo`
```bash
docker restart dogforce-prod-odoo
```

---

## 3. Step-by-Step Mobile Workflows

### **Workflow A: Deploying Code Changes from GitHub**
1. Open **Termius** on your phone.
2. Tap **DogForce Production VPS**.
3. Tap the **`1. Update Production`** snippet.
4. Watch the terminal output:
   * Look for: `✅ Pre-deploy snapshot completed.`
   * Look for: `✅ Module upgrade completed successfully.`
   * Look for: `🎉 PROMOTION SUCCESSFUL! DeployGuard Production is healthy & operational.`

---

### **Workflow B: Activating a Newly Created Odoo Module**
If a brand new module was added to GitHub and you need to force Odoo to recognize it:

```bash
cd /opt/dogforce
git pull origin main
docker exec -i dogforce-prod-odoo odoo -c /etc/odoo/odoo.conf -d dogforce_prod -i security_reconciliation_core,security_reconciliation_billing_account --stop-after-init
docker restart dogforce-prod-odoo
```

---

### **Workflow C: Triggering a Manual Full Backup to Cloud Vault**
To trigger an immediate database + attachment filestore backup to Cloudflare R2 from your phone:

```bash
docker exec -i dogforce-prod-odoo odoo shell --no-http -c /etc/odoo/odoo.conf -d dogforce_prod -c "env['security.backup.manager'].sudo().run_nightly_full_backup()"
```

---

## 4. Emergency Troubleshooting from Mobile

| Symptom on Mobile | What to Do | Mobile Command |
|---|---|---|
| **Site is slow / un-responsive** | Check live container logs for memory or worker locks | `docker logs --tail 50 dogforce-prod-odoo` |
| **Site displays 502 Bad Gateway** | Restart Odoo container | `docker restart dogforce-prod-odoo` |
| **Database error after update** | The promotion script auto-rolls back, but to manually restart: | `./scripts/promote_staging_to_prod.sh security_suite` |
| **Low Disk Warning on WhatsApp** | Check free disk space | `df -h /` |

---

*Guide prepared for DogForce Management & Engineering.*
