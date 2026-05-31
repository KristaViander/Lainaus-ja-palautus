import sys
import json
import psycopg

from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QInputDialog, QTableWidgetItem, QLineEdit
from PySide6.QtCore import QThreadPool, Slot
from lainauspalautus_ui import Ui_MainWindow
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




def get_henkilokunta_password():

    """Return the configured henkilökunta password for history access."""

    try:

        settings = load_settings()

        return settings.get("henkilokunta_password", "henkilokunta123")
    
    except Exception:

        return "henkilokunta123"





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

                cur.execute(
                    "INSERT INTO palautukset (item, return_rfid, note) VALUES (%s, %s, %s)",
                    (item, return_rfid, note)
                )

        conn.commit()




def get_lainaukset(item=None, borrower=None, date=None):

    """Hae lainaus historian rivit tietokannasta."""

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

        self.user_role = 'customer'

        self.ui.lainauksenvalikoima.currentTextChanged.connect(self.update_selected_lainaus_item)



        try:
            with open("settings.json") as settingsFile:

                jsonData = settingsFile.read()
                self.currentSettings = json.loads(jsonData)
                self.user_role = self.currentSettings.get('user_role', 'customer')
            


        except Exception as error:

            title = 'Tietokannan luku ei onnistunut'
            text = 'Tietokannan avaaminen ja salasanan purku ei onnistunut'
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



        self.ask_user_role()

        self.setInitialElements()




        #Ohjelmoidut signaalit


        #Kun käynnistetään
        self.ui.stackedWidget.setCurrentWidget(self.ui.page)


        #Tervetuloa sivun nappi jossa painat lainaa for now
        self.ui.lainausnappi.clicked.connect(self.lainaa)



        #painaa vahvista
        self.ui.vahvistanappilainauksessa.clicked.connect(self.lainauksentallennus)



        #Kun painaa palauta
        self.ui.palautusnappi.clicked.connect(self.palauta)



        #Painaa vahvista
        self.ui.vahvistanappipalautuksessa.clicked.connect(self.palautuksen_tallennus)


        #Kun painaa historia
        self.ui.historianappi.clicked.connect(self.try_show_history)

        self.ui.haenappi.clicked.connect(self.load_history)



        #Kun painaa palaa nappia mennään alkutilaan
        self.ui.palaanappihistoriassa.clicked.connect(self.palautuminen)

        self.ui.palaanappilainauksessa.clicked.connect(self.palautuminen)

        self.ui.palaanappipalautuksessa.clicked.connect(self.palautuminen)

        self.ui.haunperuutusnappi.clicked.connect(self.palautuminen)




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

        self.ui.historianappi.hide()

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

        if self.user_role == 'henkilokunta':

            self.ui.historianappi.show()


        self.ui.vahvistanappilainauksessa.setEnabled(True)

        self.ui.vahvistanappipalautuksessa.setEnabled(True)




    def load_lainaus_items(self):

        """Laita kaikki tavarat comboboxiin."""

        self.update_lainausvalikoima(self.get_all_items())




    def get_all_items(self):

        return [
            "Ruuvimeisseli",
            "Vasara",
            "Sähköpora",
            "Kirves",
            "Pihdit",
            "Jakoavain",
            "Saha",
            "Apina-avain",
            "Suorakulma mitta",
            "Vesivaaka",
        ]




    def get_reserved_items(self):

        rows = get_lainaukset()
        return {
            row['item'] for row in rows
            if row.get('item') and row.get('returned_at') is None
        }




    def is_item_reserved(self, item):

        return item in self.get_reserved_items()




    def ask_user_role(self):

        """Prompt for henkilökunta login; default to customer if not authenticated."""

        password, ok = QInputDialog.getText(
            self,
            'Henkilökunnan kirjautuminen',
            'Anna henkilökunnan salasana tai jätä tyhjäksi asiakkaana jatkamista varten:',
            QLineEdit.Password
        )

        if not ok:

            self.user_role = 'customer'
            return



        if password and password == get_henkilokunta_password():

            self.user_role = 'henkilokunta'
            QMessageBox.information(self, 'Tervetuloa', 'Kirjauduit henkilökuntaan.')
            self.ui.historianappi.show()



        elif password:

            QMessageBox.warning(self, 'Väärä salasana', 'Salasana on väärä, jatketaan asiakkaana.')
            self.user_role = 'customer'
            self.ui.historianappi.hide()



        else:

            self.user_role = 'customer'
            self.ui.historianappi.hide()




    def update_lainausvalikoima(self, items):

        self.ui.lainauksenvalikoima.clear()

        self.ui.lainauksenvalikoima.addItems(items)

        self.ui.lainauksenvalikoima.show()

        self.ui.lainausnappi.setEnabled(len(items) > 0)

        self.update_selected_lainaus_item(self.ui.lainauksenvalikoima.currentText())




    def update_selected_lainaus_item(self, selected_item):

        """Näyt laina tavarat."""

        self.ui.lainausvalikoimalista.setRowCount(1)

        self.ui.lainausvalikoimalista.setItem(0, 0, QTableWidgetItem(selected_item or ''))

        if selected_item and self.is_item_reserved(selected_item):

            self.ui.lainausvalikoimalista.setItem(0, 1, QTableWidgetItem('Varattu'))

            self.ui.vahvistanappilainauksessa.setEnabled(False)

        else:

            self.ui.lainausvalikoimalista.setItem(0, 1, QTableWidgetItem('Saatavilla' if selected_item else ''))

            self.ui.vahvistanappilainauksessa.setEnabled(bool(selected_item))




    #lainauksen vienti
    @Slot()
    def lainaa(self):

        self.load_lainaus_items()

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

        selected_item = self.ui.lainauksenvalikoima.currentText().strip()

        if not selected_item:

            self.openWarning(
                'Valitse tavara',
                'Valitse ensin lainausvalikoimasta tavara ennen tallentamista.'
            )

            return
        
        if self.is_item_reserved(selected_item):

            self.openWarning(
                'Varattu',
                'Valittu tavara on varattu. Valitse toinen tavara.'
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

            self.ui.lainausvalikoimalista.setItem(0, 1, QTableWidgetItem('Varattu'))

            QMessageBox.information(
                self,
                'Onnistui',
                f'Lainaus onnistui: {selected_item} ({borrower.strip()})'
            )

            self.load_lainaus_items()

            if self.user_role == 'henkilokunta':

                self.load_history_filters()

                self.load_history()

            self.ui.stackedWidget.setCurrentWidget(self.ui.page)

            self.setInitialElements()

        except Exception as error:

            self.openWarning(
                'Tallennus ei onnistunut',
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


        try:

            save_palautus_record(return_item, None, None)

            QMessageBox.information(
                self,
                'Palautus onnistui',
                f'Palautettu tavara: {return_item}'
            )

            self.ui.palautus.clear()

            self.palautuminen()

        except Exception as error:

            self.openWarning(
                'Palautus epäonnistui',
                'Palautus tietokantaan ei onnistunut.',
                str(error)
            )




    class Item:

        def __init__(self, title, item_id):

            self.title = title
            self.item_id = item_id
            self.status = "Available"
            self.borrowed_by = None




    @Slot()
    def try_show_history(self):

        password, ok = QInputDialog.getText(
            self,
            'Henkilökunnan pääsy',
            'Anna henkilökunnan salasana:',
            QLineEdit.Password
        )

        if not ok:

            return

        if password == get_henkilokunta_password():

            self.show_history_page()

        else:

            self.openWarning(
                'Pääsy estetty',
                'Väärä salasana. Historia on vain henkilökunnalle.'
            )


    def show_history_page(self):

        if self.user_role != 'henkilokunta':

            self.openWarning(
                'Pääsy estetty',
                'Historia on vain henkilökunnalle.'
            )

            return



        #Historia
        self.ui.stackedWidget.setCurrentWidget(self.ui.page_4)

        self.ui.historia.show()

        self.ui.haenappi.show()

        self.ui.tavarahistoriassa.show()

        self.ui.henkilohistoriassa.show()

        self.ui.paivahistoriassa.show()

        self.ui.haunperuutusnappi.show()

        self.ui.historialista.show()

        self.ui.palaanappihistoriassa.show()

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

        headers = ['Tavara', 'Lainaaja', 'RFID', 'Lainattu', 'Palautettu', 'Palautuksen RFID', 'Tila']

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
                row.get('return_rfid') or '',
                'Varattu' if row.get('returned_at') is None else 'Palautettu'
            ]

            for col_index, value in enumerate(values):

                self.ui.historialista.setItem(
                    row_index,
                    col_index,
                    QTableWidgetItem(value)
                )




    @Slot()
    def palautuminen(self):

        self.ui.stackedWidget.setCurrentWidget(self.ui.page)

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

        print("Tietokantaan yhdistetty onnistuneesti.")

    except Exception as error:

        print("Tietokantayhteys epäonnistui:", error)

        raise




if __name__ == "__main__":

    test_db_connection()

    app = QtWidgets.QApplication(sys.argv)

    app.setStyle('fusion')

    window = MainWindow()

    window.show()

    sys.exit(app.exec())