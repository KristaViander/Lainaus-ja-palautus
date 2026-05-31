import sys
import json

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QInputDialog, QTableWidgetItem
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




def create_lainaus_table():
    """Create loan and return tables if they do not exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS lainaukset (
                    id SERIAL PRIMARY KEY,
                    item TEXT NOT NULL,
                    borrower TEXT,
                    rfid TEXT,
                    loaned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                    returned_at TIMESTAMP WITHOUT TIME ZONE,
                    return_rfid TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS palautukset (
                    id SERIAL PRIMARY KEY,
                    item TEXT NOT NULL,
                    return_rfid TEXT,
                    note TEXT,
                    returned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
                )
                """
            )
        conn.commit()


def save_lainaus(item, borrower=None, rfid=None):
    """Save a loan record to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO lainaukset (item, borrower, rfid) VALUES (%s, %s, %s)",
                (item, borrower, rfid)
            )
        conn.commit()


def save_palautus_record(item, return_rfid=None, note=None):
    """Save a return record to the database and update the matching loan."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH updated AS (
                    SELECT id
                    FROM lainaukset
                    WHERE item = %s AND returned_at IS NULL
                    ORDER BY loaned_at DESC
                    LIMIT 1
                )
                UPDATE lainaukset
                SET returned_at = now(), return_rfid = %s
                WHERE id IN (SELECT id FROM updated)
                RETURNING id
                """,
                (item, return_rfid)
            )
            updated_row = cur.fetchone()
            if updated_row is None:
                # If no active loan exists, store a return record anyway.
                cur.execute(
                    "INSERT INTO palautukset (item, return_rfid, note) VALUES (%s, %s, %s)",
                    (item, return_rfid, note)
                )
        conn.commit()


def get_lainaukset(item=None, borrower=None, date=None):
    """Fetch loan history rows from the database."""
    query = "SELECT * FROM lainaukset WHERE 1=1"
    params = []
    if item:
        query += " AND item = %s"
        params.append(item)
    if borrower:
        query += " AND borrower = %s"
        params.append(borrower)
    if date:
        query += " AND DATE(loaned_at) = %s"
        params.append(date)
    query += " ORDER BY loaned_at DESC"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()

        self.threadPool = QThreadPool().globalInstance()

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)
        self.load_lainaus_items()

        try:
            with open("settings.json") as settingsFile:

                jsonData = settingsFile.read()
                self.currentSettings = json.loads(jsonData)
            
        except Exception as error:
            title = 'Tietokanta-asetusten luku ei onnistunut'
            text = 'Tietokanta-asetuksien avaaminen ja salasanan purku ei onnistunut'
            detailedText = str(error)
            self.openWarning(title, text, detailedText)
        else:
            try:
                create_lainaus_table()
            except Exception as error:
                self.openWarning(
                    'Tietokantataulun luonti ei onnistunut',
                    'Lainausdatan tallennus ei toimi ennen kuin tietokantataulu on luotu.',
                    str(error)
                )

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
        self.ui.vahvistanappipalautuksessa.clicked.connect(self.palautuksen_tallennus)

        #Muokkaa vielä että se lukee ne RFID:t ja hakee niillä tavaratiedot ja laittaa ne sinne historiaan

        #Kun painaa historia
        self.ui.historianappi.clicked.connect(self.show_history_page)
        self.ui.haenappi.clicked.connect(self.load_history)

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




    def load_lainaus_items(self):
        """Load available loan items into the combobox."""
        sample_items = [
            "Kirja 1",
            "Työkalu",
            "Kannettava tietokone",
            "Kaapeli",
        ]
        self.update_lainausvalikoima(sample_items)


    def update_lainausvalikoima(self, items):
        self.ui.lainauksenvalikoima.clear()
        self.ui.lainauksenvalikoima.addItems(items)
        self.ui.lainauksenvalikoima.show()
        self.ui.lainausnappi.setEnabled(len(items) > 0)




    #lainauksen vienti
    @Slot()
    def lainaa(self):

        self.ui.stackedWidget.setCurrentWidget(self.ui.page_2)
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

        selected_item = self.ui.lainausvalikoima.currentText().strip()
        if not selected_item:
            self.openWarning(
                'Valitse tavara',
                'Valitse ensin lainausvalikosta tavara ennen tallentamista.'
            )
            return

        borrower, ok = QInputDialog.getText(
            self,
            'Lainaaja',
            'Anna lainaajan nimi:'
        )
        if not ok or not borrower.strip():
            return

        rfid, ok = QInputDialog.getText(
            self,
            'RFID',
            'Anna RFID-koodi (tai jätä tyhjäksi):'
        )
        if not ok:
            return

        try:
            save_lainaus(selected_item, borrower.strip(), rfid.strip() or None)
            QMessageBox.information(
                self,
                'Tallennettu',
                f'Lainaus tietokantaan tallennettu: {selected_item} ({borrower.strip()})'
            )
        except Exception as error:
            self.openWarning(
                'Tallennus epäonnistui',
                'Lainaus tietokantaan ei onnistunut.',
                str(error)
            )

   

   #palautuksen vienti
    @Slot()
    def palauta(self):

        self.ui.stackedWidget.setCurrentWidget(self.ui.page_3)
        self.ui.palautus.show()
        self.ui.vahvistanappipalautuksessa.show()
        self.ui.palaanappipalautuksessa.show()

    @Slot()
    def palautuksen_tallennus(self):
        return_item = self.ui.palautus.toPlainText().strip()
        if not return_item:
            return_item, ok = QInputDialog.getText(
                self,
                'Palautettava tavara',
                'Anna palautettava tavara:'
            )
            if not ok or not return_item.strip():
                return
            return_item = return_item.strip()

        return_rfid, ok = QInputDialog.getText(
            self,
            'Palautus RFID',
            'Anna palautuksen RFID (tai jätä tyhjäksi):'
        )
        if not ok:
            return

        try:
            save_palautus_record(return_item, return_rfid.strip() or None, None)
            QMessageBox.information(
                self,
                'Palautettu',
                f'Palautus tallennettu: {return_item}'
            )
            self.ui.palautus.clear()
            self.setInitialElements()
        except Exception as error:
            self.openWarning(
                'Palautus epäonnistui',
                'Palautus tietokantaan ei onnistunut.',
                str(error)
            )


    @Slot()
    def show_history_page(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.page_4)
        self.load_history_filters()
        self.load_history()

    def load_history_filters(self):
        rows = get_lainaukset()
        items = sorted({row['item'] for row in rows if row.get('item')})
        borrowers = sorted({row['borrower'] for row in rows if row.get('borrower')})

        self.ui.tavarahistoriassa.clear()
        self.ui.tavarahistoriassa.addItem("")
        self.ui.tavarahistoriassa.addItems(items)
        self.ui.henkilohistoriassa.clear()
        self.ui.henkilohistoriassa.addItem("")
        self.ui.henkilohistoriassa.addItems(borrowers)

    def load_history(self):
        item_filter = self.ui.tavarahistoriassa.currentText().strip()
        borrower_filter = self.ui.henkilohistoriassa.currentText().strip()

        rows = get_lainaukset(
            item=item_filter or None,
            borrower=borrower_filter or None
        )
        self.populate_history_table(rows)

    def populate_history_table(self, rows):
        headers = ['Tavara', 'Lainaaja', 'RFID', 'Lainattu', 'Palautettu', 'Palautuksen RFID']
        self.ui.historialista.setColumnCount(len(headers))
        self.ui.historialista.setHorizontalHeaderLabels(headers)
        self.ui.historialista.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                row.get('item') or '',
                row.get('borrower') or '',
                row.get('rfid') or '',
                str(row.get('loaned_at') or ''),
                str(row.get('returned_at') or ''),
                row.get('return_rfid') or ''
            ]
            for col_index, value in enumerate(values):
                self.ui.historialista.setItem(
                    row_index,
                    col_index,
                    QTableWidgetItem(value)
                )


    @Slot()
    def palautuminen(self):
        self.ui.palaanappipalautuksessa.show()
        self.ui.palautus.show()
        self.ui.palautusnappi.show()


        self.setInitialElements()

    def openWarning(self, title, text, detailedText=None):
        message = QMessageBox(self)
        message.setWindowTitle(title)
        message.setText(text)
        if detailedText:
            message.setDetailedText(detailedText)
        message.setIcon(QMessageBox.Warning)
        message.exec()


def test_db_connection():
    try:
        conn = get_db_connection()
        conn.close()
        print("Database connected successfully.")
    except Exception as error:
        print("Database connection failed:", error)
        raise




if __name__ == "__main__":
    test_db_connection()
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())