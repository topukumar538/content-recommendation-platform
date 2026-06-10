import pytest
from unittest.mock import patch
from database import get_db
from models import User, Category, Feed, UserInteraction

# mock email globally
@pytest.fixture(autouse=True)
def mock_email():
    with patch("services.otp_service.send_otp_email"):
        yield

def create_user_and_login(client, email="user@test.com", password="123456"):
    client.post("/auth/signup", json={
        "username": "testuser",
        "email": email,
        "password": password
    })
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == email).first()
    user.is_active = True
    db.commit()
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.cookies, user.id

def create_admin_and_login(client, email="admin@test.com", password="123456"):
    client.post("/auth/signup", json={
        "username": "admin",
        "email": email,
        "password": password
    })
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == email).first()
    user.is_active = True
    user.role = "admin"
    db.commit()
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.cookies

def test_update_profile(client):
    cookies, user_id = create_user_and_login(client)
    
    # Update profile username
    res = client.patch("/user/profile", json={"username": "newusername"}, cookies=cookies)
    assert res.status_code == 200
    assert res.json()["message"] == "Profile updated successfully"
    
    # Verify username updated in database
    db = next(client.app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.id == user_id).first()
    assert user.username == "newusername"

def test_update_profile_empty_username(client):
    cookies, _ = create_user_and_login(client)
    
    res = client.patch("/user/profile", json={"username": "   "}, cookies=cookies)
    assert res.status_code == 400
    assert "Username cannot be empty" in res.json()["detail"]

def test_submit_feedback_success(client):
    cookies, user_id = create_user_and_login(client)
    
    # Submit feedback (tests our bugfix!)
    res = client.post("/user/feedback", json={
        "message": "This platform is awesome!",
        "rating": 5
    }, cookies=cookies)
    
    assert res.status_code == 200
    assert res.json()["message"] == "Feedback submitted successfully"

def test_submit_feedback_invalid_rating(client):
    cookies, _ = create_user_and_login(client)
    
    res = client.post("/user/feedback", json={
        "message": "Too high rating",
        "rating": 6
    }, cookies=cookies)
    assert res.status_code == 400
    assert "Rating must be between 1 and 5" in res.json()["detail"]

def test_saved_posts_flow(client):
    user_cookies, user_id = create_user_and_login(client, email="regular@test.com")
    admin_cookies = create_admin_and_login(client)
    
    # Admin creates category and post
    db = next(client.app.dependency_overrides[get_db]())
    category = Category(name="General")
    db.add(category)
    db.commit()
    
    res_post = client.post("/feed", json={
        "title": "A Saved Post",
        "content": "This post will be saved.",
        "category_id": category.id
    }, cookies=admin_cookies)
    assert res_post.status_code == 200
    feed_id = res_post.json()["id"]
    
    # User saves the post
    res_save = client.post(f"/feed/{feed_id}/save", cookies=user_cookies)
    assert res_save.status_code == 200
    assert res_save.json()["action"] == "added"
    
    # Get saved posts
    res_get_saved = client.get("/user/saved", cookies=user_cookies)
    assert res_get_saved.status_code == 200
    saved_posts = res_get_saved.json()
    assert len(saved_posts) == 1
    assert saved_posts[0]["id"] == feed_id
    assert saved_posts[0]["title"] == "A Saved Post"
    
    # Unsave the post
    res_unsave = client.delete(f"/user/saved/{feed_id}", cookies=user_cookies)
    assert res_unsave.status_code == 200
    assert res_unsave.json()["message"] == "Post unsaved"
    
    # Get saved posts again — should be empty
    res_get_saved_empty = client.get("/user/saved", cookies=user_cookies)
    assert res_get_saved_empty.status_code == 200
    assert len(res_get_saved_empty.json()) == 0
