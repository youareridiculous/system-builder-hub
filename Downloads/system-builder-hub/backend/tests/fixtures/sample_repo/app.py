"""
Sample Flask application for testing
"""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/healthz')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'sample-app'})

@app.route('/api/hello')
def hello():
    """Hello endpoint"""
    return jsonify({'message': 'Hello, World!'})

if __name__ == '__main__':
    app.run(debug=True)
