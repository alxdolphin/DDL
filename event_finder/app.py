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
        
        # results area - split into events and rooms
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # events section
        events_label = QLabel("Events:")
        self.events_results = QTextBrowser()
        results_layout.addWidget(events_label)
        results_layout.addWidget(self.events_results)
        
        # room availability section
        rooms_label = QLabel("Room Availability:")
        self.rooms_results = QTextBrowser()
        results_layout.addWidget(rooms_label)
        results_layout.addWidget(self.rooms_results)
        
        layout.addWidget(results_widget)
        
    def search_events(self):
        # clear previous results
        self.events_results.clear()
        self.rooms_results.clear()
        
        # get selected date
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        # get selected libraries
        selected_libraries = [lib_id for lib_id, checkbox in self.library_checkboxes.items() 
                            if checkbox.isChecked()]
        
        if not selected_libraries:
            self.events_results.append("Please select at least one library.")
            return
            
        try:
            # get events
            token = libCal.get_access_token()
            events = libCal.get_events(token, date_str, selected_libraries)
            library_ids = libCal.get_library_ids()
            
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
                    self.events_results.append(event_text)
            else:
                self.events_results.append(f"No events found on {date_str}")
            
            # fetch and display room availability
            for cal_id in selected_libraries:
                library_name = library_ids[cal_id]
                lid = libCal.library_info[library_name]['lid']
                
                if lid:  # only process libraries with space booking capability
                    try:
                        bookings = libCal.get_space_bookings(token, lid, date_str)
                        rooms = libCal.process_space_availability(bookings)
                        
                        if rooms:
                            self.rooms_results.append(f"<h3>{library_name}</h3>")
                            for room, bookings in rooms.items():
                                self.rooms_results.append(f"<p><b>{room}</b></p>")
                                if bookings:
                                    for booking in bookings:
                                        self.rooms_results.append(
                                            f"• {booking['from']} - {booking['to']}: {booking['nickname']}<br>"
                                        )
                                else:
                                    self.rooms_results.append("• Available all day<br>")
                            self.rooms_results.append("<hr>")
                    except Exception as e:
                        self.rooms_results.append(f"Could not get space bookings for {library_name}: {str(e)}<br>")
                
        except Exception as e:
            self.events_results.append(f"Error fetching data: {str(e)}")

def format_status_gui(status):
    if status == "CONFIRMED":
        return '<span style="color: #2ecc71;">[CONFIRMED]</span>'
    return '<span style="color: #f1c40f;">[PENDING]</span>'

def main():
    app = QApplication(sys.argv)
    window = LibraryApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 