from burp import IBurpExtender, ITab, IContextMenuFactory, IMessageEditorController
from javax.swing import (JPanel, JButton, JTable, JScrollPane, JComboBox, JLabel, JMenuItem, JDialog, JPopupMenu,
                         ListSelectionModel, DefaultCellEditor, JFileChooser, JOptionPane, DefaultListCellRenderer,
                         SwingUtilities, JTextArea, SwingConstants)
from javax.swing.table import DefaultTableModel, DefaultTableCellRenderer
from javax.swing.border import EmptyBorder
from javax.swing.filechooser import FileNameExtensionFilter
from java.awt.event import MouseAdapter, MouseEvent
from java.awt import BorderLayout, Point, GridLayout, Font, Color, FlowLayout
from java.util import ArrayList
from java.io import File
from datetime import datetime
import json
import base64
import os

VERSION = "1.0.1"
BsRed = Color(255, 100, 101)
BsOrange = Color(255, 200, 100)
BsGreen = Color(100, 255, 100)
BsGray = Color(180, 180, 180)
BsYellow = Color(255, 255, 100)

def get_findings_tracker_directory():
        user_documents_folder = os.path.expanduser("~/Documents")
        findings_tracker_folder = os.path.join(user_documents_folder, "Burp Suite", "Findings Tracker")

        if not os.path.exists(findings_tracker_folder):
            os.makedirs(findings_tracker_folder)

        print("Findings Tracker Directory:", findings_tracker_folder)
        return findings_tracker_folder

class RightClickListener(MouseAdapter):
    def __init__(self, extender):
        self.extender = extender

    def mouseClicked(self, event):
        if event.isPopupTrigger() or (event.getButton() == MouseEvent.BUTTON3 and event.getClickCount() == 1):
            self.show_popup(event)

    def mousePressed(self, event):
        self.show_popup_if_required(event)

    def mouseReleased(self, event):
        self.show_popup_if_required(event)

    def show_popup_if_required(self, event):
        if event.isPopupTrigger():
            self.show_popup(event)

    def show_popup(self, event):
        row = event.getSource().rowAtPoint(Point(event.getX(), event.getY()))
        if row >= 0:
            event.getSource().getSelectionModel().setSelectionInterval(row, row)
            popup_menu = JPopupMenu()
            show_request_response_item = JMenuItem("Show Request & Response", actionPerformed=lambda e: self.extender.show_request_response(row))
            remove_finding_item = JMenuItem("Remove Finding", actionPerformed=lambda e: self.extender.remove_finding(row))
            popup_menu.add(show_request_response_item)
            popup_menu.add(remove_finding_item)
            popup_menu.show(event.getComponent(), event.getX(), event.getY())

class RowColorRenderer(DefaultTableCellRenderer):
    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        component = super(RowColorRenderer, self).getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column)
        status = table.getValueAt(row, 2)
        if status == "Remediated":
            component.setBackground(BsGreen)
        elif status == "Fail":
            component.setBackground(BsRed)
        elif status == "Warning":
            component.setBackground(BsOrange)
        elif status == "Exception":
            component.setBackground(BsYellow)
        elif status == "False Positive":
            component.setBackground(BsGray)
        else:
            component.setBackground(Color.WHITE)

        # Align the text to the top
        component.setVerticalAlignment(SwingConstants.TOP)

        return component

class DescriptionRenderer(DefaultTableCellRenderer):
    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        component = super(DescriptionRenderer, self).getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column)
        status = table.getValueAt(row, 2)
        if status == "Remediated":
            component.setBackground(BsGreen)
        elif status == "Fail":
            component.setBackground(BsRed)
        elif status == "Warning":
            component.setBackground(BsOrange)
        elif status == "Exception":
            component.setBackground(BsYellow)
        elif status == "False Positive":
            component.setBackground(BsGray)
        else:
            component.setBackground(Color.WHITE)

        # Set word wrap and line breaks for the description column
        text_area = JTextArea(value)
        text_area.setLineWrap(True)
        text_area.setWrapStyleWord(True)
        text_area.setOpaque(True)
        text_area.setBackground(component.getBackground())
        text_area.setForeground(component.getForeground())
        text_area.setFont(component.getFont())
        text_area.setBorder(component.getBorder())
        text_area.setEditable(False)

        if not value:
            text_area.setText("Add Description")
            text_area.setForeground(Color.GRAY)
        else:
            if value == "Add Description":
                text_area.setForeground(Color.GRAY)
            else:
                text_area.setForeground(Color.BLACK)

        return text_area

class NotesRenderer(DefaultTableCellRenderer):
    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        component = super(NotesRenderer, self).getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column)
        status = table.getValueAt(row, 2)
        if status == "Remediated":
            component.setBackground(BsGreen)
        elif status == "Fail":
            component.setBackground(BsRed)
        elif status == "Warning":
            component.setBackground(BsOrange)
        elif status == "Exception":
            component.setBackground(BsYellow)
        elif status == "False Positive":
            component.setBackground(BsGray)
        else:
            component.setBackground(Color.WHITE)

        # Set word wrap and line breaks for the notes column
        text_area = JTextArea(value)
        text_area.setLineWrap(True)
        text_area.setWrapStyleWord(True)
        text_area.setOpaque(True)
        text_area.setBackground(component.getBackground())
        text_area.setForeground(component.getForeground())
        text_area.setFont(component.getFont())
        text_area.setBorder(component.getBorder())
        text_area.setEditable(False)

        if not value:
            text_area.setText("Add Notes")
            text_area.setForeground(Color.GRAY)
        else:
            if value == "Add Notes":
                text_area.setForeground(Color.GRAY)
            else:
                text_area.setForeground(Color.BLACK)

        return text_area

class BurpExtender(IBurpExtender, ITab, IContextMenuFactory, IMessageEditorController):
    class MessageController(IMessageEditorController):
        def __init__(self, request, response, helpers):
            self._request = request
            self._response = response
            self._helpers = helpers

        def getHttpService(self):
            return None

        def getRequest(self):
            return self._request

        def getResponse(self):
            return self._response

        def getHelpers(self):
            return self._helpers
        
    def registerExtenderCallbacks(self, callbacks):
        self.callbacks = callbacks
        self.helpers = callbacks.getHelpers()
        self.last_exported_file = None
        self.is_importing = False

        self.initUI()

        callbacks.addSuiteTab(self)
        callbacks.setExtensionName("Findings Tracker")
        callbacks.registerContextMenuFactory(self)

    def initUI(self):
        self.panel = JPanel()
        self.panel.setLayout(BorderLayout())

        self.columns = ["ID", "OWASP Top 10", "Status", "Description", "Host", "Notes", "Request", "Response"]
        table_data = []
        table_model = DefaultTableModel(table_data, self.columns)
        table_model.addTableModelListener(self.handle_table_change)
        self.table = JTable(table_model)
        # The line below doubles the height for findings
        self.table.setRowHeight(2 * self.table.getFontMetrics(self.table.getFont()).getHeight() + 4)

        for column_index in range(len(self.columns)):
            self.table.getColumnModel().getColumn(column_index).setCellRenderer(RowColorRenderer())

        self.table.getColumnModel().getColumn(3).setCellRenderer(DescriptionRenderer())
        self.table.getColumnModel().getColumn(5).setCellRenderer(NotesRenderer())

        id_column = self.table.getColumnModel().getColumn(0)
        id_column.setPreferredWidth(50)
        id_column.setMinWidth(50)
        id_column.setMaxWidth(50)

        id_column = self.table.getColumnModel().getColumn(1)
        id_column.setPreferredWidth(300)
        id_column.setMinWidth(300)
        id_column.setMaxWidth(300)

        id_column = self.table.getColumnModel().getColumn(2)
        id_column.setPreferredWidth(100)
        id_column.setMinWidth(100)
        id_column.setMaxWidth(100)

        id_column = self.table.getColumnModel().getColumn(4)
        id_column.setPreferredWidth(100)
        id_column.setMinWidth(100)
        id_column.setMaxWidth(200)

        # Hide the Request and Response columns
        self.table.getColumnModel().getColumn(6).setWidth(0)
        self.table.getColumnModel().getColumn(6).setMinWidth(0)
        self.table.getColumnModel().getColumn(6).setMaxWidth(0)
        self.table.getColumnModel().getColumn(7).setWidth(0)
        self.table.getColumnModel().getColumn(7).setMinWidth(0)
        self.table.getColumnModel().getColumn(7).setMaxWidth(0)

        self.table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION)
        self.table.getColumnModel().getColumn(1).setCellEditor(DefaultCellEditor(self.owasp_dropdown()))
        self.table.getColumnModel().getColumn(2).setCellEditor(DefaultCellEditor(self.status_dropdown()))

        self.table.addMouseListener(RightClickListener(self))

        table_panel = JPanel()
        table_panel.setLayout(BorderLayout())
        table_panel.add(JScrollPane(self.table), BorderLayout.CENTER)

        self.panel.add(table_panel, BorderLayout.CENTER)

        button_panel = JPanel()
        button_panel.setLayout(FlowLayout(FlowLayout.RIGHT))
        add_finding_button = JButton("Add Finding", actionPerformed=self.add_finding)
        export_json_button = JButton("Export as JSON", actionPerformed=lambda event: self.export_to_json(event))
        import_json_button = JButton("Import from JSON", actionPerformed=lambda event: self.import_from_json(event))
        button_panel.add(add_finding_button)
        button_panel.add(export_json_button)
        button_panel.add(import_json_button)

        self.panel.add(button_panel, BorderLayout.SOUTH)

        print("Findings Tracker v" + VERSION + " loaded.")

    def handle_table_change(self, event):
        if self.is_importing:
            return
        
        if self.last_exported_file is not None:
            with open(self.last_exported_file, "w") as json_file:
                table_data = self.get_table_data()
                json.dump(table_data, json_file, indent=4)
        else:
            user_choice = JOptionPane.showConfirmDialog(
                None,
                "There are unsaved findings. Do you want to export them to a JSON file?",
                "Unsaved Findings",
                JOptionPane.YES_NO_OPTION,
            )
            if user_choice == JOptionPane.YES_OPTION:
                self.export_to_json(None)

    def get_table_data(self):
        table_data = []
        for row_index in range(self.table.getRowCount()):
            row = {}
            for column_index in range(self.table.getColumnCount()):
                row[self.table.getColumnName(column_index)] = self.table.getValueAt(row_index, column_index)
            table_data.append(row)
        return table_data

    def getTabCaption(self):
        return "Findings Tracker"

    def getUiComponent(self):
        return self.panel

    def createMenuItems(self, invocation):
        self.invocation = invocation
        menu_items = ArrayList()
        menu_item = JMenuItem("Send to Findings Tracker", actionPerformed=self.send_to_findings_tracker)
        menu_items.add(menu_item)
        return menu_items

    def send_to_findings_tracker(self, event):
        message_info = self.invocation.getSelectedMessages()[0]

        host = message_info.getHttpService().getHost()

        request = message_info.getRequest()
        response = message_info.getResponse()

        request_base64 = base64.b64encode(request).decode()
        response_base64 = base64.b64encode(response).decode()

        finding_data = [self.table.getRowCount() + 1, "", "New", "Add Description", host, "", request_base64, response_base64]
        self.table.getModel().addRow(finding_data)

    def show_request_response(self, row):
        request_base64 = self.table.getValueAt(row, 6)
        response_base64 = self.table.getValueAt(row, 7)

        request = base64.b64decode(request_base64)
        response = base64.b64decode(response_base64)

        message_controller = self.MessageController(request, response, self.helpers)

        dialog = JDialog()
        dialog.setTitle("Request & Response")
        dialog.setSize(1200, 600)
        dialog.setLocationRelativeTo(None)

        main_panel = JPanel()
        main_panel.setLayout(GridLayout(1, 2))

        # Request panel
        request_panel = JPanel()
        request_panel.setLayout(BorderLayout())
        request_label = JLabel("Request")
        request_label.setFont(Font("Dialog", Font.BOLD, 16))
        request_label.setBorder(EmptyBorder(10, 10, 0, 0))
        request_panel.add(request_label, BorderLayout.NORTH)

        request_editor = self.callbacks.createMessageEditor(self, False)
        request_editor.setMessage(request, True)
        request_panel.add(request_editor.getComponent(), BorderLayout.CENTER)

        main_panel.add(request_panel)

        # Response panel
        response_panel = JPanel()
        response_panel.setLayout(BorderLayout())
        response_label = JLabel("Response")
        response_label.setFont(Font("Dialog", Font.BOLD, 16))
        response_label.setBorder(EmptyBorder(10, 10, 0, 0))
        response_panel.add(response_label, BorderLayout.NORTH)

        response_editor = self.callbacks.createMessageEditor(self, False)
        response_editor.setMessage(response, False)
        response_panel.add(response_editor.getComponent(), BorderLayout.CENTER)

        main_panel.add(response_panel)

        dialog.add(main_panel)
        dialog.setVisible(True)

    def owasp_dropdown(self):
        owasp_options = ["A01: Broken Access Control", "A02: Cryptographic Failures", "A03: Injection", "A04: Insecure Design", "A05: Security Misconfiguration", "A06: Vulnerable and Outdated Components", "A07: Identification and Authentication Failures", "A08: Software and Data Integrity Failures", "A09: Security Logging and Monitoring Failures", "A10: Server Side Request Forgery (SSRF)"]
        owasp_dropdown = JComboBox(owasp_options)
        return owasp_dropdown
    
    def status_dropdown(self):
        class StatusRenderer(DefaultListCellRenderer):
            def getListCellRendererComponent(self, listbox, value, index, isSelected, cellHasFocus):
                component = super(StatusRenderer, self).getListCellRendererComponent(listbox, value, index, isSelected, cellHasFocus)
                if value == "Remediated":
                    component.setBackground(BsGreen)
                elif value == "Fail":
                    component.setBackground(BsRed)
                elif value == "Warning":
                    component.setBackground(BsOrange)
                elif value == "Exception":
                    component.setBackground(BsYellow)
                elif value == "False Positive":
                    component.setBackground(BsGray)
                else:
                    component.setBackground(Color.WHITE)
                return component
    
        status_options = ["New", "Fail", "Warning", "Exception", "Remediated", "False Positive"]
        status_dropdown = JComboBox(status_options)
        status_dropdown.setRenderer(StatusRenderer())
        return status_dropdown
    
    def add_finding(self, event):
        finding_data = [self.table.getRowCount() + 1, "", "New", "Add Description", "", "", "", ""]
        self.table.getModel().addRow(finding_data)

    def remove_finding(self, row):
        def remove_row():
            self.table.getModel().removeRow(row)

        SwingUtilities.invokeLater(remove_row)

    def export_to_json(self, event):
        findings_tracker_directory = get_findings_tracker_directory()
        file_chooser = JFileChooser()
        file_chooser.setCurrentDirectory(File(findings_tracker_directory))
        file_chooser.setDialogTitle("Export to JSON")
        file_chooser.setFileSelectionMode(JFileChooser.FILES_ONLY)
    
        filter = FileNameExtensionFilter("JSON Files", ["json"])
        file_chooser.addChoosableFileFilter(filter)
        file_chooser.setFileFilter(filter)
    
        # Set the default file name with the current date and time
        current_time = datetime.now()
        default_file_name = current_time.strftime("%Y-%m-%d-%H-%M-%S-findings.json")
        file_chooser.setSelectedFile(File(default_file_name))
    
        result = file_chooser.showSaveDialog(None)
    
        if result == JFileChooser.APPROVE_OPTION:
            file_path = file_chooser.getSelectedFile().getAbsolutePath()
            if not file_path.lower().endswith(".json"):
                file_path += ".json"
    
            table_data = []
            for row_index in range(self.table.getRowCount()):
                row = {}
                for column_index in range(self.table.getColumnCount()):
                    row[self.table.getColumnName(column_index)] = self.table.getValueAt(row_index, column_index)
                table_data.append(row)
    
            with open(file_path, "w") as json_file:
                table_data = self.get_table_data()
                json.dump(table_data, json_file, indent=4)
                self.last_exported_file = file_path
                JOptionPane.showMessageDialog(None, "Table exported successfully to JSON file.")
                print("Table exported successfully to JSON file", self.last_exported_file)
    
    def import_from_json(self, event):
        findings_tracker_directory = get_findings_tracker_directory()
        file_chooser = JFileChooser()
        file_chooser.setCurrentDirectory(File(findings_tracker_directory))
        file_chooser.setDialogTitle("Import from JSON")
        file_chooser.setFileSelectionMode(JFileChooser.FILES_ONLY)

        filter = FileNameExtensionFilter("JSON Files", ["json"])
        file_chooser.addChoosableFileFilter(filter)
        file_chooser.setFileFilter(filter)

        result = file_chooser.showOpenDialog(None)

        if result == JFileChooser.APPROVE_OPTION:
            file_path = file_chooser.getSelectedFile().getAbsolutePath()
            if not file_path.lower().endswith(".json"):
                file_path += ".json"

            with open(file_path, "r") as json_file:
                table_data = json.load(json_file)

                # Clear the existing table data
                table_model = self.table.getModel()
                table_model.setRowCount(0)

                # Set the import flag to True
                self.is_importing = True

                # Load the imported data into the table
                for row in table_data:
                    row_data = [row[column_name] for column_name in self.columns]
                    table_model.addRow(row_data)

                # Reset the import flag to False
                self.is_importing = False

                # Save the imported file name and location for future automatic saves
                self.last_exported_file = file_path

                JOptionPane.showMessageDialog(None, "Table imported successfully from JSON file.")

    # Implement IMessageEditorController methods
    def getHttpService(self):
        return self.invocation.getSelectedMessages()[0].getHttpService()
    
    def getRequest(self):
        return self.invocation.getSelectedMessages()[0].getRequest()
    
    def getResponse(self):
        return self.invocation.getSelectedMessages()[0].getResponse()
