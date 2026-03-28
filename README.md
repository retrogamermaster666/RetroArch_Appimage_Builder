# RetroArch AppImage Builder for Raspberry Pi

This tool creates a **fully portable, self-contained** AppImage of RetroArch specifically optimized for the Raspberry Pi 5 (aarch64).

## Project Structure

- `main_builder.py`: The main script that runs the build process.
- `config/config.json`: Where you specify the RetroArch version and cores to build.
- `src/AppRun`: The startup script bundled inside the AppImage.
- `dist/`: Where the final, versioned AppImage will be placed.
- `build_artifacts/`: Temporary folder for intermediate build files.

## How to use

### 1. Preparation
Open a terminal and ensure you are located **inside the `RetroArch_Appimage_Builder` folder**. The script must be run from this directory to correctly find its configuration and source files.

```bash
cd ~/path/to/RetroArch_Appimage_Builder
```

### 2. Configure the Build
Edit `config/config.json` to customize your AppImage:

#### **Change RetroArch Version**
To build a specific version of RetroArch:
1. Locate the `"retroarch"` section.
2. Update the `"version"` field with the desired Git tag or branch name (e.g., `"v1.19.1"`, `"v1.21.0"`, or `"master"` for the latest).

#### **Configure Cores**
- Add core names (e.g., `mgba`, `snes9x2010`) to the `"core_to_build"` list.
- A list of all available cores for Raspberry Pi 5 is provided in the `"available_cores"` section of the JSON file for reference.

### Currently Configured Cores
The builder is currently configured to build a comprehensive set of **111 cores**, including:

- **Nintendo:** `bnes`, `snes9x`, `mesen`, `mgba`, `gambatte`, `melonds`, `mupen64plus_next` (use with caution), `pokemini`, `vb`
- **Sega:** `genesis_plus_gx`, `picodrive`, `flycast` (if available), `saturn`
- **Sony PlayStation:** `swanstation`, `pcsx_rearmed`, `pcsx1`, `mednafen_psx`, `mednafen_psx_hw`
- **Arcade:** `mame`, `mame2003_plus`, `fbneo`, `neocd`
- **Computers:** `dosbox_pure`, `scummvm`, `puae`, `vice_x64sc`, `fuse`, `hatari`
- **Others:** `ppsspp`, `dolphin`, `opera`, `prosystem`, `stella`, `2048`, and many more.

> [!IMPORTANT]
> **Nintendo 64 (N64) Support:** N64 cores are currently not recommended for this ARM-based AppImage build due to compatibility issues. For the best N64 experience on Linux/ARM, it is highly recommended to install [**RMG (Rosalie's Mupen GUI)** via Flathub](https://flathub.org/en/apps/com.github.Rosalie241.RMG), which works exceptionally well.

### 3. Run the Builder
Execute the main script:
```bash
python main_builder.py
```
*Note: This process is extremely comprehensive and will take approximately **10 to 12 hours** on a Raspberry Pi 5 with the current configuration of 111 cores, as it compiles RetroArch, builds each core individually, and bundles all assets (icons, databases, joypad configs, shaders, filters, and cheats).*

### 4. Locate and Use the AppImage
Once finished, look in the `dist/` directory. Your AppImage will be inside a versioned subfolder:
`dist/RetroArch-{version}/`

Inside this folder, you will find:
- **`RetroArch-aarch64.AppImage`**: The main executable.
- **`build_info.txt`**: A detailed report of the build environment, including OS version, library versions (Glibc, SDL2), and hardware specs used during compilation.

#### To run it:
1. Navigate to the versioned folder: `cd dist/RetroArch-{version}/`
2. Make the AppImage executable: `chmod +x RetroArch-aarch64.AppImage`
3. Run it: Double-click the file in your file manager or run `./RetroArch-aarch64.AppImage` from the terminal.

*Note: On first run, the AppImage will automatically create a desktop and menu shortcut for you.*

## Build Information and Compatibility
The `build_info.txt` file is included to help you and other users verify compatibility. It contains:
- **Glibc version**: This is the most critical factor for AppImage compatibility. The destination system must have a Glibc version equal to or newer than the one shown in this file.
- **Hardware Details**: Information about the CPU and GPU used during the build.
- **Included Cores**: A complete list of all Libretro cores bundled inside the AppImage.

## Portability Details
When you run the AppImage for the first time:
- It creates a folder named `retroarch_portable_config` **next to the AppImage file**.
- It **extracts and copies** all bundled resources (cores, shaders, assets, etc.) into this portable folder.
- **Everything stays in this folder.** You can move the AppImage and the `retroarch_portable_config` folder together to any other Raspberry Pi 5, and it will work perfectly without needing an internet connection or any system-wide installation.

### Advanced Dependency Bundling
Unlike standard AppImages, this builder includes a **recursive dependency bundler**. It automatically identifies and copies all required shared libraries (like FFmpeg/libavcodec, SDL2, and Qt) into the AppImage. This ensures that the application will launch even on a "fresh" OS install that lacks these multimedia libraries, fulfilling the goal of true portability.

## Adding New Cores
To add more cores later:
1. Update the `"core_to_build"` list in `config/config.json`.
2. Re-run `python main_builder.py`.
3. The new AppImage will include the new cores. If you use it with an existing `retroarch_portable_config` folder, the execution of the new Appimage will add new cores into your existing `retroarch_protable_config`.

