# Architecture

Internal architecture and extension points for
libvlc-gen.

## Overview

`libvlc-gen` is a single-file Python CLI
(`tools/generate_libvlc.py`) with a modular internal structure:

<!-- markdownlint-disable MD013 -->
```txt
generate_libvlc.py
├── Constants & Configuration
├── Logger (colorized output)
├── Platform Detection
├── Core Utilities
│   ├── run_cmd() - subprocess wrapper
│   ├── download_file() - HTTP download with progress
│   ├── extract_archive() - zip/tar extraction
│   ├── find_vlc_artifacts() - locate libs/headers
│   ├── organize_output() - standardize output layout
│   └── create_package() - zip packaging
├── Fetch Functions (per-platform)
│   ├── fetch_ios_prebuilt()
│   ├── fetch_android_prebuilt()
│   ├── fetch_macos_prebuilt()
│   ├── fetch_linux_prebuilt()
│   ├── fetch_windows_prebuilt()
│   └── fetch_freebsd_prebuilt()
├── Build Functions (per-platform)
│   ├── build_ios()
│   ├── build_android()
│   ├── build_macos()
│   ├── build_linux()
│   ├── build_windows()
│   └── build_freebsd()
├── High-Level Orchestration
│   ├── fetch_prebuilt()
│   └── build_from_source()
└── CLI Entry Point (main())
│   ├── organize_output() - standardize output layout
│   └── create_package() - zip packaging
├── Fetch Functions (per-platform)
│   ├── fetch_ios_prebuilt()
│   ├── fetch_android_prebuilt()
│   ├── fetch_macos_prebuilt()
│   ├── fetch_linux_prebuilt()
│   ├── fetch_windows_prebuilt()
│   └── fetch_freebsd_prebuilt()
├── Build Functions (per-platform)
│   ├── build_ios()
│   ├── build_android()
│   ├── build_macos()
│   ├── build_linux()
│   ├── build_windows()
│   └── build_freebsd()
├── High-Level Orchestration
│   ├── fetch_prebuilt()
│   └── build_from_source()
└── CLI Entry Point (main())
<!-- markdownlint-enable MD013 -->
```

## Key Design Decisions

### Single-File CLI

- No external dependencies beyond `requirements.txt`
- Easy to copy/deploy to CI runners
- Self-contained for GitHub Actions

### Platform Abstraction

Each platform has:

- `fetch_<os>_prebuilt()` - downloads from VideoLAN artifacts
- `build_<os>()` - compiles from source via Meson/Ninja

Common interface:

```python
def fetch_<os>_prebuilt(arch: str, output_dir: Path) -> bool
def build_<os>(src_dir: Path, arch: str, output_dir: Path) -> bool
```

### Cross-Compilation via Meson

All builds use Meson cross-files:

- Generated dynamically per platform/arch
- Specifies compiler, linker, flags, SDK paths
- Single build system for all targets

### Artifact Organization

Standardized output layout regardless of source:

```txt
<output>/<os>-<arch>[-<compiler>]/
├── include/vlc/*.h
└── lib/libvlc.*, libvlccore.*
```

## Extension Points

### Adding a New Platform

1. Add to `TARGET_OS_CHOICES` and `ARCH_CHOICES`
2. Add entry to `OS_ARCH_MAP`
3. Implement `fetch_<os>_prebuilt(arch, output_dir)`
4. Implement `build_<os>(src_dir, arch, output_dir)`
5. Add case in `fetch_prebuilt()` and `build_from_source()`
6. Add GitHub Actions matrix entry

### Adding a New Architecture

1. Add to `ARCH_CHOICES`
2. Update `OS_ARCH_MAP` for relevant OSes
3. Update `HOST_ARCH_MAP` for auto-detection
4. Add cross-file generation in build function
5. Test fetch/build

### Custom Artifact Sources

Modify `VLC_NIGHTLY_BASE`, `VLC_STABLE_BASE`, `VLC_RELEASES_API` constants.
Implement custom fetch logic in platform fetch function.

### Custom Build Options

Modify `meson_args` in platform build functions.
Common options:

- `-Dbuildtype=release|debug`
- `-Dvulkan=enabled|disabled`
- `-Dlua=enabled|disabled`
- `-Dffmpeg=enabled|disabled`

## Data Flow

```text
User Input (CLI args)
       │
       ▼
validate_os_arch() ──► Invalid? ──► Error exit
       │
       ▼
fetch_prebuilt() OR build_from_source()
       │
       ├── fetch_<os>_prebuilt() ──► download_file() ──► extract_archive()
       │       │
       │       ▼
       │   find_vlc_artifacts() ──► organize_output() ──► create_package()
       │
       └── build_from_source()
               │
               ▼
           git clone (shallow)
               │
               ▼
           build_<os>() ──► meson setup + ninja
               │
               ▼
           find_vlc_artifacts() ──► organize_output() ──► create_package()
       │
       ▼
print_summary() ──► Success exit
```

## Error Handling

- All functions return `bool` (success/failure)
- Errors logged via `Logger.error()`
- Exceptions caught and converted to `False` return
- Non-zero exit code on any failure

## Logging

`Logger` class with levels:

- `info()` - General progress (cyan)
- `success()` - Completed operations (green)
- `warning()` - Non-fatal issues (yellow)
- `error()` - Failures (red)
- `debug()` - Verbose details (magenta)

Color output via `colorama` (auto-disabled on non-TTY).

## Testing

No formal test suite. Manual verification:

```bash
# Test fetch
python tools/generate_libvlc.py --mode fetch --target-os linux --arch x86_64

# Test build (requires toolchain)
python tools/generate_libvlc.py --mode build --target-os linux --arch x86_64

# Verify output
ls -la dist/linux-x86_64/
```

## Performance Considerations

- Shallow git clone (`--depth 1`) by default
- Parallel ninja jobs (`-j$(nproc)`)
- Streaming downloads (no full buffer)
- Chunked archive extraction

## Security

- No arbitrary code execution
- HTTPS for all downloads
- No credential handling
- Input validation on OS/arch combinations

## Future Improvements

- [ ] Parallel platform builds
- [ ] Cache management (ccache, sccache)
- [ ] Incremental builds
- [ ] Binary compatibility checks
- [ ] Automated version detection
- [ ] Plugin for custom VLC modules
