
"""Organize Camera Roll picture offload from iPhone
(Newest folde"I:/JB Documents/Tech/Back-up Data/iPhone_Pictures/Raw_Offload/Buffer") to
a new folder with today's date in this directory:
"I:/JB Documents/Tech/Back-up Data/iPhone_Pictures/Raw_Offload".
"""

import time
import os
import shutil


class TimeStamp(object):

    def __init__(self):
        # Get date and time to put in filename
        # These are integers
        self.yr = time.localtime().tm_year
        self.mon = time.localtime().tm_mon
        self.day = time.localtime().tm_mday
        self.hr = time.localtime().tm_hour
        self.minute = time.localtime().tm_min
        self.sec = time.localtime().tm_sec

    def short_form(self):
        return '%.4i-%.2i-%.2i' % (self.yr, self.mon, self.day)

    def long_form(self):
        return ('%.4i-%.2i-%.2i' % (self.yr, self.mon, self.day) + '_' +
                '%.2i%.2i%.2i' % (self.hr, self.minute, self.sec))

src_folder="Computer/Telefono/Internal Storage/DCIM"
dst_folders= ["P:/Current Projects/100620 Kawasaki Walbro EFI/Prod_Engg/Vehicle Tracking/Vehicle_DB_Backup/",
            "U:/Departments/Engineering/Users/JBowen/Vehicle-tracking_Database/BU/",
            "V:/Vehicle-tracking_Database/BU/"]

# use current date to label new BU folder.
date_stamp = TimeStamp()
today = date_stamp.short_form()

for d in xrange(len(dst_folders)):

    full_dst_path = dst_folders[d] + '%s_BU' % (today)
    # make sure new dest folder doesn't exist before copying
    if not os.path.exists(dst_folders[d]):
        print("Path not found!\n[%s]\nMoving on." % dst_folders[d])
    elif os.path.exists(full_dst_path):
        print("\nCopy aborted. Folder with today's date already exists in [%s]."
            % dst_folders[d])
    else:

        # test to determine how many folders to keep and if today is a backup day.
        # Default value:
        backing_up_today = False

        if dst_folders[d][0] == "P":
            dst_num_folders = 200
            backing_up_today = True
        elif dst_folders[d][0] == "U":
            dst_num_folders = 100
            if int(today[-2:]) % 2 == 0:
                backing_up_today = True
        elif dst_folders[d][0] == "V":
            dst_num_folders = 10
            if int(today[-2:]) % 7 == 0:
                backing_up_today = True

        if backing_up_today:
            print("\nBacking up to [%s]..." % dst_folders[d])

            # If more than certain number of folders exist, delete oldest one
            # before creating new one.
            BU_folder_list = os.listdir(dst_folders[d])
            for n in xrange(len(BU_folder_list) - dst_num_folders - 1):
                shutil.rmtree(dst_folders[d] + BU_folder_list[n])

            # copy DB files into new folder.
            shutil.copytree(src_folder, full_dst_path)
            print("Successful backup to [%s]" % dst_folders[d])

rawinput("End of Script. Press Enter to finish and close.")
time.sleep(200)
