"""
X-Plane Plugin Manager
----------------------------
A desktop application for managing X-Plane plugins. Features include:
- Installing plugins from ZIP files or folders
- Backing up plugins to ZIP archives
- Disabling/enabling plugins
- Restoring plugins from backups
- Viewing plugin contents
- Managing plugin installations
- Logging all operations
- Maintaining persistent settings

The application provides a user-friendly interface for X-Plane users to manage their 
plugin installations without manually handling files and folders.

Author: Your Name
License: MIT
"""

import sys
import os
import shutil
import zipfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QFileDialog, QListWidget, QListWidgetItem, QStyle, QDialog, 
                             QLabel, QTextEdit, QSplitter, QToolTip, QMessageBox, QStatusBar)
from PyQt6.QtGui import QIcon, QColor, QBrush, QPainter, QPen, QPixmap, QCursor
from PyQt6.QtCore import QSettings, QSize, Qt, QTimer, QEvent, QPoint
from datetime import datetime

INITIAL_VERSION = "0.002"  # Starting version

class PluginManager(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize settings
        self.settings = QSettings("YourCompany", "XPlanePluginManager")
        
        # Get or set initial version
        self.version = self.settings.value("version", INITIAL_VERSION)
        if not self.version:
            self.version = INITIAL_VERSION
            self.settings.setValue("version", self.version)
        
        self.setWindowTitle(f"X-Plane Plugin Manager v{self.version}")
        self.setGeometry(100, 100, 800, 600)

        # Initialize status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Ready - v{self.version}")

        # Load other settings
        self.xplane_folder = self.settings.value("xplane_folder", "")
        self.backup_folder = self.settings.value("backup_folder", "")
        self.log_history = self.settings.value("log_history", [])

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QLabel {
                color: #2f3542;
                font-size: 13px;
            }
            QPushButton {
                background-color: #fff;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 8px 16px;
                color: #2f3542;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f1f2f6;
                border-color: #a4b0be;
            }
            QPushButton:pressed {
                background-color: #dcdde1;
            }
            QListWidget {
                background-color: #fff;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #f1f2f6;
                padding: 8px 4px;
                color: #2f3542;
            }
            QListWidget::item:selected {
                background-color: #f1f2f6;
                color: #2f3542;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
                color: #2f3542;
            }
            QTextEdit {
                background-color: #fff;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 13px;
            }
            QSplitter::handle {
                background-color: #dcdde1;
                height: 2px;
            }
        """)

        self.init_ui()
        self.load_log_history()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Create top bar with logo
        top_bar = QHBoxLayout()
        
        # X-Plane folder selection
        xplane_layout = QHBoxLayout()
        select_folder_btn = QPushButton("Select X-Plane Folder")
        select_folder_btn.setIcon(QIcon.fromTheme("folder-open", self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)))
        select_folder_btn.clicked.connect(self.select_xplane_folder)
        xplane_layout.addWidget(select_folder_btn)
        self.xplane_label = QLabel(f"X-Plane Folder: {self.xplane_folder}")
        xplane_layout.addWidget(self.xplane_label, 1)
        top_bar.addLayout(xplane_layout)

        # Add logo to top right
        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.jpg")
        # Scale the logo to 40x40 pixels while maintaining aspect ratio
        scaled_logo = logo_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_logo)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_bar.addWidget(logo_label)

        main_layout.addLayout(top_bar)

        # Backup folder selection
        backup_layout = QHBoxLayout()
        select_backup_btn = QPushButton("Select Backup Folder")
        select_backup_btn.setIcon(QIcon.fromTheme("folder-open", self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)))
        select_backup_btn.clicked.connect(self.select_backup_folder)
        backup_layout.addWidget(select_backup_btn)
        self.backup_label = QLabel(f"Backup Folder: {self.backup_folder}")
        backup_layout.addWidget(self.backup_label, 1)
        main_layout.addLayout(backup_layout)

        # Splitter for plugin list and output panel
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Plugin list
        self.plugin_list = QListWidget()
        splitter.addWidget(self.plugin_list)

        # Output panel
        self.output_panel = QTextEdit()
        self.output_panel.setReadOnly(True)
        splitter.addWidget(self.output_panel)

        main_layout.addWidget(splitter)

        # Buttons
        button_layout = QHBoxLayout()
        restore_btn = QPushButton("Restore Plugin")
        restore_btn.setIcon(QIcon.fromTheme("edit-undo", self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)))
        restore_btn.clicked.connect(self.show_restore_dialog)
        button_layout.addWidget(restore_btn)

        # Add Install Plugin button here
        install_btn = QPushButton("Install Plugin")
        install_btn.setIcon(QIcon.fromTheme("document-new", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)))
        install_btn.clicked.connect(self.install_plugin)
        button_layout.addWidget(install_btn)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.setIcon(QIcon.fromTheme("edit-clear", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)))
        clear_log_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_log_btn)

        exit_btn = QPushButton("Exit")
        exit_btn.setIcon(QIcon.fromTheme("application-exit", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)))
        exit_btn.clicked.connect(self.close)
        button_layout.addWidget(exit_btn)
        main_layout.addLayout(button_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        if self.xplane_folder:
            self.load_plugins()

    def log_output(self, message):
        # Update both log and status bar
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.output_panel.append(log_message)
        self.status_bar.showMessage(message, 5000)  # Show in status bar for 5 seconds
        
        self.log_history.append(log_message)
        if len(self.log_history) > MAX_LOG_LINES:
            self.log_history = self.log_history[-MAX_LOG_LINES:]
        self.save_log_history()

    def load_log_history(self):
        self.output_panel.clear()
        for message in self.log_history:
            self.output_panel.append(message)

    def save_log_history(self):
        self.settings.setValue("log_history", self.log_history)

    def select_xplane_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select X-Plane Folder")
        if folder:
            self.xplane_folder = folder
            self.settings.setValue("xplane_folder", folder)
            self.xplane_label.setText(f"X-Plane Folder: {folder}")
            self.status_bar.showMessage(f"X-Plane folder set to: {folder}", 5000)
            self.load_plugins()

    def select_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self.backup_folder = folder
            self.settings.setValue("backup_folder", folder)
            self.backup_label.setText(f"Backup Folder: {folder}")
            self.status_bar.showMessage(f"Backup folder set to: {folder}", 5000)

    def load_plugins(self):
        plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins")
        if not os.path.exists(plugin_path):
            return

        self.plugin_list.clear()
        plugins = []
        for folder in os.listdir(plugin_path):
            if os.path.isdir(os.path.join(plugin_path, folder)):
                plugins.append(folder)
        
        # Sort plugins alphabetically
        plugins.sort(key=str.lower)

        for folder in plugins:
            item = QListWidgetItem(folder)
            self.plugin_list.addItem(item)

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            delete_btn = QPushButton()
            delete_btn.setIcon(QIcon.fromTheme("edit-delete", self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)))
            delete_btn.setToolTip("Delete Plugin")
            delete_btn.clicked.connect(lambda _, f=folder: self.delete_plugin(f))

            backup_btn = QPushButton()
            backup_btn.setIcon(QIcon.fromTheme("document-save", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)))
            backup_btn.setToolTip("Backup Plugin to Zip")
            backup_btn.clicked.connect(lambda _, f=folder: self.backup_plugin(f))

            disable_btn = QPushButton()
            disable_btn.setIcon(QIcon.fromTheme("dialog-cancel", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)))
            disable_btn.setToolTip("Disable Plugin")
            disable_btn.clicked.connect(lambda _, f=folder: self.disable_plugin(f))

            contents_btn = QPushButton()
            contents_btn.setIcon(QIcon.fromTheme("folder", self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)))
            contents_btn.setToolTip("Show Folder Contents")
            contents_btn.clicked.connect(lambda _, f=folder: self.show_folder_contents(f))

            layout.addStretch()
            layout.addWidget(delete_btn)
            layout.addWidget(backup_btn)
            layout.addWidget(disable_btn)
            layout.addWidget(contents_btn)

            for btn in (delete_btn, backup_btn, disable_btn, contents_btn):
                btn.setFixedSize(QSize(32, 32))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 16px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 0, 0, 0.05);
                    }
                    QPushButton:pressed {
                        background-color: rgba(0, 0, 0, 0.1);
                    }
                """)

            self.plugin_list.setItemWidget(item, widget)

    def delete_plugin(self, folder):
        self.increment_version()  # Increment version on delete
        self.status_bar.showMessage(f"Deleting plugin: {folder}...")
        plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", folder)
        shutil.rmtree(plugin_path)
        self.load_plugins()

    def backup_plugin(self, folder):
        self.increment_version()  # Increment version on backup
        self.status_bar.showMessage(f"Backing up plugin: {folder}...")
        plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", folder)
        if not os.path.exists(plugin_path):
            self.log_output(f"Error: Plugin folder {folder} not found.")
            return

        if self.backup_folder:
            backup_path = self.backup_folder
        else:
            backup_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup")

        os.makedirs(backup_path, exist_ok=True)

        zip_filename = f"{folder}.zip"
        zip_path = os.path.join(backup_path, zip_filename)
        counter = 1
        while os.path.exists(zip_path):
            zip_filename = f"{folder}_{counter}.zip"
            zip_path = os.path.join(backup_path, zip_filename)
            counter += 1

        self.log_output(f"Backing up plugin: {folder}")
        self.log_output(f"Source folder: {plugin_path}")
        self.log_output(f"Creating zip file: {zip_path}")

        try:
            total_size = 0
            for root, _, files in os.walk(plugin_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

            self.log_output(f"Total size before compression: {total_size} bytes")

            if total_size == 0:
                self.log_output("Warning: Plugin folder is empty.")
                return

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(plugin_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, plugin_path)
                        zipf.write(file_path, arcname)
                        self.log_output(f"Added to zip: {arcname}")

            zip_size = os.path.getsize(zip_path)
            self.log_output(f"Total size after compression: {zip_size} bytes")
            
            if total_size > 0:
                compression_ratio = (1 - (zip_size / total_size)) * 100
                self.log_output(f"Compression ratio: {compression_ratio:.2f}%")
            else:
                self.log_output("Compression ratio: N/A (original size was 0 bytes)")

            self.log_output(f"Plugin {folder} backed up successfully to {zip_path}")
        except Exception as e:
            self.log_output(f"Error backing up plugin {folder}: {str(e)}")

    def disable_plugin(self, folder):
        self.increment_version()  # Increment version on disable
        self.status_bar.showMessage(f"Disabling plugin: {folder}...")
        plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", folder)
        if self.backup_folder:
            backup_path = self.backup_folder
        else:
            backup_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup")
        os.makedirs(backup_path, exist_ok=True)
        shutil.move(plugin_path, os.path.join(backup_path, folder))
        self.load_plugins()

    def show_restore_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Restore Plugin")
        dialog.setGeometry(200, 200, 500, 400)

        layout = QVBoxLayout(dialog)

        if self.backup_folder:
            backup_path = self.backup_folder
        else:
            backup_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup")

        if not os.path.exists(backup_path):
            layout.addWidget(QLabel("No backups found."))
        else:
            backup_list = QListWidget()
            backup_list.setMouseTracking(True)  # Enable mouse tracking
            backup_list.viewport().installEventFilter(self)  # Install event filter
            layout.addWidget(backup_list)

            for item in os.listdir(backup_path):
                item_path = os.path.join(backup_path, item)
                if os.path.isdir(item_path) or (os.path.isfile(item_path) and item.endswith('.zip')):
                    list_item = QListWidgetItem(item)
                    backup_list.addItem(list_item)

                    if item.endswith('.zip'):
                        # Create a hashed background for zip files
                        pixmap = self.create_hash_background(backup_list.viewport().width(), 30)
                        list_item.setBackground(QBrush(pixmap))

                    widget = QWidget()
                    item_layout = QHBoxLayout(widget)
                    item_layout.setContentsMargins(0, 0, 0, 0)

                    restore_btn = QPushButton()
                    restore_btn.setIcon(QIcon.fromTheme("edit-undo", self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)))
                    restore_btn.setToolTip("Restore Plugin")
                    restore_btn.clicked.connect(lambda _, i=item: self.restore_plugin(i))

                    delete_btn = QPushButton()
                    delete_btn.setIcon(QIcon.fromTheme("edit-delete", self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)))
                    delete_btn.setToolTip("Delete Backup")
                    delete_btn.clicked.connect(lambda _, i=item: self.delete_backup(i))

                    item_layout.addStretch()
                    item_layout.addWidget(restore_btn)
                    item_layout.addWidget(delete_btn)

                    if item.endswith('.zip'):
                        recover_btn = QPushButton()
                        recover_btn.setIcon(QIcon.fromTheme("archive-extract", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)))
                        recover_btn.setToolTip("Recover from Zip")
                        recover_btn.clicked.connect(lambda _, i=item: self.recover_from_zip(i))
                        item_layout.addWidget(recover_btn)

                        view_btn = QPushButton()
                        view_btn.setIcon(QIcon.fromTheme("document-preview", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView)))
                        view_btn.setToolTip("View Zip Contents")
                        view_btn.clicked.connect(lambda _, i=item: self.view_zip_contents(i))
                        item_layout.addWidget(view_btn)

                    backup_list.setItemWidget(list_item, widget)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def create_hash_background(self, width, height):
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.white)
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.SolidLine))
        
        # Draw diagonal lines to create a hash pattern
        for i in range(0, width + height, 5):
            painter.drawLine(i, 0, 0, i)
            painter.drawLine(i - height, height, width, i - width)
        
        painter.end()
        return pixmap

    def restore_plugin(self, item):
        self.increment_version()  # Increment version on restore
        self.status_bar.showMessage(f"Restoring plugin: {item}...")
        if self.backup_folder:
            backup_path = os.path.join(self.backup_folder, item)
        else:
            backup_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup", item)
        
        self.log_output(f"Restoring plugin: {item}")
        self.log_output(f"Source: {backup_path}")

        if item.endswith('.zip'):
            # Extract plugin name
            plugin_name = item[:-4]  # Remove .zip extension
            plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", plugin_name)
            self.log_output(f"Extracting to: {plugin_path}")
            
            try:
                with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                    zip_ref.extractall(plugin_path)
                    for file in zip_ref.namelist():
                        self.log_output(f"Extracted: {file}")
                message = f"Plugin {plugin_name} restored successfully from zip."
                self.log_output(message)
                self.show_popup(message)
            except Exception as e:
                message = f"Error restoring plugin from zip {item}: {str(e)}"
                self.log_output(message)
                self.show_popup(message)
        else:
            plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", item)
            self.log_output(f"Moving to: {plugin_path}")
            try:
                shutil.move(backup_path, plugin_path)
                message = f"Plugin {item} restored successfully."
                self.log_output(message)
                self.show_popup(message)
            except Exception as e:
                message = f"Error restoring plugin {item}: {str(e)}"
                self.log_output(message)
                self.show_popup(message)
        
        self.load_plugins()

    def delete_backup(self, item):
        if self.backup_folder:
            backup_path = os.path.join(self.backup_folder, item)
        else:
            backup_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup", item)
        
        self.log_output(f"Deleting backup: {item}")
        self.log_output(f"Deleting path: {backup_path}")
        
        try:
            if os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            else:
                os.remove(backup_path)
            self.log_output(f"Backup {item} deleted successfully.")
        except Exception as e:
            self.log_output(f"Error deleting backup {item}: {str(e)}")
        
        self.show_restore_dialog()

    def recover_from_zip(self, zip_file):
        if self.backup_folder:
            zip_path = os.path.join(self.backup_folder, zip_file)
        else:
            zip_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup", zip_file)
        
        self.log_output(f"Recovering plugin from zip: {zip_file}")
        self.log_output(f"Zip file path: {zip_path}")

        # Extract plugin name
        plugin_name = zip_file[:-4]  # Remove .zip extension

        plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", plugin_name)

        self.log_output(f"Extracting to: {plugin_path}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                if os.path.exists(plugin_path):
                    self.log_output(f"Warning: Plugin directory {plugin_name} already exists. Overwriting...")
                    shutil.rmtree(plugin_path)
                
                os.makedirs(plugin_path)
                zip_ref.extractall(plugin_path)
                
                for file in zip_ref.namelist():
                    self.log_output(f"Extracted: {file}")

            message = f"Plugin {plugin_name} recovered successfully from {zip_file}"
            self.log_output(message)
            self.show_popup(message)
        except Exception as e:
            message = f"Error recovering plugin from {zip_file}: {str(e)}"
            self.log_output(message)
            self.show_popup(message)

        self.load_plugins()

    def show_popup(self, message, duration=3000):
        popup = QDialog(self)
        popup.setWindowTitle("Operation Complete")
        
        popup.setStyleSheet("""
            QDialog {
                background-color: #f5f6fa;
                border: 1px solid #dcdde1;
                border-radius: 8px;
            }
            QLabel {
                color: #2f3542;
                font-size: 13px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout()
        label = QLabel(message)
        layout.addWidget(label)
        popup.setLayout(layout)
        popup.setGeometry(300, 300, 250, 150)

        # Close the popup after the specified duration
        QTimer.singleShot(duration, popup.close)

        popup.show()

    def show_folder_contents(self, folder):
        plugin_path = os.path.join(self.xplane_folder, "Resources", "plugins", folder)
        if not os.path.exists(plugin_path):
            self.show_popup(f"Error: Plugin folder {folder} not found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Contents of {folder}")
        dialog.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout(dialog)

        content_text = QTextEdit()
        content_text.setReadOnly(True)
        layout.addWidget(content_text)

        for root, dirs, files in os.walk(plugin_path):
            level = root.replace(plugin_path, '').count(os.sep)
            indent = ' ' * 4 * level
            content_text.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for file in files:
                content_text.append(f"{sub_indent}{file}")

        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.clicked.connect(lambda: QFileDialog.getExistingDirectory(dialog, "Open Folder", plugin_path))
        layout.addWidget(open_folder_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def view_zip_contents(self, zip_file):
        if self.backup_folder:
            zip_path = os.path.join(self.backup_folder, zip_file)
        else:
            zip_path = os.path.join(self.xplane_folder, "Resources", "plugins", "backup", zip_file)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Contents of {zip_file}")
        dialog.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout(dialog)

        content_text = QTextEdit()
        content_text.setReadOnly(True)
        layout.addWidget(content_text)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    content_text.append(file)
        except Exception as e:
            content_text.append(f"Error reading zip file: {str(e)}")

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.HoverMove:
            backup_list = source.parent()
            pos = event.position().toPoint()  # Convert QPointF to QPoint
            item = backup_list.itemAt(pos)
            if item and item.text().endswith('.zip'):
                QToolTip.showText(QCursor.pos(), item.text(), backup_list.viewport())
            else:
                QToolTip.hideText()
        elif event.type() == QEvent.Type.Leave:
            QToolTip.hideText()
        return super().eventFilter(source, event)

    def clear_log(self):
        self.output_panel.clear()
        self.log_history = []
        self.save_log_history()
        self.log_output("Log cleared.")

    def install_plugin(self):
        self.increment_version()  # Increment version on installation
        self.status_bar.showMessage("Select a plugin to install...")
        # Create file dialog that accepts both folders and zip files
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Plugin files (*.zip);;All files (*)")
        dialog.setViewMode(QFileDialog.ViewMode.Detail)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        
        # Add button to select folder
        folderButton = dialog.findChild(QPushButton, "folderButton")
        if not folderButton:
            folderButton = QPushButton("Select Folder", dialog)
            dialog.layout().addWidget(folderButton)
            folderButton.clicked.connect(lambda: self.handle_folder_selection(dialog))

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                if os.path.isfile(file_path) and file_path.lower().endswith('.zip'):
                    self.install_from_zip(file_path)
                elif os.path.isdir(file_path):
                    self.install_from_folder(file_path)

    def handle_folder_selection(self, dialog):
        folder = QFileDialog.getExistingDirectory(self, "Select Plugin Folder")
        if folder:
            self.install_from_folder(folder)
            dialog.close()

    def install_from_zip(self, zip_path):
        try:
            # Extract plugin name from zip file (remove .zip extension)
            plugin_name = os.path.splitext(os.path.basename(zip_path))[0]
            target_dir = os.path.join(self.xplane_folder, "Resources", "plugins", plugin_name)

            # Check if plugin already exists
            if os.path.exists(target_dir):
                reply = QMessageBox.question(self, 'Plugin Exists', 
                    f'Plugin "{plugin_name}" already exists. Do you want to replace it?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    shutil.rmtree(target_dir)
                else:
                    return

            # Create target directory
            os.makedirs(target_dir, exist_ok=True)

            # Extract zip contents
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)

            self.log_output(f"Successfully installed plugin from zip: {plugin_name}")
            self.show_popup(f"Plugin {plugin_name} installed successfully")
            self.load_plugins()

        except Exception as e:
            error_msg = f"Error installing plugin from zip: {str(e)}"
            self.log_output(error_msg)
            self.show_popup(error_msg)

    def install_from_folder(self, folder_path):
        try:
            plugin_name = os.path.basename(folder_path)
            target_dir = os.path.join(self.xplane_folder, "Resources", "plugins", plugin_name)

            # Check if plugin already exists
            if os.path.exists(target_dir):
                reply = QMessageBox.question(self, 'Plugin Exists', 
                    f'Plugin "{plugin_name}" already exists. Do you want to replace it?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    shutil.rmtree(target_dir)
                else:
                    return

            # Copy folder contents
            shutil.copytree(folder_path, target_dir, dirs_exist_ok=True)

            self.log_output(f"Successfully installed plugin from folder: {plugin_name}")
            self.show_popup(f"Plugin {plugin_name} installed successfully")
            self.load_plugins()

        except Exception as e:
            error_msg = f"Error installing plugin from folder: {str(e)}"
            self.log_output(error_msg)
            self.show_popup(error_msg)

    def increment_version(self):
        """Increment version number by 0.001"""
        try:
            current = float(self.version)
            new_version = f"{current + 0.001:.3f}"
            self.version = new_version
            self.settings.setValue("version", new_version)
            self.setWindowTitle(f"X-Plane Plugin Manager v{new_version}")
            self.status_bar.showMessage(f"Version updated to v{new_version}")
            return new_version
        except ValueError:
            return self.version

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PluginManager()
    window.show()
    sys.exit(app.exec())
