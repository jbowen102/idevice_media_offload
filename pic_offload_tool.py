# https://docs.python.org/3/library/time.html
from time import localtime, strftime
from os import listdir
from os.path import exists as path_exists
from os.path import getctime, getmtime
from subsystem import Popen
import shutil


class iPhoneLocError(Exception):
    pass

class CurrentTimeStamp(object):
# Is this needed or can strftime('%Y-%m-%d T %H:%M:%S') be used?

    def __init__(self):
        # Get date and time to put in filename
        # These are integers
        self.yr = localtime().tm_year
        self.mon = localtime().tm_mon
        self.day = localtime().tm_mday
        self.hr = localtime().tm_hour
        self.minute = localtime().tm_min
        self.sec = localtime().tm_sec

    def short_form(self):
        return '%.4i-%.2i-%.2i' % (self.yr, self.mon, self.day)

    def long_form(self):
        return ('%.4i-%.2i-%.2i' % (self.yr, self.mon, self.day) + 'T' +
                '%.2i%.2i%.2i' % (self.hr, self.minute, self.sec))

# use current date to label new BU folder.
date_stamp = CurrentTimeStamp()
today = date_stamp.short_form()


# Phase 0: Find iPhone in GVFS.
# iPhone DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.

class iPhone_DCIM(object):
    def __init__(self):
        self.find_root()

    def find_root(self):
        iphone_DCIM_prefix = "/run/user/1000/gvfs/"
        gvfs_handles = listdir(iphone_DCIM_prefix)
        iphone_handle = ""
        count = 0

        for i, handle in enumerate(gvfs_handles):
            if 'gphoto' in gvfs_handles[i]:
                iphone_handle = handle
                count += 1

        if not iphone_handle:
            raise iPhoneLocError("Error: Can't find iPhone in %s" % iphone_DCIM_prefix)
        elif count > 1:
            raise iPhoneLocError("Error: Multiple 'gphoto' handles in %s" % iphone_DCIM_prefix)
        else:
            self.iphone_DCIM_path = iphone_DCIM_prefix + iphone_handle + "/DCIM/"

    def get_root(self):
        return self.iphone_DCIM_path

    def get_APPLE_folders(self):
        return listdir(self.iphone_DCIM_path)

    def update_path(self):
        self.find_root()
        return self.get_root()

    def __repr__(self):
        return "iPhone DCIM directory object with root path:\n\t" + self.get_root()


# Phase 1: Copy any new pics from iPhone to raw_offload folder.
# How to determine if they're new? Look at modified time but also check for collisions.
# If mtime is newer, is it necessarily newer?

# Prompt to confirm location of pic BU directory or allow different directory to be input.
# Program creates new folder with today’s date in raw offload directory.
# Copies from buffer all that don’t exist in previous-date folder.
# At end, flush anything left in buffer.


# Compare creation and modification times
iPhone_root = iPhone_DCIM()

all_APPLE_folders = iPhone_root.get_APPLE_folders()

for APPLE_folder in all_APPLE_folders:
    APPLE_folder_path = iPhone_root.get_root() + APPLE_folder + '/'

    for img in listdir(APPLE_folder_path):
        full_img_path = APPLE_folder_path + img
        ctime_str = strftime('%Y-%m-%d T %H:%M:%S', localtime(getctime(full_img_path)))
        mtime_str = strftime('%Y-%m-%d T %H:%M:%S', localtime(getmtime(full_img_path)))
        # print("%s created: %s; modified: %s" % (img, ctime_str, mtime_str))
        if ctime_str != mtime_str:
            print("%s created/modified:\n\t%s\n\t%s" % (APPLE_folder +'/'+ img,
                                                        ctime_str, mtime_str))
            print("\t\t\t\t^----ctime/mtime discrepancy")



# bu_root = input("Confirm BU folder is the following"
#                 "or input a new directory path:\n"
#                 "\t/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures")
# if not bu_root:
#     bu_root = "/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures"
#
# raw_offoad_dir = bu_root + "/Raw_Offload"
# org_dir = bu_root + "/Organized"
#
# raw_dst_path = raw_offoad_dir + '/%s' % (today)
#
# # Double-check root folder is there and that Raw_Offload and Organized folders are there.
# # Make sure folder w/ today's date doesn't already exist.
# if not path_exists(bu_root):
#     print("BU Root not found! Pics not offloaded. Terminating")
#     return
# elif path_exists(raw_dst_path):
#     print("\nCopy aborted. Folder with today's date already exists in [%s]."
#         % raw_dst_path)
# else:
#     # algorithm to determine which photos are new.
#     shutil.copytree([src], [dest]])
#
#
# raw_BU_folder_list = listdir(raw_dst_path)
# org_BU_folder_list = listdir(raw_dst_path)



# Phase 2: Organize files by date into dated directory.
# Create new folder if none exists

# Phase 3: Display pics one by one and prompt for where to copy each.
# Have a Manual Sort folder to use in case of no correct choice available.
# Prepend date to each file name when copying to various folders.
# Handle name collisions.

# subsystem.Popen(['xdg-open', [filename in quotes])
