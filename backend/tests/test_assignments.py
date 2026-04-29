def test_create_assignment(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.post(f"/api/v1/courses/{course_id}/assignments", json={
        "title": "과제 1",
        "description": "첫 번째 과제",
        "due_date": "2024-12-31T23:59:59",
        "is_completed": False
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "과제 1"
    assert data["course_id"] == course_id

def test_list_assignments(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    client.post(f"/api/v1/courses/{course_id}/assignments", json={
        "title": "과제 1"
    }, headers=auth_headers)
    response = client.get(f"/api/v1/courses/{course_id}/assignments", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_update_assignment(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    create_resp = client.post(f"/api/v1/courses/{course_id}/assignments", json={
        "title": "과제 1"
    }, headers=auth_headers)
    assignment_id = create_resp.json()["id"]
    
    response = client.put(f"/api/v1/courses/{course_id}/assignments/{assignment_id}", json={
        "is_completed": True,
        "grade": 95.0
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_completed"] == True
    assert response.json()["grade"] == 95.0

def test_delete_assignment(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    create_resp = client.post(f"/api/v1/courses/{course_id}/assignments", json={
        "title": "과제 1"
    }, headers=auth_headers)
    assignment_id = create_resp.json()["id"]
    
    response = client.delete(f"/api/v1/courses/{course_id}/assignments/{assignment_id}", headers=auth_headers)
    assert response.status_code == 204

def test_assignment_not_found(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    response = client.get(f"/api/v1/courses/{course_id}/assignments/999", headers=auth_headers)
    assert response.status_code == 404

def test_stats_endpoint(client, auth_headers, sample_course):
    course_id = sample_course["id"]
    client.post(f"/api/v1/courses/{course_id}/assignments", json={
        "title": "과제 1",
        "is_completed": True
    }, headers=auth_headers)
    client.post(f"/api/v1/courses/{course_id}/assignments", json={
        "title": "과제 2",
        "due_date": "2099-12-31T23:59:59"
    }, headers=auth_headers)
    
    response = client.get("/api/v1/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 1
    assert data["total_assignments"] == 2
    assert data["completed_assignments"] == 1
    assert data["upcoming_assignments"] == 1
