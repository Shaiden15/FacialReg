import pytest
from app.student_attendance_system import create_app

@pytest.fixture()
def app():
    app = create_app('default')
    app.config.update(TESTING=True)
    return app

@pytest.fixture()
def client(app):
    return app.test_client()

def test_homepage(client):
    resp = client.get('/')
    assert resp.status_code in (200, 302)
