# api/management/commands/sync_projects_to_odoo.py

from django.core.management.base import BaseCommand
from api.models import OpenSolarProject
import requests
from decouple import config

# ─── Odoo JSON‐RPC settings ───
ODOO_URL      = config("ODOO_URL")
ODOO_DB       = config("ODOO_DB")
ODOO_USERNAME = config("ODOO_API_USERNAME")
ODOO_PASSWORD = config("ODOO_API_TOKEN")
ODOO_RPC      = f"{ODOO_URL}/jsonrpc"

# ─── Your Studio‑fields on x_projects ───
FIELD_PROJECT_NAME       = "x_name"                          # holds customer name
FIELD_PARTNER_ID         = "x_studio_partner_id"
FIELD_EXTERNAL_ID        = "x_studio_opensolar_external_id"
FIELD_PROPOSAL_LINK      = "x_studio_open_solar_proposal"
FIELD_VALUE              = "x_studio_value"
FIELD_CHANGE_ORDER_PRICE = "x_studio_change_order_price"
FIELD_SYS_SIZE           = "x_studio_system_size_kw_1"       # new float field

class Command(BaseCommand):
    help = "Sync OpenSolarProject → Odoo x_projects (dedupe on External ID OR customer name)"

    def handle(self, *args, **kwargs):
        uid      = self._authenticate()
        projects = OpenSolarProject.objects.all()
        self.stdout.write(f"\n🔎  {projects.count()} projects in Django\n")

        for proj in projects:
            # ——— extract all source values early ———
            ext_id      = int(proj.external_id)
            share       = proj.share_link or ""
            price       = float(proj.price) if proj.price is not None else 0.0
            system_size = float(proj.system_size_kw or 0.0)   # <— here’s your system size
            cust        = proj.customer

            # ——— logging ———
            self.stdout.write(f"➡️  OS#{ext_id} – customer: {cust.name}")
            self.stdout.write(f"   🔗 share_link: {share!r}")
            self.stdout.write(f"   💲 price:      {price!r}")
            self.stdout.write(f"   📏 sys_size:   {system_size!r}")

            if not share:
                self.stdout.write("   ‼️  SKIP: no share_link\n")
                continue

            # ——— find the partner in Odoo (by ext_id or email) ———
            partner_domain = [
                "|",
                [FIELD_EXTERNAL_ID, "=", cust.external_id],
                ["email",           "=", cust.email or False]
            ]
            part = self._search_read(uid, "res.partner", partner_domain, ["id", "name"])
            if not part:
                self.stderr.write(f"   ❌  No Odoo contact for {cust.external_id}/{cust.email}\n")
                continue
            pid = part[0]["id"]
            self.stdout.write(f"   👤  partner #{pid}: {part[0]['name']}")

            # ——— build your payload ———
            vals = {
                FIELD_PROJECT_NAME:       cust.name,
                FIELD_PARTNER_ID:         pid,
                FIELD_EXTERNAL_ID:        ext_id,
                FIELD_PROPOSAL_LINK:      share,
                FIELD_VALUE:              price,
                FIELD_CHANGE_ORDER_PRICE: price,
                FIELD_SYS_SIZE:           system_size,
            }
            self.stdout.write(f"   [DEBUG] payload → {vals}")

            # ——— dedupe on External ID OR customer name ———
            search_domain = [
                "|",
                [FIELD_EXTERNAL_ID, "=", ext_id],
                [FIELD_PROJECT_NAME,  "=", cust.name],
            ]
            self.stdout.write(f"   [DEBUG] x_projects search domain → {search_domain}")
            existing = self._search_read(uid, "x_projects", search_domain, ["id"])
            self.stdout.write(f"   [DEBUG] x_projects search → {existing}")

            if existing:
                rec_id = existing[0]["id"]
                self.stdout.write(f"   ✏️  Updating x_projects #{rec_id}")
                self._write(uid, "x_projects", rec_id, vals)
            else:
                new_id = self._create(uid, "x_projects", vals)
                self.stdout.write(self.style.SUCCESS(f"   🆕 Created x_projects #{new_id}\n"))

        self.stdout.write(self.style.SUCCESS("✅  Sync complete\n"))


    # ─── JSON‑RPC helpers ───
    def _rpc(self, payload):
        resp = requests.post(ODOO_RPC, json=payload).json()
        if "error" in resp:
            raise RuntimeError(resp["error"]["message"])
        return resp.get("result", [])

    def _authenticate(self):
        return self._rpc({
            "jsonrpc":"2.0","method":"call",
            "params":{
                "service":"common","method":"login",
                "args":[ODOO_DB,ODOO_USERNAME,ODOO_PASSWORD]
            },"id":1
        })

    def _search_read(self, uid, model, domain, fields):
        return self._rpc({
            "jsonrpc":"2.0","method":"call",
            "params":{
                "service":"object","method":"execute_kw",
                "args":[
                    ODOO_DB, uid, ODOO_PASSWORD,
                    model, "search_read",
                    [domain],
                    {"fields": fields, "limit": 1}
                ]
            },"id":2
        }) or []

    def _create(self, uid, model, vals):
        return self._rpc({
            "jsonrpc":"2.0","method":"call",
            "params":{
                "service":"object","method":"execute_kw",
                "args":[
                    ODOO_DB, uid, ODOO_PASSWORD,
                    model, "create",
                    [vals]
                ]
            },"id":3
        })

    def _write(self, uid, model, rec_id, vals):
        return self._rpc({
            "jsonrpc":"2.0","method":"call",
            "params":{
                "service":"object","method":"execute_kw",
                "args":[
                    ODOO_DB, uid, ODOO_PASSWORD,
                    model, "write",
                    [[rec_id], vals]
                ]
            },"id":4
        })
