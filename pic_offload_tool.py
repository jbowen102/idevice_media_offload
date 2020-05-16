# https://docs.python.org/3/library/time.html
from os import listdir, mkdir, rmdir
from os.path import getsize, isfile
from os.path import exists as path_exists
from shutil import copy2 as sh_copy2
from shutil import copytree as sh_copytree
from time import strftime, strptime
from tqdm import tqdm
from dir_names import IPHONE_DCIM_PREFIX


class iPhoneLocError(Exception):
    pass

class iPhoneIOError(Exception):
    pass

class DirectoryNameError(Exception):
    pass

class RawOffloadError(Exception):
    pass


DATETIME_FORMAT = "%Y-%m-%dT%H%M%S"  # Global format


# Phase 1: Copy any new pics from iPhone to raw_offload folder.
# Find iPhone in GVFS.
# Create new RawOffload folder.
# Copy in all images newer than the last raw offload.

class iPhoneDCIM(object):
    """Represents DCIM folder structure at gvfs iPhone (or iPad) mount point"""
    def __init__(self):
        self.find_root()

    def find_root(self):
        # Look at all gvfs handles to find one having name starting w/ "gphoto".
        # There should only be one.
        gvfs_handles = listdir(IPHONE_DCIM_PREFIX)
        count = 0
        for i, handle in enumerate(gvfs_handles):
            if handle[0:6] == 'gphoto':
                iphone_handle = handle
                count += 1

        if count == 0 or not listdir(IPHONE_DCIM_PREFIX + iphone_handle):
            input("Error: Can't find iOS device in %s\nPress Enter to try again." % IPHONE_DCIM_PREFIX)
            self.find_root()
        elif count > 1:
            raise iPhoneLocError("Error: Multiple 'gphoto' handles in " + IPHONE_DCIM_PREFIX)
            # Have not seen this happen. In fact, with two iOS devices plugged
            # in, only the first one shows up as a gvfs directory.
        else:
            # Found exactly one "gphoto" folder
            self.DCIM_path = IPHONE_DCIM_PREFIX + iphone_handle + "/DCIM/"
            self.APPLE_folders = listdir(self.DCIM_path)
            self.APPLE_folders.sort()

    def get_root(self):
        return self.DCIM_path

    def list_APPLE_folders(self):
        return self.APPLE_folders

    def APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.APPLE_folders:
            return self.get_root() + APPLE_folder_name + '/'
        else:
            raise DirectoryNameError("Tried to access iOS DCIM folder %s, "
                                     "but it does not exist in\n%s\n"
                                     % (APPLE_folder_name, get_root()))

    def APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by APPLE_folder_path() method
        APPLE_contents = listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def update_root_path(self):
        self.find_root()
        return self.get_root()

    def __str__(self):
        return self.get_root()

    def __repr__(self):
        return ("iPhone DCIM directory object with path:\n\t" + self.get_root())


##########################################

# Program creates new folder with today’s date in raw offload directory.
# Copies all photos that did not exist last time device was offloaded.

class RawOffloadGroup(object):
    """Requires no input. Creates object representing Raw_Offload root struct."""
    def __init__(self, bu_root_path):
        # Upon creation, RawOffloadGroup creates a RawOffload object for the
        # most recent offload and any other offloads that contain latest APPLE
        # folder (the overlap folder)

        self.bu_root_path = bu_root_path
        self.RO_root_path = self.bu_root_path + "Raw_Offload/"

        # Double-check Raw_Offload folder is there.
        if not path_exists(self.RO_root_path):
            raise RawOffloadError("Raw_Offload dir not found at %s! "
                        "Pics not offloaded. Terminating" % self.RO_root_path)

        # Create attribute that contains all raw-offload folder names.
        RO_root_contents = listdir(self.RO_root_path)
        RO_root_contents.sort()
        self.offload_list = RO_root_contents

        # Find all folders that contain the newest APPLE folder (the "overlap" folder)
        # and create RawOffload objects for them. Put into a list.
        self.find_overlap_offloads()


    def get_BU_root(self):
        return self.bu_root_path

    def get_RO_root(self):
        return self.RO_root_path

    def find_overlap_offloads(self):
        """Create a RawOffload instance representing most recent offload."""

        if isfile(self.offload_list[-1]):
            raise DirectoryNameError("File found where only offload folders should "
            "be in %s. Cannot determine last offload." % self.offload_list)
        else:
            LastOffload = RawOffload(self.offload_list[-1], self)

        # Find every offload that shares the overlap folder (latest APPLE).
        self.prev_offload_list = [LastOffload]
        overlap_folder = LastOffload.newest_APPLE_folder()
        for offload in self.offload_list[:-1]:
            if overlap_folder in listdir(self.get_RO_root() + offload):
                # Make RawOffload object for each offload containing overlap
                # folder, and add them to the list.
                PrevOL = RawOffload(offload, self)
                self.prev_offload_list += [PrevOL]
        self.prev_offload_list.sort()

    def get_offload_list(self):
        return self.offload_list.copy()

    def get_last_offload(self):
        return self.prev_offload_list[-1]

    def overlap_offload_list(self):
        return self.prev_offload_list.copy()

    def newest_APPLE_folder(self):
        if isfile(self.get_last_offload().newest_APPLE_folder()):
            raise DirectoryNameError("File found where only APPLE folders should "
            "be in %s. Cannot determine newest APPLE folder." % self.get_last_offload())
        return self.get_last_offload().newest_APPLE_folder()

    def create_new_offload(self):
        # Pass in current timestamp as the new offload's name
        new_timestamp = strftime(DATETIME_FORMAT)
        NewOffload = NewRawOffload(new_timestamp, self)
        return NewOffload

    def __str__(self):
        return self.get_RO_root()

    def __repr__(self):
        return "RawOffloadGroup object with path:\n\t" + self.get_RO_root()


class RawOffload(object):
    """Represents a datestamped folder under the Raw_Offload root containing
    APPLE folders."""
    def __init__(self, offload_name, Parent):
        self.Parent = Parent
        self.full_path = self.Parent.get_RO_root() + offload_name + '/'

        if len(offload_name) != 17:
            raise DirectoryNameError("Raw_Offload directory name '%s' not in "
                                            "expected format." % offload_name)
        else:
            self.offload_dir = offload_name

    def get_parent(self):
        return self.Parent

    def get_offload_dir(self):
        return self.offload_dir

    def get_full_path(self):
        return self.full_path

    def list_APPLE_folders(self):
        # Sorted; not full paths
        APPLE_folders = listdir(self.full_path)
        APPLE_folders.sort()
        return APPLE_folders

    def newest_APPLE_folder(self):
        if isfile(self.list_APPLE_folders()[-1]):
            raise DirectoryNameError("File found where only APPLE folders should "
            "be in %s. Cannot determine newest APPLE folder." % self.full_path)
        else:
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
        return self.offload_dir

    def get_timestamp(self):
        return strptime(self.offload_dir, DATETIME_FORMAT)

    def __str__(self):
        return self.full_path

    def __repr__(self):
        return "RawOffload object with path:\n\t" + self.full_path

    def __lt__(self, other):
        return self.offload_dir < other.offload_dir


class NewRawOffload(RawOffload):
    """Represents new RawOffload instance (timestamped folder).
    Includes functionality to perform the offload from an iPhoneDCIM obj."""

    def __init__(self, offload_name, Parent):
        self.Parent = Parent
        self.src_iPhone_dir = iPhoneDCIM()

        self.create_target_folder(offload_name)
        self.run_overlap_offload()
        self.run_new_offload()

    def create_target_folder(self, offload_name):
        # Create new directory w/ today's date/time stamp in Raw_Offload.
        self.offload_dir = offload_name
        self.full_path = (self.Parent.get_RO_root() + self.offload_dir + '/')
        if path_exists(self.full_path):
            # Make sure folder w/ this name (current date/time stamp) doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                  "directory already exists. No changes made."
                                                    % self.full_path)
        else:
            mkdir(self.full_path)

    def run_overlap_offload(self):
        # Find the last (newest) APPLE dir in the most recent offload.
        self.overlap_folder = self.Parent.newest_APPLE_folder()
        print("Overlap folder: %s" % self.overlap_folder)

        # See if the newest APPLE folder in the offload dir is found on the phone
        # as well. Example when it won't be: new phone.
        try:
            src_APPLE_path = self.src_iPhone_dir.APPLE_folder_path(self.overlap_folder)
        except DirectoryNameError:
            while True:
                confirm_no_ovp = input("\nWARNING: No folder found on source "
                "device corresponding to overlap offload folder %s.\n"
                "Check source device for folder %s.\nPress Enter to continue, "
                "skipping overlap offload.\nOr press 'q' to quit.\n>>> "
                         % (self.overlap_folder, self.overlap_folder))

                if confirm_no_ovp == '':
                    self.overlap_folder = None
                    return
                elif confirm_no_ovp.lower() == 'q':
                    raise DirectoryNameError("Tried to access %s on source device "
                    "for overlap offload, but it could not be found."
                     % self.overlap_folder)

        # Runs only if there is a match found between overlap folder in offload
        # directory and the source device.
        src_APPLE_pics = self.src_iPhone_dir.APPLE_contents(self.overlap_folder)
        src_APPLE_pics.sort()

        # Create a destination folder in the new Raw Offload directory with the same APPLE name.
        self.new_overlap_path = self.full_path + self.overlap_folder + '/'
        mkdir(self.new_overlap_path)

        # Iterate through each folder that contains the overlap folder.
        # store the img names in a set for fast membership testing (order not important).
        prev_APPLE_pics = set()
        for PrevOffload in self.Parent.overlap_offload_list():

            for pic in PrevOffload.APPLE_contents(self.overlap_folder):
                prev_APPLE_pics.add(pic)

        # Run througha all photos, only copying ones which are new (not contained
        # in overlap folders):
        print("Overlap-transfer progress:")
        # tqdm provides the terminal status bar
        for img_name in tqdm(src_APPLE_pics):

            if img_name not in prev_APPLE_pics:
                src_img_path = src_APPLE_path + img_name

                # iOS has bug that can terminate PC connection during copies.
                # Requires iOS restart to fix.
                try:
                    sh_copy2(src_img_path, self.new_overlap_path)
                except IOError:
                    ioerror_response = input("\nEncountered IOError during overlap "
                    "offload. iPhone/iPad must be restarted to fix.\n"
                    "Restart iOS device then press Enter to continue offload, "
                    "or press 'q' to quit.\n>>> ")
                    if ioerror_response == '':
                        # tell iPhoneDCIM object to re-find its gvfs root
                        # ("gphoto" handle likely changed)
                        self.src_iPhone_dir.find_root()
                        # Try copy operation again. If it fails this time, something
                        # else is going on. Have not seen IOError persist on same day after restart
                        sh_copy2(src_img_path, self.new_overlap_path)
                        # update local variable that has gvfs root path embedded
                        src_APPLE_path = self.src_iPhone_dir.APPLE_folder_path(self.overlap_folder)
                        continue
                    elif ioerror_response.lower() == 'q':
                        raise iPhoneIOError("Cannot access files on source device. "
                        "for overlap offload. Restart device to fix then try again.")
            else:
                # If a picture of the same name is found in an overlap folder,
                # ignore new one. Leave old one in place.
                pass

        # If the target overlap APPLE folder ends up being empty, delete it.
        # This would happen in the rare case of the previous offload happening
        # just before the next photo saved starts a new APPLE photo on the device.
        if not self.APPLE_contents(self.overlap_folder):
            rmdir(self.new_overlap_path)
            print("No new pictures contained in %s (overlap folder) since "
                                    "last offload." % self.overlap_folder)


    def run_new_offload(self):
        # Look for new APPLE folders to offload.
        src_APPLE_list = self.src_iPhone_dir.list_APPLE_folders()

        # If the iPhone contains any APPLE folders numbered higher than the
        # overlap case, copy them in full.
        new_APPLE_folder = False
        for folder in src_APPLE_list:
            # If there is no overlap folder, like in the case of a brand new device,
            # folder-name comparison (second half of if stmt) not used. self.overlap_folder
            # is set to None (by run_overlap_offload() method) in that case.
            if not self.overlap_folder or folder > self.overlap_folder:
                print("New APPLE folder %s found on iPhone - copying." % folder)
                # Create the new destination folder
                new_dst_APPLE_path = self.full_path + folder + '/'
                mkdir(new_dst_APPLE_path)

                # Loop through source APPLE folder and copy to new dst folder.
                imgs = listdir(self.src_iPhone_dir.APPLE_folder_path(folder))
                imgs.sort() # Need to sort so if a pic offload fails, you can determine which
                for img in tqdm(imgs):
                    try:
                        sh_copy2(self.src_iPhone_dir.APPLE_folder_path(folder) + img,
                                new_dst_APPLE_path)
                    except IOError:
                        ioerror_response = input("\nEncountered IOError during new "
                        "offload. iPhone/iPad must be restarted to fix.\n"
                        "Restart iOS device then press Enter to continue offload, "
                        "or press 'q' to quit.\n>>> ")
                        if ioerror_response == '':
                            # tell iPhoneDCIM object to re-find its gvfs root
                            # ("gphoto" handle likely changed)
                            self.src_iPhone_dir.find_root()
                            # Try copy operation again. If it fails this time, something
                            # else is going on. Have not seen IOError persist on same day after restart
                            sh_copy2(self.src_iPhone_dir.APPLE_folder_path(folder) + img,
                                    new_dst_APPLE_path)
                            continue
                        elif ioerror_response.lower() == 'q':
                            raise iPhoneIOError("Cannot access files on source device. "
                            "for overlap offload. Restart device to fix then try again.")

                new_APPLE_folder = True # Set if any new folder found in loop

        if not new_APPLE_folder:
            print("No new APPLE folders found on iPhone.")

    def __repr__(self):
        return "NewRawOffload object with path:\n\t" + self.full_path


# TEST
# rog = RawOffloadGroup()
# nro = rog.create_new_offload()


# iPhone DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.
