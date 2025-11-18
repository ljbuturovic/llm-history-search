#!/usr/bin/env python3
"""
ConversAI Storage Synchronizer

Synchronizes Chrome extension storage across multiple workstations.
Merges conversations from remote host with local storage.

Usage:
    python conversai-sync.py --remote_host <IP_or_hostname>

Requirements:
    - Chrome must be closed on both machines
    - SSH access to remote host
    - plyvel library (pip install plyvel)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import plyvel
except ImportError:
    print("ERROR: plyvel library not found. Install with: pip install plyvel")
    sys.exit(1)


# Extension ID for conversai
EXTENSION_ID = "hafalgcffhhmhjgeaciekloejcnadggi"

# Chrome storage key for threads
STORAGE_KEY = "threads"


class ChromeStorageSync:
    def __init__(self, remote_host: str, remote_user: Optional[str] = None,
                 chrome_profile: str = "Default", local_only: bool = False):
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.chrome_profile = chrome_profile
        self.local_only = local_only

        # Local storage path
        self.local_storage_path = self._get_local_storage_path()

        # Remote storage path
        self.remote_storage_path = self._get_remote_storage_path()

    def _get_local_storage_path(self) -> Path:
        """Get local Chrome extension storage path"""
        home = Path.home()

        # Try different Chrome paths
        possible_paths = [
            home / ".config/google-chrome" / self.chrome_profile / "Local Extension Settings" / EXTENSION_ID,
            home / ".config/chromium" / self.chrome_profile / "Local Extension Settings" / EXTENSION_ID,
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Return default even if doesn't exist (for error message)
        return possible_paths[0]

    def _get_remote_storage_path(self) -> str:
        """Get remote Chrome extension storage path"""
        return f"~/.config/google-chrome/{self.chrome_profile}/Local Extension Settings/{EXTENSION_ID}"

    def check_chrome_not_running(self) -> bool:
        """Check if Chrome is running locally"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "chrome"],
                capture_output=True,
                text=True
            )
            return result.returncode != 0  # Returns True if no Chrome process found
        except Exception as e:
            print(f"WARNING: Could not check if Chrome is running: {e}")
            return True

    def check_remote_chrome_not_running(self) -> bool:
        """Check if Chrome is running on remote host"""
        try:
            ssh_host = f"{self.remote_user}@{self.remote_host}" if self.remote_user else self.remote_host
            result = subprocess.run(
                ["ssh", ssh_host, "pgrep -f chrome"],
                capture_output=True,
                text=True
            )
            return result.returncode != 0  # Returns True if no Chrome process found
        except Exception as e:
            print(f"WARNING: Could not check remote Chrome status: {e}")
            return True

    def read_leveldb_storage(self, db_path: Path) -> Dict[str, Any]:
        """Read Chrome extension storage from LevelDB"""
        if not db_path.exists():
            raise FileNotFoundError(f"Storage path not found: {db_path}")

        try:
            db = plyvel.DB(str(db_path), create_if_missing=False)
        except Exception as e:
            raise Exception(f"Failed to open LevelDB at {db_path}: {e}")

        threads = {}

        try:
            # Chrome stores extension data with various key formats
            # We need to find the key that contains our 'threads' data
            for key, value in db:
                try:
                    # Keys in Chrome extension storage are often prefixed
                    # The actual key might be just the string 'threads' or have a prefix
                    key_str = key.decode('utf-8', errors='ignore')

                    # Try to decode the value as JSON
                    value_str = value.decode('utf-8', errors='ignore')
                    data = json.loads(value_str)

                    # Check if this looks like our threads data
                    if isinstance(data, dict) and any(
                        isinstance(v, dict) and 'provider' in v and 'text' in v
                        for v in data.values()
                    ):
                        threads = data
                        break

                    # Also check if the key matches our storage key
                    if STORAGE_KEY in key_str:
                        if isinstance(data, dict):
                            threads = data
                            break

                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    continue

        finally:
            db.close()

        return threads

    def write_leveldb_storage(self, db_path: Path, threads: Dict[str, Any]):
        """Write merged threads back to LevelDB"""
        if not db_path.exists():
            raise FileNotFoundError(f"Storage path not found: {db_path}")

        try:
            db = plyvel.DB(str(db_path), create_if_missing=False)
        except Exception as e:
            raise Exception(f"Failed to open LevelDB at {db_path}: {e}")

        try:
            # Find the existing key that stores threads
            threads_key = None

            for key, value in db:
                try:
                    key_str = key.decode('utf-8', errors='ignore')
                    value_str = value.decode('utf-8', errors='ignore')
                    data = json.loads(value_str)

                    # Check if this is the threads data
                    if isinstance(data, dict) and any(
                        isinstance(v, dict) and 'provider' in v and 'text' in v
                        for v in data.values()
                    ):
                        threads_key = key
                        break

                    if STORAGE_KEY in key_str:
                        threads_key = key
                        break

                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    continue

            # If no existing key found, use default
            if threads_key is None:
                threads_key = STORAGE_KEY.encode('utf-8')

            # Write the merged threads
            threads_json = json.dumps(threads)
            db.put(threads_key, threads_json.encode('utf-8'))

        finally:
            db.close()

    def fetch_remote_database(self, temp_dir: Path) -> Path:
        """Copy remote database to local temp directory"""
        remote_db = temp_dir / "remote_db"
        remote_db.mkdir(exist_ok=True)

        ssh_host = f"{self.remote_user}@{self.remote_host}" if self.remote_user else self.remote_host
        rsync_source = f"{ssh_host}:{self.remote_storage_path}/"

        print(f"Fetching remote database from {ssh_host}...")

        try:
            result = subprocess.run(
                ["rsync", "-az", "--progress", rsync_source, str(remote_db) + "/"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to fetch remote database:\n{e.stderr}")
        except FileNotFoundError:
            raise Exception("rsync not found. Please install rsync: sudo apt-get install rsync")

        return remote_db

    def push_to_remote(self, local_db: Path):
        """Push updated database to remote host"""
        ssh_host = f"{self.remote_user}@{self.remote_host}" if self.remote_user else self.remote_host
        rsync_dest = f"{ssh_host}:{self.remote_storage_path}/"

        print(f"Pushing merged data to {ssh_host}...")

        try:
            result = subprocess.run(
                ["rsync", "-az", "--progress", str(local_db) + "/", rsync_dest],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to push to remote:\n{e.stderr}")

    def merge_threads(self, local_threads: Dict, remote_threads: Dict) -> Dict:
        """Merge threads from local and remote (union)"""
        merged = local_threads.copy()

        added_count = 0
        updated_count = 0

        for thread_id, remote_thread in remote_threads.items():
            if thread_id not in merged:
                # New thread from remote
                merged[thread_id] = remote_thread
                added_count += 1
            else:
                # Thread exists in both - keep the most recent one
                local_captured = merged[thread_id].get('capturedAt', '')
                remote_captured = remote_thread.get('capturedAt', '')

                if remote_captured > local_captured:
                    merged[thread_id] = remote_thread
                    updated_count += 1

        print(f"\nMerge results:")
        print(f"  Local threads: {len(local_threads)}")
        print(f"  Remote threads: {len(remote_threads)}")
        print(f"  Total merged: {len(merged)}")
        print(f"  New from remote: {added_count}")
        print(f"  Updated from remote: {updated_count}")

        return merged

    def sync(self):
        """Main sync operation"""
        print("ConversAI Storage Synchronizer")
        if self.local_only:
            print("MODE: Local-only (remote will NOT be modified)")
        print("=" * 50)

        # Determine total steps
        total_steps = 6 if self.local_only else 7

        # Safety checks
        print(f"\n[1/{total_steps}] Checking Chrome processes...")
        if not self.check_chrome_not_running():
            print("ERROR: Chrome is running locally. Please close Chrome before syncing.")
            sys.exit(1)
        print("  ✓ Local Chrome not running")

        # Only check remote Chrome if we're going to write to it
        if not self.local_only:
            if not self.check_remote_chrome_not_running():
                print(f"ERROR: Chrome is running on {self.remote_host}. Please close Chrome on remote host.")
                sys.exit(1)
            print(f"  ✓ Remote Chrome not running")
        else:
            print(f"  ⓘ Skipping remote Chrome check (--local_only mode, read-only access)")

        # Read local storage
        print(f"\n[2/{total_steps}] Reading local storage...")
        if not self.local_storage_path.exists():
            print(f"ERROR: Local storage not found at {self.local_storage_path}")
            sys.exit(1)

        try:
            local_threads = self.read_leveldb_storage(self.local_storage_path)
            print(f"  ✓ Found {len(local_threads)} local threads")
        except Exception as e:
            print(f"ERROR: Failed to read local storage: {e}")
            sys.exit(1)

        # Fetch and read remote storage
        print(f"\n[3/{total_steps}] Fetching remote storage...")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                remote_db_path = self.fetch_remote_database(temp_path)
                print("  ✓ Remote database fetched")
            except Exception as e:
                print(f"ERROR: {e}")
                sys.exit(1)

            print(f"\n[4/{total_steps}] Reading remote storage...")
            try:
                remote_threads = self.read_leveldb_storage(remote_db_path)
                print(f"  ✓ Found {len(remote_threads)} remote threads")
            except Exception as e:
                print(f"ERROR: Failed to read remote storage: {e}")
                if self.local_only:
                    print("\nHINT: If Chrome is running on the remote host, it may interfere with reading.")
                    print("      Consider closing Chrome on remote, or the database might be corrupted.")
                sys.exit(1)

            # Merge
            print(f"\n[5/{total_steps}] Merging threads...")
            merged_threads = self.merge_threads(local_threads, remote_threads)

            # Write to local
            print(f"\n[6/{total_steps}] Writing merged data to local storage...")
            try:
                self.write_leveldb_storage(self.local_storage_path, merged_threads)
                print("  ✓ Local storage updated")
            except Exception as e:
                print(f"ERROR: Failed to write to local storage: {e}")
                sys.exit(1)

            # Write to temp copy of remote and push (only if not local_only mode)
            if not self.local_only:
                print(f"\n[7/{total_steps}] Updating remote storage...")
                try:
                    self.write_leveldb_storage(remote_db_path, merged_threads)
                    self.push_to_remote(remote_db_path)
                    print("  ✓ Remote storage updated")
                except Exception as e:
                    print(f"ERROR: Failed to update remote storage: {e}")
                    print("  Local storage has been updated successfully.")
                    print("  You may need to manually copy the database to the remote host.")
                    sys.exit(1)
            else:
                print("\n  ⓘ Skipping remote update (--local_only mode)")

        print("\n" + "=" * 50)
        print("✓ Synchronization completed successfully!")
        if self.local_only:
            print("\nLocal storage has been updated with remote conversations.")
            print("Remote storage remains unchanged (--local_only mode).")
            print("\nYou can now start Chrome on the local machine.")
        else:
            print("\nYou can now start Chrome on both machines.")


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize ConversAI storage across workstations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python conversai-sync.py --remote_host 192.168.1.100
  python conversai-sync.py --remote_host myserver.local --remote_user john
  python conversai-sync.py --remote_host 10.0.0.5 --profile "Profile 1"
  python conversai-sync.py --remote_host 192.168.1.100 --local_only

Notes:
  - Chrome must be closed on local machine (and remote too, unless --local_only)
  - Requires SSH access to remote host (with key-based authentication recommended)
  - Requires rsync to be installed on both machines
  - The script merges threads from both machines (union operation)
  - If a thread exists on both machines, the most recent version is kept
  - Use --local_only to update only local storage (preserves remote as backup)
        """
    )

    parser.add_argument(
        "--remote_host",
        required=True,
        help="IP address or hostname of remote workstation"
    )

    parser.add_argument(
        "--remote_user",
        help="SSH username for remote host (optional, uses current user if not specified)"
    )

    parser.add_argument(
        "--profile",
        default="Default",
        help="Chrome profile name (default: Default)"
    )

    parser.add_argument(
        "--local_only",
        action="store_true",
        help="Only update local storage, leave remote unchanged (safety mode)"
    )

    args = parser.parse_args()

    # Create syncer and run
    syncer = ChromeStorageSync(
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        chrome_profile=args.profile,
        local_only=args.local_only
    )

    try:
        syncer.sync()
    except KeyboardInterrupt:
        print("\n\nSync cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
