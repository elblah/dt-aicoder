"""
Example plugin: Cloud Memory Sync

Demonstrates how to extend the memory system with cloud synchronization
using the simple monkey-patching approach.
"""

import os
import json
import requests
from datetime import datetime


class CloudMemorySync:
    """Example plugin that adds cloud sync to the memory system."""
    
    def __init__(self):
        self.api_url = os.getenv('MEMORY_SYNC_URL', 'https://api.example.com/memory')
        self.api_key = os.getenv('MEMORY_SYNC_KEY')
        
        # Store original methods
        self.original_create = None
        self.original_read = None
        
    def _upload_to_cloud(self, name: str, content: str, tags: list = None) -> bool:
        """Upload memory note to cloud storage."""
        if not self.api_key:
            return False
            
        try:
            response = requests.post(
                f"{self.api_url}/notes",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    'name': name,
                    'content': content,
                    'tags': tags or [],
                    'timestamp': datetime.now().isoformat()
                },
                timeout=10
            )
            return response.status_code == 201
        except Exception:
            return False
    
    def _download_from_cloud(self, name: str) -> dict:
        """Download memory note from cloud storage."""
        if not self.api_key:
            return None
            
        try:
            response = requests.get(
                f"{self.api_url}/notes/{name}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None
    
    def _enhanced_create(self, memory_instance, name: str, content: str, tags: list = None) -> str:
        """Enhanced create method that also syncs to cloud."""
        # Call original method first
        result = self.original_create(memory_instance, name, content, tags)
        
        # Then upload to cloud
        if "Created" in result or "Updated" in result:
            if self._upload_to_cloud(name, content, tags):
                print(f"☁️  Synced '{name}' to cloud")
        
        return result
    
    def _enhanced_read(self, memory_instance, name: str):
        """Enhanced read method that can fallback to cloud."""
        # Try local first
        result = self.original_read(memory_instance, name)
        
        if result is None:
            # Try cloud as fallback
            cloud_note = self._download_from_cloud(name)
            if cloud_note:
                # Save locally and return
                memory_instance.create(name, cloud_note['content'], cloud_note.get('tags', []))
                print(f"☁️  Downloaded '{name}' from cloud")
                return memory_instance.read(name)
        
        return result
    
    def initialize(self):
        """Initialize the plugin by monkey-patching the memory module."""
        try:
            import aicoder.memory as memory_module
            
            # Store original methods
            self.original_create = memory_module.ProjectMemory.create
            self.original_read = memory_module.ProjectMemory.read
            
            # Replace with enhanced versions
            memory_module.ProjectMemory.create = self._enhanced_create
            memory_module.ProjectMemory.read = self._enhanced_read
            
            print("✅ Cloud Memory Sync plugin loaded")
            print(f"   Sync URL: {self.api_url}")
            print(f"   API Key: {'Configured' if self.api_key else 'Not configured'}")
            
        except ImportError as e:
            print(f"❌ Failed to load Cloud Memory Sync plugin: {e}")


# Initialize plugin
plugin = CloudMemorySync()
plugin.initialize()