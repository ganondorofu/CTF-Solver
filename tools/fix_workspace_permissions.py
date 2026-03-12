#!/usr/bin/env python3
"""
Fix workspace directory permissions.

Root-owned directories cause "Permission denied" errors when agents try to create files.
This script fixes ownership and ensures all workspace directories are owned by the current user.
"""

import os
import subprocess
from pathlib import Path


def fix_workspace_permissions(workspace_dir: Path = Path("workspace")):
    """Fix all workspace directory permissions."""
    if not workspace_dir.exists():
        print(f"Workspace directory not found: {workspace_dir}")
        return
    
    current_user = os.getenv("USER", "ctfuser")
    
    print(f"Checking workspace permissions in: {workspace_dir}")
    print(f"Target user: {current_user}")
    print()
    
    fixed = []
    errors = []
    
    for agent_dir in workspace_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name == "shared":
            continue
        
        # Check ownership
        stat_info = agent_dir.stat()
        uid = stat_info.st_uid
        
        # Get owner name
        try:
            import pwd
            owner = pwd.getpwuid(uid).pw_name
        except:
            owner = str(uid)
        
        if owner != current_user:
            print(f"[FIX] {agent_dir.name}: owned by {owner}, changing to {current_user}")
            
            try:
                # Use sudo to fix ownership recursively
                result = subprocess.run(
                    ["sudo", "chown", "-R", f"{current_user}:{current_user}", str(agent_dir)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    fixed.append(agent_dir.name)
                    print(f"  ✅ Fixed: {agent_dir.name}")
                else:
                    errors.append((agent_dir.name, result.stderr))
                    print(f"  ❌ Failed: {result.stderr}")
            except Exception as e:
                errors.append((agent_dir.name, str(e)))
                print(f"  ❌ Error: {e}")
        else:
            print(f"[OK]  {agent_dir.name}: correct ownership")
        
        # Ensure subdirectories exist with correct permissions
        for subdir in ["challenges", "state"]:
            subdir_path = agent_dir / subdir
            if not subdir_path.exists():
                try:
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    print(f"  ✅ Created: {subdir}")
                except Exception as e:
                    print(f"  ⚠️  Could not create {subdir}: {e}")
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    if fixed:
        print(f"\n✅ Fixed {len(fixed)} directories:")
        for name in fixed:
            print(f"   - {name}")
    
    if errors:
        print(f"\n❌ Errors in {len(errors)} directories:")
        for name, error in errors:
            print(f"   - {name}: {error}")
    
    if not fixed and not errors:
        print("\n✅ All directories have correct permissions")


if __name__ == "__main__":
    import sys
    
    if os.geteuid() == 0:
        print("Warning: Running as root. This script should be run as a regular user.")
        print("It will use sudo internally when needed.")
        response = input("Continue? (y/N): ")
        if response.lower() != "y":
            sys.exit(1)
    
    fix_workspace_permissions()
