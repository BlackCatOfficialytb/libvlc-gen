# libvlc-gen

> **Automated extraction and building of static LibVLC binaries for iOS/tvOS**

`libvlc-gen` provides two ways to obtain production-ready static LibVLC libraries (`libvlc.a`, `libvlccore.a`) and C headers for embedding in jailbreak tweaks, Theos projects, and embedded iOS applications.

---

## 🎯 Features

| Tool | Description | Platform |
|------|-------------|----------|
| **Python CLI** (`tools/generate_libvlc.py`) | Downloads pre-built static frameworks from VideoLAN releases | Linux, macOS, Windows |
| **GitHub Action: Artifacts** (`.github/workflows/generate-artifacts.yml`) | CI/CD pipeline to fetch & package official binaries | Ubuntu, macOS |
| **GitHub Action: From Source** (`.github/workflows/build-from-source.yml`) | Compiles LibVLC from VideoLAN source on macOS runners | macOS (Apple Silicon) |

---

## 📦 Quickstart

### Local Generation (Python)

```bash
# Clone the repository
git clone https://github.com/your-org/libvlc-gen.git
cd libvlc-gen

# Generate for iOS arm64 (default)
python tools/generate_libvlc.py

# Generate for iOS arm64e
python tools/generate_libvlc.py --arch arm64e

# Generate for tvOS arm64
python tools/generate_libvlc.py --target-os tvos --arch arm64

# Custom output directory
python tools/generate_libvlc.py --output-dir ./my_dist
```

**Output structure:**
```
dist/
├── include/
│   └── vlc/
│       ├── vlc.h
│       ├── vlc_common.h
│       ├── vlc_version.h
│       └── ... (all public headers)
└── lib/
    ├── libvlc.a
    └── libvlccore.a
```

### GitHub Actions (Automated)

#### 1. Generate Artifacts Workflow
- **Triggers**: Manual (`workflow_dispatch`), push to `main`, weekly schedule
- **Runner**: `ubuntu-latest` (iOS) or `macos-latest` (tvOS)
- **Artifacts**: `libvlc-ios-arm64.zip`, `libvlc-ios-arm64e.zip`, `libvlc-tvos-arm64.zip`

```bash
# Trigger manually via GitHub CLI
gh workflow run generate-artifacts.yml -f target_os=ios -f arch=arm64

# Or via GitHub UI: Actions → Generate LibVLC Artifacts → Run workflow
```

#### 2. Build from Source Workflow
- **Trigger**: Manual only (`workflow_dispatch`)
- **Runner**: `macos-14` (Apple Silicon with Xcode)
- **Builds**: Full LibVLC from `videolan/vlc` source

```bash
# Trigger with specific version
gh workflow run build-from-source.yml -f vlc_version=3.0.20 -f arch=arm64

# Build debug version
gh workflow run build-from-source.yml -f vlc_version=master -f arch=arm64 -f enable_debug=true
```

---

## 🔧 Consuming in Your Project

### Theos Makefile (iOS Jailbreak Tweaks)

```makefile
# Theos makefile for a tweak using libvlc
TWEAK_NAME = MyVLCTweak
MyVLCTweak_FILES = Tweak.xm
MyVLCTweak_CFLAGS = -I$(THEOS_PROJECT_DIR)/libvlc-gen/dist/include
MyVLCTweak_LDFLAGS = -L$(THEOS_PROJECT_DIR)/libvlc-gen/dist/lib -lvlc -lvlccore
MyVLCTweak_FRAMEWORKS = AudioToolbox VideoToolbox CoreMedia CoreVideo AVFoundation

include $(THEOS_MAKE_PATH)/tweak.mk
```

### CMake (Cross-platform)

```cmake
cmake_minimum_required(VERSION 3.16)
project(MyVLCApp LANGUAGES C CXX)

# Path to libvlc-gen dist directory
set(LIBVLC_DIST "${CMAKE_SOURCE_DIR}/libvlc-gen/dist")

include_directories(${LIBVLC_DIST}/include)
link_directories(${LIBVLC_DIST}/lib)

add_executable(my_app main.c)
target_link_libraries(my_app vlc vlccore)

# iOS specific frameworks
if(CMAKE_SYSTEM_NAME STREQUAL "Darwin" AND CMAKE_OSX_SYSROOT MATCHES "iphone")
    find_library(AUDIOTOOLBOX AudioToolbox)
    find_library(VIDEOTOOLBOX VideoToolbox)
    find_library(COREMEDIA CoreMedia)
    find_library(COREVIDEO CoreVideo)
    find_library(AVFOUNDATION AVFoundation)
    target_link_libraries(my_app ${AUDIOTOOLBOX} ${VIDEOTOOLBOX} ${COREMEDIA} ${COREVIDEO} ${AVFOUNDATION})
endif()
```

### Xcode Project

1. **Header Search Paths**: Add `$(SRCROOT)/libvlc-gen/dist/include`
2. **Library Search Paths**: Add `$(SRCROOT)/libvlc-gen/dist/lib`
3. **Other Linker Flags**: `-lvlc -lvlccore`
4. **Frameworks**: Add `AudioToolbox.framework`, `VideoToolbox.framework`, `CoreMedia.framework`, `CoreVideo.framework`, `AVFoundation.framework`

### Plain Makefile

```makefile
CC = clang
CFLAGS = -Ilibvlc-gen/dist/include -arch arm64 -isysroot $(SDKROOT)
LDFLAGS = -Llibvlc-gen/dist/lib -lvlc -lvlccore \
          -framework AudioToolbox -framework VideoToolbox \
          -framework CoreMedia -framework CoreVideo -framework AVFoundation

TARGET = my_vlc_app
SRCS = main.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGET)
```

---

## 📋 Requirements

| Component | Version |
|-----------|---------|
| Python | 3.7+ (stdlib only) |
| GitHub Actions | Ubuntu-latest / macOS-14 |
| Xcode (source build) | 15+ (included in macOS-14) |
| iOS Deployment Target | 12.0+ |

---

## 🏗️ Architecture

```
libvlc-gen/
├── .github/workflows/
│   ├── generate-artifacts.yml   # Downloads pre-built frameworks
│   └── build-from-source.yml    # Compiles from VLC source
├── tools/
│   └── generate_libvlc.py       # Standalone Python generator
├── dist/                        # Output (gitignored)
│   ├── include/vlc/             # C headers
│   └── lib/                     # Static libraries (.a)
├── .gitignore
├── requirements.txt             # Empty (stdlib only)
├── LICENSE                      # MIT
└── README.md
```

### generate-artifacts.yml Flow
```
Checkout → Setup Python → Run generate_libvlc.py → Zip dist/ → Upload Artifact → (Optional) Create Release
```

### build-from-source.yml Flow
```
Checkout VLC source → Install deps (brew) → Run extras/package/ios/build.sh -a arm64
    → Extract framework → Copy headers/libs to dist/ → Zip → Upload Artifact
```

---

## 🔍 Verification

After generation, verify the output:

```bash
# Check library sizes (should be ~20-50 MB each)
ls -lh dist/lib/

# Verify headers
ls dist/include/vlc/ | head -20

# Test linking (macOS)
clang -Ilibvlc-gen/dist/include -Llibvlc-gen/dist/lib test.c -lvlc -lvlccore
```

Expected library sizes (approximate):
- `libvlc.a`: 25-45 MB
- `libvlccore.a`: 15-30 MB

---

## 📝 Version Matrix

| LibVLC Version | iOS arm64 | iOS arm64e | tvOS arm64 | Source Build |
|----------------|-----------|------------|------------|--------------|
| 3.6.x          | ✅        | ✅         | ✅         | ✅           |
| 3.5.x          | ✅        | ❌         | ✅         | ✅           |
| 3.0.x (LTS)    | ✅        | ❌         | ✅         | ✅           |
| master (dev)   | ❌        | ❌         | ❌         | ✅           |

> **Note**: Pre-built binaries are fetched from VideoLAN's official GitHub releases. Source builds compile whatever tag/branch you specify.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test locally with `python tools/generate_libvlc.py`
4. Submit a PR

### Adding New Versions
Update `VLC_RELEASES` dictionary in `tools/generate_libvlc.py` with new URLs and SHA256 hashes.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

LibVLC itself is licensed under **LGPL v2.1+**. This project only packages and distributes the binaries; compliance with LGPL is the responsibility of the end user.

---

## 🙏 Acknowledgments

- [VideoLAN](https://www.videolan.org/) for LibVLC
- [VLC-iOS](https://github.com/videolan/vlc-ios) for MobileVLCKit frameworks
- [CocoaPods](https://cocoapods.org/) for binary distribution

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/libvlc-gen/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/libvlc-gen/discussions)
- **Documentation**: This README + inline code comments