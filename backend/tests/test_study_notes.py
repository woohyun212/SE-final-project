def test_create_note(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.post(f"/api/v1/courses/{course_id}/notes", json={
        "title": "1주차 강의 노트",
        "content": "소프트웨어 공학 개론..."
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "1주차 강의 노트"
    assert data["course_id"] == course_id

def test_list_notes(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    client.post(f"/api/v1/courses/{course_id}/notes", json={
        "title": "노트 1"
    }, headers=auth_headers)
    response = client.get(f"/api/v1/courses/{course_id}/notes", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_update_note(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    create_resp = client.post(f"/api/v1/courses/{course_id}/notes", json={
        "title": "노트 1",
        "content": "원본 내용"
    }, headers=auth_headers)
    note_id = create_resp.json()["id"]
    
    response = client.put(f"/api/v1/courses/{course_id}/notes/{note_id}", json={
        "content": "수정된 내용"
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "수정된 내용"

def test_delete_note(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    create_resp = client.post(f"/api/v1/courses/{course_id}/notes", json={
        "title": "노트 1"
    }, headers=auth_headers)
    note_id = create_resp.json()["id"]
    
    response = client.delete(f"/api/v1/courses/{course_id}/notes/{note_id}", headers=auth_headers)
    assert response.status_code == 204

def test_note_not_found(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.get(f"/api/v1/courses/{course_id}/notes/999", headers=auth_headers)
    assert response.status_code == 404
