# CLI Reference

Complete command-line interface documentation for `tools/generate_libvlc.py`.

## Usage

```bash
python tools/generate_libvlc.py [OPTIONS]
```

## Options

### Target Selection

<!-- markdownlint-disable MD013 MD060 -->
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--target-os` | choice | auto-detect | Target OS: `ios`, `android`, `macos`, `linux`, `windows`, `freebsd` |
| `--arch` | choice | auto-detect | Target architecture: `arm64`, `armv7`, `x86_64`, `x86` |
<!-- markdownlint-enable MD013 MD060 -->

### Operation Mode

<!-- markdownlint-disable MD013 MD060 -->
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--mode` | choice | `fetch` | Operation mode: `fetch` (prebuilt) or `build` (from source) |
<!-- markdownlint-enable MD013 MD060 -->

### Output Configuration

<!-- markdownlint-disable MD013 MD060 -->
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output-dir` | Path | `./dist` | Output directory for binaries |
| `--package` | flag | `false` | Create zip package of output |
<!-- markdownlint-enable MD013 MD060 -->

### Build Configuration (when `--mode build`)

<!-- markdownlint-disable MD013 MD060 -->
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--source-url` | string | `https://code.videolan.org/videolan/vlc.git` | VLC source repository URL |
| `--branch` | string | `master` | Git branch/tag to build |
| `--compiler` | choice | `gcc` | Compiler: `gcc`, `clang`, `msvc`, `clang-cl` |
<!-- markdownlint-enable MD013 MD060 -->

### General

<!-- markdownlint-disable MD013 MD060 -->
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--verbose`, `-v` | flag | `false` | Enable verbose output |
| `--help`, `-h` | flag | - | Show help message and exit |
<!-- markdownlint-enable MD013 MD060 -->

## Examples

### Fetch Prebuilt Binaries

```bash
# Auto-detect and fetch for current platform
python tools/generate_libvlc.py --mode fetch

# Fetch Android arm64
python tools/generate_libvlc.py --mode fetch --target-os android --arch arm64

# Fetch iOS arm64
python tools/generate_libvlc.py --mode fetch --target-os ios --arch arm64

# Fetch Windows x86_64
python tools/generate_libvlc.py --mode fetch --target-os windows --arch x86_64

# Fetch with package creation
python tools/generate_libvlc.py --mode fetch --target-os linux --arch x86_64 --package
```

### Build from Source

```bash
# Build for current platform
python tools/generate_libvlc.py --mode build \
  --target-os linux --arch x86_64

# Build specific version
python tools/generate_libvlc.py --mode build \
  --target-os macos --arch arm64 --branch 3.0.20

# Build with custom source
python tools/generate_libvlc.py --mode build \
  --target-os windows --arch x86_64 \
  --source-url https://code.videolan.org/videolan/vlc.git

# Build with specific compiler
python tools/generate_libvlc.py --mode build \
  --target-os linux --arch x86_64 --compiler clang
```

## Exit Codes

<!-- markdownlint-disable MD013 MD060 -->
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operation failed (invalid args, download error, build error, etc.) |
<!-- markdownlint-enable MD013 MD060 -->

## Environment Variables

<!-- markdownlint-disable MD013 MD060 -->
| Variable | Description |
|----------|-------------|
| `ANDROID_NDK_HOME` | Path to Android NDK (required for Android builds) |
| `VLC_REPO_URL` | Override default VLC repository URL |
<!-- markdownlint-enable MD013 MD060 -->

## Output Structure

```text
<output-dir>/
└── <target-os>-<arch>[-<compiler>]/
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

For multi-compiler builds (Linux/Windows), the compiler suffix is added to the
output directory name.
