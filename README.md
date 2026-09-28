# libvlc-gen

Universal LibVLC Binary Generator - Automates fetching, building, and packaging LibVLC for all platforms.

## Overview

`libvlc-gen` provides two primary tools for obtaining LibVLC binaries:

1. **Local Generator** (`tools/generate_libvlc.py`) - Cross-platform Python CLI for fetching prebuilt binaries or building from source locally
2. **GitHub Actions Pipelines** - Automated CI/CD workflows for matrix builds across all supported platforms

## Supported Platforms

| OS | Architectures | Fetch | Build |
|---|---|---|---|
| iOS | arm64, armv7 | ✓ | ✓ (macOS runner) |
| Android | arm64, armv7, x86_64, x86 | ✓ | ✓ (Linux runner + NDK) |
| macOS | arm64, x86_64 | ✓ | ✓ (macOS runner) |
| Linux | x86_64, arm64, x86 | ✓ | ✓ (Linux runner) |
| Windows | x86_64, arm64, x86 | ✓ | ✓ (Windows runner) |

## Quick Start

### Prerequisites

- Python 3.8+
- Git
- Platform-specific build tools (for `--mode build`)

```bash
# Clone the repository
git clone https://github.com/yourusername/libvlc-gen.git
cd libvlc-gen

# Install Python dependencies
pip install -r requirements.txt
```

### Fetch Prebuilt Binaries (Recommended)

```bash
# Auto-detect host OS/arch and fetch
python tools/generate_libvlc.py --mode fetch

# Fetch for specific target
python tools/generate_libvlc.py --mode fetch --target-os android --arch arm64
python tools/generate_libvlc.py --mode fetch --target-os ios --arch arm64
python tools/generate_libvlc.py --mode fetch --target-os windows --arch x86_64
python tools/generate_libvlc.py --mode fetch --target-os linux --arch x86_64
python tools/generate_libvlc.py --mode fetch --target-os macos --arch arm64

# Create zip package
python tools/generate_libvlc.py --mode fetch --target-os android --arch arm64 --package
```

### Build from Source

```bash
# Build for current platform (requires build tools)
python tools/generate_libvlc.py --mode build --target-os linux --arch x86_64

# Build specific version from branch/tag
python tools/generate_libvlc.py --mode build --target-os macos --arch arm64 --branch 3.0.20

# Build with custom source URL
python tools/generate_libvlc.py --mode build --target-os windows --arch x86_64 --source-url https://code.videolan.org/videolan/vlc.git
```

## Output Structure

```
dist/
└── <target-os>-<arch>/
    ├── include/
    │   └── vlc/
    │       ├── vlc.h
    │       ├── vlc_common.h
    │       ├── vlc_version.h
    │       └── ... (all public headers)
    └── lib/
        ├── libvlc.a / libvlc.lib / libvlc.dll.a
        ├── libvlccore.a / libvlccore.lib / libvlccore.dll.a
        ├── libvlc.so / libvlc.dylib / libvlc.dll
        └── libvlccore.so / libvlccore.dylib / libvlccore.dll
```

## GitHub Actions Workflows

### 1. Fetch Artifacts Workflow (`.github/workflows/fetch-artifacts.yml`)

Downloads official VideoLAN nightly builds for all platforms.

**Triggers:**
- Manual: `workflow_dispatch` with OS/arch selection
- Scheduled: Daily at 02:00 UTC

**Usage:**
1. Go to Actions → "Fetch LibVLC Prebuilt Artifacts"
2. Click "Run workflow"
3. Select target OSes (comma-separated) or leave blank for all
4. Optionally enable "Create Release" to publish to GitHub Releases

**Artifacts produced:**
- `libvlc-<os>-<arch>-prebuilt.zip` - Packaged headers + libraries
- Individual artifacts for each platform/arch combination

### 2. Build from Source Workflow (`.github/workflows/build-from-source.yml`)

Compiles LibVLC from source using native toolchains on each platform.

**Triggers:**
- Manual: `workflow_dispatch` with branch/tag parameter

**Usage:**
1. Go to Actions → "Build LibVLC from Source"
2. Click "Run workflow"
3. Enter VLC branch/tag (e.g., `master`, `3.0`, `4.0.0`)
4. Select target OSes or leave blank for all
5. Optionally enable "Create Release"

**Build Matrix:**
- **iOS/macOS**: `macos-14` runner with Xcode + Meson/Ninja
- **Android**: `ubuntu-latest` with Android NDK r27b + Meson
- **Linux**: `ubuntu-latest` with GCC/Clang cross-compilers + Meson
- **Windows**: `windows-latest` with MSVC 2022 + Meson/Ninja

**Artifacts produced:**
- `libvlc-<os>-<arch>-built.zip` - Packaged headers + libraries
- Individual artifacts for each platform/arch combination

## Local Development Requirements

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update && sudo apt-get install -y \
  build-essential meson ninja-build pkg-config \
  gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
  gcc-i686-linux-gnu g++-i686-linux-gnu
```

### macOS
```bash
brew install meson ninja pkg-config
# Xcode Command Line Tools required
xcode-select --install
```

### Windows
```powershell
# Using Chocolatey
choco install meson ninja pkg-config -y
# Visual Studio 2022 with C++ workload required
```

### Android (for local builds)
- Android NDK r27b+
- Set `ANDROID_NDK_HOME` environment variable

## Command Reference

```bash
python tools/generate_libvlc.py --help
```

```
usage: generate_libvlc.py [-h] [--target-os {ios,android,macos,linux,windows}]
                          [--arch {arm64,armv7,x86_64,x86}]
                          [--mode {fetch,build}] [--output-dir OUTPUT_DIR]
                          [--source-url SOURCE_URL] [--branch BRANCH]
                          [--package] [--verbose]

Universal LibVLC Binary Generator

options:
  -h, --help            show this help message and exit
  --target-os           Target OS (default: auto-detect)
  --arch                Target architecture (default: auto-detect)
  --mode                Operation mode: fetch prebuilt or build from source (default: fetch)
  --output-dir          Output directory (default: ./dist)
  --source-url          VLC source repository URL (default: https://code.videolan.org/videolan/vlc.git)
  --branch              Git branch/tag to build (default: master)
  --package             Create zip package of output
  --verbose             Enable verbose output
```

## Examples

### Generate Android ARM64 for mobile app development
```bash
python tools/generate_libvlc.py --mode fetch --target-os android --arch arm64 --package
# Output: dist/android-arm64/ + dist/libvlc-android-arm64-prebuilt.zip
```

### Generate iOS ARM64 for iOS app
```bash
python tools/generate_libvlc.py --mode fetch --target-os ios --arch arm64 --package
# Output: dist/ios-arm64/ + dist/libvlc-ios-arm64-prebuilt.zip
```

### Generate Windows x86_64 for desktop app
```bash
python tools/generate_libvlc.py --mode fetch --target-os windows --arch x86_64 --package
# Output: dist/windows-x86_64/ + dist/libvlc-windows-x86_64-prebuilt.zip
```

### Build latest VLC 4.0 from source for Linux
```bash
python tools/generate_libvlc.py --mode build --target-os linux --arch x86_64 --branch 4.0 --package
```

### Cross-compile Linux ARM64 from x86_64 host
```bash
python tools/generate_libvlc.py --mode build --target-os linux --arch arm64
```

## Integrating in Your Project

### CMake (C/C++)
```cmake
# Find LibVLC
find_path(VLC_INCLUDE_DIR vlc/vlc.h PATHS ${CMAKE_SOURCE_DIR}/libvlc-android-arm64/include)
find_library(VLC_LIBRARY NAMES vlc PATHS ${CMAKE_SOURCE_DIR}/libvlc-android-arm64/lib)
find_library(VLCCORE_LIBRARY NAMES vlccore PATHS ${CMAKE_SOURCE_DIR}/libvlc-android-arm64/lib)

target_include_directories(your_target PRIVATE ${VLC_INCLUDE_DIR})
target_link_libraries(your_target PRIVATE ${VLC_LIBRARY} ${VLCCORE_LIBRARY})
```

### Android (Gradle)
```gradle
// Copy dist/android-arm64/lib/*.so to src/main/jniLibs/arm64-v8a/
// Copy dist/android-arm64/include/vlc/ to src/main/cpp/include/vlc/
```

### iOS/macOS (Xcode)
- Add `dist/ios-arm64/include` to Header Search Paths
- Add `dist/ios-arm64/lib` to Library Search Paths
- Link `libvlc.a`, `libvlccore.a` and required system frameworks

## License

This project (build tools, scripts, workflows) is licensed under the **MIT License**.

**Important:** LibVLC binaries generated by this tool are licensed under **GPLv2+** (GNU General Public License version 2 or later). When distributing LibVLC binaries, you must comply with GPLv2+ terms including providing source code access.

See [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test across platforms
5. Submit a Pull Request

## Troubleshooting

### Fetch fails with 404
Nightly builds may not exist for all arch/OS combinations. Try a different architecture or use `--mode build`.

### Build fails on macOS/iOS
Ensure Xcode Command Line Tools are installed and `xcode-select -p` points to a valid SDK.

### Build fails on Windows
Ensure Visual Studio 2022 with "Desktop development with C++" workload is installed.

### Android build fails
Verify `ANDROID_NDK_HOME` is set and NDK version is r27b+.

## Links

- [VLC Source Repository](https://code.videolan.org/videolan/vlc.git)
- [VideoLAN Nightly Artifacts](https://artifacts.videolan.org/vlc/nightly)
- [LibVLC Documentation](https://wiki.videolan.org/LibVLC/)
- [GPLv2 License](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)