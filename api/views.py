import logging
from django.conf import settings
from django.core.management import call_command
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

@require_GET
def sync_all(request):
    """
    Runs in order:
      1. sync_opensolar
      2. sync_contacts_to_odoo
      3. sync_projects_to_odoo
    """
    secret = request.GET.get("key")
    if getattr(settings, "SYNC_SECRET", None):
        if secret != settings.SYNC_SECRET:
            logger.warning("Rejected sync_all call with bad key=%r", secret)
            return HttpResponseForbidden("❌ Invalid sync key")

    try:
        logger.info("▶️ Full sync: OpenSolar → Django → Odoo")

        call_command("sync_opensolar")
        logger.info("   ✔️  sync_opensolar complete")

        call_command("sync_contacts_to_odoo")
        logger.info("   ✔️  sync_contacts_to_odoo complete")

        call_command("sync_projects_to_odoo")
        logger.info("   ✔️  sync_projects_to_odoo complete")

        logger.info("✅ Full sync_all succeeded")
        return JsonResponse({"status": "ok"})

    except Exception:
        logger.exception("💥 Full sync_all failed")
        return JsonResponse(
            {"status": "error", "detail": "See server logs"},
            status=500
        )
