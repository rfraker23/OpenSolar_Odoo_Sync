from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import xmlrpc.client
import requests
import os
from dotenv import load_dotenv
from api.serializers import OpenSolarProjectSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.serializers import OpenSolarProjectSerializer

@api_view(['POST'])
def validate_opensolar_project(request):
    serializer = OpenSolarProjectSerializer(data=request.data)
    if serializer.is_valid():
        return Response({
            "status": "valid",
            "data": serializer.validated_data
        })
    else:
        return Response({
            "status": "invalid",
            "errors": serializer.errors
        }, status=400)

# Load .env variables
load_dotenv()
opensolar_token = os.getenv("OPENSOLAR_API_TOKEN")  # Your actual OpenSolar token
odoo_api_token = os.getenv("ODOO_API_TOKEN")        # You can also move this to .env
odoo_username = os.getenv("ODOO_USERNAME")
odoo_url = "https://sun-energy-partners-inc.odoo.com/"
odoo_db = "sun-energy-partners-inc"

@api_view(['GET'])
def sync_projects_from_opensolar(request):
    headers = {
        'Authorization': f'Bearer {opensolar_token}',
        'Content-Type': 'application/json',
    }

    url = "https://api.opensolar.com/v1/projects"

    try:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return Response({
                "status": "error",
                "message": f"OpenSolar API error: {response.status_code}",
                "response": response.text
            }, status=response.status_code)

        projects = response.json()

        # Optional: limit, filter, or sanitize here
        return Response({
            "status": "fetched",
            "projects": projects
        })

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=500)

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
    
@api_view(['GET'])
def opensolar_webhook_logs(request):
    headers = {
        'Authorization': f'Bearer {opensolar_token}',
        'Content-Type': 'application/json',
    }

    org_id = os.getenv("OPENSOLAR_ORG_ID")
    url = f"https://api.opensolar.com/api/orgs/{org_id}/webhook_process_logs/"

    params = {
        "limit": 10  # Optional: try paging
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return Response({
                "status": "error",
                "message": f"OpenSolar API error: {response.status_code}",
                "response": response.text
            }, status=response.status_code)

        return Response({
            "status": "fetched",
            "logs": response.json()
        })

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=500)


# ✅ Test OpenSolar Token
@api_view(['GET'])
def test_opensolar_token(request):
    headers = {
    "Authorization": f"Bearer {settings.OPENSOLAR_API_TOKEN}",
    "Content-Type": "application/json"
    }

    url = "https://api.opensolar.com/api/v1/projects"  

    try:
        response = requests.get(url, headers=headers)

        # Check if the response is a valid JSON and if the status is OK
        if response.status_code == 200:
            return Response({
                "status": "success",
                "code": response.status_code,
                "response": response.json()  # Parse the response as JSON
            })
        else:
            return Response({
                "status": "error",
                "message": f"Error from OpenSolar API: {response.status_code} - {response.text}"
            })

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        })

