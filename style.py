# style.py

PASTEL_THEME = """
QMainWindow {
    background-color: #e3e1ea; /* Açık lila zemin */
    background-image: 
        linear-gradient(#cfcce0 1px, transparent 1px),
        linear-gradient(90deg, #cfcce0 1px, transparent 1px);
    background-size: 20px 20px; /* Karelerin boyutu */
    background-position: center;
}

QWidget {
    font-family: "Courier New", monospace;
    font-size: 13px;
    color: #4a4a4a;
}

/* Tabs */ 
QTabWidget::pane {
    border: 2px solid #8e99f3;
    background-color: #fff0f5; 
    border-radius: 0px;
    top: -1px; 
}

QTabBar::tab {
    background: #dcd6f7;
    color: #555;
    border: 2px solid #8e99f3;
    border-bottom: none;
    padding: 8px 15px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background: #fff0f5; /* Seçili sekme içerikle aynı renk */
    color: #8e99f3;
    margin-bottom: -2px; 
}

/* Butonlar */
QPushButton {
    background-color: #ffb7b2; 
    border: 2px solid #ff9e99;
    border-right-color: #c46c68; /* gölge */
    border-bottom-color: #c46c68;
    color: #fff;
    padding: 8px;
    font-weight: bold;
    border-radius: 0px; /* Keskin köşeler */
}

QPushButton:hover {
    background-color: #ffdac1; 
    border-color: #ffcba4;
    color: #555;
    position: relative;
    top: 1px;
    left: 1px;
}

QPushButton:pressed {
    background-color: #e2f0cb; 
    border: 2px solid #b5c99a;
    border-top-color: #8b9c75;
    border-left-color: #8b9c75;
}

/* Input Alanları */
QLineEdit, QTextEdit {
    background-color: #ffffff;
    border: 2px dashed #8e99f3; /* Kesikli çizgi çerçeve */
    padding: 5px;
    color: #555;
    selection-background-color: #ff9aa2;
}

/*  Tablo */
QTableWidget {
    background-color: #ffffff;
    gridline-color: #ffdac1;
    border: 2px solid #8e99f3;
}
QHeaderView::section {
    background-color: #ffb7b2;
    color: white;
    border: 1px solid #ff9e99;
    padding: 4px;
}

/* Progress Bar */
QProgressBar {
    border: 2px solid #8e99f3;
    background-color: #fff;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #b5ead7;
    width: 10px;
    margin: 1px;
}
"""