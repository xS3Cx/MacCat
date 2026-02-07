# 🍏 MacCat - Universal macOS Build System

Welcome to the **GoodFeelings** professional build and deployment suite for macOS. This ecosystem allows you to build, convert, sign, and deploy iOS tweaks directly to **PlayCover** (Mac Catalyst) with a single command.

---

## 🚀 Features
- **Automatic Conversion**: Converts standard iOS dylibs to Mac Catalyst format using `vtool`.
- **Auto-Signing**: Automatically signs the dylib for local macOS execution.
- **Dynamic Metadata**: Reads `control` (Theos) and `Info.plist` (App Bundle) to automatically detect project names, versions, and process names.
- **Smart Deployment**: Cleans old dylibs, injects new ones into the app bundle, and restarts the game process automatically.
- **Safety First**: Diagnostics ensure the App Bundle exists and `CydiaSubstrate.framework` is present before anything starts.

---

## 💡 Why MacCat?
Testing tweaks on a physical iOS device for every small code change is slow and tedious. **MacCat** transforms your macOS into a rapid development environment:
- **Instant Testing**: No more installing DEBs on iPhones/iPads. Build and see changes on your Mac in seconds.
- **Automated Workflow**: The script replaces the old dylib inside the PlayCover app bundle with your fresh build and restarts the game automatically.
- **Physical Device Freedom**: Develop and debug UI, shaders, and logic without even touching your phone.

---

## 🛠 Prerequisites
1. **Theos**: Installed and configured for iOS development.
2. **PlayCover**: Installed with the target game/app already imported.
3. **Python 3**: Required to run the build automation.
4. **Dependecies**: The script uses the `rich` library for its premium UI. The `Makefile` will attempt to install it automatically.

---

## 📦 Setup & Customization

### 1. Initial Setup (First Time)
Before using this automation, your game must be installed in **PlayCover** with your tweak's dylib already injected. This establishes the necessary file structure that the script then updates.

**How to prepare your IPA:**
1.  Open **Sideloadly**.
2.  Drag your target game **.ipa** into Sideloadly.
3.  Go to the **Advanced Options** and add your **.dylib** (or **.deb**) file.
4.  **Crucial**: The dylib file name must exactly match your `TWEAK_NAME` (e.g., `UnityChamsTool.dylib`).
5.  Select **"Export to IPA"** and save the modified file.
6.  Install this new IPA into **PlayCover**.

Once the game is installed in PlayCover, this build system will handle all future updates dynamically.

### 2. Makefile Integration
Add the following to your project's `Makefile`:

```makefile
# Single command to build and deploy to PlayCover
package-macos: package
	@python3 -c "import rich" 2>/dev/null || pip3 install rich --quiet --disable-pip-version-check
	@python3 scripts/macos_build.py full-deploy --tweak $(TWEAK_NAME)

.PHONY: package-macos
```

### 2. Script Configuration
Open `scripts/macos_build.py` and set your **Bundle ID**:

```python
# Game Settings
BUNDLE_ID = "com.your.game.bundleid"
```

---

## ⌨️ Commands

| Command | Description |
| :--- | :--- |
| `make package-macos` | The "All-in-One" command. Builds, converts, signs, and launches. |

---

## 🛡 Safety Checks
The system will automatically abort if:
- The **Bundle ID** is incorrect or the app is not installed in PlayCover.
- The tweak hasn't been compiled yet (`make` was not run).
- **CydiaSubstrate.framework** is missing from the target's `Frameworks/` folder.

---

> [!TIP]
> **Enjoy a seamless development workflow with MacCat.**
