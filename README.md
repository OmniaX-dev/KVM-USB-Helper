# KVM-USB-Helper
 
A simple gui written in Python (with PyQt6) to help you pass USB Devices back and forth between the host OS (Linux) and a running VM (in KVM/QEMU).

 ![](Screenshot.png)
     
 The tool makes use of the `lsusb` command to list all available devices on the host OS, and uses the `virsh` command to comunicate with the VM. It also depends on the `pyqt6` and the `xmltodict` python libraries.
 You can run the tool via the `KVMHelper.sh` bash script.
