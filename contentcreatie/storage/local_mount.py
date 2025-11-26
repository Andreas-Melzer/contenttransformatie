import os
import hashlib
from ..storage.storage_service import storage_service

class LocalMount:
    def __init__(self, blob_path: str, is_directory: bool = False, read_only: bool = False):
        """
        Initializes the LocalMount instance, pulling data from storage.

        :param blob_path: str, The path to the blob or directory in the cloud storage.
        :param is_directory: bool, Indicates if the path refers to a directory, defaults to False
        :param read_only: bool, If True, prevents syncing local changes back to the cloud, defaults to False
        :return: None, None
        """
        self.blob_path = blob_path
        self.storage = storage_service
        self.is_directory = is_directory
        self.read_only = read_only
        
        # Construct the absolute path
        self.local_path = os.path.join(self.storage.local_base_path, "mounts", blob_path)
        
        # State is a dict {rel_path: hash} for directories, or a single str hash for files
        self._last_sync_state = {} if self.is_directory else None
        
        # Initial Pull
        self._pull()

    @property
    def path(self) -> str:
        """
        Returns the absolute local path of the mount.

        :return: str, The absolute local filesystem path.
        """
        return os.path.abspath(self.local_path)

    def _pull(self):
        """
        Initial hydration from Azure.
        """
        # Ensure the directory structure exists locally
        os.makedirs(os.path.dirname(self.local_path), exist_ok=True)

        if self.is_directory:
            print(f"Pulling directory: {self.blob_path} -> {self.local_path}")
            self.storage.download_directory(self.blob_path, self.local_path, clean_destination=True)
            self._update_internal_state()
        else:
            content = self.storage.download_blob(self.blob_path)
            
            if content is not None:
                mode = 'wb' if isinstance(content, bytes) else 'w'
                with open(self.local_path, mode) as f:
                    f.write(content)
                
                self._update_internal_state()
                
            else:
                if not os.path.exists(self.local_path):
                    print(f"File not found in cloud. Creating empty local file: {self.local_path}")
                    with open(self.local_path, 'w') as f:
                        pass
                    self._update_internal_state()
                else:
                    print(f"New local file detected (not in cloud): {self.blob_path}")
                    pass

    def sync_if_dirty(self) -> bool:
        """
        Checks if the local files have changed since the last sync and uploads them if read_only is False.

        :return: bool, True if files were uploaded, False if no changes detected or mount is read_only.
        """
        if self.read_only:
            return False

        if self.is_directory:
            return self._sync_directory()
        else:
            return self._sync_single_file()

    def _sync_single_file(self) -> bool:
        current_hash = self._calculate_single_file_hash(self.local_path)
        
        # Compare current disk hash with the last known synced hash
        if current_hash == self._last_sync_state:
            return False 

        print(f"Syncing change in file {self.blob_path}...")
        try:
            self.storage.upload_from_file(
                local_path=self.local_path, 
                blob_folder=os.path.dirname(self.blob_path), 
                overwrite=True
            )
            # Update state ONLY after successful upload
            self._last_sync_state = current_hash
            return True
        except Exception as e:
            print(f"Sync failed for {self.blob_path}: {e}")
            return False

    def _sync_directory(self) -> bool:
        current_state = self._calculate_directory_state()
        files_updated = 0

        for rel_path, current_hash in current_state.items():
            previous_hash = self._last_sync_state.get(rel_path)
            
            if previous_hash != current_hash:
                full_local_path = os.path.join(self.local_path, rel_path)
                full_blob_path = os.path.join(self.blob_path, rel_path)
                target_blob_folder = os.path.dirname(full_blob_path)
                
                print(f"Syncing file: {rel_path}...")
                
                try:
                    self.storage.upload_from_file(
                        local_path=full_local_path,
                        blob_folder=target_blob_folder,
                        overwrite=True
                    )
                    files_updated += 1
                except Exception as e:
                    print(f"Failed to sync file {rel_path}: {e}")

        if files_updated > 0 or len(current_state) != len(self._last_sync_state):
             self._last_sync_state = current_state

        return files_updated > 0

    def _update_internal_state(self):
        """
        Updates the internal hash state to match the current disk content.
        """
        if self.is_directory:
            self._last_sync_state = self._calculate_directory_state()
        else:
            self._last_sync_state = self._calculate_single_file_hash(self.local_path)

    def _calculate_directory_state(self) -> dict:
        state_map = {}
        if not os.path.exists(self.local_path):
            return state_map

        for root, _, files in sorted(os.walk(self.local_path)):
            for name in sorted(files):
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, self.local_path)
                state_map[rel_path] = self._calculate_single_file_hash(full_path)
        return state_map

    def _calculate_single_file_hash(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return ""
        hasher = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
        except OSError:
            return ""
        return hasher.hexdigest()