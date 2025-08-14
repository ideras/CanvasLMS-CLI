"""
Canvas API Request Executor Module
Handles Canvas API Requests
"""

import requests

class CanvasRequestExecutor:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()

        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def make_request(self, endpoint: str, method: str = 'GET', data: dict = None) -> dict:
        """Make a request to Canvas API"""
        url = f"{self.base_url}/api/v1{endpoint}"
        
        if method.upper() == 'GET':
            response = self.session.get(url)
        elif method.upper() == 'PUT':
            response = self.session.put(url, json=data)
        elif method.upper() == 'POST':
            response = self.session.post(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    