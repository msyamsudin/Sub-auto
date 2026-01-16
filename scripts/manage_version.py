import sys
import re
from pathlib import Path

VERSION_FILE = Path(__file__).parent.parent / "core" / "version.py"

def get_current_version():
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    raise RuntimeError("Could not find version string in core/version.py")

def update_version(new_version):
    content = VERSION_FILE.read_text(encoding="utf-8")
    new_content = re.sub(
        r'__version__\s*=\s*"([^"]+)"',
        f'__version__ = "{new_version}"',
        content
    )
    VERSION_FILE.write_text(new_content, encoding="utf-8")
    print(f"Updated version to {new_version}")

def bump_version(part):
    current = get_current_version()
    major, minor, patch = map(int, current.split('.'))
    
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        print("Invalid part. Use: major, minor, or patch")
        sys.exit(1)
        
    return f"{major}.{minor}.{patch}"

def main():
    if len(sys.argv) != 2:
        print("Usage: python manage_version.py [show|major|minor|patch]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "show":
        print(get_current_version())
    elif command in ["major", "minor", "patch"]:
        new_ver = bump_version(command)
        update_version(new_ver)
    else:
        print("Unknown command. Use: show, major, minor, patch")

if __name__ == "__main__":
    main()
