from django.core.management.base import BaseCommand
from api.models import OpenSolarProject
import requests
from decouple import config

# ─── Odoo JSON-RPC settings ─────────────────────────────────────────────────
ODOO_URL      = config("ODOO_URL")
ODOO_DB       = config("ODOO_DB")
ODOO_USERNAME = config("ODOO_API_USERNAME")
ODOO_PASSWORD = config("ODOO_API_TOKEN")
ODOO_RPC      = f"{ODOO_URL}/jsonrpc"

# ─── x_projects field names ────────────────────────────────────────────────
F_NAME       = "x_name"
F_PARTNER    = "x_studio_partner_id"
F_EXT_ID     = "x_studio_opensolar_external_id"
F_PROPOSAL   = "x_studio_open_solar_proposal"
F_VALUE      = "x_studio_value"
F_CHANGE     = "x_studio_change_order_price"
F_SYS_SIZE   = "x_studio_system_size_kw_1"

F_MOD_MAN    = "x_studio_module_manufacturer_name"
F_MOD_TYPE   = "x_studio_module_type"
F_MOD_QTY    = "x_studio_module_qty"

F_INV_MAN    = "x_studio_inverter_manufacturer_name"
F_INV_TYPE   = "x_studio_inverter_type"
F_INV_QTY    = "x_studio_inverter_qty"

F_BAT_MAN    = "x_studio_battery_manufacturer_name"
F_BAT_TYPE   = "x_studio_battery_type"
F_BAT_QTY    = "x_studio_battery_quantity"


class Command(BaseCommand):
    help = "Sync OpenSolarProject → Odoo x_projects (incl. first Module/Inverter/Battery)"

    def handle(self, *args, **kwargs):
        uid      = self._authenticate()
        projects = OpenSolarProject.objects.all()
        self.stdout.write(f"\n🔎  {projects.count()} projects in Django\n")

        for proj in projects:
            # ─── GUARD: skip any project with no customer linked
            if not proj.customer:
                self.stderr.write(
                    f"   ❌  SKIP: no customer linked for project external_id={proj.external_id}\n\n"
                )
                continue

            ext_id   = int(proj.external_id)
            share    = proj.share_link or ""
            price    = float(proj.price_including_tax or 0.0)  # Ensure using price_including_tax
            sys_size = float(proj.system_size_kw or 0.0)
            cust     = proj.customer

            self.stdout.write(
                f"➡️  OS#{ext_id} – customer: {cust.name}\n"
                f"   🔗 share_link: {share!r}\n"
                f"   💲 price (including tax): {price!r}\n"  # Display the price (including tax)
                f"   📏 sys_size:   {sys_size!r}"
            )

            if not share:
                self.stdout.write("   ‼️  SKIP: no share_link\n\n")
                continue

            # ─── Find or skip partner in Odoo (Map customer contact using external_id)
            partner = self._search_read(
                uid, "res.partner",
                ["|",
                    [F_EXT_ID, "=", cust.external_id],  # Use customer external_id
                    ["email", "=", cust.email or False],
                ],
                ["id", "name"]
            )
            if not partner:
                self.stderr.write(
                    f"   ❌  No Odoo contact for {cust.name} ({cust.email})\n\n"
                )
                continue

            pid = partner[0]["id"]
            self.stdout.write(f"   👤 partner #{pid}: {partner[0]['name']}")

            # ─── Build project vals
            vals = {
                F_NAME:     cust.name,
                F_PARTNER:  pid,
                F_EXT_ID:   ext_id,
                F_PROPOSAL: share,
                F_SYS_SIZE: sys_size,

                # Map price_including_tax to both value and change fields
                F_VALUE:    price,  # This is for the x_studio_value field (monetary field)
                F_CHANGE:   price,  # This is for the x_studio_change_order_price field (monetary field)
                "x_studio_open_solar_project_id": ext_id  # Correct field name here
            }

            # ─── Flatten first Module
            first_mod = proj.modules.first()
            if first_mod:
                vals.update({
                    F_MOD_MAN:  first_mod.manufacturer_name,
                    F_MOD_TYPE: first_mod.code,
                    F_MOD_QTY:  first_mod.quantity,
                })

            # ─── Flatten first Inverter
            first_inv = proj.inverters.first()
            if first_inv:
                vals.update({
                    F_INV_MAN:  first_inv.manufacturer_name,
                    F_INV_TYPE: first_inv.code,
                    F_INV_QTY:  first_inv.quantity,
                })

            # ─── Flatten first Battery
            first_bat = proj.batteries.first()
            if first_bat:
                vals.update({
                    F_BAT_MAN:  first_bat.manufacturer_name,
                    F_BAT_TYPE: first_bat.code,
                    F_BAT_QTY:  first_bat.quantity,
                })

            self.stdout.write(f"   [DEBUG] payload → {vals}")

            # ─── Dedupe on (external_id, customer_name) for the project
            existing = self._search_read(
                uid, "x_projects",
                ["|",
                    [F_EXT_ID, "=", ext_id],
                    [F_NAME,  "=", cust.name],
                ],
                ["id"]
            )

            if existing:
                prj_id = existing[0]["id"]
                self.stdout.write(f"   ✏️  Updating x_projects #{prj_id}")
                self._write(uid, "x_projects", prj_id, vals)
            else:
                prj_id = self._create(uid, "x_projects", vals)
                self.stdout.write(
                    self.style.SUCCESS(f"   🆕 Created x_projects #{prj_id}")
                )

            self.stdout.write("")  # blank line

        self.stdout.write(self.style.SUCCESS("✅ Full sync complete\n"))

    # ─── JSON-RPC helpers ────────────────────────────────────────────────────
    def _rpc(self, payload):
        resp = requests.post(ODOO_RPC, json=payload).json()
        if "error" in resp:
            raise RuntimeError(resp["error"]["data"]["message"])
        return resp.get("result", [])

    def _authenticate(self):
        return self._rpc({
            "jsonrpc":"2.0", "method":"call",
            "params":{
                "service":"common","method":"login",
                "args":[ODOO_DB,ODOO_USERNAME,ODOO_PASSWORD]
            }, "id":1
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
                    {"fields":fields,"limit":1}
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
                    model, "create",[vals]
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
                    model, "write",[[rec_id],vals]
                ]
            },"id":4
        })
