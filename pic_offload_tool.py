# https://docs.python.org/3/library/time.html
from time import localtime, strftime, strptime
from os import listdir, mkdir, rmdir
from os.path import exists as path_exists
from os.path import getctime, getmtime
from subprocess import Popen
from hashlib import sha256
import shutil


class iPhoneLocError(Exception):
    pass

class DirectoryNameError(Exception):
    pass

class RawOffloadError(Exception):
    pass

# DEFAULT_BU_ROOT = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/'
# IPHONE_DCIM_PREFIX = '/run/user/1000/gvfs/'

# Test directories:
# DEFAULT_BU_ROOT = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/TEST/BU_root_dir/'
# IPHONE_DCIM_PREFIX = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/TEST/gvfs_dir/'

# Small test directories:
DEFAULT_BU_ROOT = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/small_BU_root_dir/'
IPHONE_DCIM_PREFIX = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/small_gvfs_dir/'


# Find iPhone in GVFS.
# iPhone DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.

class iPhoneDCIM(object):
    """Represents DCIM folder structure at gvfs iPhone mount point"""
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
            self.DCIM_path = IPHONE_DCIM_PREFIX + iphone_handle + "/DCIM/"
            self.APPLE_folders = listdir(self.DCIM_path)
            self.APPLE_folders.sort()

    def get_root(self):
        return self.DCIM_path

    def list_APPLE_folders(self):
        return self.APPLE_folders

    def APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.APPLE_folders:
            return self.DCIM_path + APPLE_folder_name + '/'
        else:
            raise DirectoryNameError("Tried to access %s, but it does not exist"
                            " in %s." % (APPLE_folder_name, self.APPLE_folders))

    def APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by APPLE_folder_path() method
        APPLE_contents = listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return contents

    def update_path(self):
        self.find_root()
        return self.DCIM_path

    def __str__(self):
        return self.DCIM_path

    def __repr__(self):
        return ("iPhone DCIM directory object with root path:\n\t" +
                                                self.DCIM_path)



##########################################

class RawOffloadGroup(object):
    """Requires no input. Creates object representing Raw_Offload root struct."""
    def __init__(self):
        self.bu_root_path = input("Confirm BU folder is the following "
                        "or input a new directory path:\n"
                        "\t%s\n" % DEFAULT_BU_ROOT)
        if not self.bu_root_path:
            self.bu_root_path = DEFAULT_BU_ROOT
            print("\tProceeding with above default.\n")

        self.RO_root_path = self.bu_root_path + "Raw_Offload/"
        # Double-check Raw_Offload folder is there.
        if not path_exists(self.RO_root_path):
            raise RawOffloadError("Raw_Offload dir not found at %s! "
                        "Pics not offloaded. Terminating" % self.RO_root_path)

        self.offload_list = listdir(self.RO_root_path)
        self.offload_list.sort()

        # Create a RawOffload instance representing most recent offload.
        self.PrevOffload = RawOffload(self.offload_list[-1], self)


    def get_root_path(self):
        return self.RO_root_path

    def get_offload_list(self):
        return self.offload_list

    def get_prev_offload(self):
        return self.PrevOffload

    def create_new_offload(self):
        NewOffload = NewRawOffload()
        return NewOffload

    def __str__(self):
        return self.get_root_path()

    def __repr__(self):
        return "Raw_Offload Group object with path:\n\t" + self.get_root_path()


class RawOffload(object):
    """Represents a datestamped folder under the Raw_Offload root containing
    APPLE folders."""
    def __init__(self, leaf_name, Parent):
        self.Parent = Parent
        self.full_path = self.Parent.get_root_path() + leaf_name + '/'

        if len(leaf_name) != 17:
            raise DirectoryNameError("Raw_Offload directory name '%s' not in "
                                            "expected format." % self.leaf_dir)
        else:
            self.leaf_dir = leaf_name

        self.APPLE_folders = listdir(self.full_path)
        self.APPLE_folders.sort()

    def get_parent(self):
        return self.Parent

    def get_leaf_dir(self):
        return self.leaf_dir

    def get_full_path(self):
        return self.full_path

    def list_APPLE_folders(self):
        # Sorted # not full paths
        return self.APPLE_folders

    def newest_APPLE_folder(self):
        return self.APPLE_folders[-1]

    def APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.APPLE_folders:
            return self.full_path + APPLE_folder_name + '/'
        else:
            raise DirectoryNameError("Tried to access %s, but it does not exist"
                            " in %s." % (APPLE_folder_name, self.APPLE_folders))

    def APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by APPLE_folder_path() method
        APPLE_contents = listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def get_timestamp_str(self):
        return self.leaf_dir

    def get_timestamp(self):
        return strptime(self.leaf_dir, '%Y-%m-%dT%H%M%S')

    def __str__(self):
        return self.full_path

    def __repr__(self):
        return "Raw_Offload object with path:\n\t" + self.full_path



# Phase 1: Copy any new pics from iPhone to raw_offload folder.
# How to determine if they're new? Look at modified time but also check for collisions.
# If two files have same name but different mtime, check sha256 sum. If same, don't
# copy. If different, display both files and timestamps, prompting user how to handle.

# Prompt to confirm location of pic BU directory or allow different directory to be input.
# Program creates new folder with today’s date in raw offload directory.
# Copies from all with timestamps newer than previous-date folder.


class NewRawOffload(RawOffload):
    """Creates object representing new RawOffload instance (timestamped folder).
    Includes extra functionality to perform offload."""

    def __init__(self, Parent):
        self.Parent = Parent
        self.full_path = self.Parent.get_root_path() + leaf_name + '/'
        self.leaf_dir = leaf_name

        # Create new directory w/ today's date in Raw_Offload.
        new_timestamp = strftime('%Y-%m-%dT%H%M%S')
        self.full_path = (self.Parent.get_root_path() + '%s' % new_timestamp + '/')
        if path_exists(self.full_path):
            # Make sure folder w/ today's date doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                "directory already exists. No changes made."
                                                    % self.full_path)
        else:
            mkdir(self.full_path)


        PrevRODir = self.Parent.get_prev_offload()

        # Find the last (newest) APPLE dir in the most recent offload.
        overlap_folder = PrevRODir.newest_APPLE_folder()
        print("Overlap folder: %s" % overlap_folder)
        prev_overlap_path = (PrevRODir.APPLE_folder_path(overlap_folder))

        # Create a destination folder in the new Raw Offload directory with the same APPLE name.
        new_overlap_path = self.full_path + overlap_folder + '/'
        mkdir(new_overlap_path)


        # Create empty dir for special cases
        self.quar_path = self.full_path() + "QUARANTINE/"
        if path_exists(self.quar_path):
            raise RawOffloadError("Raw_Offload folder with today's timestamp "
            "already contains QUARANTINE directory. Pics not offloaded. Terminating")
        else:
            mkdir(self.quar_path)


        # Get matching iPhone source folder and list of pics there.
        iPhone_dir = iPhoneDCIM()

        src_APPLE_dir = iPhone_dir.APPLE_folder_path(overlap_folder)
        src_APPLE_pics = iPhone_dir.APPLE_contents(overlap_folder)


        # algorithm to determine which photos are new.
        prev_APPLE_pics = PrevRODir.APPLE_contents(overlap_folder)

        for img_name in src_APPLE_pics:
            src_img_path = src_APPLE_dir + img_name
            # Get last modified time as a struct_time, compare to last BU struct_time
            img_mod_time = localtime(getmtime(src_img_path))
            # If mod time earlier than last offload, pic should have been offloaded last time.
            if img_mod_time > PrevRODir.get_timestamp():
                # Check for duplication. Required since datestamps update by themselves on iPhone.
                if img_name in prev_APPLE_pics:
                    old_img_file_obj = open(prev_RO_newest_APPLE_full_path + img_name, 'rb')
                    new_img_file_obj = open(src_img_path, 'rb')
                    if sha256(new_img_file_obj) != sha256(old_img_file_obj):
                        # Put in quarantine for later manual sorting if they are truly different.
                        shutil.copy2(src_img_path, self.quar_path)
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
        # If the overlap APPLE folder ends up being empty, delete it.
        self.APPLE_folders = listdir(self.full_path)
        self.APPLE_folders.sort()

        if not self.APPLE_contents(overlap_folder):
            rmdir(self.APPLE_folder_path(overlap_folder))
            print("No new pictures contained in %s since last offload." % overlap_folder)
        else:
            # Display output on screen of quarantined files.
            # If no special cases were found, delete the quarantine directory.
            if listdir(self.quar_path):
                print("QUARANTINED FILES:")
                for img in listdir(self.quar_path):
                    print("\t" + img)
            else:
                rmdir(self.quar_path)
                print("No files quarantined.")


        # Look for new APPLE folders to offload.
        # If the iPhone contains any APPLE folders numbered higher than the overlap case, copy them wholesale.
        for folder in iPhone_dir.list_APPLE_folders():
            if folder > overlap_folder:
                shutil.copytree(iPhone_dir.get_root() + folder, self.full_path + folder)
                print("New img folder found on iPhone: %s. Copying." % folder)

        # Update APPLE_folders attribute after possibly adding more folders.
        self.APPLE_folders = listdir(self.full_path)
        self.APPLE_folders.sort()



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
