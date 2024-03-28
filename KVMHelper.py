#!/usr/bin/python3

from PyQt6.QtWidgets import *
from PyQt6 import uic, QtCore

from PyQt6.QtGui import QIcon, QIntValidator
import subprocess, os, xmltodict, re
from pathlib import Path

DEVICE_FILE_CONTENT = "<hostdev mode='subsystem' type='usb' managed='no'>\n\
                       \t<source>\n\
                           \t\t<vendor id='0x0000'/>\n\
                           \t\t<product id='0x0000'/>\n\
                       \t</source>\n\
                       </hostdev>"

DEVICE_STATUS_HOST = True
DEVICE_STATUS_VM = False

VM_STATUS_RUNNING = True
VM_STATUS_STOPPED = False

class USBDeviceList(QDialog):
    def __init__(self, mainWindow):
        super().__init__()
        self.setWindowTitle("USB Devices")
        self.setWindowIcon(QIcon("icons/app.png"))
        self.resize(500, 500)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()

        self.listWidget = QListWidget()
        self.listWidget.itemSelectionChanged.connect(self.list_selection_changed)
        self.listWidget.itemDoubleClicked.connect(self.accept)

        self.name_layout = QHBoxLayout()
        
        self.name_lbl = QLabel()
        self.name_lbl.setText("<html><head/><body><p align=\"center\"><span style=\" font-size:10pt; font-weight:600;\">Name:</span></p></body></html>")
        self.name_lbl.setMinimumWidth(50)
        self.name_lbl.setMaximumWidth(50)

        self.name_txt = QLineEdit()

        self.name_layout.addWidget(self.name_lbl)
        self.name_layout.addWidget(self.name_txt)

        self.layout.addWidget(self.listWidget)
        self.layout.addLayout(self.name_layout)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        self.mainWindow = mainWindow

        self.populate_list()

    def list_selection_changed(self):
        selected = self.listWidget.selectedItems()
        if len(selected) == 0:
            return
        device = selected[0].text()
        self.name_txt.setText(device[device.find(" ") + 1:])

    def run_lsusb(self):
        rgx = "(?<=id ).*"
        res = self.mainWindow.run_command(["lsusb"])
        return re.findall(rgx, res)

    def populate_list(self):
        entries = self.run_lsusb()
        for entry in entries:
            if self.mainWindow.device_id_exists(entry.strip().lower()[:9].strip()):
                continue
            self.listWidget.addItem(entry)

    def get_selected_usb_device(self):
        selected = self.listWidget.selectedItems()
        if len(selected) == 0:
            return None
        return USBDevice(self.name_txt.text(), selected[0].text(), self.mainWindow)

class USBDevice:
    def __init__(self, name, device_string, mainWindow):
        self.layout = QHBoxLayout()

        self.name_lbl = QLabel()
        self.name_lbl.setText(name)
        self.name_lbl.setMinimumWidth(120)
        self.name_lbl.setObjectName(name + "_name_lbl")

        self.tgl_btn = QPushButton()
        self.tgl_btn.setText("Toggle")
        self.tgl_btn.setMinimumWidth(70)
        self.tgl_btn.setMaximumWidth(70)
        self.tgl_btn.setObjectName(name + "_tgl_btn")
        self.tgl_btn.clicked.connect(self.tgl_btn_clicked)

        self.status_lbl = QLabel()
        self.status_lbl.setText("<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:600; color:#00aa00;\">Host</span></p></body></html>")
        self.status_lbl.setMinimumWidth(70)
        self.status_lbl.setMaximumWidth(70)
        self.status_lbl.setObjectName(name + "_status_lbl")

        self.remove_btn = QPushButton()
        self.remove_btn.setMaximumWidth(24)
        self.remove_btn.setStyleSheet("QPushButton { color: red; font-weight: bold; }")
        self.remove_btn.setIcon(QIcon("icons/delete.png"))
        self.remove_btn.setObjectName(name + "_remove_btn")
        self.remove_btn.clicked.connect(self.remove_btn_clicked)

        self.layout.addWidget(self.name_lbl)
        self.layout.addWidget(self.tgl_btn)
        self.layout.addWidget(self.status_lbl)
        self.layout.addWidget(self.remove_btn)
        self.layout.setObjectName(name + "_h_layout")

        self.mainWindow = mainWindow
        self.deviceString = device_string
        self.deviceID = device_string[0:9].strip()
        self.deviceName = name.replace("/", "_")
        self.added = False
        self.deviceStatus = False

    def setStatusText(self, status):
        if status:
            self.deviceStatus = True
            self.status_lbl.setText("<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:600; color:#00aa00;\">Host</span></p></body></html>")
        else:
            self.deviceStatus = False
            self.status_lbl.setText("<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:600; color:#aa0000;\">VM</span></p></body></html>")

    def addToLayout(self, layout: QBoxLayout):
        if self.added:
            return
        self.added = True
        layout.addLayout(self.layout)
        self.mainWindow.resize(1, 1)

    def enable(self, enable = True):
        self.tgl_btn.setEnabled(enable)
        self.remove_btn.setEnabled(enable)

    def remove_btn_clicked(self):
        self.removeFromLayout(True)

    def tgl_btn_clicked(self):
        if self.deviceStatus:
            self.mainWindow.connect_device_to_vm(self)
            self.deviceStatus = False
        else:
            self.mainWindow.disconnect_device_from_vm(self)
            self.deviceStatus = True
        self.mainWindow.refresh()

    def removeFromLayout(self, delete = False):
        if not self.added:
            return
        self.added = False
        self._removeFromLayout(self.layout)
        self.mainWindow.resize(80, 80)
        if delete:
            self.mainWindow.delete_device_file(self)

    def _removeFromLayout(self, item):
        if hasattr(item, "layout"):
            if callable(item.layout):
                layout = item.layout()
        else:
            layout = None

        if hasattr(item, "widget"):
            if callable(item.widget):
                widget = item.widget()
        else:
            widget = None

        if widget:
            widget.setParent(None)
        elif layout:
            for i in reversed(range(layout.count())):
                self._removeFromLayout(layout.itemAt(i))

class UI(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("kvm_helper.ui", self)
        self.resize(80, 80)
        self.setWindowTitle("KVM USB Helper")
        self.setWindowIcon(QIcon("icons/app.png"))
        self.btnAddUSB.clicked.connect(self.show_usb_devices_list)

        onlyInt = QIntValidator()
        onlyInt.setRange(0, 99999)
        self.editRefreshSeconds.setValidator(onlyInt)
        self.editRefreshSeconds.setText("60")

        self.checkAutoRefresh.stateChanged.connect(self.check_auto_refresh_state_changed)

        self.btnRefresh.clicked.connect(self.btn_refresh_clicked)
        self.btnStartVM.clicked.connect(self.btn_start_vm_clicked)

        self._update_timer = QtCore.QTimer()
        self._update_timer.timeout.connect(self.update_timer_tick)
        self._update_timer.start(60000)
        self.check_auto_refresh_state_changed()

        self.device_list = []

        self.load_device_files()
        self.load_vm_info()

    def btn_start_vm_clicked(self):
        command = ["virsh", "start", self.get_vm_name()]
        print(self.run_command(command))
        self.refresh()

    def update_timer_tick(self):
        self.refresh()

    def refresh(self):
        for device in self.device_list:
            device.removeFromLayout()
        self.device_list.clear()
        self.load_device_files()
        self.load_vm_info()

    def btn_refresh_clicked(self):
        if self.checkAutoRefresh.isChecked():
            self._update_timer.stop()
            self._update_timer.start()
        self.refresh()

    def check_auto_refresh_state_changed(self):
        if self.checkAutoRefresh.isChecked():
            self._update_timer.start()
            self.editRefreshSeconds.setEnabled(True)
        else:
            self._update_timer.stop()
            self.editRefreshSeconds.setEnabled(False)

    def create_new_usb_device_passthrough_gui_block(self, device):
        self.device_list.append(device)
        self.device_list[len(self.device_list) - 1].addToLayout(self.verticalLayout)

    def show_usb_devices_list(self):
        dlg = USBDeviceList(self)
        if dlg.exec():
            device = dlg.get_selected_usb_device()
            if device == None:
                return
            if self.device_exists(device):
                return
            device.setStatusText(self.get_device_status(device))
            self.create_device_file(device)
            self.create_new_usb_device_passthrough_gui_block(device)
            self.btn_refresh_clicked()

    def load_device_files(self):
        files_list = os.listdir("./devices")
        vm_status = self.check_vm_status(self.get_vm_name())
        for file in files_list:
            device_file_path = ("./devices/" + file).strip()
            if not device_file_path.lower().endswith(".xml"):
                continue
            device_file = open(device_file_path, "r")
            xml_string = device_file.read()
            device_dict = xmltodict.parse(xml_string)
            vid = device_dict["hostdev"]["source"]["vendor"]["@id"].strip().lower()
            pid = device_dict["hostdev"]["source"]["product"]["@id"].strip().lower()
            if not vid.startswith("0x") or not pid.startswith("0x"):
                continue
            vid = vid[2:]
            pid = pid[2:]
            device_name = file.strip()[:-4]
            device = USBDevice(device_name, vid + ":" + pid, self)
            device.setStatusText(self.get_device_status(device))
            device.enable(vm_status)
            self.create_new_usb_device_passthrough_gui_block(device)
            device_file.close()

    def get_device_status(self, device):
        command = ["virsh", "dumpxml", self.get_vm_name()]
        if self.check_vm_status(self.get_vm_name()) == VM_STATUS_RUNNING:
            res = self.run_command(command)
            status = res.lower().find("<vendor id='0x" + device.deviceID[0:4] + "'/>") >= 0
            status = status and res.lower().find("<product id='0x" + device.deviceID[5:] + "'/>") >= 0
            if status:
                return DEVICE_STATUS_VM
            else:
                return DEVICE_STATUS_HOST
        else:
            return DEVICE_STATUS_HOST
    
    def create_device_file(self, device):
        device_file = open("./devices/" + device.deviceName + ".xml", "w")
        xml_string = DEVICE_FILE_CONTENT
        xml_dict = xmltodict.parse(xml_string)
        split = device.deviceID.find(":")
        vid = device.deviceID[:split].strip().lower()
        pid = device.deviceID[split + 1:].strip().lower()
        xml_dict["hostdev"]["source"]["vendor"]["@id"] = "0x" + vid
        xml_dict["hostdev"]["source"]["product"]["@id"] = "0x" + pid
        device_file.seek(0)
        device_file.truncate()
        xmltodict.unparse(xml_dict, device_file)
        device_file.close()

    def delete_device_file(self, device):
        device_file_path = "./devices/" + device.deviceName + ".xml"
        if not Path(device_file_path).is_file():
            print("Error, no file found: " + device_file_path)
            return
        os.remove(device_file_path)

    def connect_device_to_vm(self, device):
        command = ["virsh", "attach-device", self.get_vm_name(), "devices/" + device.deviceName + ".xml"]
        self.run_command(command)
        self.refresh()

    def disconnect_device_from_vm(self, device):
        command = ["virsh", "detach-device", self.get_vm_name(), "devices/" + device.deviceName + ".xml"]
        self.run_command(command)
        self.refresh()
    
    def device_exists(self, device):
        files_list = os.listdir("./devices")
        for file in files_list:
            device_file = device.deviceName + ".xml"
            if file.lower() == device_file.lower().strip():
                print("Device exists: " + device_file)
                return True
            device_file_path = ("./devices/" + file).strip()
            if not device_file_path.lower().endswith(".xml"):
                continue
            device_file = open(device_file_path, "r")
            xml_string = device_file.read()
            device_dict = xmltodict.parse(xml_string)
            vid = device_dict["hostdev"]["source"]["vendor"]["@id"].strip().lower()
            pid = device_dict["hostdev"]["source"]["product"]["@id"].strip().lower()
            if not vid.startswith("0x") or not pid.startswith("0x"):
                continue
            vid = vid[2:]
            pid = pid[2:]
            if device.deviceID.lower() == (vid + ":" + pid):
                print("Device exists: " + vid + ":" + pid)
                return True
        return False
    
    def device_id_exists(self, deviceID):
        files_list = os.listdir("./devices")
        for file in files_list:
            device_file_path = ("./devices/" + file).strip()
            if not device_file_path.lower().endswith(".xml"):
                continue
            device_file = open(device_file_path, "r")
            xml_string = device_file.read()
            device_dict = xmltodict.parse(xml_string)
            vid = device_dict["hostdev"]["source"]["vendor"]["@id"].strip().lower()
            pid = device_dict["hostdev"]["source"]["product"]["@id"].strip().lower()
            if not vid.startswith("0x") or not pid.startswith("0x"):
                continue
            vid = vid[2:]
            pid = pid[2:]
            if deviceID.lower().strip() == (vid + ":" + pid):
                return True
        return False

    def get_vm_name(self):
        vm_file_path = "./vm_name"
        vm_name_file = open(vm_file_path, "r")
        vm_name = vm_name_file.read()
        vm_name_file.close()
        return vm_name

    def run_command(self, command, to_lower=True):
        result = subprocess.run(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, text = True)
        res = result.stdout.strip()
        if to_lower:
            res = res.lower()
        return res

    def check_vm_status(self, vm_name):
        command = ["virsh", "list", "--all"]
        res = self.run_command(command, False)
        for line in res.split("\n"):
            if line.find(vm_name) >= 0 and line.lower().find("running") >= 0:
                return VM_STATUS_RUNNING
        return VM_STATUS_STOPPED

    def enable_gui(self, enabled = True):
        for device in self.device_list:
            device.enable(enabled)
        pass

    def load_vm_info(self):
        vm_name = self.get_vm_name()
        if self.check_vm_status(vm_name) == VM_STATUS_RUNNING:
            self.lblVM.setText("<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:600; color:#00aa00;\">VM Running (%s)</span></p></body></html>" % (vm_name))
            self.enable_gui(True)
            self.btnStartVM.setEnabled(False)
            self.btnAddUSB.setEnabled(True)
        else:
            self.lblVM.setText("<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:600; color:#aa0000;\">VM Not Running (%s)</span></p></body></html>" % (vm_name))
            self.enable_gui(False)
            self.btnStartVM.setEnabled(True)
            self.btnAddUSB.setEnabled(False)

app = QApplication([])
window = UI()
window.show()
app.exec()
