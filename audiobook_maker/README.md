# Audiobook Maker

Audiobook Maker is a small PyQt6 desktop app for turning a folder of audio or video files into one `.m4b` audiobook with chapters, metadata, and optional cover art.

It is designed for macOS packaging, but the source app is plain Python and can run anywhere PyQt6 and FFmpeg are available.

## Features

- Drag and drop an audiobook folder, or click the drop zone to browse.
- Detect one audiobook or multiple audiobook subfolders automatically.
- Sort tracks by leading order number and natural filename order.
- Edit chapter titles before export.
- Remove tracks, move selected tracks to the first or last position, and drag rows to reorder.
- Parse album and artist from folders named like `[Album][Artist]`.
- Auto-detect cover images from the audiobook folder or parent folders.
- Upload, crop, resize, and compress cover art.
- Export one `.m4b` per detected audiobook with embedded chapters and cover art.
- Choose output audio codec preset: M4A/AAC or MP3/libmp3lame.
- Choose bitrate, or keep the original bitrate with `-`.
- Switch between English and Chinese UI.
- Switch between light, dark, and system theme.

## Requirements

- Python 3.12+ recommended
- PyQt6
- PyInstaller, only for packaging
- FFmpeg and FFprobe

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install FFmpeg on macOS:

```bash
brew install ffmpeg
```

## Run From Source

```bash
python main.py
```

`app.py` is a legacy entry-point shim kept for existing launch scripts and PyInstaller specs.

## Build macOS App

```bash
./build_dmg.sh
```

The build script creates a PyInstaller app bundle, signs it ad-hoc, then tries to create a DMG. If `create-dmg` is not installed, it falls back to a zip package.

Install the optional DMG tool:

```bash
brew install create-dmg
```

## Function Tutorial

### 1. Import Audiobook Folders

Open the app, then drag a folder onto the drop zone or click the drop zone to choose a folder.

The app scans the folder recursively. Every directory that directly contains supported media files becomes one audiobook section.

Supported media inputs:

- Audio: `.m4a`, `.mp3`
- Video: `.mp4`, `.mkv`, `.mov`, `.m4v`, `.avi`, `.webm`

### 2. Prepare Folder Metadata

If a folder in the path is named like this:

```text
[Album][Artist]
```

the app uses the first part as the album and the second part as the artist.

For example:

```text
[My Book Series][Jane Author]/Volume 1/01 Opening.mp3
```

creates an audiobook section with:

- Album: `My Book Series`
- Artist: `Jane Author`
- Title: `Volume 1`

You can still edit Album, Title, and Artist in the UI before export.

### 3. Review and Edit Tracks

Each audiobook section contains a track table.

You can:

- Edit chapter titles directly in the table.
- Select rows and click `Remove Audio` to remove tracks from the export.
- Select rows and click `Move to First` or `Move to Last`.
- Drag selected rows inside the table to reorder chapters.
- Click the `#` header to reset to natural filename order.
- Click other headers to sort by title, format, size, or duration.
- Use undo/redo from the Edit menu for track and cover changes.

By default, leading track order numbers are removed from chapter titles. Toggle this with `Edit > Remove Order Number from Track Title`.

### 4. Edit Cover Art

The app looks for a cover image in the audiobook folder, then walks upward toward the imported root folder. Images with `cover` in the filename are preferred.

Supported cover inputs include:

```text
.jpg, .jpeg, .png, .webp, .bmp, .tiff, .tif, .gif, .avif, .heic, .heif
```

Click the cover thumbnail to open the cover editor, or right-click it to open the cover menu.

In the cover editor, you can:

- Crop freely or with ratio presets.
- Add a custom crop ratio.
- Swap crop orientation.
- Resize to a specific pixel size.
- Compress to a target KB size.
- Save the edited cover back to the audiobook section.
- Save a separate edited copy with `Save to...`.

Use `Edit > Cover Edit Format` to choose JPEG or PNG for edited cover outputs.

### 5. Choose Export Options

At the bottom of the window:

- `Output`: choose the destination folder.
- `Format`: choose the encoder preset.
- `Quality`: choose bitrate, or `-` to copy the original audio stream.
- `Cover`: set exported cover width, height, and max file size. `-` means keep the current value.

The final container is always `.m4b`. The `Format` option controls the audio codec used when re-encoding.

### 6. Create Audiobooks

Click `Create Audiobook` or `Create N Audiobooks`.

The app checks if output files already exist. If there are conflicts, it asks before overwriting.

During export, the progress dialog shows the current book and FFmpeg step. When complete, the app lists the saved output paths.

## Project Structure

```text
main.py              Main app entry point
app.py               Legacy entry point shim
i18n.py              English and Chinese UI strings
theme.py             Light/dark theme styling
scanner.py           Folder, track, cover, and metadata scanning
utils.py             Sorting, title cleanup, formatting helpers
workers.py           QThread workers for durations and conversion
converter.py         FFmpeg audiobook builder
ui/                  PyQt6 widgets and windows
build_dmg.sh         macOS build helper
Audiobook Maker.spec PyInstaller spec
```

## Notes

- `build/`, `dist/`, and `__pycache__/` are generated artifacts and are not required for running from source.
- FFmpeg must be available in `PATH`. The app also checks common Homebrew paths: `/usr/local/bin` and `/opt/homebrew/bin`.
- Conversion cancellation currently terminates the worker thread.

---

# 有声书制作器

有声书制作器是一个 PyQt6 桌面应用，可以把一个音频或视频文件夹转换成一个带章节、元数据和可选封面的 `.m4b` 有声书文件。

项目主要面向 macOS 打包，但源码应用是普通 Python 程序，只要系统中有 PyQt6 和 FFmpeg，就可以运行。

## 功能

- 拖入有声书文件夹，或点击拖放区域浏览选择。
- 自动识别单本有声书或多个有声书子文件夹。
- 根据开头序号和自然文件名顺序排序音轨。
- 导出前编辑章节标题。
- 删除音轨、将选中音轨移动到首位或末位、拖动行重新排序。
- 从 `[专辑][艺术家]` 格式的文件夹名解析专辑和艺术家。
- 自动从有声书文件夹或上级文件夹寻找封面。
- 上传、裁剪、调整尺寸、压缩封面。
- 为每本检测到的有声书导出一个带章节和封面的 `.m4b` 文件。
- 选择输出音频编码预设：M4A/AAC 或 MP3/libmp3lame。
- 选择比特率，或使用 `-` 保持原始码率。
- 支持英文和中文界面切换。
- 支持浅色、深色和跟随系统主题。

## 运行要求

- 推荐 Python 3.12+
- PyQt6
- PyInstaller，仅打包时需要
- FFmpeg 和 FFprobe

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

在 macOS 安装 FFmpeg：

```bash
brew install ffmpeg
```

## 从源码运行

```bash
python main.py
```

`app.py` 是旧入口的兼容层，用于保留现有启动脚本和 PyInstaller 配置的兼容性。

## 构建 macOS 应用

```bash
./build_dmg.sh
```

构建脚本会创建 PyInstaller app bundle，进行 ad-hoc 签名，然后尝试生成 DMG。如果没有安装 `create-dmg`，会回退生成 zip 包。

安装可选的 DMG 工具：

```bash
brew install create-dmg
```

## 功能教程

### 1. 导入有声书文件夹

打开应用后，把文件夹拖到拖放区域，或点击拖放区域选择文件夹。

应用会递归扫描该文件夹。每一个直接包含受支持媒体文件的目录，都会成为一个有声书分区。

支持的媒体输入：

- 音频：`.m4a`、`.mp3`
- 视频：`.mp4`、`.mkv`、`.mov`、`.m4v`、`.avi`、`.webm`

### 2. 准备文件夹元数据

如果路径中的某个文件夹名称符合以下格式：

```text
[专辑][艺术家]
```

应用会把第一部分作为专辑，第二部分作为艺术家。

例如：

```text
[我的书籍系列][某位作者]/第一卷/01 开场.mp3
```

会创建一个有声书分区：

- 专辑：`我的书籍系列`
- 艺术家：`某位作者`
- 标题：`第一卷`

导出前，你仍然可以在界面中手动编辑专辑、标题和艺术家。

### 3. 检查和编辑音轨

每个有声书分区都有一个音轨表格。

你可以：

- 直接在表格中编辑章节标题。
- 选择行，然后点击 `删除音频`，从导出中移除音轨。
- 选择行，然后点击 `移至首位` 或 `移至末位`。
- 在表格中拖动选中行，重新排列章节。
- 点击 `#` 表头，恢复为自然文件名顺序。
- 点击其他表头，按标题、格式、大小或时长排序。
- 通过“编辑”菜单使用撤销和重做，恢复音轨和封面修改。

默认情况下，章节标题会移除开头的音轨序号。可以通过 `编辑 > 删除曲目序号` 开关此行为。

### 4. 编辑封面

应用会先在有声书文件夹中查找封面图片，然后向上级目录查找，直到导入根目录。文件名中包含 `cover` 的图片会优先使用。

支持的封面输入包括：

```text
.jpg, .jpeg, .png, .webp, .bmp, .tiff, .tif, .gif, .avif, .heic, .heif
```

点击封面缩略图可以打开封面编辑器，右键缩略图可以打开封面菜单。

在封面编辑器中，你可以：

- 自由裁剪，或使用比例预设裁剪。
- 添加自定义裁剪比例。
- 交换裁剪比例方向。
- 调整为指定像素尺寸。
- 压缩到指定 KB 大小。
- 将编辑后的封面保存回当前有声书分区。
- 使用 `另存为...` 保存单独的编辑副本。

可以通过 `编辑 > 封面编辑格式` 选择编辑后封面的输出格式：JPEG 或 PNG。

### 5. 选择导出选项

在窗口底部：

- `输出`：选择保存目录。
- `格式`：选择编码预设。
- `质量`：选择比特率，或选择 `-` 复制原始音频流。
- `封面`：设置导出封面的宽度、高度和最大文件大小。`-` 表示保持当前值。

最终容器始终是 `.m4b`。`格式` 选项控制重新编码时使用的音频编码器。

### 6. 创建有声书

点击 `创建有声书` 或 `创建 N 本有声书`。

应用会检查输出文件是否已经存在。如果发现同名文件，会在覆盖前询问。

导出过程中，进度窗口会显示当前书籍和 FFmpeg 步骤。完成后，应用会列出保存的输出路径。

## 项目结构

```text
main.py              主应用入口
app.py               旧入口兼容层
i18n.py              英文和中文界面文本
theme.py             浅色/深色主题样式
scanner.py           文件夹、音轨、封面和元数据扫描
utils.py             排序、标题清理、格式化工具函数
workers.py           用于时长读取和转换的 QThread 工作线程
converter.py         基于 FFmpeg 的有声书构建逻辑
ui/                  PyQt6 窗口和控件
build_dmg.sh         macOS 构建辅助脚本
Audiobook Maker.spec PyInstaller 配置
```

## 备注

- `build/`、`dist/` 和 `__pycache__/` 是生成产物，从源码运行时不需要。
- FFmpeg 需要在 `PATH` 中。应用也会检查常见 Homebrew 路径：`/usr/local/bin` 和 `/opt/homebrew/bin`。
- 当前取消转换时会终止工作线程。
