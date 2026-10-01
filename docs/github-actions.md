# GitHub Actions Workflows

CI/CD workflow configuration and usage for
automated LibVLC builds.

## Workflows

### 1. Fetch Artifacts Workflow (`.github/workflows/fetch-artifacts.yml`)

Downloads official VideoLAN nightly builds for all platforms.

#### Fetch Triggers

- **Manual**: `workflow_dispatch` with OS/arch selection
- **Scheduled**: Daily at 02:00 UTC

#### Fetch Usage

1. Go to **Actions** → "Fetch LibVLC Prebuilt Artifacts"
2. Click **"Run workflow"**
3. Select target OSes (comma-separated) or leave blank for all
4. Optionally enable **"Create Release"** to publish to GitHub Releases

#### Fetch Inputs

<!-- markdownlint-disable MD013 MD060 -->
| Input          | Type    | Default | Description                              |
|----------------|---------|---------|------------------------------------------|
| `target_oses`  | string  | `all`   | Comma-separated list: `ios`, `android`,  |
|                |         |         | `macos`, `linux`, `windows`              |
| `create_release` | boolean | `false` | Create GitHub Release with artifacts     |
<!-- markdownlint-enable MD013 MD060 -->

#### Fetch Artifacts Produced

- `libvlc-<os>-<arch>-prebuilt.zip` - Packaged headers + libraries
- Individual artifacts for each platform/arch combination

### 2. Build from Source Workflow (`.github/workflows/build-from-source.yml`)

Compiles LibVLC from source using native toolchains on each platform.

#### Build Triggers

- **Manual**: `workflow_dispatch` with branch/tag parameter

#### Build Usage

1. Go to **Actions** → "Build LibVLC from Source"
2. Click **"Run workflow"**
3. Enter VLC branch/tag (e.g., `master`, `3.0`, `4.0.0`)
4. Select target OSes or leave blank for all
5. Optionally enable **"Create Release"**

#### Build Inputs

<!-- markdownlint-disable MD013 MD060 -->
| Input           | Type    | Default | Description                          |
|-----------------|---------|---------|--------------------------------------|
| `vlc_branch`    | string  | `master` | VLC branch/tag to build              |
| `target_oses`   | string  | `all`   | Comma-separated list of target OSes  |
| `create_release` | boolean | `false` | Create GitHub Release with artifacts |
<!-- markdownlint-enable MD013 MD060 -->

#### Build Matrix

<!-- markdownlint-disable MD013 MD060 -->
| Platform  | Runner         | Toolchain                          |
|-----------|----------------|------------------------------------|
| iOS/macOS | `macos-14`     | Xcode + Meson/Ninja                |
| Android   | `ubuntu-latest` | Android NDK r27b + Meson           |
| Linux     | `ubuntu-latest` | GCC/Clang cross-compilers + Meson  |
| Windows   | `windows-latest` | MSVC 2022 + Meson/Ninja            |
| FreeBSD   | `ubuntu-latest` | Cross-compilation via qemu-user    |
<!-- markdownlint-enable MD013 MD060 -->

#### Build Artifacts Produced

- `libvlc-<os>-<arch>-built.zip` - Packaged headers + libraries
- Individual artifacts for each platform/arch combination

## Workflow Configuration

### Required Secrets

No secrets required for public VideoLAN artifacts.

For private repositories or custom artifact hosting:

- `GH_TOKEN` - GitHub token for release creation (auto-provided)

### Customization

#### Modify Build Matrix

Edit `.github/workflows/build-from-source.yml`:

```yaml
strategy:
  matrix:
    include:
      - os: linux
        arch: [x86_64, arm64, x86]
      - os: windows
        arch: [x86_64, arm64, x86]
      # Add/remove platforms as needed
```

#### Custom VLC Source

Fork VLC and update `VLC_REPO_URL` in workflow or pass via input.

#### Additional Build Options

Modify `meson_args` in the workflow steps or in `tools/generate_libvlc.py`.

## Artifact Retention

- Default: 90 days (GitHub default)
- Configure in workflow: `retention-days: 30`

## Release Creation

When `create_release: true`:

1. Workflow creates a draft release
2. Title: `LibVLC <branch> - <date>`
3. Assets: All platform artifacts uploaded
4. Publish manually or auto-publish with additional step

## Local Testing

Test workflows locally with `act`:

```bash
# Install act
brew install act  # macOS
# or download from https://github.com/nektos/act

# Run fetch workflow
act workflow_dispatch -W .github/workflows/fetch-artifacts.yml

# Run build workflow
act workflow_dispatch -W .github/workflows/build-from-source.yml \
  -i vlc_branch=3.0.20
```

## Troubleshooting

### Build Timeouts

- Default timeout: 6 hours
- Increase in workflow: `timeout-minutes: 480`

### Out of Memory (Linux/Android)

```yaml
# Add to job:
env:
  NINJA_JOBS: 4  # Limit parallel jobs
```

### macOS Runner Issues

- Use `macos-14` (latest stable)
- Xcode version: `xcodebuild -version` in workflow

### Windows MSVC Detection

Workflow auto-detects VS 2022 Enterprise/Community paths.
If custom path needed, set `VCVARS_PATH` environment variable.

### Android NDK Version

Update in workflow:

```yaml
- name: Setup Android NDK
  uses: android-actions/setup-android@v2
  with:
    ndk-version: r27b
```

## Monitoring

- Check **Actions** tab for run history
- Enable notifications for failed runs
- Artifacts available for download from run summary

## Cost Optimization

- Use `if:` conditions to skip unnecessary matrix entries
- Self-hosted runners for frequent builds
- Schedule fetches during off-peak hours
