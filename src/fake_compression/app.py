"""Desktop entry point and main window."""
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QToolButton,
)

from . import __version__

from .archive import ArchiveService
from .archive_paths import validate_package_name
from .tools import find_7z, find_rar
from .worker import TaskWorker

STYLE = """
QMainWindow, QWidget { background: #242424; color: #eeeeeb; font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 13px; }
QMenuBar { background: #202020; color: #deded9; border-bottom: 1px solid #333333; padding: 3px 8px; }
QMenuBar::item { background: transparent; padding: 6px 10px; }
QMenuBar::item:selected, QMenu { background: #303030; }
QMenu { border: 1px solid #444444; padding: 4px; }
QMenu::item { padding: 7px 24px; }
QMenu::item:selected { background: #414141; }
QFrame#rail { background: #1d1d1d; border-right: 1px solid #343434; }
QLabel#brand { color: #f0a33d; font-size: 15px; font-weight: 650; letter-spacing: .4px; }
QLabel#heading { font-size: 25px; font-weight: 500; color: #f1f1ee; }
QLabel#muted { color: #aaa9a2; }
QPushButton { background: transparent; color: #e2e1dc; border: 1px solid transparent; border-radius: 2px; padding: 9px 12px; text-align: left; }
QPushButton:hover { background: #333333; }
QPushButton:checked { background: #37332d; color: #f0ad50; border-left: 3px solid #e5a044; font-weight: 600; }
QPushButton#primary { background: #e4a047; color: #201b14; border: 1px solid #e4a047; padding: 10px 20px; font-weight: 600; }
QPushButton#primary:hover { background: #f0b15d; }
QPushButton:disabled { color: #777; }
QLineEdit, QPlainTextEdit { background: #2c2c2c; color: #eeeeeb; border: 1px solid #484848; border-radius: 2px; padding: 8px; selection-background-color: #9d7138; }
QLineEdit:focus { border-color: #d89a43; }
QToolButton { color: #e5aa59; border: 1px solid #4b4b4b; padding: 6px 10px; }
QToolButton:hover { background: #39342c; }
QProgressBar { background: #393939; border: none; height: 5px; text-align: center; }
QProgressBar::chunk { background: #e5a044; }
QDialog { background: #262626; }
QDialogButtonBox QPushButton { min-width: 84px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("FakeCompression", "FakeCompression")
        self.setWindowTitle(f"Fake-Compression  ·  {__version__}")
        icon_path = Path(__file__).resolve().parent / "assets" / "fake-compression.svg"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1040, 700)
        self._build_menu()
        self.setMinimumSize(860, 600)
        saved_geometry = self.settings.value("window/geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)

        self.worker = None
        self.active_log = None
        self.stack = QStackedWidget()
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(92)
        nav = QVBoxLayout(rail)
        nav.setContentsMargins(10, 22, 10, 16)
        brand = QLabel("FC")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignCenter)
        brand.setToolTip("Fake-Compression")
        nav.addWidget(brand)
        nav.addSpacing(30)
        self.nav_buttons = []
        for label, index in [("打包", 0), ("恢复", 1), ("设置", 2)]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(48)
            button.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            nav.addWidget(button)
            self.nav_buttons.append(button)
        nav.addStretch()
        footer = QLabel(f"{__version__}  ·  Windows")
        footer.setObjectName("muted")
        nav.addWidget(footer)
        row.addWidget(rail)
        row.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.stack.addWidget(self.build_compress_page())
        self.stack.addWidget(self.build_extract_page())
        self.stack.addWidget(self.build_settings_page())
        self.switch_page(0)

    def _build_menu(self):
        about_menu = self.menuBar().addMenu("关于")
        about_action = QAction("关于 Fake-Compression", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(
            self,
            "关于 Fake-Compression",
            '<h3>Fake-Compression</h3>'
            f'<p>版本：{__version__}</p>'
            '<p>开发者：AllenShiina-Mashiiro</p>'
            '<p><a href="https://github.com/AllenShiina-Mashiiro">GitHub 个人主页</a></p>'
            '<p><a href="https://github.com/AllenShiina-Mashiiro/Fake-Compression">项目仓库</a></p>',
        )

    @staticmethod
    def add_password_field(layout, label, edit):
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        toggle = QToolButton()
        toggle.setText("显示")
        toggle.setCheckable(True)
        toggle.toggled.connect(
            lambda visible: (edit.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password),
                             toggle.setText("隐藏" if visible else "显示"))
        )
        row.addWidget(toggle)
        layout.addLayout(row)

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def page_shell(self, title, subtitle):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 34, 40, 28)
        heading = QLabel(title)
        heading.setObjectName("heading")
        note = QLabel(subtitle)
        note.setObjectName("muted")
        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addSpacing(28)
        return page, layout

    @staticmethod
    def add_field(layout, label, widget):
        layout.addWidget(QLabel(label))
        layout.addWidget(widget)

    @staticmethod
    def path_row(edit, button):
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(button)
        return row

    def build_compress_page(self):
        page, layout = self.page_shell("创建加密包", "将文件安全归档。分卷策略会根据输入总量自动选择。")
        self.source = QLineEdit()
        self.source.setPlaceholderText("选择文件或文件夹")
        choose = QPushButton("浏览…")
        choose.clicked.connect(self.pick_source)
        layout.addWidget(QLabel("输入内容"))
        layout.addLayout(self.path_row(self.source, choose))

        self.video = QLineEdit()
        self.video.setPlaceholderText("可选的预览视频；原文件保持不变")
        choose_video = QPushButton("浏览…")
        choose_video.clicked.connect(self.pick_video)
        layout.addSpacing(12)
        layout.addWidget(QLabel("预览视频（可选）"))
        layout.addLayout(self.path_row(self.video, choose_video))

        self.output = QLineEdit(str(self.settings.value("paths/output", Path.home() / "Fake-Compression")))
        choose_output = QPushButton("浏览…")
        choose_output.clicked.connect(self.pick_output)
        layout.addSpacing(12)
        layout.addWidget(QLabel("输出目录"))
        layout.addLayout(self.path_row(self.output, choose_output))
        self.output.editingFinished.connect(self.save_settings)

        self.package_name = QLineEdit("archive")
        self.batch_mode = QCheckBox("批量压缩：将所选总目录中的每个子文件夹分别打包")
        self.batch_mode.toggled.connect(lambda checked: self.package_name.setEnabled(not checked))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("设置用于保护本次加密包的密码")
        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.Password)
        self.password_confirm.setPlaceholderText("再次输入密码以确认")
        self.repeat_password = QCheckBox("两层使用相同密码")
        self.repeat_password.setChecked(True)
        self.second_password = QLineEdit()
        self.second_password.setEchoMode(QLineEdit.Password)
        self.second_password.setPlaceholderText("设置 WinRAR 第二层密码")
        self.second_password_confirm = QLineEdit()
        self.second_password_confirm.setEchoMode(QLineEdit.Password)
        self.second_password_confirm.setPlaceholderText("再次输入第二层密码")
        self.second_password.setEnabled(False)
        self.second_password_confirm.setEnabled(False)
        self.repeat_password.toggled.connect(
            lambda checked: (self.second_password.setEnabled(not checked),
                             self.second_password_confirm.setEnabled(not checked))
        )
        layout.addWidget(self.batch_mode)
        self.add_field(layout, "包名称（批量模式下使用各子文件夹名称）", self.package_name)
        self.add_password_field(layout, "加密密码", self.password)
        self.add_password_field(layout, "确认密码", self.password_confirm)
        layout.addWidget(self.repeat_password)
        self.add_password_field(layout, "第二层密码（WinRAR）", self.second_password)
        self.add_password_field(layout, "确认第二层密码", self.second_password_confirm)

        self.size_note = QLabel("尚未选择输入内容")
        self.size_note.setObjectName("muted")
        layout.addWidget(self.size_note)
        self.source.textChanged.connect(self.update_size_note)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("muted")
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_label)
        layout.addLayout(progress_row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        self.log.setPlaceholderText("压缩任务输出")
        layout.addWidget(self.log, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel_compress_button = QPushButton("取消任务")
        self.cancel_compress_button.hide()
        self.cancel_compress_button.clicked.connect(self.cancel_active_task)
        actions.addWidget(self.cancel_compress_button)
        self.start_button = QPushButton("开始打包")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_compress)
        actions.addWidget(self.start_button)
        layout.addLayout(actions)
        return page

    def build_extract_page(self):
        page, layout = self.page_shell("恢复文件", "验证加密清单与全部分卷后，再恢复原始文件。")
        self.fc_path = QLineEdit()
        self.fc_path.setPlaceholderText("选择一个或多个加密成品")
        self.selected_packages = []
        self.extract_batch_mode = QCheckBox("批量恢复：处理所选的全部成品")
        layout.addWidget(self.extract_batch_mode)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self.pick_fc)
        layout.addWidget(QLabel("FC 文件"))
        layout.addLayout(self.path_row(self.fc_path, browse))

        self.extract_output = QLineEdit(str(self.settings.value("paths/extract_output", Path.home() / "Restored")))
        browse_out = QPushButton("浏览…")
        browse_out.clicked.connect(self.pick_extract_output)
        layout.addSpacing(12)
        layout.addWidget(QLabel("恢复目录"))
        layout.addLayout(self.path_row(self.extract_output, browse_out))
        self.extract_output.editingFinished.connect(self.save_settings)

        self.extract_password = QLineEdit()
        self.extract_password.setEchoMode(QLineEdit.Password)
        self.extract_repeat_password = QCheckBox("两层使用相同密码")
        self.extract_repeat_password.setChecked(True)
        self.extract_second_password = QLineEdit()
        self.extract_second_password.setEchoMode(QLineEdit.Password)
        self.extract_second_password.setPlaceholderText("WinRAR 第二层密码")
        self.extract_second_password.setEnabled(False)
        self.extract_repeat_password.toggled.connect(
            lambda checked: self.extract_second_password.setEnabled(not checked)
        )
        self.add_password_field(layout, "第一层密码（7-Zip）", self.extract_password)
        layout.addWidget(self.extract_repeat_password)
        self.add_password_field(layout, "第二层密码（WinRAR）", self.extract_second_password)
        self.extract_progress = QProgressBar()
        self.extract_progress.setRange(0, 100)
        self.extract_progress.setValue(0)
        self.extract_progress.hide()
        self.extract_progress_label = QLabel("0%")
        self.extract_progress_label.setObjectName("muted")
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.extract_progress, 1)
        progress_row.addWidget(self.extract_progress_label)
        layout.addLayout(progress_row)
        self.extract_log = QPlainTextEdit()
        self.extract_log.setReadOnly(True)
        self.extract_log.setMaximumBlockCount(400)
        layout.addWidget(self.extract_log, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel_extract_button = QPushButton("取消任务")
        self.cancel_extract_button.hide()
        self.cancel_extract_button.clicked.connect(self.cancel_active_task)
        actions.addWidget(self.cancel_extract_button)
        self.extract_button = QPushButton("验证并恢复")
        self.extract_button.setObjectName("primary")
        self.extract_button.clicked.connect(self.start_extract)
        actions.addWidget(self.extract_button)
        layout.addLayout(actions)
        return page

    def build_settings_page(self):
        page, layout = self.page_shell("设置", "外部工具路径。留空时会尝试从 PATH 和常见安装目录查找。")
        saved_7z = self.settings.value("tools/seven_zip", "")
        saved_rar = self.settings.value("tools/winrar", "")
        self.seven_zip_path = QLineEdit(str(saved_7z or find_7z() or ""))
        self.add_field(layout, "7-Zip 可执行文件", self.seven_zip_path)
        self.seven_zip_path.editingFinished.connect(self.save_settings)
        browse = QPushButton("选择 7z.exe…")
        browse.clicked.connect(self.pick_7zip)
        layout.addWidget(browse, 0, Qt.AlignLeft)
        self.winrar_path = QLineEdit(str(saved_rar or find_rar() or ""))
        self.add_field(layout, "WinRAR 命令行工具（rar.exe）", self.winrar_path)
        self.winrar_path.editingFinished.connect(self.save_settings)
        browse_rar = QPushButton("选择 rar.exe…")
        browse_rar.clicked.connect(self.pick_winrar)
        layout.addWidget(browse_rar, 0, Qt.AlignLeft)
        self.settings_note = QLabel("设置会保存在当前 Windows 用户配置中，不会写入压缩包。")
        self.settings_note.setObjectName("muted")
        layout.addWidget(self.settings_note)
        layout.addStretch()
        return page

    def save_settings(self):
        self.settings.setValue("paths/output", self.output.text().strip())
        self.settings.setValue("paths/extract_output", self.extract_output.text().strip())
        self.settings.setValue("tools/seven_zip", self.seven_zip_path.text().strip())
        self.settings.setValue("tools/winrar", self.winrar_path.text().strip() if hasattr(self, "winrar_path") else "")
        self.settings.sync()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            answer = QMessageBox.question(
                self, "任务仍在运行", "任务尚未结束。取消任务并退出吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(5000)
            if self.worker.isRunning():
                event.ignore()
                QMessageBox.warning(self, "正在停止", "外部压缩程序仍在退出，请稍后再关闭窗口。")
                return
        self.save_settings()
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.sync()
        event.accept()

    def pick_source(self):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not path:
            path = QFileDialog.getOpenFileName(self, "选择文件")[0]
        if path:
            self.source.setText(path)

    def pick_video(self):
        path = QFileDialog.getOpenFileName(
            self, "选择预览视频",
            filter="Video (*.mp4 *.mkv *.mov *.avi);;All files (*)",
        )[0]
        if path:
            self.video.setText(path)

    def pick_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output.text())
        if path:
            self.output.setText(path)
            self.save_settings()

    def pick_fc(self):
        paths = QFileDialog.getOpenFileNames(self, "选择一个或多个加密成品", filter="All files (*)")[0]
        if paths:
            self.selected_packages = [Path(item) for item in paths]
            self.fc_path.setText("；".join(item.name for item in self.selected_packages))

    def pick_extract_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择恢复目录", self.extract_output.text())
        if path:
            self.extract_output.setText(path)
            self.save_settings()

    def pick_winrar(self):
        path = QFileDialog.getOpenFileName(
            self, "选择 rar.exe", filter="Executable (*.exe)",
        )[0]
        if path:
            self.winrar_path.setText(path)
            self.save_settings()

    def pick_7zip(self):
        path = QFileDialog.getOpenFileName(
            self, "选择 7z.exe", filter="Executable (*.exe)",
        )[0]
        if path:
            self.seven_zip_path.setText(path)
            self.save_settings()

    def update_size_note(self):
        from .sizing import GIB, inspect_source
        try:
            plan = inspect_source(self.source.text())
            volume = f"{plan.volume_bytes / GIB:g} GiB" if plan.volume_bytes else "不分卷"
            self.size_note.setText(
                f"输入大小：{plan.total_bytes / GIB:.3f} GiB    ·    分卷：{volume}"
            )
        except (OSError, ValueError):
            self.size_note.setText("输入路径尚不可用")

    def make_service(self):
        return ArchiveService(
            self.seven_zip_path.text().strip() or None,
            self.winrar_path.text().strip() or None if hasattr(self, "winrar_path") else None,
        )

    def start_compress(self):
        source_text, output_text = self.source.text().strip(), self.output.text().strip()
        password, name = self.password.text(), self.package_name.text().strip()
        if not source_text:
            QMessageBox.warning(self, "输入路径无效", "请先选择要压缩的文件或文件夹。")
            return
        if not output_text:
            QMessageBox.warning(self, "输出目录无效", "请选择压缩包的输出目录。")
            return
        source, output = Path(source_text), Path(output_text)
        if not source.exists():
            QMessageBox.warning(self, "输入路径无效", "请选择一个存在的文件或文件夹。")
            return
        try:
            validate_package_name(name)
        except ValueError as exc:
            QMessageBox.warning(self, "包名称无效", str(exc))
            return
        if password != self.password_confirm.text():
            QMessageBox.warning(self, "密码不一致", "两次输入的第一层密码不一致，请检查后重试。")
            return
        if not self.repeat_password.isChecked() and self.second_password.text() != self.second_password_confirm.text():
            QMessageBox.warning(self, "密码不一致", "两次输入的第二层密码不一致，请检查后重试。")
            return
        video = Path(self.video.text()) if self.video.text().strip() else None
        try:
            service = self.make_service()
        except Exception as exc:
            QMessageBox.critical(self, "无法启动压缩", str(exc))
            return

        self.save_settings()
        self.start_button.setEnabled(False)
        self.cancel_compress_button.setEnabled(True)
        self.cancel_compress_button.show()
        self.progress.setValue(0)
        self.progress_label.setText("处理中")
        self.progress.show()
        self.log.clear()
        self.active_log = self.log
        operation = service.create_batch if self.batch_mode.isChecked() else service.create
        if self.batch_mode.isChecked():
            if not source.is_dir():
                QMessageBox.warning(self, "批量输入无效", "批量模式需要选择包含多个子文件夹的总目录。")
                self.start_button.setEnabled(True)
                self.cancel_compress_button.hide()
                return
            self.worker = TaskWorker(
                operation, source, output, password,
                second_password=self.second_password.text(),
                repeat_password=self.repeat_password.isChecked(),
            )
        else:
            self.worker = TaskWorker(
                operation, source, output, name, password, video,
                second_password=self.second_password.text(),
                repeat_password=self.repeat_password.isChecked(),
            )
        self.worker.message.connect(self.log.appendPlainText)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.progress.connect(lambda value: self.progress_label.setText(f"{value}%"))
        self.worker.succeeded.connect(self.compress_succeeded)
        self.worker.failed.connect(self.compress_failed)
        self.worker.cancelled.connect(self.compress_cancelled)
        self.worker.start()

    def start_extract(self):
        fc_text = self.fc_path.text().strip()
        output_text = self.extract_output.text().strip()
        fc, password = Path(fc_text), self.extract_password.text()
        packages = self.selected_packages or ([fc] if fc_text else [])
        if not packages or any(not item.is_file() for item in packages) or not password:
            QMessageBox.warning(self, "信息不完整", "请选择有效的加密成品并输入第一层密码。")
            return
        if not output_text:
            QMessageBox.warning(self, "恢复目录无效", "请选择文件恢复目录。")
            return
        try:
            service = self.make_service()
        except Exception as exc:
            QMessageBox.critical(self, "无法启动恢复", str(exc))
            return

        self.save_settings()
        self.extract_button.setEnabled(False)
        self.cancel_extract_button.setEnabled(True)
        self.cancel_extract_button.show()
        self.extract_progress.setValue(0)
        self.extract_progress_label.setText("处理中")
        self.extract_progress.show()
        self.extract_log.clear()
        self.active_log = self.extract_log
        operation = service.extract_batch if self.extract_batch_mode.isChecked() else service.extract
        if self.extract_batch_mode.isChecked():
            self.worker = TaskWorker(
                operation, packages, Path(output_text), password,
                second_password=self.extract_second_password.text(),
                repeat_password=self.extract_repeat_password.isChecked(),
            )
        else:
            if len(packages) != 1:
                QMessageBox.warning(self, "恢复模式不匹配", "选择了多个文件，请启用批量恢复。")
                self.extract_button.setEnabled(True)
                self.cancel_extract_button.hide()
                return
            self.worker = TaskWorker(
                operation, packages[0], Path(output_text), password,
                second_password=self.extract_second_password.text(),
                repeat_password=self.extract_repeat_password.isChecked(),
            )
        self.worker.message.connect(self.extract_log.appendPlainText)
        self.worker.progress.connect(self.extract_progress.setValue)
        self.worker.progress.connect(lambda value: self.extract_progress_label.setText(f"{value}%"))
        self.worker.succeeded.connect(self.extract_succeeded)
        self.worker.failed.connect(self.extract_failed)
        self.worker.cancelled.connect(self.extract_cancelled)
        self.worker.start()

    def cancel_active_task(self):
        if self.worker and self.worker.isRunning():
            self.cancel_compress_button.setEnabled(False)
            self.cancel_extract_button.setEnabled(False)
            if self.active_log:
                self.active_log.appendPlainText("正在请求取消…")
            self.worker.cancel()

    def compress_succeeded(self, result):
        self.progress_label.setText("完成")
        self.progress.hide()
        self.start_button.setEnabled(True)
        self.cancel_compress_button.hide()
        self.log.appendPlainText(f"完成：{result}")

    def compress_failed(self, message):
        self.progress_label.setText("失败")
        self.progress.hide()
        self.start_button.setEnabled(True)
        self.cancel_compress_button.hide()
        self.log.appendPlainText("错误：" + message)

    def compress_cancelled(self):
        self.progress_label.setText("已取消")
        self.progress.hide()
        self.start_button.setEnabled(True)
        self.cancel_compress_button.hide()
        self.log.appendPlainText("任务已取消。请检查并清理可能残留的临时文件。")

    def extract_succeeded(self, result):
        self.extract_progress_label.setText("完成")
        self.extract_progress.hide()
        self.extract_button.setEnabled(True)
        self.cancel_extract_button.hide()
        self.extract_log.appendPlainText(f"恢复完成：{result}")

    def extract_failed(self, message):
        self.extract_progress_label.setText("失败")
        self.extract_progress.hide()
        self.extract_button.setEnabled(True)
        self.cancel_extract_button.hide()
        self.extract_log.appendPlainText("错误：" + message)

    def extract_cancelled(self):
        self.extract_progress_label.setText("已取消")
        self.extract_progress.hide()
        self.extract_button.setEnabled(True)
        self.cancel_extract_button.hide()
        self.extract_log.appendPlainText("恢复任务已取消。输出目录中可能保留部分已恢复文件，请检查后再继续。")


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("FakeCompression")
    app.setApplicationName("FakeCompression")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
