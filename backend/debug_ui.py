"""
Debug script to test UI page generation
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

app = create_app()

with app.test_client() as client:
    # Test UI page generation
    print("Testing UI page generation...")
    
    # Save state with db_table and ui_page
    save_payload = {
        'project_id': 'test-ui-123',
        'version': 'v1',
        'nodes': [
            {
                'id': 'table1',
                'type': 'db_table',
                'props': {
                    'name': 'tasks',
                    'columns': [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "title", "type": "TEXT"}
                    ]
                }
            },
            {
                'id': 'page1',
                'type': 'ui_page',
                'props': {
                    'name': 'TasksPage',
                    'route': '/tasks',
                    'title': 'Tasks',
                    'content': '<h1>Tasks</h1>',
                    'bind_table': 'tasks',
                    'form': {
                        'enabled': True,
                        'fields': ['title']
                    }
                }
            }
        ],
        'edges': [],
        'metadata': {}
    }
    
    save_response = client.post('/api/builder/save', json=save_payload)
    print(f"Save response: {save_response.status_code}")
    
    generate_response = client.post('/api/builder/generate-build', json={'project_id': 'test-ui-123'})
    print(f"Generate response: {generate_response.status_code}")
    
    # Test UI page access
    print("\nTesting UI page access...")
    page_response = client.get('/ui/tasks')
    print(f"Page response: {page_response.status_code}")
    if page_response.status_code != 200:
        print(f"Page error: {page_response.data}")
