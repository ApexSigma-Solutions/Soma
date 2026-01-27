# User Authentication System - Implementation Guide

## Overview

I've implemented a complete user authentication system for CortexBridge using **Alembic** for database migrations and proper password hashing with bcrypt.

## What Was Implemented

### 1. Database Schema (Alembic Migration)
- **Migration File**: `alembic/versions/b0956be3903b_create_users_table.py`
- **Table**: `users` with the following fields:
  - `id` (Primary Key)
  - `email` (Unique, Indexed)
  - `username` (Unique, Indexed)
  - `hashed_password` (bcrypt hashed)
  - `full_name` (Optional)
  - `role` (default: 'user', indexed)
  - `is_active` (default: true)
  - `is_verified` (default: false)
  - `created_at` (Timestamp with timezone)
  - `updated_at` (Timestamp with timezone)
  - `last_login` (Nullable timestamp)

### 2. Models & Schemas
- **`omega_kg/models/user.py`**: SQLAlchemy User model
- **`omega_kg/models/user_schemas.py`**: Pydantic schemas for:
  - User registration (`UserCreate`)
  - User login (`UserLogin`)
  - User response (`UserResponse`)
  - User updates (`UserUpdate`)
  - Password changes (`PasswordChange`)

### 3. Authentication Logic
- **`omega_kg/auth_utils.py`**: Added functions:
  - `verify_password()`: Verify plain password against hash
  - `get_password_hash()`: Hash passwords with bcrypt
  - `authenticate_user()`: Authenticate user by email/password
  - `get_current_user()`: Extract user from JWT token

### 4. API Endpoints
- **`omega_kg/routers/auth.py`**: New authentication router with:
  - `POST /auth/register`: Register new user
  - `POST /auth/login`: Login and receive JWT token
  - `GET /auth/me`: Get current user info
  - `PUT /auth/me`: Update user profile
  - `POST /auth/change-password`: Change password

### 5. Scripts
- **`scripts/database/create-admin-user.py`**: Interactive script to create admin users
- **`scripts/database/create-users-table.py`**: Legacy SQL migration (replaced by Alembic)

### 6. Server Configuration
- **`capture_server.py`**: 
  - Added auth router
  - Added CORS support for port 6001 (CortexBridge)

## How to Use

### Step 1: Run Migrations (Already Done)
```bash
cd Omega_KG_stable
poetry run python -m alembic upgrade head
```

### Step 2: Create Admin User
The interactive script is currently running. You'll need to provide:
- Admin email
- Admin username
- Full name (optional)
- Password (min 8 characters)

```bash
cd Omega_KG_stable
poetry run python scripts/database/create-admin-user.py
```

### Step 3: Login to CortexBridge
1. Navigate to `http://localhost:6001`
2. Enter your admin email and password
3. Click "Sign In"

## API Flow

### Registration Flow
```
POST /auth/register
{
  "email": "user@example.com",
  "username": "username",
  "password": "securepassword",
  "full_name": "Full Name"
}

Response: UserResponse (without password)
```

### Login Flow
```
POST /auth/login
{
  "email": "user@example.com",
  "password": "securepassword"
}

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Authenticated Requests
Include the JWT token in the Authorization header:
```
Authorization: Bearer eyJ...
```

## Frontend Integration

The CortexBridge login page (`LoginPage.tsx`) needs to be updated to use the new `/auth/login` endpoint instead of `/auth/token`. The current implementation:

1. Sends email + password to `/auth/token` with API key
2. **Should send** email + password to `/auth/login` 

### Required Frontend Changes
Update `LoginPage.tsx` to:
```typescript
const response = await axios.post<TokenResponse>(
    `${API_CONFIGS[0].baseUrl}/auth/login`,
    {
        email: email,
        password: password
    },
    {
        headers: {
            'Content-Type': 'application/json'
        }
    }
);
```

## Security Features

1. **Password Hashing**: bcrypt with automatic salt generation
2. **JWT Tokens**: Secure token-based authentication
3. **Rate Limiting**: Existing rate limiting on auth endpoints
4. **CORS**: Properly configured for CortexBridge frontend
5. **Input Validation**: Pydantic schema validation
6. **SQL Injection Protection**: SQLAlchemy ORM

## Database Management

### Using Alembic (Recommended)
```bash
# Create new migration
poetry run python -m alembic revision -m "description"

# Apply migrations
poetry run python -m alembic upgrade head

# Rollback one migration
poetry run python -m alembic downgrade -1

# View migration history
poetry run python -m alembic history
```

### Why Alembic?
- **Version Control**: Track database schema changes
- **Rollback Support**: Safely revert changes
- **Team Collaboration**: Share schema changes via git
- **Production Safety**: Test migrations before deployment
- **Auto-generation**: Can auto-generate migrations from models

## Next Steps

1. **Update Frontend**: Modify `LoginPage.tsx` to use `/auth/login`
2. **Test Login**: Verify authentication works end-to-end
3. **Add User Management**: Admin interface to manage users
4. **Email Verification**: Implement email verification flow
5. **Password Reset**: Add forgot password functionality
6. **Role-Based Access**: Implement permission system

## Files Created/Modified

### Created:
- `omega_kg/models/user.py`
- `omega_kg/models/user_schemas.py`
- `omega_kg/routers/auth.py`
- `alembic/versions/b0956be3903b_create_users_table.py`
- `scripts/database/create-admin-user.py`
- `scripts/database/create-users-table.py` (legacy)

### Modified:
- `omega_kg/auth_utils.py` (added user auth functions)
- `omega_kg/capture_server.py` (added auth router, CORS)

## Troubleshooting

### Migration Issues
If migrations fail, check:
1. Database connection (PostgreSQL running on port 6000)
2. Database credentials in `.env`
3. Alembic version table: `SELECT * FROM alembic_version;`

### Login Issues
If login fails:
1. Verify user exists: `SELECT * FROM users;`
2. Check password hash is valid
3. Verify JWT secret key in `.env`
4. Check CORS headers in browser console

### Frontend Issues
If frontend can't connect:
1. Verify backend is running on port 8765
2. Check CORS configuration includes port 6001
3. Verify API endpoint URLs in frontend code
