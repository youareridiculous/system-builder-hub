# CRM Flagship - Quality Assurance Checklist

This document provides comprehensive testing guidelines for the CRM Flagship template. Test each role thoroughly to ensure all features work correctly.

## 🔐 Authentication & RBAC Testing

### Login Flow
- [ ] **All Roles**: Login with valid credentials
- [ ] **All Roles**: Login with invalid credentials (should fail)
- [ ] **All Roles**: Logout functionality
- [ ] **All Roles**: Session persistence across browser refresh
- [ ] **All Roles**: Redirect to login when accessing protected pages without auth

### Role-Based Access Control
- [ ] **Owner**: Access to all pages and features
- [ ] **Admin**: Access to settings, users, analytics (no owner-only features)
- [ ] **Manager**: Access to CRM features, no settings access
- [ ] **Sales**: Limited access to contacts, deals, communications
- [ ] **ReadOnly**: View-only access to permitted data

## 👥 Contact Management

### Contact CRUD Operations
- [ ] **Manager/Sales**: Create new contact
- [ ] **Manager/Sales**: Edit existing contact
- [ ] **Manager/Sales**: Delete contact (with confirmation)
- [ ] **Manager/Sales**: View contact details
- [ ] **Manager/Sales**: Search and filter contacts
- [ ] **ReadOnly**: View contacts (no edit/delete buttons)

### Contact Detail Workspace
- [ ] **All Roles**: View contact timeline
- [ ] **Manager/Sales**: Add notes to contact
- [ ] **Manager/Sales**: Edit notes
- [ ] **Manager/Sales**: Delete notes
- [ ] **Manager/Sales**: View associated deals
- [ ] **Manager/Sales**: View associated activities

## 💼 Deal Pipeline

### Kanban Board
- [ ] **Manager/Sales**: View deals in pipeline
- [ ] **Manager/Sales**: Drag and drop deals between stages
- [ ] **Manager/Sales**: Create new deal
- [ ] **Manager/Sales**: Edit deal details
- [ ] **Manager/Sales**: Delete deal (with confirmation)
- [ ] **ReadOnly**: View deals (no drag/drop or edit buttons)

### Deal Management
- [ ] **Manager/Sales**: Set deal amount
- [ ] **Manager/Sales**: Assign deal to contact
- [ ] **Manager/Sales**: Add deal notes
- [ ] **Manager/Sales**: Update deal stage manually

## 📧 Communications

### Email/SMS Sending
- [ ] **Manager/Sales**: Send email to contact
- [ ] **Manager/Sales**: Send SMS to contact
- [ ] **Manager/Sales**: View communication history
- [ ] **Manager/Sales**: Filter communications by type/status
- [ ] **ReadOnly**: View communications (no send buttons)

### Templates
- [ ] **Manager/Sales**: View email templates
- [ ] **Manager/Sales**: Preview template with contact data
- [ ] **Manager/Sales**: Send email using template
- [ ] **Manager/Sales**: Test template send (dry-run)

### Call Recordings
- [ ] **All Roles**: View call recording player in communications
- [ ] **All Roles**: Play/pause call recordings
- [ ] **All Roles**: Single-play guard (only one recording plays at a time)
- [ ] **All Roles**: Download call recordings (if permitted)

## 🤖 Automations

### Rule Builder
- [ ] **Manager**: View automation rules list
- [ ] **Manager**: Create new automation rule
- [ ] **Manager**: Edit existing automation rule
- [ ] **Manager**: Toggle automation on/off
- [ ] **Manager**: Duplicate automation rule
- [ ] **Manager**: Delete automation rule

### Rule Testing
- [ ] **Manager**: Dry-run test automation rule
- [ ] **Manager**: View automation runs history
- [ ] **Manager**: Test with different trigger conditions

## 📊 Analytics Dashboard

### Dashboard Access
- [ ] **Owner/Admin/Manager**: Access analytics dashboard
- [ ] **Sales/ReadOnly**: Limited or no analytics access

### Charts and KPIs
- [ ] **Authorized Roles**: View communication success rates
- [ ] **Authorized Roles**: View pipeline velocity metrics
- [ ] **Authorized Roles**: View activity heatmaps

## 🎯 First-Run Checklist Testing

### Checklist Display
- [ ] **Owner/Admin**: First-run checklist appears on Dashboard
- [ ] **Sales/ReadOnly**: No checklist access (settings.read required)
- [ ] **All Roles**: Checklist can be dismissed with X button
- [ ] **All Roles**: Checklist shows completion progress (X/Y items)

### Checklist Items
- [ ] **Owner/Admin**: "Set Branding" item auto-completes when branding is configured
- [ ] **Owner/Admin**: "Configure Providers" item auto-completes when real providers are set
- [ ] **Owner/Admin**: "Create First Contact" item auto-completes when contacts exist
- [ ] **Owner/Admin**: "Send First Communication" item auto-completes when communications exist
- [ ] **Owner/Admin**: "Set Up Automations" item auto-completes when automations exist
- [ ] **Owner/Admin**: Manual "Mark Complete" buttons work for each item

### Checklist Persistence
- [ ] **Owner/Admin**: Checklist completion status persists across sessions
- [ ] **Owner/Admin**: Dismissed checklist stays hidden until reset
- [ ] **Owner/Admin**: All items completed shows success message

## 🔄 Reset Demo Data Testing

### Reset Functionality
- [ ] **Owner/Admin**: Reset demo endpoint accessible at `/api/settings/admin/reset-demo`
- [ ] **Owner/Admin**: Reset clears all tenant data except users/roles
- [ ] **Owner/Admin**: Reset returns counts of cleared records
- [ ] **Sales/ReadOnly**: Reset endpoint returns 403 (forbidden)

### Post-Reset Verification
- [ ] **All Roles**: Can login after reset
- [ ] **All Roles**: Fresh demo data is seeded
- [ ] **All Roles**: First-run checklist appears again
- [ ] **All Roles**: All features work with fresh data

## 🧪 Smoke Test Verification

### Automated Testing
- [ ] **All Roles**: `make smoke` command runs successfully
- [ ] **All Roles**: Smoke test verifies all major functionality
- [ ] **All Roles**: Smoke test provides clear PASS/FAIL output
- [ ] **All Roles**: Smoke test exits with proper error codes

### Manual Verification
- [ ] **All Roles**: All smoke test steps can be performed manually
- [ ] **All Roles**: Smoke test covers RBAC, CRUD, communications, automations
- [ ] **All Roles**: Smoke test includes analytics and webhooks verification
- [ ] **Authorized Roles**: View top accounts table
- [ ] **Authorized Roles**: Filter by date ranges
- [ ] **Authorized Roles**: Drill-down from charts to detailed data

## ⚙️ Settings

### Providers Tab
- [ ] **Admin**: View provider status
- [ ] **Admin**: Configure SendGrid credentials
- [ ] **Admin**: Configure Twilio credentials
- [ ] **Admin**: Validate provider connections
- [ ] **Admin**: Save provider configurations
- [ ] **Non-Admin**: No access to provider settings

### Users & Roles Tab
- [ ] **Owner/Admin**: View users list
- [ ] **Owner/Admin**: Edit user roles
- [ ] **Owner/Admin**: Assign/unassign roles via modal
- [ ] **Owner/Admin**: View role permissions matrix
- [ ] **Non-Admin**: No access to user management

### Branding Tab
- [ ] **Admin**: Configure tenant name
- [ ] **Admin**: Set logo URL
- [ ] **Admin**: Choose primary color
- [ ] **Admin**: Set login subtitle
- [ ] **Admin**: Preview branding changes
- [ ] **Admin**: Save branding settings
- [ ] **Non-Admin**: No access to branding settings

### Environment Tab
- [ ] **Admin**: View backend version
- [ ] **Admin**: View build ID
- [ ] **Admin**: View tenant ID
- [ ] **Admin**: View secrets configuration status
- [ ] **Admin**: View feature flags
- [ ] **Admin**: View provider status summary
- [ ] **Non-Admin**: No access to environment info

## 🔗 Webhooks Console

### Event Management
- [ ] **Admin**: View webhook events list
- [ ] **Admin**: Filter events by provider/type/status
- [ ] **Admin**: Search events by text
- [ ] **Admin**: Paginate through events
- [ ] **Admin**: View event payload in modal
- [ ] **Admin**: Replay webhook events (dry-run)
- [ ] **Non-Admin**: No access to webhooks console

## 📱 Responsive Design

### Mobile Testing
- [ ] **All Roles**: Login on mobile device
- [ ] **All Roles**: Navigate sidebar on mobile
- [ ] **All Roles**: View contacts list on mobile
- [ ] **All Roles**: View deal pipeline on mobile
- [ ] **All Roles**: Send communications on mobile
- [ ] **All Roles**: Access settings on mobile

### Tablet Testing
- [ ] **All Roles**: All features work on tablet
- [ ] **All Roles**: Sidebar navigation works
- [ ] **All Roles**: Forms are usable on tablet

## 🔧 Technical Testing

### API Endpoints
- [ ] **All Roles**: JWT authentication works
- [ ] **All Roles**: RBAC enforced on API calls
- [ ] **All Roles**: Multi-tenant isolation works
- [ ] **All Roles**: CORS configured correctly

### Error Handling
- [ ] **All Roles**: 401 errors redirect to login
- [ ] **All Roles**: 403 errors show permission denied
- [ ] **All Roles**: 404 errors handled gracefully
- [ ] **All Roles**: Network errors show user-friendly messages

### Performance
- [ ] **All Roles**: Page load times are reasonable
- [ ] **All Roles**: Large data sets load without issues
- [ ] **All Roles**: Search and filtering are responsive

## 🧪 Integration Testing

### Provider Integration
- [ ] **Admin**: SendGrid configuration works
- [ ] **Admin**: Twilio configuration works
- [ ] **Admin**: Webhook endpoints receive events
- [ ] **Admin**: Mock mode works when no real credentials

### Database
- [ ] **All Roles**: Data persists across sessions
- [ ] **All Roles**: Multi-tenant data isolation
- [ ] **All Roles**: Database migrations work

## 🚀 Deployment Testing

### Docker
- [ ] **All Roles**: Application starts with docker-compose
- [ ] **All Roles**: All services are accessible
- [ ] **All Roles**: Environment variables are loaded correctly

### Production Readiness
- [ ] **All Roles**: No sensitive data in logs
- [ ] **All Roles**: Error messages don't expose internals
- [ ] **All Roles**: HTTPS works (if configured)
- [ ] **All Roles**: Health check endpoint responds

## 📋 Test Data Requirements

Ensure the following test data exists:
- [ ] At least 10 accounts
- [ ] At least 20 contacts
- [ ] At least 15 deals across different stages
- [ ] At least 25 activities
- [ ] At least 12 communications with varied statuses
- [ ] At least 2 communications with recording_url
- [ ] At least 6 templates
- [ ] At least 4 automation rules
- [ ] At least 5 demo users (one per role)

## ✅ Completion Checklist

Before marking testing complete:
- [ ] All role-based tests pass
- [ ] All feature smoke tests pass
- [ ] No console errors in browser
- [ ] No unhandled promise rejections
- [ ] All API endpoints return expected responses
- [ ] Mobile responsiveness verified
- [ ] Performance is acceptable
- [ ] Security requirements met

---

**Note**: This checklist should be run for each role (Owner, Admin, Manager, Sales, ReadOnly) to ensure proper RBAC enforcement and feature access.
