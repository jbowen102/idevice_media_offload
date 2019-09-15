# https://docs.python.org/3/library/time.html
from time import localtime, strftime, strptime
from os import listdir, mkdir, rmdir
from os.path import exists as path_exists
from os.path import getctime, getmtime, getsize
from subprocess import Popen
from hashlib import sha256
from tqdm import tqdm
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
DEFAULT_BU_ROOT = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/full_BU_root_dir/'
IPHONE_DCIM_PREFIX = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/full_gvfs_dir/'

# Small test directories:
# DEFAULT_BU_ROOT = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/small_BU_root_dir/'
# IPHONE_DCIM_PREFIX = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/small_gvfs_dir/'


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
            raise iPhoneLocError("Error: Can't find iPhone in " + IPHONE_DCIM_PREFIX)
        elif count > 1:
            raise iPhoneLocError("Error: Multiple 'gphoto' handles in " + IPHONE_DCIM_PREFIX)
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
            raise DirectoryNameError("Tried to access iPhone DCIM folder %s, "
                                     "but it does not exist in\n%s\n"
                                     % (APPLE_folder_name, self.DCIM_path))

    def APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by APPLE_folder_path() method
        APPLE_contents = listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def update_path(self):
        self.find_root()
        return self.DCIM_path

    def __str__(self):
        return self.DCIM_path

    def __repr__(self):
        return ("iPhone DCIM directory object with path:\n\t" + self.DCIM_path)


##########################################

# Prompt to confirm location of pic BU directory or allow different directory to be input.
# Program creates new folder with today’s date in raw offload directory.
# Copies from all with timestamps newer than previous-date folder.

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

        self.find_overlap_offloads()

    def find_overlap_offloads(self):
        # Create a RawOffload instance representing most recent offload.
        LastOffload = RawOffload(self.offload_list[-1], self)
        self.prev_offload_list = [LastOffload]
        overlap_folder = LastOffload.newest_APPLE_folder()
        # Find every other offload that shares the overlap folder.
        for offload in self.offload_list[:-1]:
            if overlap_folder in listdir(self.RO_root_path + offload):
                PrevOL = RawOffload(offload, self)
                self.prev_offload_list += [PrevOL]
        self.prev_offload_list.sort()

    def get_root_path(self):
        return self.RO_root_path

    def get_offload_list(self):
        return self.offload_list.copy()

    def get_prev_offload(self):
        return self.prev_offload_list[-1]

    def get_prev_offload_list(self):
        return self.prev_offload_list.copy()

    def create_new_offload(self):
        NewOffload = NewRawOffload(self)
        return NewOffload

    def __str__(self):
        return self.get_root_path()

    def __repr__(self):
        return "RawOffloadGroup object with path:\n\t" + self.get_root_path()


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

    def get_parent(self):
        return self.Parent

    def get_leaf_dir(self):
        return self.leaf_dir

    def get_full_path(self):
        return self.full_path

    def list_APPLE_folders(self):
        # Sorted; not full paths
        APPLE_folders = listdir(self.full_path)
        APPLE_folders.sort()
        return APPLE_folders

    def newest_APPLE_folder(self):
        return self.list_APPLE_folders()[-1]

    def APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.list_APPLE_folders():
            return self.full_path + APPLE_folder_name + '/'
        else:
            raise DirectoryNameError("Tried to access %s, but it does not exist"
                    " in %s." % (APPLE_folder_name, self.list_APPLE_folders()))

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
        return "RawOffload object with path:\n\t" + self.full_path

    def __lt__(self, other):
        return self.leaf_dir < other.leaf_dir


# Phase 1: Copy any new pics from iPhone to raw_offload folder.
# How to determine if they're new? Look at modified time but also check for collisions.
# If two files have same name but different mtime, check sha256 sum. If same, don't
# copy. If different, display both files and timestamps, prompting user how to handle.

class NewRawOffload(RawOffload):
    """Creates object representing new RawOffload instance (timestamped folder).
    Includes extra functionality to perform offload."""

    def __init__(self, Parent):
        self.Parent = Parent
        self.src_iPhone_dir = iPhoneDCIM()

        self.create_target_folder()
        self.run_overlap_offload()
        self.run_new_offload()

    def create_target_folder(self):
        # Create new directory w/ today's date in Raw_Offload.
        new_timestamp = strftime('%Y-%m-%dT%H%M%S')
        self.leaf_dir = new_timestamp
        self.full_path = (self.Parent.get_root_path() + self.leaf_dir + '/')
        if path_exists(self.full_path):
            # Make sure folder w/ today's date doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                  "directory already exists. No changes made."
                                                    % self.full_path)
        else:
            mkdir(self.full_path)

    def create_quar_folder(self, APPLE_folder):
        # Create empty dir for special cases
        self.quar_path = self.full_path + "%s-QUARANTINE/" % APPLE_folder
        if path_exists(self.quar_path):
            raise RawOffloadError("Raw_Offload folder with today's timestamp "
            "already contains QUARANTINE directory. Pics not offloaded. Terminating")
        else:
            mkdir(self.quar_path)

    def run_overlap_offload(self):
        self.PrevOffload = self.Parent.get_prev_offload()

        # Find the last (newest) APPLE dir in the most recent offload.
        self.overlap_folder = self.PrevOffload.newest_APPLE_folder()
        print("Overlap folder: " + self.overlap_folder)

        # Create a destination folder in the new Raw Offload directory with the same APPLE name.
        self.new_overlap_path = self.full_path + self.overlap_folder + '/'
        mkdir(self.new_overlap_path)

        self.create_quar_folder(self.overlap_folder)

        # algorithm to determine which photos are new.
        prev_overlap_path = self.PrevOffload.APPLE_folder_path(self.overlap_folder)
        prev_APPLE_pics = self.PrevOffload.APPLE_contents(self.overlap_folder)

        # tqdm provides the console status bar
        src_APPLE_pics = self.src_iPhone_dir.APPLE_contents(self.overlap_folder)
        src_APPLE_pics.sort()
        print("Overlap-transfer progress:")
        for img_name in tqdm(src_APPLE_pics):
            # print("\t%s" % img_name)
            src_APPLE_dir = self.src_iPhone_dir.APPLE_folder_path(self.overlap_folder)
            src_img_path = src_APPLE_dir + img_name
            # Get last modified time as a struct_time, compare to last BU struct_time
            img_mod_time = localtime(getmtime(src_img_path))
            # If mod time earlier than last offload, pic should have been offloaded last time.
            if img_mod_time > self.PrevOffload.get_timestamp():
                # Check for duplication. Required since existing pic datestamps update unnecessarily on iPhone.
                if img_name in prev_APPLE_pics:

                    if getsize(src_img_path) != getsize(prev_overlap_path + img_name):
                        # Put in quarantine for later manual sorting if they are truly different.
                        # One possible reason for this is if an image was cropped or a video trimmed after offload.
                        shutil.copy2(src_img_path, self.quar_path)
                    else:
                        # do nothing if the files have different mod dates but have same size.
                        pass

                else:
                    shutil.copy2(src_img_path, self.new_overlap_path)
            else:
                continue

        # If the overlap APPLE folder ends up being empty, delete it.
        if not self.APPLE_contents(self.overlap_folder):
            rmdir(self.new_overlap_path)
            rmdir(self.quar_path)
            print("No new pictures contained in %s (overlap folder) since "
                                    "last offload." % self.overlap_folder)
        else:
            self.process_quar()

    def process_quar(self):
        # Display output on screen of quarantined files.
        # If no special cases were found, delete the quarantine directory.
        # add more functionality here to show both old and new pics side by side to allow use to choose via command line which to choose.
        if listdir(self.quar_path):
            print("QUARANTINED FILES from %s (same name as existing BU file "
                                "but different size):" % self.overlap_folder)
            quar_list = listdir(self.quar_path)
            quar_list.sort()
            for img in quar_list:
                print("\t" + img)
        else:
            rmdir(self.quar_path)
            print("No files quarantined.")

    def run_new_offload(self):
        # Look for new APPLE folders to offload.
        src_APPLE_list = self.src_iPhone_dir.list_APPLE_folders()

        # If the iPhone contains any APPLE folders numbered higher than the overlap case, copy them wholesale.
        new_APPLE_folder = False
        for folder in src_APPLE_list:
            if folder > self.overlap_folder:
                print("New APPLE folder %s found on iPhone - copying." % folder)
                shutil.copytree(self.src_iPhone_dir.APPLE_folder_path(folder),
                                                        self.full_path + folder)
                new_APPLE_folder = True

        if not new_APPLE_folder:
            print("No new APPLE folders found on iPhone.")

    def __repr__(self):
        return "NewRawOffload object with path:\n\t" + self.full_path


rog = RawOffloadGroup()
nro = rog.create_new_offload()


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
