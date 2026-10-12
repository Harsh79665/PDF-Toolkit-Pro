"""Integration tests for Flask Web API endpoints."""

import io
from pathlib import Path

def test_index_route(web_client):
    """Verifies that the index page loads with the correct title and copyright text."""
    response = web_client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "PDF Utility Toolkit" in html
    assert "Copyright Reserved. Made by Harsh Patel." in html


def test_upload_endpoint(web_client, sample_pdf_3pages):
    """Verifies uploading PDF documents to the API."""
    with open(sample_pdf_3pages, "rb") as f:
        data = {
            "files": (io.BytesIO(f.read()), "test_upload.pdf")
        }
        response = web_client.post("/api/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "job_id" in json_data
    assert len(json_data["files"]) == 1
    assert json_data["files"][0]["page_count"] == 3


def test_merge_endpoint(web_client, sample_pdf_3pages, sample_pdf_1page):
    """Verifies complete upload and merge pipeline through API."""
    with open(sample_pdf_3pages, "rb") as f1, open(sample_pdf_1page, "rb") as f2:
        upload_data = {
            "files": [
                (io.BytesIO(f1.read()), "doc1.pdf"),
                (io.BytesIO(f2.read()), "doc2.pdf")
            ]
        }
        up_res = web_client.post("/api/upload", data=upload_data, content_type="multipart/form-data")

    job_id = up_res.get_json()["job_id"]

    # Execute merge
    process_data = {
        "operation": "merge",
        "job_id": job_id,
        "file_order": ["doc1.pdf", "doc2.pdf"]
    }
    proc_res = web_client.post("/api/process", json=process_data)
    assert proc_res.status_code == 200
    res_json = proc_res.get_json()
    assert res_json["success"] is True
    assert res_json["output"]["page_count"] == 4

    # Download output
    file_id = res_json["output"]["file_id"]
    down_res = web_client.get(f"/api/download/{file_id}")
    assert down_res.status_code == 200
    assert down_res.headers["Content-Type"] == "application/pdf"


def test_rotate_endpoint(web_client, sample_pdf_3pages):
    """Verifies rotate operation via API."""
    with open(sample_pdf_3pages, "rb") as f:
        up_res = web_client.post("/api/upload", data={"files": (io.BytesIO(f.read()), "rot.pdf")}, content_type="multipart/form-data")

    job_id = up_res.get_json()["job_id"]

    proc_res = web_client.post("/api/process", json={
        "operation": "rotate",
        "job_id": job_id,
        "filename": "rot.pdf",
        "angle": 90,
        "scope": "all"
    })
    assert proc_res.status_code == 200
    res_json = proc_res.get_json()
    assert res_json["summary"]["count_rotated"] == 3


def test_text_extract_endpoint(web_client, sample_pdf_3pages):
    """Verifies text extraction endpoint."""
    with open(sample_pdf_3pages, "rb") as f:
        up_res = web_client.post("/api/upload", data={"files": (io.BytesIO(f.read()), "extract.pdf")}, content_type="multipart/form-data")

    job_id = up_res.get_json()["job_id"]

    proc_res = web_client.post("/api/process", json={
        "operation": "extract_text",
        "job_id": job_id,
        "filename": "extract.pdf",
        "scope": "all"
    })
    assert proc_res.status_code == 200
    res_json = proc_res.get_json()
    assert res_json["data"]["total_words"] > 0
    assert "Lorem ipsum" in res_json["data"]["full_text"]


def test_list_and_delete_files_endpoint(web_client, sample_pdf_1page):
    """Verifies listing active files and deleting an asset."""
    # Create an asset via rotate
    with open(sample_pdf_1page, "rb") as f:
        up_res = web_client.post("/api/upload", data={"files": (io.BytesIO(f.read()), "todel.pdf")}, content_type="multipart/form-data")

    job_id = up_res.get_json()["job_id"]
    proc_res = web_client.post("/api/process", json={
        "operation": "rotate",
        "job_id": job_id,
        "filename": "todel.pdf",
        "angle": 90
    })
    file_id = proc_res.get_json()["output"]["file_id"]

    # Check in list
    list_res = web_client.get("/api/files")
    assert list_res.status_code == 200
    files = list_res.get_json()["files"]
    assert any(item["file_id"] == file_id for item in files)

    # Delete
    del_res = web_client.delete(f"/api/delete/{file_id}")
    assert del_res.status_code == 200

    # Ensure removed
    list_res_after = web_client.get("/api/files")
    files_after = list_res_after.get_json()["files"]
    assert not any(item["file_id"] == file_id for item in files_after)
