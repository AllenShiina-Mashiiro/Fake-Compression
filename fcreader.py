"""Standalone graphical reader for Fake-Compression .fckey metadata."""
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget, QCheckBox,
)

from fcreader_core import read_and_derive


class ReaderWindow(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        self.initial_file = Path(initial_file) if initial_file else None
        self.setWindowTitle("FCKey Reader")
        self.resize(620, 520)
        self.setMinimumSize(560, 460)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        title = QLabel("FCKey Reader")
        title.setStyleSheet("font-size:22px;font-weight:600")
        layout.addWidget(title)
        intro = QLabel("读取 Fake-Compression 的 .fckey 文件，验证密码并显示外部归档工具密码。")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#999")
        layout.addWidget(intro)

        file_row = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        browse = QPushButton("选择 .fckey…")
        browse.clicked.connect(self.choose_file)
        file_row.addWidget(self.file_path, 1)
        file_row.addWidget(browse)
        layout.addLayout(file_row)

        form = QFormLayout()
        self.password1 = QLineEdit()
        self.password1.setEchoMode(QLineEdit.Password)
        self.password1.setPlaceholderText("输入创建归档时的第一层原始密码")
        self.same_password = QCheckBox("两层使用相同密码")
        self.same_password.setChecked(True)
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.Password)
        self.password2.setPlaceholderText("输入创建归档时的第二层原始密码")
        self.password2.setEnabled(False)
        self.same_password.toggled.connect(lambda checked: self.password2.setEnabled(not checked))
        form.addRow("第一层原始密码", self.password1)
        form.addRow(self.same_password)
        form.addRow("第二层原始密码", self.password2)
        layout.addLayout(form)

        self.info = QLabel("尚未读取文件")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info.setStyleSheet("background:#292929;padding:12px;border:1px solid #444")
        layout.addWidget(self.info)

        self.out1 = QLineEdit()
        self.out1.setReadOnly(True)
        self.out1.setEchoMode(QLineEdit.Password)
        self.out2 = QLineEdit()
        self.out2.setReadOnly(True)
        self.out2.setEchoMode(QLineEdit.Password)
        self.toggle = QPushButton("显示密码")
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self.toggle_passwords)
        self.copy1 = QPushButton("复制")
        self.copy1.clicked.connect(lambda: self.copy_value(self.out1))
        self.copy2 = QPushButton("复制")
        self.copy2.clicked.connect(lambda: self.copy_value(self.out2))
        for label, edit, copy in (
            ("7-Zip 第一层密码", self.out1, self.copy1),
            ("WinRAR 第二层密码", self.out2, self.copy2),
        ):
            row = QHBoxLayout()
            row.addWidget(edit, 1)
            row.addWidget(copy)
            layout.addWidget(QLabel(label))
            layout.addLayout(row)
        layout.addWidget(self.toggle)
        self.read_button = QPushButton("验证并读取")
        self.read_button.setDefault(True)
        self.read_button.clicked.connect(self.read_file)
        self.read_button.setStyleSheet("padding:10px;font-weight:600")
        layout.addWidget(self.read_button)
        layout.addStretch()
        self.setCentralWidget(root)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 FCKEY 文件", "", "FCKey files (*.fckey);;All files (*)")
        if path:
            self.file_path.setText(path)
            self.info.setText("已选择文件。输入两层原始密码后点击“验证并读取”。")
            self.out1.clear()
            self.out2.clear()

    def read_file(self):
        path = self.file_path.text().strip()
        if not path:
            QMessageBox.warning(self, "缺少文件", "请先选择 .fckey 文件。")
            return
        try:
            metadata, first, second = read_and_derive(
                Path(path), self.password1.text(),
                self.password1.text() if self.same_password.isChecked() else self.password2.text()
            )
        except Exception as exc:
            QMessageBox.critical(self, "读取失败", str(exc))
            return
        first_layer = metadata.get("first_layer", {})
        second_layer = metadata.get("second_layer", {})
        volume_count = len(first_layer.get("volumes", []))
        self.info.setText(
            f"验证成功\n原始文件夹：{metadata.get('source_root', '未知')}\n"
            f"第一层：{first_layer.get('format', '未知')} / {first_layer.get('encryption', '未知')}\n"
            f"分卷数量：{volume_count}\n"
            f"第二层：{second_layer.get('format', '未知')} / {second_layer.get('encryption', '未知')}\n"
            f"第二层分卷：{'是' if second_layer.get('split') else '否'}\n"
            f"源文件记录数：{len(metadata.get('source_files', []))}"
        )
        self.out1.setText(first)
        self.out2.setText(second)

    def toggle_passwords(self, visible):
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        self.out1.setEchoMode(mode)
        self.out2.setEchoMode(mode)
        self.toggle.setText("隐藏密码" if visible else "显示密码")

    @staticmethod
    def copy_value(edit):
        if edit.text():
            QApplication.clipboard().setText(edit.text())

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background:#242424; color:#eee; font-family:'Segoe UI','Microsoft YaHei UI'; font-size:13px; }
        QLineEdit { background:#303030; border:1px solid #505050; padding:8px; }
        QPushButton { background:#383838; border:1px solid #555; padding:7px 12px; }
        QPushButton:hover { background:#454545; }
    """)
    initial_file = next((arg for arg in sys.argv[1:] if not arg.startswith("-")), None)
    window = ReaderWindow(initial_file=initial_file)
    if window.initial_file and window.initial_file.is_file():
        window.file_path.setText(str(window.initial_file))
        window.info.setText("已从文件关联打开。输入原始密码后点击“验证并读取”。")
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
