import sys
import json

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QThreadPool, Slot
from lainauspalautus_ui import Ui_MainWindow
import psycopg
from psycopg.rows import dict_row


def load_settings():
    """Load database settings from settings.json"""
    with open("settings.json") as f:
        return json.load(f)

def get_db_connection():
    """Get PostgreSQL connection"""
    settings = load_settings()
    db_config = settings["database"]
    return psycopg.connect(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["database"],
        user=db_config["user"],
        password=db_config["password"],
        row_factory=dict_row
    )


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()

        self.threadPool = QThreadPool().globalInstance()

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)

        try:
            with open("settings.json") as settingsFile:

                jsonData = settingsFile.read()
                self.currentSettings = json.loads(jsonData)
            
        except Exception as error:
            title = 'Tietokanta-asetusten luku ei onnistunut'
            text = 'Tietokanta-asetuksien avaaminen ja salasanan purku ei onnistunut'
            detailedText = str(error)
            self.openWarning(title, text, detailedText)

        self.setInitialElements()


        #Ohjelmoidut signaalit

        #Kun käynnistetään
        self.ui.stackedWidget.setCurrentWidget(self.ui.page)

        #Tervetuloa sivun nappi jossa painat lainaa for now
        self.ui.lainausnappi.clicked.connect(self.lainaa)

        #painaa vahvista
        self.ui.vahvistanappilainauksessa.clicked.connect(self.lainauksentallennus)

        #sama juttu kuin palautuksessa rfidn kanssa

        #Kun painaa palauta
        self.ui.palautusnappi.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.page_3))

        #Painaa vahvista
        self.ui.vahvistanappipalautuksessa.clicked.connect(self.palauta)

        #Muokkaa vielä että se lukee ne RFID:t ja hakee niillä tavaratiedot ja laittaa ne sinne historiaan

        #Kun painaa historia
        self.ui.historianappi.clicked.connect(lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.page_4))

        #Kun painaa palaa nappia mennään alkutilaan
        self.ui.palaanappihistoriassa.clicked.connect(self.palautuminen)
        self.ui.palaanappilainauksessa.clicked.connect(self.palautuminen)
        self.ui.palaanappipalautuksessa.clicked.connect(self.palautuminen)



       


    @Slot()
    def setInitialElements(self):

        #Piilotetaan
        self.ui.historianappi.hide()
        self.ui.palaanappilainauksessa.hide()
        self.ui.vahvistanappilainauksessa.hide()
        self.ui.otsikkolainaus.hide()
        self.ui.lainauksenvalikoima.hide()
        self.ui.lainausvalikoimalista.hide()
        self.ui.palaanappipalautuksessa.hide()
        self.ui.vahvistanappipalautuksessa.hide()
        self.ui.palautus.hide()
        self.ui.palaanappihistoriassa.hide()
        self.ui.historia.hide()
        self.ui.haenappi.hide()
        self.ui.tavarahistoriassa.hide()
        self.ui.henkilohistoriassa.hide()
        self.ui.paivahistoriassa.hide()
        self.ui.haunperuutusnappi.hide()
        self.ui.historialista.hide()
       

        #Alku
        self.ui.tervetuloa.show()
        self.ui.lainausnappi.show()
        self.ui.palautusnappi.show()

        self.ui.vahvistanappilainauksessa.setEnabled(True)
        self.ui.vahvistanappipalautuksessa.setEnabled(True)

        #dbSettings = self.currentSettings
        #plainTextPassword = self.plainTextPassword

        #Tarvitsen tietokannan tiedot




    def update_lainausvalikoima(self, items):
        self.ui.lainausvalikoimalista.clear()
        self.ui.lainausvalikoimalista.addItems(items)
        self.ui.lainausvalikoimalista.show()
        self.ui.lainausnappi.setEnabled(len(items) > 0)


        if self.ui.inUsePlainTextEdit.toPlainText() == '':
            self.ui.palautusnappi.setEnabled(False)
        else:
            self.ui.palautusnappi.setEnabled(True)


    #lainauksen vienti
    @Slot()
    def lainaa(self):
       
        self.ui.otsikkolainaus.show()
        self.ui.lainausvalikoimalista.show()
        self.ui.lainauksenvalikoima.show()
        self.ui.vahvistanappilainauksessa.show()
        self.ui.palaanappilainauksessa.show()

   
    @Slot()
    def lainauksentallennus(self):

        self.ui.lainausvalikoimalista.show()
        self.ui.otsikkolainaus.show()
        self.ui.vahvistanappilainauksessa.show()
        self.ui.palaanappilainauksessa.show()
        self.ui.lainauksenvalikoima.hide()

   
    @Slot()
    def palauta(self):

        self.ui.palautus.show()
        self.ui.vahvistanappipalautuksessa.show()
        self.ui.palaanappipalautuksessa.show()


    @Slot()
    def palautuminen(self):

        self.setInitialElements()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())