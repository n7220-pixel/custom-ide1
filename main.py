import sys
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMainWindow,
    QStatusBar,
    QToolBar,
    QTextEdit
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom IDE")
        self.setGeometry(1000, 1000, 800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #0af055; }
            QToolBar { background-color: #323232; }
            QToolBar QAction { color: #FFFFFF; }
            QAction{ background-color: #444444; }
        """)

        label = QLabel("Hello, welcome to the Custom IDE!")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 28px;")
        self.setCentralWidget(label)
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        button_action = QAction("File", self)
        button_action.setStatusTip("This is your button")
        button_action.triggered.connect(self.toolbar_button_clicked)
        toolbar.addAction(button_action)

        button_action2 = QAction("Edit", self)
        button_action2.setStatusTip("This is your second button")
        button_action2.triggered.connect(self.toolbar_button_clicked)
        toolbar.addAction(button_action2)

        button_action3 = QAction("View", self)
        button_action3.setStatusTip("This is your third button")
        button_action3.triggered.connect(self.toolbar_button_clicked)
        toolbar.addAction(button_action3)

        button_action4 = QAction("Tools", self)
        button_action4.setStatusTip("This is your fourth button")
        button_action4.triggered.connect(self.toolbar_button_clicked)
        toolbar.addAction(button_action4)

        button_action5 = QAction("Help", self)
        button_action5.setStatusTip("This is your fifth button")
        button_action5.triggered.connect(self.toolbar_button_clicked)
        toolbar.addAction(button_action5)

    def toolbar_button_clicked(self):
        pass

app = QApplication([])
window = MainWindow()
window.show()
app.exec()
