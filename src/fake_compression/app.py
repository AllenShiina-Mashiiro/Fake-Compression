"""Desktop entry point and main window."""
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .archive import ArchiveService
from .tools import find_7z
from .worker import TaskWorker

STYLE = """
QMainWindow, QWidget { background: #f4f4f1; color: #242522; font-family: "Segoe UI", "Microsoft YaHei"; font-size: 13px; }
QFrame#rail { background: #eaeae5; border-right: 1px solid #d5d5ce; }
QLabel#brand { font-size: 15px; font-weight: 650; letter-spacing: 1px; }
QLabel#heading { font-size: 24px; font-weight: 600; }
QLabel#muted { color: #777970; }
QPushButton { background: transparent; border: 1px solid transparent; border-radius: 3px; padding: 9px 12px; text-align: left; }
QPushButton:hover { background: #deded7; }
QPushButton:checked { background: #d8d8d0; border-color: #c8c8bf; font-weight: 600; }
QPushButton#primary { background: #292a26; color: #fff; border: 1px solid #292a26; padding: 10px 18px; }
QPushButton#primary:hover { background: #41423d; }
QPushButton:disabled { color: #999; }
QLineEdit, QPlainTextEdit { background: #fff; border: 1px solid #d2d2ca; border-radius: 3px; padding: 8px; selection-background-color: #a6a99a; }
QLineEdit:focus { border-color: #777c68; }
QProgressBar { background: #e4e4dd; border: none; height: 5px; text-align: center; }
QProgressBar::chunk { background: #5e6651; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("FakeCompression", "FakeCompression")
        self.setWindowTitle("Fake-Compression")
        self.resize(1040, 700)
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
        rail.setFixedWidth(190)
        nav = QVBoxLayout(rail)
        nav.setContentsMargins(15, 22, 15, 16)
        brand = QLabel("FAKE-COMPRESSION")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        nav.addSpacing(30)
        self.nav_buttons = []
        for label, index in [("创建加密包", 0), ("恢复文件", 1), ("设置", 2)]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            nav.addWidget(button)
            self.nav_buttons.append(button)
        nav.addStretch()
        footer = QLabel("0.2.0  ·  Windows")
        footer.setObjectName("muted")
        nav.addWidget(footer)
        row.addWidget(rail)
        row.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.stack.addWidget(self.build_compress_page())
        self.stack.addWidget(self.build_extract_page())
        self.stack.addWidget(self.build_settings_page())
        self.switch_page(0)

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def page_shell(self, title, subtitle):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 24)
        heading = QLabel(title)
        heading.setObjectName("heading")
        note = QLabel(subtitle)
        note.setObjectName("muted")
        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addSpacing(22)
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
        page, layout = self.page_shell("创建加密包", "选择要归档的内容。分卷大小按输入总量自动决定。")
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
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("请使用足够强且可记住的主密码")
        self.add_field(layout, "包名称", self.package_name)
        self.add_field(layout, "主密码", self.password)

        self.size_note = QLabel("尚未选择输入内容")
        self.size_note.setObjectName("muted")
        layout.addWidget(self.size_note)
        self.source.textChanged.connect(self.update_size_note)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        layout.addWidget(self.progress)
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
        page, layout = self.page_shell("恢复文件", "选择 .fc 文件。程序会先验证所有分卷，再开始解压。")
        self.fc_path = QLineEdit()
        self.fc_path.setPlaceholderText("选择 .fc 文件")
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
        self.add_field(layout, "主密码", self.extract_password)
        self.extract_progress = QProgressBar()
        self.extract_progress.setRange(0, 100)
        self.extract_progress.setValue(0)
        self.extract_progress.hide()
        layout.addWidget(self.extract_progress)
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
        self.seven_zip_path = QLineEdit(str(saved_7z or find_7z() or ""))
        self.add_field(layout, "7-Zip 可执行文件", self.seven_zip_path)
        self.seven_zip_path.editingFinished.connect(self.save_settings)
        browse = QPushButton("选择 7z.exe…")
        browse.clicked.connect(self.pick_7zip)
        layout.addWidget(browse, 0, Qt.AlignLeft)
        self.settings_note = QLabel("设置会保存在当前 Windows 用户配置中，不会写入压缩包。")
        self.settings_note.setObjectName("muted")
        layout.addWidget(self.settings_note)
        layout.addStretch()
        return page

    def save_settings(self):
        self.settings.setValue("paths/output", self.output.text().strip())
        self.settings.setValue("paths/extract_output", self.extract_output.text().strip())
        self.settings.setValue("tools/seven_zip", self.seven_zip_path.text().strip())
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
        path = QFileDialog.getOpenFileName(self, "选择 FC 文件", filter="FC manifest (*.fc)")[0]
        if path:
            self.fc_path.setText(path)

    def pick_extract_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择恢复目录", self.extract_output.text())
        if path:
            self.extract_output.setText(path)
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
        return ArchiveService(self.seven_zip_path.text().strip() or None)

    def start_compress(self):
        source, output = Path(self.source.text()), Path(self.output.text())
        password, name = self.password.text(), self.package_name.text().strip()
        if not source.exists() or not password or not name or Path(name).name != name:
            QMessageBox.warning(self, "信息不完整", "请检查输入路径、包名称和主密码。")
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
        self.progress.show()
        self.log.clear()
        self.active_log = self.log
        self.worker = TaskWorker(service.create, source, output, name, password, video)
        self.worker.message.connect(self.log.appendPlainText)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.succeeded.connect(self.compress_succeeded)
        self.worker.failed.connect(self.compress_failed)
        self.worker.cancelled.connect(self.compress_cancelled)
        self.worker.start()

    def start_extract(self):
        fc, password = Path(self.fc_path.text()), self.extract_password.text()
        if not fc.is_file() or not password:
            QMessageBox.warning(self, "信息不完整", "请选择有效的 .fc 文件并输入主密码。")
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
        self.extract_progress.show()
        self.extract_log.clear()
        self.active_log = self.extract_log
        self.worker = TaskWorker(
            service.extract, fc, Path(self.extract_output.text()), password,
        )
        self.worker.message.connect(self.extract_log.appendPlainText)
        self.worker.progress.connect(self.extract_progress.setValue)
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
        self.progress.hide()
        self.start_button.setEnabled(True)
        self.cancel_compress_button.hide()
        self.log.appendPlainText(f"完成：{result}")

    def compress_failed(self, message):
        self.progress.hide()
        self.start_button.setEnabled(True)
        self.cancel_compress_button.hide()
        self.log.appendPlainText("错误：" + message)

    def compress_cancelled(self):
        self.progress.hide()
        self.start_button.setEnabled(True)
        self.cancel_compress_button.hide()
        self.log.appendPlainText("任务已取消。请检查并清理可能残留的临时文件。")

    def extract_succeeded(self, result):
        self.extract_progress.hide()
        self.extract_button.setEnabled(True)
        self.cancel_extract_button.hide()
        self.extract_log.appendPlainText(f"恢复完成：{result}")

    def extract_failed(self, message):
        self.extract_progress.hide()
        self.extract_button.setEnabled(True)
        self.cancel_extract_button.hide()
        self.extract_log.appendPlainText("错误：" + message)

    def extract_cancelled(self):
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
