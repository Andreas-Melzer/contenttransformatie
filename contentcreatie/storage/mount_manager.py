import threading
import time
import signal
import sys
import atexit
from typing import Dict
from .local_mount import LocalMount

class MountManager:
    """
    Application-wide Daemon.
    - Maintains a registry of mounted files.
    - Runs a background thread to auto-sync changes to Azure.
    - Handles graceful shutdown.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MountManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, sync_interval: int = 30):
        """
        :param sync_interval: How often (in seconds) to check for file changes.
        """
        # Singleton check: Only run init logic once
        if getattr(self, '_initialized', False):
            return
            
        self.mounts: Dict[str, LocalMount] = {}
        self.sync_interval = sync_interval
        self.running = False
        self.thread = None
        
        # Register Lifecycle Hooks
        atexit.register(self.stop)
        
        # Only register signals if we are in the main thread (avoids errors in some contexts)
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except ValueError:
                # Signal registration can fail if not in main interpreter (e.g. some notebooks)
                pass

        self._initialized = True

    def mount(self, blob_name: str, is_directory: bool = False, read_only: bool = False) -> str:
        """
        Registers a file/folder to be managed. 
        Downloads it immediately and returns the local path.
        """
        if blob_name not in self.mounts:
            # Assuming LocalMount is defined as shown in the previous step
            self.mounts[blob_name] = LocalMount(blob_name, is_directory,read_only=False)
        
        # Auto-start the background syncer if not running
        if not self.running:
            self.start()
            
        return self.mounts[blob_name].path
    
    def unmount(self, blob_name: str):
            """
            Stops tracking a file. 
            This prevents the background syncer from trying to upload/download it 
            while we are deleting it.
            """
            if blob_name in self.mounts:
                del self.mounts[blob_name]
                print(f"MountManager: Unmounted {blob_name}")
                
    def start(self):
        """Starts the background sync thread."""
        if self.running: return
        
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=False)
        self.thread.start()
        print(f"MountManager: Background sync started (Interval: {self.sync_interval}s)")

    def stop(self):
        """Stops the background thread and forces a final sync."""
        if not self.running: return
        
        print("MountManager: Stopping... performing final sync.")
        self.running = False
        if self.thread:
            self.thread.join()
        
        # Final Force Sync
        self._run_sync_cycle()
        print("MountManager: Shutdown complete.")

    def _sync_loop(self):
        """Internal loop running in the background."""
        while self.running:
            time.sleep(self.sync_interval)
            self._run_sync_cycle()

    def _run_sync_cycle(self):
        """Iterates all mounts and syncs if dirty."""
        # Create a copy of items to avoid runtime modification errors during iteration
        for name, mount in list(self.mounts.items()):
            if mount.sync_if_dirty():
                print(f"Auto-synced changes in: {name}")

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C or Docker stopping the container."""
        self.stop()
        sys.exit(0)

# Global Singleton Initialization
mount_manager = MountManager(sync_interval=10)