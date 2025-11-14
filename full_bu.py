import subprocess
import os
import time

import idevice_media_offload.pic_offload_tool as offload_tool
import idevice_media_offload.date_organize_tool as org_tool
import idevice_media_offload.pic_categorize_tool as cat_tool

from idevice_media_offload.dir_names import IPHONE_BU_ROOT_J, IPHONE_BU_ROOT_M, IPAD_BU_ROOT_7, IPAD_BU_ROOT_10, ST_VID_ROOT
from idevice_media_offload.dir_names import NAS_BU_ROOT, NAS_ST_DIR
from idevice_media_offload.dir_names import NAS_BU_ROOT_SSH, NAS_ST_DIR_SSH, SSH_PORT


# dir path where this script is stored
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# https://stackoverflow.com/questions/29768937/return-the-file-path-of-the-file-not-the-current-directory

# global vars to update later. Depends on device.
LOCAL_BU_ROOT=None
LOCAL_BUFFER_ROOT=None


def run_offload():
    print('\n\t', '*' * 10, 'OFFLOAD program', '*' * 10)
    # Instantiate a RawOffloadGroup instance then call its create_new_offload()
    # method.
    rog = offload_tool.RawOffloadGroup(LOCAL_BU_ROOT)
    try:
        rog.create_new_offload()
    except KeyboardInterrupt:
        response = input("\nReceived kbd interrupt. Run rsync job? "
                    "Press Enter to continue then quit or 'q' to quit now.\n> ")
        if response.lower() in ['q', 'n']:
            quit()
        else:
            pass

    if "ipad" in LOCAL_BU_ROOT.lower():
        bu_root_for_sync = os.path.dirname(LOCAL_BU_ROOT[:-1]) # must strip trailing slash
    else:
        bu_root_for_sync = LOCAL_BU_ROOT

    offload_dir = os.path.join(bu_root_for_sync, "Raw_Offload/")
    call_rs_script("NAS_BU_sync.sh", offload_dir, NAS_BU_ROOT, NAS_BU_ROOT_SSH)

    print('\t', '*' * 10, 'OFFLOAD program complete', '*' * 10, "\n")
    input("You should proceed to run the ORGANIZE program, even if not "
            "intending to run the CAT program right now.\nThe only reason "
            "not to run ORG after OFFLOAD is if you never intend to CAT this "
            "offload.\n")

def run_org():
    print('\n\t', '*' * 10, 'ORGANIZE program', '*' * 10)
    # Instantiate an OrganizedGroup instance then call its run_org() method.
    orgg = org_tool.OrganizedGroup(LOCAL_BU_ROOT, LOCAL_BUFFER_ROOT)
    try:
        orgg.run_org()
    except KeyboardInterrupt:
        response = input("\nReceived kbd interrupt. Run rsync job? "
                    "Press Enter to continue then quit or 'q' to quit now.\n> ")
        if response.lower() in ['q', 'n']:
            quit()
        else:
            pass

    if "ipad" in LOCAL_BU_ROOT.lower():
        bu_root_for_sync = os.path.dirname(LOCAL_BU_ROOT[:-1]) # must strip trailing slash
    else:
        bu_root_for_sync = LOCAL_BU_ROOT

    # run rsync script to copy new data to NAS
    org_dir = os.path.join(bu_root_for_sync, "Organized/")
    call_rs_script("NAS_BU_sync.sh", org_dir, NAS_BU_ROOT, NAS_BU_ROOT_SSH)

    print('\t', '*' * 10, 'ORGANIZE program complete', '*' * 10, '\n')

def run_cat():
    print('\n\t', '*' * 10, 'CATEGORIZE program', '*' * 10)

    Cat = cat_tool.Categorizer(LOCAL_BUFFER_ROOT)
    # Prompt user to put all bulk media in appropriate buffers (ex. st_buffer.)
    # Then automatically categorize all.
    try:
        Cat.run_auto_cat()
        Cat.photo_transfer()
    except KeyboardInterrupt:
        response = input("\nReceived kbd interrupt. Run rsync job? "
                    "Press Enter to continue then quit or 'q' to quit now.\n> ")
        if response.lower() in ['q', 'n']:
            quit()
        else:
            pass

    # run rsync script to copy new data to NAS
    call_rs_script("NAS_ST_sync.sh", ST_VID_ROOT, NAS_ST_DIR, NAS_ST_DIR_SSH)

    print('\t', '*' * 10, 'CATEGORIZE program complete', '*' * 10, "\n")

def run_all():
    run_offload()
    run_org()
    run_cat()


def call_rs_script(script, src_dir, dest_dir, dest_dir_ssh):

    while True:
        if not os.path.isdir(dest_dir):
            # NAS not reachable
            input("\nCan't reach NAS share to run %s. Check network connection "
                                        "and ensure NAS share is mounted.\n"
                                        "Press Enter to try again." % script)
            continue
        else:
            print("\nRunning NAS rsync in new terminal.\n")
            time.sleep(2) # Pause for two seconds so user sees above message.
            break

    shell_command = ("gnome-terminal --tab -- /bin/bash -c \"%s/%s %s %s %d; "
        "/bin/bash\"" % (SCRIPT_DIR, script, src_dir, dest_dir_ssh, SSH_PORT))

    subprocess.run([shell_command],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

if __name__ == "__main__":
    # Don't run if module being imported. Only if script being run directly.
    while True:
        device_type = input("Backing up iPhone or iPad? ['oj' for J iPhone, '"
                                        "om' for M iPhone, 'a' for iPad]\n> ")
        if device_type.lower() in ['oj', 'o']:
            LOCAL_BU_ROOT = IPHONE_BU_ROOT_J
            break
        if device_type.lower() == 'om':
            LOCAL_BU_ROOT = IPHONE_BU_ROOT_M
            break
        elif device_type.lower() == 'a':
            device_ver = input("iPad 7 or 10?\n> ")
            if device_ver == "7":
                LOCAL_BU_ROOT = IPAD_BU_ROOT_7
                break
            elif device_ver == "10":
                LOCAL_BU_ROOT = IPAD_BU_ROOT_10
                break
            else:
                print("Input not recognized. Expected '7' or '10'. "
                                                        "Got %s\n" % device_ver)
                continue # Try again.
        elif device_type.lower() == 'q':
            quit()
        else:
            print("Input not recognized.")

    LOCAL_BUFFER_ROOT = os.path.join(LOCAL_BU_ROOT, "Cat_Buffer/")

    # Main loop
    while True:
        prog = input("Choose program to run:\n"
                    "\tType 'f' to run the OFFLOAD program only.\n"
                    "\tType 'g' to run the ORGANIZE (by date) program only.\n"
                    "\tType 'c' to run the CATEGORIZE program only.\n"
                    "\tType 'a' or press Enter to run all three programs.\n"
                    "\tType 'q' to quit.\n"
                    "\tType 'h' for help.\n> ")

        if prog.lower() == 'f':
            run_offload()

        elif prog.lower() == 'g':
            run_org()

        elif prog.lower() == 'c':
            run_cat()

        elif prog.lower() == 'q':
            break

        elif prog.lower() == 'a':
            run_all()
            break

        elif prog.lower() == 'h':
            print("\tBasic workflow:\n"
                "\t\tRun OFFLOAD and ORGANIZE.\n"
                "\t\tLook at buffer, move all st vids or other big blocks of pics.\n"
                "\t\tRun CAT tool on rest of pics in buffer.\n"
                "\t\tProcess leftover uncategorized pics.\n"
                "\t\tCopy data to NAS (automatic if NAS share mounted).\n")

        else:
            print("Invalid response. Try again.")
