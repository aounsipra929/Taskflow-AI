from tests.conftest import register_and_login

API = "/api/v1"


def test_register_login_and_me(client):
    h = register_and_login(client)
    me = client.get(f"{API}/auth/me", headers=h).json()
    assert me["email"] == "user@example.com" and me["role"] == "user"


def test_duplicate_email_and_weak_password(client, user_headers):
    dup = client.post(f"{API}/auth/register", json={"email": "user@example.com", "full_name": "X Y", "password": "Passw0rdX"})
    assert dup.status_code == 409
    weak = client.post(f"{API}/auth/register", json={"email": "a@b.com", "full_name": "X Y", "password": "onlyletters"})
    assert weak.status_code == 422


def test_wrong_password_rejected(client, user_headers):
    r = client.post(f"{API}/auth/login", data={"username": "user@example.com", "password": "nope12345"})
    assert r.status_code == 401


def test_task_crud_and_status(client, user_headers):
    r = client.post(f"{API}/tasks", json={"title": "Write tests", "priority": "high"}, headers=user_headers)
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.put(f"{API}/tasks/{tid}", json={"title": "Write more tests"}, headers=user_headers).json()["title"] == "Write more tests"
    assert client.patch(f"{API}/tasks/{tid}/status", json={"status": "completed"}, headers=user_headers).json()["status"] == "completed"
    assert client.delete(f"{API}/tasks/{tid}", headers=user_headers).status_code == 204
    assert client.get(f"{API}/tasks/{tid}", headers=user_headers).status_code == 404


def test_search_filter_sort_pagination(client, user_headers):
    for title, prio in [("Alpha", "low"), ("Beta", "high"), ("Gamma", "medium")]:
        client.post(f"{API}/tasks", json={"title": title, "priority": prio}, headers=user_headers)
    by_prio = client.get(f"{API}/tasks?sort_by=priority&order=desc", headers=user_headers).json()
    assert [t["title"] for t in by_prio["items"]] == ["Beta", "Gamma", "Alpha"]
    assert client.get(f"{API}/tasks?q=alp", headers=user_headers).json()["total"] == 1
    assert client.get(f"{API}/tasks?priority=high", headers=user_headers).json()["total"] == 1
    page = client.get(f"{API}/tasks?page=2&page_size=2", headers=user_headers).json()
    assert len(page["items"]) == 1 and page["pages"] == 2


def test_users_are_isolated(client, user_headers):
    tid = client.post(f"{API}/tasks", json={"title": "Private"}, headers=user_headers).json()["id"]
    other = register_and_login(client, "other@example.com")
    assert client.get(f"{API}/tasks/{tid}", headers=other).status_code == 404
    assert client.get(f"{API}/tasks", headers=other).json()["total"] == 0


def test_admin_endpoints(client, user_headers, admin_headers):
    client.post(f"{API}/tasks", json={"title": "T1"}, headers=user_headers)
    assert client.get(f"{API}/admin/stats", headers=user_headers).status_code == 403  # normal user blocked
    stats = client.get(f"{API}/admin/stats", headers=admin_headers).json()
    assert stats["total_users"] == 2 and stats["total_tasks"] == 1 and stats["pending_tasks"] == 1
    tasks = client.get(f"{API}/admin/tasks", headers=admin_headers).json()
    assert tasks["total"] == 1 and tasks["items"][0]["owner"]["email"] == "user@example.com"


def test_admin_can_deactivate_user(client, user_headers, admin_headers):
    users = client.get(f"{API}/admin/users", headers=admin_headers).json()["items"]
    uid = next(u["id"] for u in users if u["role"] == "user")
    assert client.patch(f"{API}/admin/users/{uid}/status", json={"is_active": False}, headers=admin_headers).status_code == 200
    assert client.get(f"{API}/auth/me", headers=user_headers).status_code == 403
    login = client.post(f"{API}/auth/login", data={"username": "user@example.com", "password": "Passw0rdX"})
    assert login.status_code == 403
