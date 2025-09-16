# Automations UI Verification Checklist

## Backend Tests (✅ Working)
- [x] GET /api/automations/ - Returns 4 seeded automation rules
- [x] POST /api/automations/1/test - Dry-run test endpoint working
- [x] Automation rules seeded successfully

## Frontend Tests (To Verify)
1. Navigate to http://localhost:5174/automations
2. Verify list view shows 4 automation rules
3. Test search and filter functionality
4. Test toggle enabled/disabled switches
5. Test Create Rule modal
6. Test Edit Rule functionality
7. Test Test Rule dry-run functionality
8. Test detail view with Definition/Runs tabs

## Quick Test Commands
```bash
# Test backend endpoints
curl -s http://localhost:8000/api/automations/ | jq '.[0].name'
curl -s -X POST http://localhost:8000/api/automations/1/test -H "Content-Type: application/json" -d '{"trigger_payload": {"entity_type": "deal", "entity_id": 1, "from_stage": "qualification", "to_stage": "proposal"}}' | jq '.conditions_met'

# Frontend should be accessible at
# http://localhost:5174/automations
```

## Expected Features
- [x] RBAC-gated (automations.read, automations.write, automations.run_test)
- [x] Multi-tenant with JWT authentication
- [x] List view with filters and pagination
- [x] Create/Edit modal with conditions and actions
- [x] Test functionality with dry-run preview
- [x] Detail view with Definition and Runs tabs
- [x] Optimistic updates for toggle switches
- [x] Toast notifications for all operations
- [x] Consistent shadcn/Tailwind design
