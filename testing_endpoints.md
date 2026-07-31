# API Gateway — Endpoint Testing Reference

All endpoints route through the Gateway at **`http://localhost:8080`**.
Swagger UI URL: **`http://localhost:8080/docs`**

---

## 1. Gateway Health & Information (Public)

```bash
# Liveness Check
GET /api/v1/live

# Readiness Check
GET /api/v1/ready

# Services Status Info
GET /api/v1/info

# Sub-service Health Checks
GET /api/v1/auth/health
GET /api/v1/conversations/health
```

---

## 2. Authentication (Public)

### 2.1 Register
```bash
POST /api/v1/auth/register
```
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "Test User"
}
```

### 2.2 Verify Email (OTP)
```bash
POST /api/v1/auth/verify-email
```
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

### 2.3 Resend Verification OTP
```bash
POST /api/v1/auth/resend-verification
```
```json
{
  "email": "user@example.com"
}
```

### 2.4 Login
```bash
POST /api/v1/auth/login
```
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

### 2.5 Refresh Token
```bash
POST /api/v1/auth/refresh
```
*(Requires HttpOnly refresh_token cookie set during login)*

### 2.6 Logout
```bash
POST /api/v1/auth/logout
```

### 2.7 Forgot Password
```bash
POST /api/v1/auth/forgot-password
```
```json
{
  "email": "user@example.com"
}
```

### 2.8 Reset Password
```bash
POST /api/v1/auth/reset-password
```
```json
{
  "token": "reset-uuid-token",
  "new_password": "NewSecurePassword123!"
}
```

---

## 3. User Profile (Protected)

### 3.1 Get Profile
```bash
GET /api/v1/auth/me
```

### 3.2 Update Profile
```bash
PATCH /api/v1/auth/profile
```
```json
{
  "full_name": "Updated User Name",
  "avatar_url": "https://example.com/avatar.png"
}
```

### 3.3 Change Password
```bash
POST /api/v1/auth/change-password
```
```json
{
  "old_password": "SecurePassword123!",
  "new_password": "NewSecurePassword123!"
}
```

---

## 4. Session Management (Protected)

### 4.1 Get Active Sessions
```bash
GET /api/v1/auth/sessions
```

### 4.2 Revoke Specific Session
```bash
DELETE /api/v1/auth/sessions/{session_id}
```

### 4.3 Revoke All Sessions
```bash
DELETE /api/v1/auth/sessions
```

---

## 5. Conversations (Protected)

### 5.1 Create Conversation
```bash
POST /api/v1/conversations
```
```json
{
  "title": "New Conversation",
  "parent_conversation_id": null
}
```

### 5.2 List My Conversations
```bash
GET /api/v1/conversations?limit=10
```

### 5.3 Get Single Conversation
```bash
GET /api/v1/conversations/{conversation_id}
```

### 5.4 Rename Conversation
```bash
PATCH /api/v1/conversations/{conversation_id}/rename
```
```json
{
  "title": "Renamed Title"
}
```

### 5.5 Archive Conversation
```bash
POST /api/v1/conversations/{conversation_id}/archive
```

### 5.6 Delete Conversation
```bash
DELETE /api/v1/conversations/{conversation_id}
```

---

## 6. Messages (Protected)

### 6.1 Send Message
```bash
POST /api/v1/conversations/{conversation_id}/messages
```
```json
{
  "content": "Explain supervised learning."
}
```

### 6.2 Get Message History
```bash
GET /api/v1/conversations/{conversation_id}/messages?limit=20
```

### 6.3 Regenerate Message
```bash
POST /api/v1/conversations/{conversation_id}/messages/{message_id}/regenerate
```

### 6.4 Delete Message
```bash
DELETE /api/v1/conversations/{conversation_id}/messages/{message_id}
```

---

## 7. Graph Lineage (Protected)

### 7.1 Graph Health Check
```bash
GET /api/v1/graph/health
```

### 7.2 Get Conversation Node
```bash
GET /api/v1/graph/conversations/{conversation_id}
```

### 7.3 Get Parent Node
```bash
GET /api/v1/graph/conversations/{conversation_id}/parent
```

### 7.4 Get Children Nodes
```bash
GET /api/v1/graph/conversations/{conversation_id}/children?skip=0&limit=100
```

### 7.5 Get Ancestors (Full Lineage)
```bash
GET /api/v1/graph/conversations/{conversation_id}/ancestors?skip=0&limit=100
```

### 7.6 Get Descendants
```bash
GET /api/v1/graph/conversations/{conversation_id}/descendants?skip=0&limit=100
```
