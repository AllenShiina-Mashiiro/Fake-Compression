# 📦 Fake-Compression-fcreader

用于读取 Fake-Compression 打包产生的 \`.fckey\` 密钥内容。

## 🧠 工作原理

- 🔑 经过验证的元数据存储在与最终压缩包同名的外部 \`.fckey\` sidecar 文件中。
- 🗂️ 完成身份验证和解密后，读取器会显示恢复归档所需的信息与密码。

## 🔄 恢复流程

FCKey Reader 会执行以下操作：

- 📖 读取对应的 \`.fckey\` 文件。
- 🔓 解密并验证元数据。
- 👁️ 显示读取结果，并提供密码显示与复制功能，供用户自行完成后续解压。

## 📝 文件命名与兼容性

- 外部压缩包文件名不是元数据中的标识字段。
- 将压缩包改名时，需要将对应的 \`.fckey\` 文件一起改为相同文件名。
- 本工具只负责读取和验证密钥元数据，不负责创建压缩包或解压文件。

## 🚀 从源代码运行

### 环境要求

- Windows 10 / 11（x64）
- Python 3.10 或更高版本
- Git

> FCKey Reader 使用 PySide6 构建图形界面，使用 cryptography 处理加密元数据。运行读取器不需要另外安装 7-Zip 或 WinRAR。

### 1. 克隆仓库

\`\`\`powershell
git clone --branch fcreader --single-branch https://github.com/AllenShiina-Mashiiro/Fake-Compression.git
cd Fake-Compression
\`\`\`

### 2. 创建虚拟环境

\`\`\`powershell
py -m venv .venv
\`\`\`

### 3. 激活虚拟环境

\`\`\`powershell
.\\.venv\\Scripts\\Activate.ps1
\`\`\`

如果 PowerShell 提示脚本执行策略限制，可以改用 CMD：

\`\`\`bat
.venv\\Scripts\\activate.bat
\`\`\`

### 4. 安装依赖

\`\`\`powershell
py -m pip install --upgrade pip
py -m pip install -r requirements-fcreader.txt
\`\`\`

### 5. 启动程序

\`\`\`powershell
py main.py
\`\`\`

启动后，点击“选择 .fckey…”并选择需要读取的文件即可。

也可以直接将文件路径作为参数传入：

\`\`\`powershell
py main.py "D:\\Path\\To\\package.fckey"
\`\`\`

## 🛠️ 从源代码构建 EXE

如果你希望自行打包为独立 EXE，在完成上面的依赖安装后执行：

\`\`\`powershell
pyinstaller --clean --noconfirm fcreader.spec
\`\`\`

构建完成后，程序位于：

\`\`\`text
dist\\FCKey-Reader.exe
\`\`\`

安装程序的制作方式请参考 [README-FCKey-Reader.md](README-FCKey-Reader.md)。

## 📄 更多说明

- [FCKey Reader 完整说明与构建指南](README-FCKey-Reader.md)
- [Fake-Compression 主项目](https://github.com/AllenShiina-Mashiiro/Fake-Compression)
