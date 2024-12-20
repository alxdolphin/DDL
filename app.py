#!/usr/bin/env python
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QCalendarWidget, QListWidget, QPushButton, QLabel,
                            QTextBrowser, QCheckBox, QScrollArea, QFrame)
from PyQt6.QtCore import QDate
import libCal
from datetime import datetime

class LibraryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delaware Library Events")
        self.setMinimumSize(800, 600)
        
        # main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.SingleLetterDayNames)
        layout.addWidget(self.calendar)
        
        # library checkboxes in scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_widget)
        
        # create checkboxes for libraries
        self.library_checkboxes = {}
        for lib_id, lib_name in libCal.library_ids.items():
            checkbox = QCheckBox(lib_name)
            self.library_checkboxes[lib_id] = checkbox
            self.checkbox_layout.addWidget(checkbox)
        
        scroll.setWidget(scroll_widget)
        scroll.setMaximumHeight(150)
        layout.addWidget(scroll)
        
        # search button
        self.search_button = QPushButton("Find Events")
        self.search_button.clicked.connect(self.search_events)
        layout.addWidget(self.search_button)
        
        # results area
        self.results = QTextBrowser()
        layout.addWidget(self.results)
        
    def search_events(self):
        # clear previous results
        self.results.clear()
        
        # get selected date
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        # get selected libraries
        selected_libraries = [lib_id for lib_id, checkbox in self.library_checkboxes.items() 
                            if checkbox.isChecked()]
        
        if not selected_libraries:
            self.results.append("Please select at least one library.")
            return
            
        try:
            # get events
            token = libCal.get_access_token()
            events = libCal.get_events(token, date_str, selected_libraries)
            library_ids = libCal.library_ids
            
            if events:
                for event in events:
                    library_name = library_ids.get(event['calendar']['id'], 'Unknown library')
                    event_text = (
                        f"<h3>{event['title']} at {library_name}</h3>"
                        f"<p><b>Time:</b> {event['start']} to {event['end']}</p>"
                        f"<p><b>Location:</b> {event.get('location', {}).get('name', 'Unknown location')}</p>"
                        f"<p><b>Description:</b> {libCal.strip_html_tags(event.get('description', 'No description available'))}</p>"
                        "<hr>"
                    )
                    self.results.append(event_text)
            else:
                self.results.append(f"No events found on {date_str}")
                
        except Exception as e:
            self.results.append(f"Error fetching events: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = LibraryApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 