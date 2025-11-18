# ConversAI Storage Synchronizer

A command-line tool to synchronize ConversAI extension storage across multiple workstations.

## What It Does

When you use ConversAI on multiple computers, each stores conversations locally. This tool merges all conversations from a remote machine with your local machine, creating a unified collection on both.

## Features

- **Union merge**: Combines conversations from both machines
- **Smart conflict resolution**: If same conversation exists on both, keeps the most recent version
- **Bidirectional sync**: Updates both local and remote storage
- **Safety checks**: Ensures Chrome is closed before syncing
- **Progress reporting**: Shows detailed merge statistics

## Prerequisites

### 1. Install Python Dependencies

```bash
pip install -r sync-requirements.txt
```

Or manually:
```bash
pip install plyvel
```

### 2. Install System Dependencies

**rsync** (for transferring databases):
```bash
sudo apt-get install rsync
```

**LevelDB development libraries** (required by plyvel):
```bash
sudo apt-get install libleveldb-dev
```

### 3. SSH Access

You need SSH access to the remote workstation. Key-based authentication is strongly recommended:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa

# Copy to remote machine
ssh-copy-id user@remote_host
```

## Usage

### Basic Syntax

```bash
python conversai-sync.py --remote_host <IP_or_hostname>
```

### Examples

**Sync with remote machine on local network:**
```bash
python conversai-sync.py --remote_host 192.168.1.100
```

**Specify remote username:**
```bash
python conversai-sync.py --remote_host 192.168.1.100 --remote_user john
```

**Sync different Chrome profile:**
```bash
python conversai-sync.py --remote_host 192.168.1.100 --profile "Profile 1"
```

**Local-only mode (safety mode - preserves remote):**
```bash
python conversai-sync.py --remote_host 192.168.1.100 --local_only
```

### Command-Line Options

- `--remote_host` (required): IP address or hostname of remote workstation
- `--remote_user` (optional): SSH username for remote host (defaults to current user)
- `--profile` (optional): Chrome profile name (default: "Default")
- `--local_only` (optional): Only update local storage, leave remote unchanged (safety mode)

### Complete Workflow

**On Machine A (local):**
1. Close Chrome completely
2. Run: `python conversai-sync.py --remote_host <machine_B_IP>`
3. Wait for sync to complete
4. Start Chrome

**On Machine B (remote):**
1. Close Chrome before running sync on Machine A
2. After sync completes, start Chrome
3. All conversations now available on both machines

### Using Local-Only Mode (Safety Feature)

The `--local_only` flag is a safety feature that updates only your local storage while preserving the remote storage unchanged. This is useful when:

- **Testing the sync for the first time**: Try `--local_only` first to verify it works correctly
- **Uncertain about data quality**: If you're not sure about the merge, keep remote as a backup
- **One-way sync needed**: You only want to pull conversations from remote without affecting it
- **Bug concerns**: As a precaution against potential software issues

**Example workflow with safety mode:**
```bash
# First run: test with --local_only
python conversai-sync.py --remote_host 192.168.1.100 --local_only

# Verify local storage looks correct in Chrome

# Second run: sync both ways if satisfied
python conversai-sync.py --remote_host 192.168.1.100
```

**What happens in local-only mode:**
- ✓ Fetches remote database (read-only)
- ✓ Merges with local conversations
- ✓ Updates local storage
- ✗ Remote storage remains untouched
- ✓ Remote Chrome check skipped (read-only access)

**Note**: In local-only mode, only **local Chrome** needs to be closed. Remote Chrome can remain running, though closing it is recommended for a consistent snapshot. If the remote database cannot be read (possibly due to Chrome activity), you'll receive a clear error message.

## How It Works

1. **Safety Check**: Verifies Chrome is closed locally (and on remote too, unless `--local_only` is used)
2. **Read Local**: Reads LevelDB database from `~/.config/google-chrome/Default/Local Extension Settings/hafalgcffhhmhjgeaciekloejcnadggi/`
3. **Fetch Remote**: Uses rsync to copy remote database via SSH
4. **Merge**: Creates union of conversations:
   - New conversations from remote are added
   - Existing conversations keep the most recent version (by `capturedAt` timestamp)
5. **Write Back**: Updates local database (and remote too, unless `--local_only` is used)
6. **Cleanup**: Removes temporary files

## Output Example

```
ConversAI Storage Synchronizer
==================================================

[1/7] Checking Chrome processes...
  ✓ Local Chrome not running
  ✓ Remote Chrome not running

[2/7] Reading local storage...
  ✓ Found 42 local threads

[3/7] Fetching remote storage...
  ✓ Remote database fetched

[4/7] Reading remote storage...
  ✓ Found 38 remote threads

[5/7] Merging threads...

Merge results:
  Local threads: 42
  Remote threads: 38
  Total merged: 65
  New from remote: 23
  Updated from remote: 0

[6/7] Writing merged data to local storage...
  ✓ Local storage updated

[7/7] Updating remote storage...
  ✓ Remote storage updated

==================================================
✓ Synchronization completed successfully!

You can now start Chrome on both machines.
```

### Output Example (Local-Only Mode)

```
ConversAI Storage Synchronizer
MODE: Local-only (remote will NOT be modified)
==================================================

[1/6] Checking Chrome processes...
  ✓ Local Chrome not running
  ⓘ Skipping remote Chrome check (--local_only mode, read-only access)

[2/6] Reading local storage...
  ✓ Found 42 local threads

[3/6] Fetching remote storage...
  ✓ Remote database fetched

[4/6] Reading remote storage...
  ✓ Found 38 remote threads

[5/6] Merging threads...

Merge results:
  Local threads: 42
  Remote threads: 38
  Total merged: 65
  New from remote: 23
  Updated from remote: 0

[6/6] Writing merged data to local storage...
  ✓ Local storage updated

  ⓘ Skipping remote update (--local_only mode)

==================================================
✓ Synchronization completed successfully!

Local storage has been updated with remote conversations.
Remote storage remains unchanged (--local_only mode).

You can now start Chrome on the local machine.
```

## Important Notes

### Chrome Requirements

**Normal sync mode:**
- Chrome MUST be closed on **both** local and remote machines
- Chrome locks the LevelDB database for writing

**Local-only mode (`--local_only`):**
- Chrome MUST be closed on **local** machine only
- Remote Chrome can remain running (read-only access)
- However, closing remote Chrome is **recommended** for a consistent database snapshot

### Data Safety

- The script creates backups by design: it reads before writing
- Original data is preserved until write succeeds
- Both machines end up with identical merged data

### Conflict Resolution

When the same conversation exists on both machines:
- The version with the later `capturedAt` timestamp wins
- This ensures the most up-to-date conversation text is preserved

### Storage Location

The script automatically detects Chrome storage at:
- **Linux**: `~/.config/google-chrome/Default/Local Extension Settings/hafalgcffhhmhjgeaciekloejcnadggi/`
- **Chromium**: `~/.config/chromium/Default/Local Extension Settings/hafalgcffhhmhjgeaciekloejcnadggi/`

For different profiles, use `--profile` flag.

## Troubleshooting

### "Chrome is running" Error

**Solution**: Close all Chrome windows and wait a few seconds. Check with:
```bash
pgrep -f chrome
```

If processes remain, kill them:
```bash
pkill chrome
```

### "Storage path not found" Error

**Possible causes:**
1. ConversAI extension not installed
2. Different Chrome profile in use
3. Never used ConversAI (storage not created yet)

**Solution**:
- Check extension is installed with ID `hafalgcffhhmhjgeaciekloejcnadggi`
- Use `--profile` flag if using non-default profile
- Run ConversAI at least once to create storage

### "Failed to fetch remote database" Error

**Possible causes:**
1. SSH connection failed
2. Remote path doesn't exist
3. rsync not installed

**Solution**:
- Test SSH: `ssh user@remote_host`
- Install rsync on remote: `sudo apt-get install rsync`
- Verify remote extension is installed

### "Failed to open LevelDB" Error

**Possible causes:**
1. Chrome still running (locked database)
2. Corrupted database
3. Missing plyvel dependencies

**Solution**:
- Ensure Chrome is fully closed
- Install libleveldb-dev: `sudo apt-get install libleveldb-dev`
- Reinstall plyvel: `pip install --upgrade --force-reinstall plyvel`

### Permission Errors

**Solution**:
```bash
chmod +x conversai-sync.py
```

## Advanced Usage

### Syncing Multiple Remote Machines

Run the script multiple times with different remote hosts:

```bash
python conversai-sync.py --remote_host machine_B
python conversai-sync.py --remote_host machine_C
python conversai-sync.py --remote_host machine_D
```

Each sync accumulates more conversations into your local storage.

### Automation with Cron

**Not recommended** while Chrome might be running. Manual sync is safer.

### SSH Port Forwarding

If remote machine is behind firewall:

```bash
# On local machine, create tunnel first
ssh -L 2222:localhost:22 gateway_host

# Then sync through tunnel
python conversai-sync.py --remote_host localhost --remote_user user
```

Modify the script to use custom SSH port if needed.

## Technical Details

### LevelDB Format

Chrome stores extension data in LevelDB key-value format. The script:
- Iterates through all keys in the database
- Identifies the key containing `threads` data
- Parses JSON values
- Merges and writes back

### Data Structure

Each conversation (thread) is stored as:
```json
{
  "https://chatgpt.com/c/abc123": {
    "id": "https://chatgpt.com/c/abc123",
    "provider": "chatgpt",
    "url": "https://chatgpt.com/c/abc123",
    "title": "Conversation title",
    "text": "Full conversation text...",
    "capturedAt": "2025-01-17T10:30:00.000Z"
  }
}
```

### Merge Algorithm

```python
for thread_id, remote_thread in remote_threads.items():
    if thread_id not in local_threads:
        # Add new thread
        merged[thread_id] = remote_thread
    else:
        # Keep most recent version
        if remote_thread['capturedAt'] > local_thread['capturedAt']:
            merged[thread_id] = remote_thread
```

## Security Considerations

- **SSH Security**: Use key-based authentication, not passwords
- **Network**: Consider using VPN for syncing over internet
- **Data Privacy**: Conversations contain your chat history - use secure connections
- **Access Control**: Ensure only you have SSH access to your machines

## Contributing

Found a bug? Want to add features?
- Open an issue at: https://github.com/anthropics/claude-code/issues
- Include the full error message and steps to reproduce

## License

This sync tool is provided as-is for use with the ConversAI extension.
