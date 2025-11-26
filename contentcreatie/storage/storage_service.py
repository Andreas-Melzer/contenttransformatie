import os
import json
import shutil
import io
import threading
from typing import Union, List, Optional, Any
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from ..config import settings
import os
import dotenv
import hashlib

class StorageService:
    """
    Thread-Safe Singleton Service for managing file operations.
    Hybrid adapter for Azure Blob Storage and Local Filesystem.
    """
    
    _instance = None
    _lock = threading.Lock()
    dotenv.load_dotenv()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(StorageService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, 
                 storage_account_name: str = None, 
                 container_name: str = None,
                 use_local_storage: bool = False,
                 local_base_path: str = "/tmp"):
        
        if getattr(self, '_initialized', False):
            return

        self.storage_account_name = storage_account_name or getattr(settings, 'azure_storage_account', 'storagekis906')
        self.container_name = container_name or getattr(settings, 'azure_container_name', 'containerkis')
        self.use_local_storage = use_local_storage
        self.local_base_path = os.path.join(local_base_path, self.container_name)

        if self.use_local_storage:
            os.makedirs(self.local_base_path, exist_ok=True)
            print(f"StorageService: Local mode at {self.local_base_path}")
        else:
            if not self.storage_account_name or not self.container_name:
                raise ValueError("Storage config missing.")
            
            try:
                conn_str = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
                sas_token = os.environ.get('AZURE_SAS_TOKEN')
                account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
                
                if conn_str:
                    print("StorageService: Found Connection String. Using Key-based auth.")
                    self.blob_service_client = BlobServiceClient.from_connection_string(conn_str)
                elif sas_token:
                    self.blob_service_client = BlobServiceClient(account_url=account_url, credential=sas_token)
                else:
                    if not self.storage_account_name:
                        raise ValueError("Storage Account Name missing for Identity Auth.")
                        
                    print("StorageService: No Connection String found. Attempting DefaultAzureCredential...")
                    
                    self.blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())

                # Validate connection immediately
                self.container_client = self.blob_service_client.get_container_client(self.container_name)
                
            except Exception as e:
                raise ConnectionError(f"Azure Storage Init Failed: {e}")

        self._initialized = True

    def _get_local_path(self, blob_name: str) -> str:
        return os.path.join(self.local_base_path, blob_name)

    def _write_bytes(self, blob_name: str, data: bytes, content_type: str = None, overwrite: bool = True) -> bool:
        """Internal helper to handle byte writing to either target."""
        try:
            if self.use_local_storage:
                full_path = self._get_local_path(blob_name)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                if not overwrite and os.path.exists(full_path):
                    return False
                with open(full_path, 'wb') as f:
                    f.write(data)
                return True
            else:
                blob_client = self.container_client.get_blob_client(blob_name)
                settings_obj = ContentSettings(content_type=content_type) if content_type else None
                blob_client.upload_blob(data, overwrite=overwrite, content_settings=settings_obj)
                return True
        except Exception as e:
            print(f"Write error ({blob_name}): {e}")
            return False

    def _read_bytes(self, blob_name: str) -> Optional[bytes]:
        """Internal helper to handle byte reading."""
        try:
            if self.use_local_storage:
                full_path = self._get_local_path(blob_name)
                if not os.path.exists(full_path):
                    return None
                with open(full_path, 'rb') as f:
                    return f.read()
            else:
                return self.container_client.get_blob_client(blob_name).download_blob().readall()
        except (ResourceNotFoundError, FileNotFoundError):
            return None
        except Exception as e:
            print(f"Read error ({blob_name}): {e}")
            return None

    def upload_blob(self, blob_name: str, data: Union[str, bytes, dict, list], content_type: str = None, overwrite: bool = True) -> bool:
        """Uploads in-memory data."""
        if isinstance(data, (dict, list)):
            content = json.dumps(data).encode('utf-8')
            content_type = content_type or 'application/json'
        elif isinstance(data, str):
            content = data.encode('utf-8')
        else:
            content = data 
        
        return self._write_bytes(blob_name, content, content_type, overwrite)

    def upload_from_file(self, local_path: str, blob_folder: str = "", overwrite: bool = True) -> bool:
        """Uploads a file from disk."""
        if not os.path.exists(local_path):
            print(f"File not found: {local_path}")
            return False

        filename = os.path.basename(local_path)
        blob_name = f"{blob_folder.rstrip('/')}/{filename}" if blob_folder else filename

        try:
            with open(local_path, "rb") as f:
                return self._write_bytes(blob_name, f.read(), None, overwrite)
        except Exception as e:
            print(f"Upload file error: {e}")
            return False

    def download_blob(self, blob_name: str, as_json: bool = False) -> Union[str, bytes, dict, list, None]:
        """Downloads content with optional JSON parsing."""
        content = self._read_bytes(blob_name)
        if content is None:
            return None

        if as_json:
            try:
                return json.loads(content.decode('utf-8'))
            except Exception:
                print(f"JSON decode failed for {blob_name}")
                return None
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content

    def download_as_stringio(self, blob_name: str) -> Optional[io.StringIO]:
        """Downloads content as StringIO for pandas."""
        content = self.download_blob(blob_name)
        if content is None: 
            return None
        if isinstance(content, str): 
            return io.StringIO(content)
        if isinstance(content, bytes):
            try:
                return io.StringIO(content.decode('utf-8'))
            except:
                return None
        return None

    def delete_blob(self, blob_name: str) -> bool:
        """Deletes a single blob."""
        try:
            if self.use_local_storage:
                full_path = self._get_local_path(blob_name)
                if os.path.exists(full_path):
                    os.remove(full_path)
                return True
            else:
                self.container_client.get_blob_client(blob_name).delete_blob()
                return True
        except ResourceNotFoundError:
            return True
        except Exception as e:
            print(f"Delete error ({blob_name}): {e}")
            return False

    def list_blobs(self, prefix: str = None) -> List[str]:
        """Lists blobs/files."""
        if self.use_local_storage:
            file_list = []
            for root, _, files in os.walk(self.local_base_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.local_base_path).replace("\\", "/")
                    if not prefix or rel_path.startswith(prefix):
                        file_list.append(rel_path)
            return file_list
        else:
            try:
                blobs = self.container_client.list_blobs(name_starts_with=prefix)
                return [b.name for b in blobs]
            except Exception as e:
                print(f"List error: {e}")
                return []

    def delete_directory(self, prefix: str) -> int:
        """Deletes files starting with prefix."""
        count = 0
        blobs = self.list_blobs(prefix)
        for blob in blobs:
            if self.delete_blob(blob):
                count += 1
        return count

    def download_directory(self, blob_prefix: Union[str, Any], local_target_dir: Union[str, Any], clean_destination: bool = False) -> int:
        """
        Downloads a folder recursively. 
        Robustly handles pathlib.Path objects by converting them to strings.
        """

        blob_prefix = str(blob_prefix)
        local_target_dir = str(local_target_dir)

        if clean_destination and os.path.exists(local_target_dir):
            shutil.rmtree(local_target_dir)
        
        blobs = self.list_blobs(blob_prefix)
        count = 0
        
        prefix_clean = blob_prefix.rstrip("/")
        
        for blob_name in blobs:
            if blob_name.startswith(prefix_clean):
                relative_path = blob_name[len(prefix_clean):].lstrip("/")
            else:
                relative_path = blob_name
            
            if not relative_path:
                continue

            dest_path = os.path.join(local_target_dir, relative_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            data = self._read_bytes(blob_name)
            if data:
                with open(dest_path, 'wb') as f:
                    f.write(data)
                count += 1
        return count

    def upload_directory(self, local_source_dir: Union[str, Any], blob_prefix: Union[str, Any] = "", overwrite: bool = True) -> int:
        """
        Recursively uploads a local directory.
        Robustly handles pathlib.Path objects.
        """
        # --- FIX: Force string conversion ---
        local_source_dir = str(local_source_dir)
        blob_prefix = str(blob_prefix)
        # ------------------------------------

        if not os.path.exists(local_source_dir):
            print(f"Local directory not found: {local_source_dir}")
            return 0

        count = 0
        blob_prefix = blob_prefix.strip("/")
        
        for root, _, files in os.walk(local_source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, local_source_dir).replace("\\", "/")
                dest_blob = f"{blob_prefix}/{rel_path}" if blob_prefix else rel_path
                
                if self.upload_from_file(full_path, os.path.dirname(dest_blob), overwrite):
                    count += 1
        return count
            
        
storage_service = StorageService()  