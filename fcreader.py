"""Standalone FCKey Reader."""
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QFileDialog,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QMessageBox,QPushButton,QVBoxLayout,QWidget
from fcreader_core import read_and_derive

class ReaderWindow(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        self.setWindowTitle("FCKey Reader")
        self.resize(680,520)
        root=QWidget(); layout=QVBoxLayout(root); layout.setContentsMargins(22,22,22,22); layout.setSpacing(14)
        title=QLabel("FCKey Reader"); title.setStyleSheet("font-size:26px;font-weight:700")
        layout.addWidget(title)
        hint=QLabel("选择 .fckey 后自动读取原始密码与三层归档所需的特殊密码。"); hint.setStyleSheet("color:#aaa")
        layout.addWidget(hint)
        row=QHBoxLayout(); self.path=QLineEdit(); self.path.setReadOnly(True)
        browse=QPushButton("选择 .fckey…"); browse.clicked.connect(self.choose)
        row.addWidget(self.path,1); row.addWidget(browse); layout.addLayout(row)
        self.status=QLabel("等待选择文件"); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.fields=[]
        for caption in ("第一层原始密码","第二层原始密码","第一层特殊密码（7-Zip）","第二层特殊密码（WinRAR）"):
            layout.addWidget(QLabel(caption))
            r=QHBoxLayout(); edit=QLineEdit(); edit.setReadOnly(True); edit.setEchoMode(QLineEdit.Password)
            show=QPushButton("显示"); show.setCheckable(True)
            show.toggled.connect(lambda v,e=edit,b=show:(e.setEchoMode(QLineEdit.Normal if v else QLineEdit.Password),b.setText("隐藏" if v else "显示")))
            copy=QPushButton("复制"); copy.clicked.connect(lambda _,e=edit: QApplication.clipboard().setText(e.text()) if e.text() else None)
            r.addWidget(edit,1); r.addWidget(show); r.addWidget(copy); layout.addLayout(r); self.fields.append(edit)
        layout.addStretch(); self.setCentralWidget(root)
        if initial_file and Path(initial_file).is_file(): self.load(Path(initial_file))

    def choose(self):
        name,_=QFileDialog.getOpenFileName(self,"选择 FCKEY","","FCKey (*.fckey);;All files (*)")
        if name: self.load(Path(name))

    def load(self,path):
        self.path.setText(str(path))
        for field in self.fields: field.clear()
        try:
            meta,p1,p2,s1,s2=read_and_derive(path)
            for field,value in zip(self.fields,(p1,p2,s1,s2)): field.setText(value)
            self.status.setText(f"读取成功 · {meta.get('source_root','')} · 分卷 {len(meta.get('first_layer',{}).get('volumes',[]))} 个")
        except Exception as exc:
            self.status.setText("读取失败")
            QMessageBox.critical(self,"读取失败",str(exc))

def main():
    app=QApplication(sys.argv)
    app.setStyleSheet("QWidget{background:#242424;color:#eee;font-family:'Segoe UI','Microsoft YaHei UI';font-size:13px} QLineEdit{background:#303030;border:1px solid #505050;padding:9px} QPushButton{background:#383838;border:1px solid #555;padding:8px 13px} QPushButton:hover{background:#494949}")
    initial=next((a for a in sys.argv[1:] if not a.startswith("-")),None)
    w=ReaderWindow(initial); w.show(); return app.exec()
if __name__=="__main__": raise SystemExit(main())
