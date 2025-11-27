"""
Canvas API Request Executor Module
Handles Canvas API Requests
"""

import requests
from typing import Optional, Dict

class CanvasRequestExecutor:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()

        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })

    def make_request(self, endpoint: str, method: str = 'GET', data: Optional[dict] = None) -> dict:
        """Make a request to Canvas API"""
        url = f"{self.base_url}/api/v1{endpoint}"

        if method.upper() == 'GET':
            response = self.session.get(url)
        elif method.upper() == 'PUT':
            response = self.session.put(url, json=data)
        elif method.upper() == 'POST':
            response = self.session.post(url, json=data)
        elif method.upper() == 'DELETE':
            response = self.session.delete(url)
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.content:
                try:
                    error_data = response.json()
                    raise RuntimeError(f"Canvas API Error {response.status_code}: {error_data}") from e
                except:
                    raise RuntimeError(f"Canvas API Error {response.status_code}: {response.text}") from e
            else:
                raise

        return response.json() if response.content else {}
