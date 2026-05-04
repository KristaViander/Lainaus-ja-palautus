import sys

from PySide6 import QtWidgets
from PySide6.QtCore import QThreadPool, Slot
from PySide6.QtUiTools import QUiLoader
from lainauspalautus_ui import Ui_MainWindow


class MainUI(QMainWindow):
    def __init__(self):
        super(MainUI, self).__init__()
        load_ui("lainauspalautus.ui", self)
        self.one_btn.clicked.connect(self.one_btn_action)

    def one_btn_action(self):
        self.label.setText("One button was clicked!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MainUI()
    ui.show()
    app.exec_()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setGeometry(200, 200, 300, 300)
        self.setWindowTitle("Lainaus ja palautus")
        self.initUI()

    def initUI(self):
        self.label = QtWidgets.QLabel(self)
        self.label.setText(" ")
        self.label.move(50, 50)

        self.b1 = QtWidgets.QPushButton(self)
        self.b1.setText("Click")
        self.b1.clicked.connect(self.clicked)

    def clicked(self):
         self.label.setText("Button was clicked!")
        
    def update(self):
        self.label.adjustSize()



class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()

        self.threadPool = QThreadPool().globalInstance()

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)

       


        self.setInitialElements()


        #Ohjelmoidut signaalit

        #Kun käynnistetään
        self.ui.stackedWidget.setCurrentWidget(self.ui.page)

        #Tervetuloa sivun nappi jossa painat lainaa for now
        self.ui.lainausnappi.clicked.connect(self.lainaa(self.ui.stackedWidget.setCurrentWidget(self.ui.page_2)))

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





#Yritän laittaa historian taulukkoon juttuja

#class Mainwindow(QDialog):
   
    #def __init__(self):
        #super(MainWindow, self).__init__()
        #load_ui("lainauspalautus.ui",self)
        #self.loaddata()

    #def loaddata(self):
        #RFID=[{"tavara":" ","päivä":" ","henkilö":" "}]
        #row=0
        #self.tableWidget.setRowCount(len(RFID))
        #for person in RFID:
            #self.tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(person["tavara"]))
            #self.tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(str(person["päivä"])))
            #self.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(person["henkilö"]))
            #row=row+1


loader = QUiLoader()

def mainwindow_setup(w):
    w.setWindowTitle("MainWindow Title")

app = QtWidgets.QApplication(sys.argv)
app.setStyle('fusion')
window = loader.load("lainauspalautus.ui", None)
window.show()
app.exec()