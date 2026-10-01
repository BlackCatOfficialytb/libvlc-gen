# libvlc-gen Documentation

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
| FreeBSD | arm64, x86_64 | ✗ | ✓ (FreeBSD runner) |

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

## Documentation

- [CLI Reference](cli-reference.md) - Complete command-line interface documentation
- [Build Guide](build-guide.md) - Platform-specific build requirements and troubleshooting
- [GitHub Actions](github-actions.md) - CI/CD workflow configuration and usage
- [Architecture](architecture.md) - Internal architecture and extension points

## License

MIT License - See [LICENSE](../LICENSE) for details.