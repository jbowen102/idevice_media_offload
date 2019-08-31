import time
import os
import shutil


class iPhoneLocError(Exception):
    pass

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

# use current date to label new BU folder.
date_stamp = TimeStamp()
today = date_stamp.short_form()


# Phase 0: Find iPhone in GVFS.
# iPhone DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.

class iPhone_DCIM(object):
    def __init__(self):
        self.find_root()

    def find_root(self):
        iphone_DCIM_prefix = "/run/user/1000/gvfs/"
        gvfs_handles = os.listdir(iphone_DCIM_prefix)
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
        return os.listdir(self.iphone_DCIM_path)

    def update_path(self):
        self.find_root()
        return self.get_root()


#Phase 1: Copy any new pics from iPhone to raw_offload folder.
# Phase 2: Prompt to confirm location of pic BU directory or allow different directory to be input.
# Program creates new folder with today’s date in raw offload directory.
# Copies from buffer all that don’t exist in previous-date folder.
# At end, flush anything left in buffer.


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
# if not os.path.exists(bu_root):
#     print("BU Root not found! Pics not offloaded. Terminating")
#     return
# elif os.path.exists(raw_dst_path):
#     print("\nCopy aborted. Folder with today's date already exists in [%s]."
#         % raw_dst_path)
# else:
#     # algorithm to determine which photos are new.
#     shutil.copytree([src], [dest]])
#
#
# raw_BU_folder_list = os.listdir(raw_dst_path)
# org_BU_folder_list = os.listdir(raw_dst_path)



# Phase 2: Organize files by date into dated directory.
# Create new folder if none exists

# Phase 3: Display pics one by one and prompt for where to copy each.
# Have a Manual Sort folder to use in case of no correct choice available.
# Prepend date to each file name when copying to various folders.
# Handle name collisions.
