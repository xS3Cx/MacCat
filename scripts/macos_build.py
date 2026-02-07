import sys
import os
import subprocess
import time
import plistlib
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# ==========================================
#           USER CONFIGURATION
# ==========================================

# Branding
TOOL_NAME = "MacCat"

# Game Settings
BUNDLE_ID = "com.AlfaBravo.CombatMaster"

# Paths
HOME_DIR = Path.home()
BASE_DIR = Path(__file__).parent.parent.absolute()
THEOS_OBJ_DIR = BASE_DIR / ".theos" / "obj"
CATALYST_OBJ_DIR = THEOS_OBJ_DIR / "catalyst"

# PlayCover Path
MACOS_APP_PATH = HOME_DIR / "Library/Containers/io.playcover.PlayCover/Applications" / f"{BUNDLE_ID}.app"

# Global state (initialized in main)
GAME_NAME = "Game"
PROCESS_NAME = "Game"
TWEAK_NAME = "yourtweak"
MACOS_DYLIB_PATH = None
MACOS_APP_EXECUTABLE = None

# ==========================================

# Custom Theme
custom_theme = Theme({
    "brand": "#ff0247",
    "info": "white",
    "success": "bold #ff0247",
    "warning": "yellow",
    "error": "bold #ff0247",
    "highlight": "bold white",
})

console = Console(theme=custom_theme)

def get_game_info():
    """Extract game name and executable name from Info.plist."""
    global GAME_NAME, PROCESS_NAME, MACOS_APP_EXECUTABLE
    
    plist_path = MACOS_APP_PATH / "Info.plist"
    if not plist_path.exists():
        # Fallback if logic fails for some reason
        return
        
    try:
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)
            
            # Extract Display Name or Name
            GAME_NAME = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or "Game"
            
            # Extract Executable for process management
            PROCESS_NAME = plist.get('CFBundleExecutable') or "Game"
            
            # Update executable path
            MACOS_APP_EXECUTABLE = MACOS_APP_PATH / PROCESS_NAME
    except Exception:
        pass

def read_control():
    """Parse the control file for project metadata."""
    control_path = BASE_DIR / "control"
    metadata = {
        "Name": "MACOS BUILD WORKFLOW",
        "Version": "1.0",
        "Package": "unknown"
    }
    
    if control_path.exists():
        with open(control_path, 'r') as f:
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
    return metadata

def pre_flight_checks():
    """Verify all requirements before starting build tasks."""
    # Run checks silently unless they fail
    
    # 1. Check if App Bundle exists
    if not MACOS_APP_PATH.exists():
        log_error(f"App bundle not found! Is the game installed in PlayCover?\nPath: {MACOS_APP_PATH}")
        sys.exit(1)
        
    # 2. Check if Info.plist exists
    if not (MACOS_APP_PATH / "Info.plist").exists():
        log_error(f"Info.plist not found in app bundle! Corrupted installation?")
        sys.exit(1)
        
    # 3. Check for CydiaSubstrate (required for tweaks)
    substrate_path = MACOS_APP_PATH / "Frameworks" / "CydiaSubstrate.framework"
    if not substrate_path.exists():
        log_error(f"CydiaSubstrate.framework not found in game bundle!\nPath: {substrate_path}\nTweaks will not load without Substrate. Please add it to the game's Frameworks folder.")
        sys.exit(1)

    # 4. Check if Tweak Dylib was already injected
    if not MACOS_DYLIB_PATH.exists():
        log_error(f"Tweak dylib not found in game bundle!\nPath: {MACOS_DYLIB_PATH}\n\n[highlight]Initial setup required:[/]\nYou must first inject the dylib into the game IPA using Sideloadly and install it in PlayCover.\nSee [brand]scripts/README.md[/] for detailed instructions.")
        sys.exit(1)

def log_info(msg):
    console.print(Text("    ➤ ", style="brand") + Text.from_markup(msg, style="info"))

def log_success(msg):
    console.print(Text("    ✔ ", style="success") + Text.from_markup(msg, style="highlight"))

def log_warning(msg):
    console.print(Text("    ⚠ ", style="warning") + Text.from_markup(msg, style="warning"))

def log_error(msg):
    console.print(Panel(Text.from_markup(msg, style="error"), border_style="brand", title="[bold #ff0247]ERROR[/]", title_align="left", expand=False))

def run_cmd(cmd, shell=True):
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def convert():
    meta = read_control()
    header_text = f"{meta['Name']} v{meta['Version']}"
    console.print(Panel(Text(header_text, style="highlight"), border_style="brand", expand=False))
    log_info(f"Converting iOS dylib to macCatalyst for {GAME_NAME}...")
    
    input_dylib = THEOS_OBJ_DIR / f"{TWEAK_NAME}.dylib"
    output_dylib = CATALYST_OBJ_DIR / f"{TWEAK_NAME}.dylib"
    
    if not input_dylib.exists():
        log_error(f"Input dylib not found at {input_dylib}\nDid you run 'make' first?")
        return False

    # Ensure catalyst directory exists
    CATALYST_OBJ_DIR.mkdir(parents=True, exist_ok=True)

    cmd = f"vtool -set-build-version maccatalyst 13.0 14.0 -replace -output {output_dylib} {input_dylib}"
    success, err = run_cmd(cmd)
    
    if success:
        log_success("Conversion successful!")
        return True
    else:
        log_error(f"Conversion failed:\n{err}")
        return False

def sign():
    log_info("Signing dylib for macOS...")
    dylib = CATALYST_OBJ_DIR / f"{TWEAK_NAME}.dylib"
    success, err = run_cmd(f"codesign --force --deep --sign - {dylib}")
    if success:
        log_success("Signing successful!")
        return True
    else:
        log_error(f"Signing failed:\n{err}")
        return False

def copy():
    log_info("Deploying to PlayCover...")
    frameworks_dir = MACOS_APP_PATH / "Frameworks"
    if not frameworks_dir.exists():
        log_error(f"Frameworks directory not found at {frameworks_dir}")
        log_info(f"Full path checked: {MACOS_APP_PATH}")
        return False
        
    log_info("Removing old dylib...")
    if MACOS_DYLIB_PATH.exists():
        MACOS_DYLIB_PATH.unlink()
        
    source_dylib = CATALYST_OBJ_DIR / f"{TWEAK_NAME}.dylib"
    
    try:
        import shutil
        shutil.copy2(source_dylib, MACOS_DYLIB_PATH)
        run_cmd(f"codesign --force --deep --sign - {MACOS_DYLIB_PATH}")
        log_success("Deployment successful!")
        return True
    except Exception as e:
        log_error(f"Failed to copy dylib: {str(e)}")
        return False

def manage_game():
    log_info(f"Checking for running {PROCESS_NAME} instance...")
    success, _ = run_cmd(f"pgrep -f {PROCESS_NAME}")
    if success:
        log_warning(f"Closing existing {PROCESS_NAME} process...")
        run_cmd(f"pkill -f {PROCESS_NAME}")
        time.sleep(1)
        log_success("Game process closed.")
    else:
        log_info("No existing process found.")
        
    log_info(f"Launching {GAME_NAME}...")
    success, err = run_cmd(f"open \"{MACOS_APP_PATH}\"")
    if success:
        log_success("Game launched successfully!")
        return True
    else:
        log_error(f"Failed to launch game: {err}")
        return False

def summary():
    meta = read_control()
    console.print("\n")
    
    # Professional Success Header
    console.print(Panel(
        Text("SUCCESS", style="bold white"),
        border_style="brand",
        subtitle=f"[brand]{TOOL_NAME}[/]",
        subtitle_align="right",
        padding=(0, 5),
        expand=False
    ))
    
    # Detailed Metadata List
    prefix = Text("    ➤ ", style="brand")
    
    console.print(prefix + Text("Tweak: ", style="info") + Text(meta['Name'].upper(), style="highlight"))
    console.print(prefix + Text("Bundle ID: ", style="info") + Text(meta['Package'], style="info"))
    console.print(prefix + Text("Version: ", style="info") + Text(meta['Version'], style="highlight"))
    console.print(prefix + Text("Target: ", style="info") + Text(GAME_NAME, style="highlight"))
    console.print("\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Universal macOS Build Script")
    parser.add_argument("command", help="Command to execute")
    parser.add_argument("--tweak", help="Override TWEAK_NAME from Makefile")
    
    args = parser.parse_args()
    command = args.command
    
    global TWEAK_NAME, MACOS_DYLIB_PATH
    
    # 1. Initialize Tweak Info
    TWEAK_NAME = args.tweak if args.tweak else "UnityChamsTool"
    
    # 2. Extract Game Info dynamically from bundle
    get_game_info()
    
    # 3. Finalize Paths
    MACOS_DYLIB_PATH = MACOS_APP_PATH / "Frameworks" / f"{TWEAK_NAME}.dylib"
    
    # 4. Run Safety Checks
    if command != "summary":
        pre_flight_checks()

    if command == "convert":
        convert()
    elif command == "sign":
        sign()
    elif command == "copy":
        copy()
    elif command == "open-game":
        manage_game()
    elif command == "full-deploy":
        if convert() and sign() and copy() and manage_game():
            summary()
    elif command == "summary":
        summary()

if __name__ == "__main__":
    main()
