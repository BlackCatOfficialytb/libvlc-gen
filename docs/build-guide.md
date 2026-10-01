# Build Guide

Platform-specific build requirements and troubleshooting for building LibVLC from source.

## Prerequisites by Platform

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update && sudo apt-get install -y \
  build-essential meson ninja-build pkg-config \
  gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
  gcc-i686-linux-gnu g++-i686-linux-gnu
```

**Cross-compilation:**
- `arm64`: `aarch64-linux-gnu` toolchain
- `x86`: `i686-linux-gnu` toolchain

### macOS

```bash
brew install meson ninja pkg-config
# Xcode Command Line Tools required
xcode-select --install
```

**iOS builds require:**
- Xcode with iOS SDK
- `xcodebuild -showsdks` to verify available SDKs

### Windows

```powershell
# Using Chocolatey
choco install meson ninja pkg-config -y
# Visual Studio 2022 with C++ workload required
```

**Visual Studio 2022** (Community/Professional/Enterprise) with:
- Desktop development with C++
- Windows 10/11 SDK

### Android

- Android NDK r27b+
- Set `ANDROID_NDK_HOME` environment variable

```bash
export ANDROID_NDK_HOME=/path/to/android-ndk-r27b
```

### FreeBSD

```bash
pkg install meson ninja pkgconf git
```

## Build Process Overview

The build process uses Meson/Ninja:

1. Clone VLC source (shallow clone by default)
2. Generate cross-compilation file for target platform
3. Run `meson setup` with cross-file
4. Run `ninja` to compile
5. Extract artifacts (libraries + headers)
6. Organize into standard output structure

## Platform-Specific Details

### iOS / macOS

- Uses Xcode's clang toolchain
- Cross-file specifies SDK path and architecture
- Supports both device (arm64) and simulator (x86_64/arm64)
- Bitcode disabled by default

### Android

- Uses Android NDK toolchain
- Cross-file generated with NDK paths
- Supports all 4 architectures: arm64, armv7, x86_64, x86
- Requires `ANDROID_NDK_HOME` set

### Linux

- Native builds use system GCC/Clang
- Cross-compilation uses installed cross-toolchains
- Static linking preferred for portability

### Windows

- Uses MSVC (Visual Studio) via `vcvarsall.bat`
- Supports `msvc` and `clang-cl` compilers
- Automatically detects VS installation paths
- DLL + import library (.lib) produced

### FreeBSD

- Native builds only (no cross-compilation tested)
- Uses system clang
- Similar to Linux but with FreeBSD-specific paths

## Troubleshooting

### Common Issues

**Meson not found:**
```bash
pip install meson ninja
# or use system package manager
```

**vcvarsall.bat not found (Windows):**
- Ensure Visual Studio 2022 is installed with C++ workload
- Script checks Enterprise, Community, and (x86) paths

**Android NDK not found:**
```bash
export ANDROID_NDK_HOME=/path/to/ndk
# Verify: $ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake exists
```

**iOS SDK not found:**
```bash
xcodebuild -showsdks
# Ensure iOS SDK is listed
```

**Cross-compilation fails (Linux):**
- Install cross-toolchains: `gcc-aarch64-linux-gnu`, `gcc-i686-linux-gnu`
- Verify: `aarch64-linux-gnu-gcc --version`

### Build Failures

**Out of memory during ninja:**
```bash
# Limit parallel jobs
ninja -C build_dir -j4
```

**Missing dependencies:**
- Check `meson.log` in build directory
- Install missing `-dev` packages

**Git clone fails:**
- Check network connectivity
- Try `--branch` with specific tag (e.g., `3.0.20`)

## Customization

### Custom Compiler Flags

Set environment variables before building:
```bash
export CFLAGS="-O2 -pipe"
export CXXFLAGS="-O2 -pipe"
python tools/generate_libvlc.py --mode build ...
```

### Custom Meson Options

Edit the `meson_args` list in `build_<platform>()` functions in `generate_libvlc.py`.

### Shallow Clone Depth

Default is `--depth 1`. For full history:
```python
# In generate_libvlc.py, modify:
result = run_cmd(["git", "clone", "--branch", branch, source_url, str(src_dir)])
```

## Verification

After build, verify output:
```bash
# Check libraries exist
ls -la dist/<target>-<arch>/lib/

# Check headers exist
ls -la dist/<target>-<arch>/include/vlc/

# Test library (Linux/macOS)
file dist/linux-x86_64/lib/libvlc.so
```

## Performance Tips

- Use `--depth 1` for faster clones (default)
- Increase ninja jobs: `-j$(nproc)` (default)
- Use ccache: `export CC="ccache gcc"` (Linux/macOS)
- Build on SSD for faster I/O