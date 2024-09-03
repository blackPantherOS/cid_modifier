#!/usr/bin/python3

#*********************************************************************************************************
#*   __     __               __     ______                __   __                      _______ _______   *
#*  |  |--.|  |.---.-..----.|  |--.|   __ \.---.-..-----.|  |_|  |--..-----..----.    |       |     __|  *
#*  |  _  ||  ||  _  ||  __||    < |    __/|  _  ||     ||   _|     ||  -__||   _|    |   -   |__     |  *
#*  |_____||__||___._||____||__|__||___|   |___._||__|__||____|__|__||_____||__|      |_______|_______|  *
#*http://www.blackpantheros.eu | http://www.blackpanther.hu - kbarcza[]blackpanther.hu * Charles K Barcza*
#*************************************************************************************(c)2002-2024********
# License: GPLv3
# Does not work on fake chinese cards - used at your own risk!
# sdinfo.sh is a smart script reading info of SD Cards

import os
import time
import fcntl
import struct
import subprocess

ioctl_commands = [
    0x12345678,  # Example IOCTL 1
    0x87654321,  # Example IOCTL 2
    0xABCD1234,  # Example IOCTL 3
]

def progress_indicator(duration=3, interval=0.5):
    for _ in range(int(duration / interval)):
        print(".", end="", flush=True)
        time.sleep(interval)
    print()

def find_cid_file():
    mmc_host_path = "/sys/class/mmc_host"

    try:
        for host in os.listdir(mmc_host_path):
                mmc_path = os.path.join(mmc_host_path, host)
        
                for device in os.listdir(mmc_path):
                    cid_path = os.path.join(mmc_path, device, "cid")
                    if os.path.exists(cid_path):
                        return cid_path
    except Exception as e:
        print(f"Failed access to MMC card: {e}")

    return None

def read_cid(cid_file):
    """CID kiolvasása a fájlból."""
    try:
        with open(cid_file, "r") as f:
            cid = f.read().strip()
        return cid
    except Exception as e:
        print(f"Failed to read CID: {e}")
        return None

def check_write_protection_sysfs():
    """Ellenőrzi, hogy az eszköz írásvédett-e a sysfs (/sys/block/mmcblk0/ro) fájl segítségével."""
    print("Checking write protection", end="")
    progress_indicator()
    
    try:
        with open("/sys/block/mmcblk0/ro", "r") as f:
            ro_status = f.read().strip()
        if ro_status == '1':
            print("Device is write-protected.")
            return True
        else:
            print("Device is not write-protected.")
            return False
    except Exception as e:
        print(f"Failed to check write protection: {e}")
        return None

def disable_write_protection():
    print("Attempting to disable write protection", end="")
    progress_indicator()
    
    try:
        result = subprocess.run(['sudo', 'hdparm', '-r0', '/dev/mmcblk0'], capture_output=True, text=True)
        if 'readonly' not in result.stdout.lower():
            print("Write protection successfully disabled.")
            return True
        else:
            print("Failed to disable write protection.")
            return False
    except Exception as e:
        print(f"Failed to disable write protection: {e}")
        return False

def send_ioctl_cmd(fd, command):
    """IOCTL parancs küldése az adott command segítségével."""
    try:
        fcntl.ioctl(fd, command)
        print(f"IOCTL command {hex(command)} sent successfully.")
        return True
    except Exception as e:
        print(f"Failed to send IOCTL command {hex(command)}: {e}")
        return False

def write_new_cid(fd, new_cid_hex):
    """Új CID írása a megfelelő lépésekkel."""
    new_cid_bytes = bytes.fromhex(new_cid_hex)
    
    if len(new_cid_bytes) != 16:
        raise ValueError("CID must be 16 bytes (32 hexadecimal characters)")
        
    try:
        with open("/dev/mmcblk0", "wb") as f:
            if write_new_cid(f.fileno(), new_cid):
                print("CID successfully written.")
            else:
                print("CID writing failed with vendor mode approach, trying IOCTL commands.")
                ioctl_commands = [0x12345678, 0xabcdef12]  # Itt add meg a próbálni kívánt IOCTL parancsokat
                new_cid_bytes = bytes.fromhex(new_cid)
                
                for cmd in ioctl_commands:
                    print(f"Trying IOCTL command: {hex(cmd)}")
                    arg = struct.pack("16s", new_cid_bytes)
                    
                    try:
                        fcntl.ioctl(f.fileno(), cmd, arg)
                        print(f"CID successfully written with IOCTL command {hex(cmd)}!")
                        return
                    except Exception as e:
                        print(f"Failed to write CID with IOCTL command {hex(cmd)}: {e}")
                
                print("All IOCTL commands failed.")

    except Exception as e:
        print(f"Failed to open device for writing: {e}")
        return


def main():
    print("Starting CID modification process...")

    print("Locating CID file", end="")
    progress_indicator()

    cid_file = find_cid_file()
    if not cid_file:
        print("No CID file found. Exiting.")
        return
    
    print(f"CID file found: {cid_file}")
    print("Reading current CID", end="")
    progress_indicator()
    
    current_cid = read_cid(cid_file)
    if not current_cid:
        print("Failed to read the current CID. Exiting.")
        return
    
    print(f"Current CID: {current_cid}")
    confirm = input("Is the CID correct? (y/n): ").strip().lower()
    if confirm != 'y':
        print("CID modification aborted.")
        return

    if check_write_protection_sysfs():
        if not disable_write_protection():
            print("Unable to disable write protection. Exiting.")
            return
    
    new_cid = input("Enter the new CID (32 hexadecimal characters): ").strip()
    if len(new_cid) != 32:
        print("Invalid CID length. Exiting.")
        return

    confirm = input(f"Are you sure you want to write the new CID {new_cid}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("CID modification aborted.")
        return
    
    print("Writing new CID", end="")
    progress_indicator()

    try:
        with open("/dev/mmcblk0", "wb") as f:
            if write_new_cid(f.fileno(), new_cid):
                print("CID successfully written.")
            else:
                print("CID writing failed.")
    except Exception as e:
        print(f"Failed to open device for writing: {e}")
        return
    
    print("Verifying new CID", end="")
    progress_indicator()

    updated_cid = read_cid(cid_file)
    if updated_cid == new_cid:
        print(f"CID successfully updated: {updated_cid}")
    else:
        print(f"CID update failed. Current CID is still: {updated_cid}")

if __name__ == "__main__":
    main()

