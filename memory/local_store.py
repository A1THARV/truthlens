"""Local storage implementation for memory persistence."""

import json
import os
from typing import Any, Dict, Optional, List
from datetime import datetime


class LocalStore:
    """Local file-based storage for agent memory."""
    
    def __init__(self, storage_dir: str = "data"):
        """Initialize the local store.
        
        Args:
            storage_dir: Directory to store data files
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def save(self, key: str, data: Any) -> bool:
        """Save data to local storage.
        
        Args:
            key: Unique identifier for the data
            data: Data to store (must be JSON serializable)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.storage_dir, f"{key}.json")
            
            # Add metadata
            store_data = {
                "key": key,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }
            
            with open(file_path, 'w') as f:
                json.dump(store_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving data: {str(e)}")
            return False
    
    def load(self, key: str) -> Optional[Any]:
        """Load data from local storage.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            The stored data, or None if not found
        """
        try:
            file_path = os.path.join(self.storage_dir, f"{key}.json")
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r') as f:
                store_data = json.load(f)
            
            return store_data.get("data")
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete data from local storage.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.storage_dir, f"{key}.json")
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return True
        except Exception as e:
            print(f"Error deleting data: {str(e)}")
            return False
    
    def list_keys(self) -> List[str]:
        """List all keys in the store.
        
        Returns:
            List of keys
        """
        try:
            files = os.listdir(self.storage_dir)
            keys = [f.replace('.json', '') for f in files if f.endswith('.json')]
            return keys
        except Exception as e:
            print(f"Error listing keys: {str(e)}")
            return []
    
    def clear(self) -> bool:
        """Clear all data from the store.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for key in self.list_keys():
                self.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing store: {str(e)}")
            return False
