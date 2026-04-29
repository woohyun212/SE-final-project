def test_create_course(client, auth_headers):
    response = client.post("/api/v1/courses/", json={
        "name": "데이터베이스",
        "professor": "이교수",
        "credits": 3
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "데이터베이스"

def test_list_courses(client, auth_headers, sample_course):
    response = client.get("/api/v1/courses/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_get_course(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.get(f"/api/v1/courses/{course_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == course_id

def test_get_nonexistent_course(client, auth_headers):
    response = client.get("/api/v1/courses/999", headers=auth_headers)
    assert response.status_code == 404

def test_update_course(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.put(f"/api/v1/courses/{course_id}", json={
        "name": "소프트웨어 공학 (수정됨)"
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "소프트웨어 공학 (수정됨)"

def test_delete_course(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.delete(f"/api/v1/courses/{course_id}", headers=auth_headers)
    assert response.status_code == 204
    
    response = client.get(f"/api/v1/courses/{course_id}", headers=auth_headers)
    assert response.status_code == 404

def test_courses_require_auth(client):
    response = client.get("/api/v1/courses/")
    assert response.status_code == 401
