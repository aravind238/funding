import requests
import os
from .response import custom_response
from src.middleware.permissions import Permissions



def get_presigned_url(content_type=None, name=None, description=None):
    url = os.environ.get("RESOURCES_URL")
    business_id = Permissions.get_user_details()["business_id"]
    api_token = os.environ.get("RESOURCES_API_TOKEN")

    content_type = content_type
    name = name
    description = description

    make_request = requests.post(
        url + "api/v2/integrators/upload",
        json={
            "business_uuid": business_id,
            "name": name,
            "description": description,
            "content_type": content_type,
        },
        headers={"api-token": api_token},
    )
    
    return make_request


def generate_pdf(file_name=None, html=None):    
    if not html:
      return custom_response(
          {"status": "error", "msg": "html file is required"}, 404
      )

    if not file_name:
      return custom_response(
          {"status": "error", "msg": "file name is required"}, 404
      )
    
    content_type = "text/html"
    name = f"{file_name}.html"
    description = "HTML File"
    html_upload = get_presigned_url(
        content_type=content_type, name=name, description=description
    )

    if not (200 <= html_upload.status_code <= 299):
        html_upload_msg = html_upload.json()["msg"]      
        return custom_response(
            {"status": "error", "msg": f"integrators/upload => {html_upload_msg}"},
            html_upload.status_code,
        )

    html_upload_url = html_upload.json()["payload"]["upload_url"]
    html_full_url = html_upload.json()["payload"]["full_url"]

    is_uploaded = requests.put(
        html_upload_url,
        data=html,
        headers={"Content-Type": content_type},
    )

    # html_upload
    print("--html_upload--", html_upload_url)
    print("--is_uploaded--", is_uploaded)

    url = os.environ.get("RESOURCES_URL")
    api_token = os.environ.get("RESOURCES_API_TOKEN")

    pdf = requests.post(
        url + "api/v2/integrators/generate",
        json={
            "folder_id": "",
            "url": html_full_url,
            "file_name": f"{file_name}.pdf",
            "file_type": "pdf",
            "height": 1080,
            "width": 1920,
            "full_page": False,
        },
        headers={"api-token": api_token},
    )

    # check if pdf generate fails
    if not (200 <= pdf.status_code <= 299):
        pdf_msg = pdf.json()["msg"]      
        return custom_response(
            {"status": "error", "msg": f"integrators/generate => {pdf_msg}"},
            pdf.status_code,
        )

    pdf_url = pdf.json()["payload"]["full_url"]

    return pdf_url
