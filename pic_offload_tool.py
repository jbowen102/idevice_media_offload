# https://docs.python.org/3/library/time.html
from time import localtime, strftime, strptime
from os import listdir, mkdir, rmdir
from os.path import exists as path_exists
from os.path import getctime, getmtime
from subprocess import Popen
from hashlib import sha256
import shutil



# DEFAULT_BU_ROOT = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/'
# IPHONE_DCIM_PREFIX = '/run/user/1000/gvfs/'

# Test directories:
# DEFAULT_BU_ROOT = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/TEST/BU_root_dir/'
# IPHONE_DCIM_PREFIX = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/TEST/gvfs_dir/'

# Small test directories:
DEFAULT_BU_ROOT = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/small_BU_root_dir/'
IPHONE_DCIM_PREFIX = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/small_gvfs_dir/'



class iPhoneLocError(Exception):
    pass

class DirectoryNameError(Exception):
    pass

class RawOffloadError(Exception):
    pass



# Phase 0: Find iPhone in GVFS.
# iPhone DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.

class iPhoneDCIM(object):
    def __init__(self):
        self.find_root()

    def find_root(self):
        gvfs_handles = listdir(IPHONE_DCIM_PREFIX)
        count = 0

        for i, handle in enumerate(gvfs_handles):
            if handle[0:6] == 'gphoto':
                iphone_handle = handle
                count += 1

        if count == 0:
            raise iPhoneLocError("Error: Can't find iPhone in %s" % IPHONE_DCIM_PREFIX)
        elif count > 1:
            raise iPhoneLocError("Error: Multiple 'gphoto' handles in %s" % IPHONE_DCIM_PREFIX)
        else:
            self.iphone_DCIM_path = IPHONE_DCIM_PREFIX + iphone_handle + "/DCIM/"

    def get_root(self):
        return self.iphone_DCIM_path

    def get_APPLE_folders(self):
        APPLE_folders = listdir(self.get_root())
        APPLE_folders.sort()
        return APPLE_folders

    def update_path(self):
        self.find_root()
        return self.get_root()

    def __str__(self):
        return self.get_root()

    def __repr__(self):
        return "iPhone DCIM directory object with root path:\n\t" + self.get_root()


# Phase 1: Copy any new pics from iPhone to raw_offload folder.
# How to determine if they're new? Look at modified time but also check for collisions.
# If two files have same name but different mtime, check sha256 sum. If same, don't
# copy. If different, display both files and timestamps, prompting user how to handle.

class RawOffloadDirectory(object):
    def __init__(self, full_path):
        if full_path[-1] != '/':
            full_path += '/'
        self.full_path = full_path
        dirs = full_path.split('/')
        self.leaf_dir = dirs[-1]

    def get_leaf_dir(self):
        return self.get_full_path().split('/')[-2]

    def get_full_path(self):
        return self.full_path

    def list_children(self):
        # not full paths
        children = listdir(self.get_full_path())
        children.sort()
        return children

    def get_timestamp_str(self):
        if len(self.get_leaf_dir()) != 17:
            raise DirectoryNameError("Raw_Offload directory name '%s' not in "
                                            "expected format." % self.get_leaf_dir())
        else:
            return self.get_leaf_dir()

    def get_timestamp(self):
        return strptime(self.get_leaf_dir(), '%Y-%m-%dT%H%M%S')

    def create_dir(self):
        if path_exists(self.get_full_path()):
            # Make sure folder w/ today's date doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                "directory already exists. No changes made."
                                                    % self.get_full_path())
        else:
            mkdir(self.get_full_path())

    def __str__(self):
        return self.get_full_path()

    def __repr__(self):
        return "Raw_Offload directory object with path:\n\t" + self.get_full_path()


# Prompt to confirm location of pic BU directory or allow different directory to be input.
# Program creates new folder with today’s date in raw offload directory.
# Copies from all with timestamps newer than previous-date folder.

bu_root = input("Confirm BU folder is the following "
                "or input a new directory path:\n"
                "\t%s\n" % DEFAULT_BU_ROOT)
if not bu_root:
    bu_root = DEFAULT_BU_ROOT
    print("\tProceeding with above default.\n")

# Double-check Raw_Offload folder is there.
RO_root = bu_root + "Raw_Offload/"
if not path_exists(RO_root):
    raise RawOffloadError("Raw_Offload dir not found! Pics not offloaded. Terminating")

# Create object for most recent Raw_Offload folder
# Folders should be in chronological order since they are named by datestamp.
RO_dirs = listdir(RO_root)
RO_dirs.sort()
prev_RO_dir = RawOffloadDirectory(RO_root + '%s' % RO_dirs[-1] + '/')
# Find the last (newest) APPLE dir in the most recent offload. Not full path.
prev_RO_newest_APPLE_dir = prev_RO_dir.list_children()[-1]
prev_RO_newest_APPLE_full_path = prev_RO_dir.get_full_path() + prev_RO_newest_APPLE_dir + '/'
print("Overlap folder: %s" % prev_RO_newest_APPLE_dir)

# Create new directory w/ today's date in Raw_Offload.
new_RO_timestamp = strftime('%Y-%m-%dT%H%M%S')
new_RO_dir = RawOffloadDirectory(RO_root + '%s' % new_RO_timestamp + '/')
new_RO_dir.create_dir()

# Create a destination folder in the new Raw Offload directory with the same APPLE name.
new_RO_APPLE_dir = new_RO_dir.get_full_path() + prev_RO_newest_APPLE_dir + '/'
mkdir(new_RO_APPLE_dir)



# Create empty dir for special cases
quar_path = new_RO_dir.get_full_path() + "QUARANTINE/"
if path_exists(quar_path):
    raise RawOffloadError("Raw_Offload folder with today's timestamp already contains "
                    "QUARANTINE directory. Pics not offloaded. Terminating")
else:
    mkdir(quar_path)


# Address for matching iPhone source folder
iPhone_dir = iPhoneDCIM()
src_APPLE_dir = iPhone_dir.get_root() + prev_RO_newest_APPLE_dir + '/'
src_APPLE_pics = listdir(src_APPLE_dir)
src_APPLE_pics.sort()


# algorithm to determine which photos are new.
prev_RO_APPLE_img_list = listdir(prev_RO_newest_APPLE_full_path)
prev_RO_APPLE_img_list.sort()

for img_name in src_APPLE_pics:
    src_img_path = src_APPLE_dir + img_name
    # Get last modified time as a struct_time, compare to last BU struct_time
    img_mod_time = localtime(getmtime(src_img_path))
    # If mod time earlier than last offload, pic should have been offloaded last time.
    if img_mod_time > prev_RO_dir.get_timestamp():
        # Check for duplication. Required since datestamps update by themselves on iPhone.
        if img_name in prev_RO_APPLE_img_list:
            old_img_file_obj = open(prev_RO_newest_APPLE_full_path + img_name, 'rb')
            new_img_file_obj = open(src_img_path, 'rb')
            if sha256(new_img_file_obj) != sha256(old_img_file_obj):
                # Put in quarantine for later manual sorting if they are truly different.
                shutil.copy2(src_img_path, quar_path)
            else:
                pass
                # do nothing if the files have different mod dates but same SHA sum.
            old_img_file_obj.close()
            new_img_file_obj.close()
        else:
            shutil.copy2(src_img_path, new_RO_APPLE_dir)
    else:
        continue


# Finish up with overlap case.
# If the first APPLE folder ends up being empty at the end, delete it.
new_APPLE_folders = listdir(new_RO_dir.get_full_path())
new_APPLE_folders.sort()
first_new_APPLE_folder = new_APPLE_folders[0]
if not listdir(new_RO_dir.get_full_path() + first_new_APPLE_folder):
    rmdir(new_RO_dir.get_full_path() + first_new_APPLE_folder)
    print("No new pictures contained in %s since last offload." % first_new_APPLE_folder)
else:
    # Display output on screen of quarantined files.
    # If no special cases were found, delete the quarantine directory.
    if listdir(quar_path):
        print("QUARANTINED FILES:")
        for file in listdir(quar_path):
            print("\t" + file)
    else:
        rmdir(quar_path)
        print("No files quarantined.")


# Look for new APPLE folders to offload.
# If the iPhone contains any APPLE folders later than the overlap case, copy them wholesale.
all_iPhone_src_folders = listdir(iPhone_dir.get_root())
all_iPhone_src_folders.sort()

for folder in all_iPhone_src_folders:
    if folder > prev_RO_newest_APPLE_dir:
        shutil.copytree(iPhone_dir.get_root() + folder, new_RO_dir.get_full_path() + folder)
        print("New img folder found on iPhone: %s. Copying." % folder)





# Phase 2: Organize files by date into dated directory.
# Create new folder if none exists

# img_mod_time = strftime('%Y-%m-%d T %H:%M:%S', localtime(getmtime(src_img_path)))



# Phase 3: Display pics one by one and prompt for where to copy each.
# Have a Manual Sort folder to use in case of no correct choice available.
# Prepend date to each file name when copying to various folders.
# Handle name collisions.









#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])

# Display image:
# subsystem.Popen(['xdg-open', [filename in quotes])
