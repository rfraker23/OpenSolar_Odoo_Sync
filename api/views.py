from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import xmlrpc.client
import requests
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
opensolar_token = os.getenv("OPENSOLAR_API_TOKEN")  # Your actual OpenSolar token
odoo_api_token = os.getenv("ODOO_API_TOKEN")        # You can also move this to .env
odoo_username = os.getenv("ODOO_USERNAME")
odoo_url = "https://sun-energy-partners-inc.odoo.com/"
odoo_db = "sun-energy-partners-inc"

# 🧪 Test endpoint
@api_view(['GET'])
def hello_world(request):
    return Response({"message": "Hello, API!"})

# 🔄 Sync from Odoo
@api_view(['POST'])
def sync_odoo_projects(request):
    try:
        common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
        uid = common.authenticate(odoo_db, odoo_username, odoo_api_token, {})

        models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
        projects = models.execute_kw(
            odoo_db, uid, odoo_api_token,
            'project.project', 'search_read',
            [[]], {'fields': ['name', 'user_id']}
        )

        return Response({"status": "success", "projects": projects})

    except Exception as e:
        return Response({"status": "error", "message": str(e)})

# 🚀 Send new project to OpenSolar
@api_view(['POST'])
def send_to_opensolar(request):
    data = request.data

    headers = {
        'Authorization': f'Bearer {opensolar_token}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.post(
            'https://api.opensolar.com/v1/projects',  # Update this if needed
            json=data,
            headers=headers
        )

        return Response({"status": "sent", "response": response.json()})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})

# ✅ Test OpenSolar Token
@api_view(['GET'])
def test_opensolar_token(request):
    headers = {
        "Authorization": f"Bearer {opensolar_token}",
        "Content-Type": "application/json"
    }

    url = "https://api.opensolar.com/v1/projects"  # Or any valid test endpoint

    try:
        response = requests.get(url, headers=headers)
        return Response({
            "status": "success",
            "code": response.status_code,
            "response": response.json()
        })
    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        })

