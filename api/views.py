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
    username = "ryan.fraker@joinsunenergy.com"  # <- Your Odoo login email
    api_token = "c956f25b438129602f8b77b47f1bee98bbd69737"  # <- Your API token

    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, api_token, {})  # correct usage

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        projects = models.execute_kw(
            db, uid, api_token,  # use api_token here too
            'project.project', 'search_read',
            [[]], {'fields': ['name', 'user_id']}
        )

        return Response({"status": "success", "projects": projects})

    except Exception as e:
        return Response({"status": "error", "message": str(e)})
    
    import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def send_to_opensolar(request):
    data = request.data  # Get project info from POST request

    headers = {
        'Authorization': f'Bearer YOUR_OPENSOLAR_API_KEY',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.post(
            'https://api.opensolar.com/v1/projects',
            json=data,
            headers=headers
        )

        return Response({"status": "sent", "response": response.json()})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})

