"""
Debug script to test DB table generation
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

app = create_app()

with app.test_client() as client:
    # Test basic app creation
    print("Testing app creation...")
    response = client.get('/healthz')
    print(f"Healthz: {response.status_code}")
    
    # Test saving a simple DB table
    print("\nTesting DB table save...")
    save_payload = {
        'project_id': 'test-db-123',
        'version': 'v1',
        'nodes': [
            {
                'id': 'node1',
                'type': 'db_table',
                'props': {
                    'name': 'tasks',
                    'columns': [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "title", "type": "TEXT"}
                    ]
                }
            }
        ],
        'edges': [],
        'metadata': {}
    }
    
    save_response = client.post('/api/builder/save', json=save_payload)
    print(f"Save response: {save_response.status_code}")
    if save_response.status_code != 200:
        print(f"Save error: {save_response.data}")
    
    # Test generate
    print("\nTesting generate...")
    generate_response = client.post('/api/builder/generate-build', json={'project_id': 'test-db-123'})
    print(f"Generate response: {generate_response.status_code}")
    if generate_response.status_code == 200:
        data = generate_response.get_json()
        print(f"Tables generated: {len(data.get('tables', []))}")
        for table in data.get('tables', []):
            print(f"  - {table['table']}: {table['route']}")
    
    # Test CRUD endpoint
    print("\nTesting CRUD endpoint...")
    crud_response = client.get('/api/tasks')
    print(f"CRUD GET response: {crud_response.status_code}")
    if crud_response.status_code != 200:
        print(f"CRUD error: {crud_response.data}")
