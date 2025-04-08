from rest_framework.decorators import api_view
from rest_framework.response import Response
import xmlrpc.client  # <- Required for Odoo XML-RPC connection

@api_view(['GET'])
def hello_world(request):
    return Response({"message": "Hello, API!"})

@api_view(['POST'])
def sync_odoo_projects(request):
    # Replace these with your actual Odoo credentials
    url = "https://sun-energy-partners-inc.odoo.com/"
    db = "sun-energy-partners-inc"
    token = "c956f25b438129602f8b77b47f1bee98bbd69737"  # Make sure your token is correct and securely stored
    
    try:
        # Set up the Odoo connection
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, token, token, {})  # token used as both user & password

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        projects = models.execute_kw(
            db, uid, token,
            'project.project', 'search_read',
            [[]], {'fields': ['name', 'user_id']}  # You can customize which fields to pull from Odoo
        )

        return Response({"status": "success", "projects": projects})

    except Exception as e:
        return Response({"status": "error", "message": str(e)})
