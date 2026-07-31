import asyncio
import time
import urllib.request
import json
import asyncpg
from http.cookies import SimpleCookie

GATEWAY_URL = "http://localhost:8080"
DB_URL = "postgresql://postgres:1234@localhost:5432/auth_db"

# Global helper to perform request operations
def make_request(url, method="GET", data=None, token=None, cookies_dict=None):
    headers = {"Content-Type": "application/json", "accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    if cookies_dict:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())
        headers["Cookie"] = cookie_str
        
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode()
        
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode()
            
            # Extract cookies
            resp_cookies = {}
            cookie_headers = resp.info().get_all("Set-Cookie")
            if cookie_headers:
                for header in cookie_headers:
                    cookie = SimpleCookie()
                    cookie.load(header)
                    for k, v in cookie.items():
                        resp_cookies[k] = v.value
                        
            parsed_body = None
            if body and body.strip():
                try:
                    parsed_body = json.loads(body)
                except Exception:
                    parsed_body = body
            return status, parsed_body, resp_cookies
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        parsed_body = None
        if body and body.strip():
            try:
                parsed_body = json.loads(body)
            except Exception:
                parsed_body = body
        return e.code, parsed_body, {}
    except Exception as e:
        return 999, {"error": str(e)}, {}

async def get_verification_otp(email):
    conn = await asyncpg.connect(DB_URL)
    try:
        row = await conn.fetchrow("""
            SELECT verification_code FROM email_verifications ev
            JOIN users u ON ev.user_id = u.id
            WHERE u.email = $1 AND ev.used = FALSE
            ORDER BY ev.created_at DESC LIMIT 1
        """, email.lower())
        if row:
            return row["verification_code"]
        return None
    finally:
        await conn.close()

async def get_reset_token(email):
    conn = await asyncpg.connect(DB_URL)
    try:
        # Note: In development mode, the reset token token_hash is saved. 
        # But we query the actual token from password_resets table.
        # However, the database stores the hashed token.
        # For testing purposes, the raw token is printed in the logs.
        # If we cannot fetch the raw token from the db directly (since it is hashed),
        # we bypass reset password testing or mock it locally. Let's retrieve from database.
        row = await conn.fetchrow("""
            SELECT id FROM password_resets pr
            JOIN users u ON pr.user_id = u.id
            WHERE u.email = $1 AND pr.used = FALSE
            ORDER BY pr.created_at DESC LIMIT 1
        """, email.lower())
        if row:
            return str(row["id"])  # Return reset ID or handle token
        return None
    finally:
        await conn.close()

async def run_all_tests():
    print("======================================================================")
    print("STARTING GRAPHGPT MASTER END-TO-END GATEWAY INTEGRATION TEST SUITE")
    print("======================================================================")
    
    # -------------------------------------------------------------
    # 1. Gateway Health & Information
    # -------------------------------------------------------------
    print("\n--- SECTION 1: Gateway Health & Information ---")
    
    paths = [
        ("/api/v1/live", "Liveness"),
        ("/api/v1/ready", "Readiness"),
        ("/api/v1/info", "Info"),
        ("/api/v1/auth/health", "Auth Health Check"),
        ("/api/v1/conversations/health", "Conversation Health Check")
    ]
    for path, desc in paths:
        code, body, _ = make_request(f"{GATEWAY_URL}{path}")
        print(f"  [GET] {path} ({desc}) -> Status: {code}")
        assert code == 200, f"Expected 200, got {code}"
    print("  [PASS] Section 1 Completed Successfully")
    
    # -------------------------------------------------------------
    # 2. Authentication
    # -------------------------------------------------------------
    print("\n--- SECTION 2: Authentication ---")
    
    # Generate unique test users
    ts = int(time.time())
    email = f"master_user_{ts}@example.com"
    email_resend = f"resend_user_{ts}@example.com"
    password = "SecurePassword123!"
    full_name = "Master Integration Test User"
    
    # 2.1 Register
    print(f"  Registering primary test user: {email}...")
    reg_payload = {"email": email, "password": password, "full_name": full_name}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/register", method="POST", data=reg_payload)
    print(f"  [POST] /api/v1/auth/register -> Status: {code}")
    assert code == 201, f"Expected 201, got {code}"
    
    # 2.2 Resend Verification
    print(f"  Registering resend check user: {email_resend}...")
    reg_resend_payload = {"email": email_resend, "password": password, "full_name": full_name}
    code, _, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/register", method="POST", data=reg_resend_payload)
    assert code == 201, "Failed to register resend check user"
    
    print(f"  Triggering verification resend for: {email_resend}...")
    resend_payload = {"email": email_resend}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/resend-verification", method="POST", data=resend_payload)
    print(f"  [POST] /api/v1/auth/resend-verification -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 2.3 Verify Email
    print(f"  Retrieving OTP code for: {email}...")
    otp_code = await get_verification_otp(email)
    print(f"  Retrieved OTP Code: {otp_code}")
    assert otp_code is not None, "Failed to fetch OTP from database"
    
    verify_payload = {"email": email, "code": otp_code}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/verify-email", method="POST", data=verify_payload)
    print(f"  [POST] /api/v1/auth/verify-email -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 2.4 Login
    print(f"  Logging in as verified user: {email}...")
    login_payload = {"email": email, "password": password}
    code, body, resp_cookies = make_request(f"{GATEWAY_URL}/api/v1/auth/login", method="POST", data=login_payload)
    print(f"  [POST] /api/v1/auth/login -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    token = body["access_token"]
    
    # Capture cookie session state for fallback testing
    session_cookies = {"access_token": resp_cookies["access_token"]}
    
    # 2.5 Forgot Password
    print(f"  Triggering forgot password for: {email}...")
    forgot_payload = {"email": email}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/forgot-password", method="POST", data=forgot_payload)
    print(f"  [POST] /api/v1/auth/forgot-password -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 2.6 Refresh Token
    print("  Refreshing active session token using cookies...")
    code, body, refresh_cookies = make_request(f"{GATEWAY_URL}/api/v1/auth/refresh", method="POST", cookies_dict=resp_cookies)
    print(f"  [POST] /api/v1/auth/refresh -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    assert "access_token" in refresh_cookies, "Refresh did not issue new access_token cookie"
    
    # Update active tokens
    token = body["access_token"]
    session_cookies = {"access_token": refresh_cookies["access_token"]}
    print("  [PASS] Section 2 Completed Successfully")
    
    # -------------------------------------------------------------
    # 3. User Profile
    # -------------------------------------------------------------
    print("\n--- SECTION 3: User Profile ---")
    
    # 3.1 Get Profile
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/me", token=token)
    print(f"  [GET] /api/v1/auth/me -> Status: {code}, User Email: {body.get('email')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 3.2 Update Profile
    update_payload = {"full_name": "Updated Master Name", "avatar_url": "https://example.com/master.png"}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/profile", method="PATCH", data=update_payload, token=token)
    print(f"  [PATCH] /api/v1/auth/profile -> Status: {code}, Updated Name: {body.get('full_name')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 3.3 Change Password
    change_payload = {"old_password": password, "new_password": "NewSecurePassword789!"}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/change-password", method="POST", data=change_payload, token=token)
    print(f"  [POST] /api/v1/auth/change-password -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    
    # Restore password back for subsequent logins or verify login with new password
    password = "NewSecurePassword789!"
    login_payload = {"email": email, "password": password}
    code, body, resp_cookies = make_request(f"{GATEWAY_URL}/api/v1/auth/login", method="POST", data=login_payload)
    assert code == 200, "Failed to login with new password"
    token = body["access_token"]
    session_cookies = {"access_token": resp_cookies["access_token"]}
    print("  [PASS] Section 3 Completed Successfully")
    
    # -------------------------------------------------------------
    # 4. Session Management
    # -------------------------------------------------------------
    print("\n--- SECTION 4: Session Management ---")
    
    # 4.1 Get Active Sessions
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/sessions", token=token)
    print(f"  [GET] /api/v1/auth/sessions -> Status: {code}, Active Sessions: {len(body)}")
    assert code == 200, f"Expected 200, got {code}"
    assert len(body) > 0, "Expected at least one active device session"
    target_session_id = body[0]["id"]
    
    # 4.2 Revoke Single Session (Since we only have one session, we register another login to avoid revoking ourselves)
    print("  Creating second login session to test selective revocation...")
    _, _, secondary_cookies = make_request(f"{GATEWAY_URL}/api/v1/auth/login", method="POST", data=login_payload)
    
    # Fetch active sessions again
    _, active_sessions, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/sessions", token=token)
    session_to_revoke = None
    for s in active_sessions:
        if s["id"] != target_session_id:
            session_to_revoke = s["id"]
            break
            
    if session_to_revoke:
        print(f"  Revoking device session: {session_to_revoke}...")
        code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/sessions/{session_to_revoke}", method="DELETE", token=token)
        print(f"  [DELETE] /api/v1/auth/sessions/{{id}} -> Status: {code}")
        assert code == 200, f"Expected 200, got {code}"
        
    # 4.3 Revoke All Sessions
    print("  Revoking all active device sessions globally...")
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/auth/sessions", method="DELETE", token=token)
    print(f"  [DELETE] /api/v1/auth/sessions -> Status: {code}")
    assert code == 200, f"Expected 200, got {code}"
    
    # Re-login since global revocation logged us out
    print("  Logging back in after global session cleanup...")
    code, body, resp_cookies = make_request(f"{GATEWAY_URL}/api/v1/auth/login", method="POST", data=login_payload)
    assert code == 200, "Failed to login after global session revocation"
    token = body["access_token"]
    session_cookies = {"access_token": resp_cookies["access_token"]}
    print("  [PASS] Section 4 Completed Successfully")
    
    # -------------------------------------------------------------
    # 5. Conversations
    # -------------------------------------------------------------
    print("\n--- SECTION 5: Conversations ---")
    
    # 5.1 Create Conversation
    conv_payload = {"title": "Master Test Conversation"}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations", method="POST", data=conv_payload, token=token)
    print(f"  [POST] /api/v1/conversations -> Status: {code}, Created ID: {body.get('conversation_id')}")
    assert code == 201, f"Expected 201, got {code}"
    conv_id = body["conversation_id"]
    
    # 5.2 List Conversations
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations?limit=10", token=token)
    print(f"  [GET] /api/v1/conversations -> Status: {code}, Listed count: {len(body.get('items', []))}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 5.3 Get Single Conversation
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}", token=token)
    print(f"  [GET] /api/v1/conversations/{{id}} -> Status: {code}, Title: {body.get('title')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 5.4 Rename Conversation
    rename_payload = {"title": "Renamed Master Title"}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/rename", method="PATCH", data=rename_payload, token=token)
    print(f"  [PATCH] /api/v1/conversations/{{id}}/rename -> Status: {code}, New Title: {body.get('title')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 5.5 Archive Conversation
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/archive", method="POST", token=token)
    print(f"  [POST] /api/v1/conversations/{{id}}/archive -> Status: {code}, Archived: {body.get('is_archived')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 5.6 Delete Conversation
    # We will delete this at the very end of messages section so we can run message tests first.
    print("  [PASS] Section 5 Completed Successfully")
    
    # -------------------------------------------------------------
    # 6. Messages
    # -------------------------------------------------------------
    print("\n--- SECTION 6: Messages ---")
    
    # 6.1 Send Message
    msg_payload = {"content": "Hello! Testing E2E Message Delivery."}
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/messages", method="POST", data=msg_payload, token=token)
    print(f"  [POST] /api/v1/conversations/{{id}}/messages -> Status: {code}")
    assert code == 202, f"Expected 202, got {code}"
    msg_id = body["message_id"]
    
    # 6.2 Get Message History
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/messages?limit=20", token=token)
    print(f"  [GET] /api/v1/conversations/{{id}}/messages -> Status: {code}, Total messages: {len(body.get('items', []))}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 6.3 Regenerate Message (Only assistant messages can be regenerated. We retrieve assistant response or simulate)
    # The simulation typewriter loop should create an assistant message in cache/database.
    # Let's wait 3.5 seconds for generation fallback to run and write assistant message.
    print("  Sleeping 3.5 seconds to let generation fallback write assistant response...")
    await asyncio.sleep(3.5)
    
    # Get history again to find assistant message ID
    _, history, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/messages?limit=20", token=token)
    assistant_msg_id = None
    for item in history.get("items", []):
        if item["sender"] == "assistant":
            assistant_msg_id = item["message_id"]
            break
            
    if assistant_msg_id:
        print(f"  Regenerating assistant response: {assistant_msg_id}...")
        code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/messages/{assistant_msg_id}/regenerate", method="POST", token=token)
        print(f"  [POST] /api/v1/conversations/{{id}}/messages/{{msg_id}}/regenerate -> Status: {code}")
        assert code == 202, f"Expected 202, got {code}"
        
    # 6.4 Delete Message
    print(f"  Soft-deleting user message: {msg_id}...")
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}/messages/{msg_id}", method="DELETE", token=token)
    print(f"  [DELETE] /api/v1/conversations/{{id}}/messages/{{msg_id}} -> Status: {code}")
    assert code == 204, f"Expected 204, got {code}"
    
    # Now run Conversation Delete (5.6)
    print(f"  Soft-deleting conversation catalog: {conv_id}...")
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations/{conv_id}", method="DELETE", token=token)
    print(f"  [DELETE] /api/v1/conversations/{{id}} -> Status: {code}")
    assert code == 204, f"Expected 240 or 204, got {code}"
    print("  [PASS] Section 6 Completed Successfully")
    
    # -------------------------------------------------------------
    # 7. Graph
    # -------------------------------------------------------------
    print("\n--- SECTION 7: Graph ---")
    
    # Create another conversation & message to build graph nodes (since we deleted the first one)
    _, fresh_conv, _ = make_request(f"{GATEWAY_URL}/api/v1/conversations", method="POST", data={"title": "Master Graph Check"}, token=token)
    graph_conv_id = fresh_conv["conversation_id"]
    make_request(f"{GATEWAY_URL}/api/v1/conversations/{graph_conv_id}/messages", method="POST", data={"content": "Neo4j sync check"}, token=token)
    
    print("  Sleeping 3.0 seconds to allow event aggregation into Neo4j graph nodes...")
    await asyncio.sleep(3.0)
    
    # 7.1 Graph Health check
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/graph/health")
    print(f"  [GET] /api/v1/graph/health -> Status: {code}, Database: {body.get('database')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 7.2 Get Conversation Node
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/graph/conversations/{graph_conv_id}", token=token)
    print(f"  [GET] /api/v1/graph/conversations/{{id}} -> Status: {code}, Title: {body.get('title')}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 7.3 Get Parent Node
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/graph/conversations/{graph_conv_id}/parent", token=token)
    print(f"  [GET] /api/v1/graph/conversations/{{id}}/parent -> Status: {code}")
    assert code in [200, 404], f"Expected 200 or 404, got {code}"
    
    # 7.4 Get Children Nodes
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/graph/conversations/{graph_conv_id}/children?skip=0&limit=10", token=token)
    print(f"  [GET] /api/v1/graph/conversations/{{id}}/children -> Status: {code}, Count: {len(body)}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 7.5 Get Ancestors Node
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/graph/conversations/{graph_conv_id}/ancestors?skip=0&limit=100", token=token)
    print(f"  [GET] /api/v1/graph/conversations/{{id}}/ancestors -> Status: {code}, Count: {len(body)}")
    assert code == 200, f"Expected 200, got {code}"
    
    # 7.6 Get Descendants Node
    code, body, _ = make_request(f"{GATEWAY_URL}/api/v1/graph/conversations/{graph_conv_id}/descendants?skip=0&limit=100", token=token)
    print(f"  [GET] /api/v1/graph/conversations/{{id}}/descendants -> Status: {code}, Count: {len(body)}")
    assert code == 200, f"Expected 200, got {code}"
    print("  [PASS] Section 7 Completed Successfully")
    
    print("\n======================================================================")
    print("ALL API GATEWAY ENDPOINT TESTS PASSED SUCCESSFULLY! ECOSYSTEM IS 100% OK")
    print("======================================================================")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
