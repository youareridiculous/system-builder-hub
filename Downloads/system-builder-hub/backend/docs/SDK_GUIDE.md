# SBH SDK Guide

The SBH SDK provides libraries and utilities for integrating with SBH scaffolds, including authentication, RBAC, API clients, and analytics.

## Python SDK

### Installation

```bash
pip install sbh-sdk
```

### Basic Usage

```python
from sbh.sdk import auth, db, files, analytics, api

# Initialize with configuration
auth.api_url = "http://localhost:5001"
db.db_url = "postgresql://user:pass@localhost/sbh"
```

### Authentication

```python
from sbh.sdk import auth, SBHUser

# Set current user
user = SBHUser(
    id="user-123",
    email="user@example.com",
    name="John Doe",
    role="admin",
    tenant_id="tenant-456",
    permissions=["contacts.read", "contacts.write"]
)
auth.set_user(user)

# Get current user
current_user = auth.get_current_user()
tenant_id = auth.get_current_tenant()
```

### RBAC Decorators

```python
from sbh.sdk import require_auth, require_role, require_permission

@require_auth
@require_role(["admin", "member"])
def get_contacts():
    """Get contacts for current tenant."""
    tenant_id = auth.get_current_tenant()
    return db.list("contacts", tenant_id)

@require_auth
@require_permission("contacts.create")
def create_contact(contact_data):
    """Create a new contact."""
    tenant_id = auth.get_current_tenant()
    contact_id = db.create("contacts", contact_data, tenant_id)
    
    # Track the event
    analytics.track("contact.created", {
        "contact_id": contact_id,
        "tenant_id": tenant_id
    }, auth.get_current_user().id)
    
    return contact_id
```

### Database Operations

```python
from sbh.sdk import db

# Query with tenant isolation
contacts = db.query(
    "SELECT * FROM contacts WHERE status = :status",
    {"status": "active", "tid": auth.get_current_tenant()}
)

# List records
contacts = db.list("contacts", auth.get_current_tenant(), {
    "status": "active",
    "type": "customer"
})

# Get by ID
contact = db.get_by_id("contacts", "contact-123", auth.get_current_tenant())

# Create record
contact_id = db.create("contacts", {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
}, auth.get_current_tenant())

# Update record
success = db.update("contacts", "contact-123", {
    "email": "john.doe@example.com"
}, auth.get_current_tenant())

# Delete record
success = db.delete("contacts", "contact-123", auth.get_current_tenant())
```

### File Operations

```python
from sbh.sdk import files

# Upload file
file_url = files.upload(
    "/path/to/file.pdf",
    auth.get_current_tenant(),
    "documents"
)

# Download file
content = files.download(file_url)

# Delete file
success = files.delete(file_url)
```

### Analytics

```python
from sbh.sdk import analytics

# Track event
analytics.track("user.login", {
    "method": "email",
    "tenant_id": auth.get_current_tenant()
}, auth.get_current_user().id)

# Identify user
analytics.identify(auth.get_current_user().id, {
    "name": auth.get_current_user().name,
    "role": auth.get_current_user().role,
    "tenant_id": auth.get_current_tenant()
})
```

### API Client

```python
from sbh.sdk import api

# Initialize with auth token
api_client = api.SBHAPI(
    api_url="http://localhost:5001",
    auth_token="your-token"
)

# Make requests
templates = api_client.get("/api/marketplace/templates")
profile = api_client.get("/api/auth/profile")

# Create resource
new_contact = api_client.post("/api/contacts", {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com"
})
```

## TypeScript/JavaScript SDK

### Installation

```bash
npm install sbh-sdk
```

### Basic Setup

```typescript
import { SBHProvider, useSBH } from 'sbh-sdk';

// Wrap your app with SBHProvider
function App() {
  return (
    <SBHProvider config={{
      apiUrl: 'http://localhost:5001',
      authToken: 'your-token'
    }}>
      <YourApp />
    </SBHProvider>
  );
}
```

### Authentication

```typescript
import { useSBHAuth } from 'sbh-sdk';

function LoginForm() {
  const { login, logout, user, isAuthenticated, isLoading } = useSBHAuth();

  const handleLogin = async (credentials: { email: string; password: string }) => {
    try {
      await login(credentials);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  if (isLoading) return <div>Loading...</div>;
  if (isAuthenticated) return <div>Welcome, {user?.name}!</div>;

  return (
    <form onSubmit={handleLogin}>
      {/* Login form */}
    </form>
  );
}
```

### RBAC Hooks

```typescript
import { useRequireAuth, useRequireRole, useRequirePermission } from 'sbh-sdk';

function ProtectedComponent() {
  // Require authentication
  useRequireAuth();

  return <div>Protected content</div>;
}

function AdminComponent() {
  // Require admin role
  useRequireRole(['admin', 'owner']);

  return <div>Admin only content</div>;
}

function ContactManager() {
  // Require specific permission
  useRequirePermission('contacts.manage');

  return <div>Contact management</div>;
}
```

### API Hooks

```typescript
import { useApi, useApiMutation, useSBHAnalytics } from 'sbh-sdk';

function ContactsList() {
  const { data, loading, error } = useApi<any[]>('/api/contacts');
  const { track } = useSBHAnalytics();

  useEffect(() => {
    track('contacts.list.viewed');
  }, []);

  if (loading) return <div>Loading contacts...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {data?.map(contact => (
        <li key={contact.id}>
          {contact.first_name} {contact.last_name}
        </li>
      ))}
    </ul>
  );
}

function CreateContactForm() {
  const { mutate, loading } = useApiMutation('/api/contacts');
  const { track } = useSBHAnalytics();

  const handleSubmit = async (formData: any) => {
    const result = await mutate(formData);
    if (result) {
      track('contact.created', { contactId: result.id });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Contact'}
      </button>
    </form>
  );
}
```

### Direct API Client

```typescript
import { useSBHApi } from 'sbh-sdk';

function CustomComponent() {
  const api = useSBHApi();

  const fetchData = async () => {
    try {
      const response = await api.get('/api/custom-endpoint');
      console.log(response.data);
    } catch (error) {
      console.error('API error:', error);
    }
  };

  return <button onClick={fetchData}>Fetch Data</button>;
}
```

## Integration Examples

### Flask Application

```python
from flask import Flask, jsonify, request
from sbh.sdk import auth, db, analytics, require_auth, require_role

app = Flask(__name__)

@app.route('/api/contacts', methods=['GET'])
@require_auth
@require_role(['admin', 'member'])
def get_contacts():
    tenant_id = auth.get_current_tenant()
    contacts = db.list("contacts", tenant_id)
    
    analytics.track("contacts.list.viewed", {
        "tenant_id": tenant_id,
        "count": len(contacts)
    })
    
    return jsonify(contacts)

@app.route('/api/contacts', methods=['POST'])
@require_auth
@require_permission("contacts.create")
def create_contact():
    tenant_id = auth.get_current_tenant()
    contact_data = request.json
    
    contact_id = db.create("contacts", contact_data, tenant_id)
    
    analytics.track("contact.created", {
        "contact_id": contact_id,
        "tenant_id": tenant_id
    })
    
    return jsonify({"id": contact_id}), 201
```

### React Application

```typescript
import React from 'react';
import { SBHProvider, useSBH, useApi, useRequireAuth } from 'sbh-sdk';

function App() {
  return (
    <SBHProvider config={{
      apiUrl: process.env.REACT_APP_SBH_API_URL,
      authToken: localStorage.getItem('sbh_token')
    }}>
      <ContactsApp />
    </SBHProvider>
  );
}

function ContactsApp() {
  useRequireAuth();
  
  return (
    <div>
      <h1>Contacts</h1>
      <ContactsList />
      <CreateContactForm />
    </div>
  );
}

function ContactsList() {
  const { data, loading } = useApi('/api/contacts');
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <ul>
      {data?.map(contact => (
        <li key={contact.id}>{contact.name}</li>
      ))}
    </ul>
  );
}
```

## Configuration

### Environment Variables

```bash
# Python
export SBH_API_URL="http://localhost:5001"
export SBH_DB_URL="postgresql://user:pass@localhost/sbh"
export SBH_AUTH_TOKEN="your-token"

# JavaScript/TypeScript
export REACT_APP_SBH_API_URL="http://localhost:5001"
export REACT_APP_SBH_AUTH_TOKEN="your-token"
```

### Configuration Files

```python
# config.py
SBH_CONFIG = {
    'api_url': 'http://localhost:5001',
    'db_url': 'postgresql://user:pass@localhost/sbh',
    'auth_token': 'your-token',
    'tenant_id': 'your-tenant-id'
}
```

```typescript
// config.ts
export const SBH_CONFIG = {
  apiUrl: process.env.REACT_APP_SBH_API_URL || 'http://localhost:5001',
  authToken: process.env.REACT_APP_SBH_AUTH_TOKEN,
  tenantId: process.env.REACT_APP_SBH_TENANT_ID
};
```

## Best Practices

### Security

1. Always use RBAC decorators for protected endpoints
2. Validate user permissions before operations
3. Use tenant isolation for all database queries
4. Track security events with analytics

### Performance

1. Use connection pooling for database operations
2. Implement caching for frequently accessed data
3. Batch analytics events when possible
4. Use pagination for large datasets

### Error Handling

```python
from sbh.sdk import auth, require_auth

@require_auth
def safe_operation():
    try:
        tenant_id = auth.get_current_tenant()
        if not tenant_id:
            raise ValueError("No tenant context")
        
        # Perform operation
        return result
    except Exception as e:
        analytics.track("operation.failed", {
            "error": str(e),
            "tenant_id": tenant_id
        })
        raise
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check API token is valid
   - Verify API URL is correct
   - Ensure user has proper permissions

2. **Database Errors**
   - Check database connection
   - Verify tenant isolation is working
   - Check table permissions

3. **Analytics Errors**
   - Check network connectivity
   - Verify analytics endpoint
   - Check event format

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

```typescript
// Enable debug logging
localStorage.setItem('sbh_debug', 'true');
```

## Support

For issues and questions:

- Check the troubleshooting section
- Review SDK documentation
- Contact support at support@sbh.com
- Join the community at community.sbh.com
