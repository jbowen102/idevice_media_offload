# https://docs.python.org/3/library/time.html
import os
import shutil
import time
from tqdm import tqdm, trange
import subprocess

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
        # If none found, an alternate method of mounting will be attempted.
        gvfs_handles = os.listdir(IPHONE_DCIM_PREFIX)
        count = 0
        for i, handle in enumerate(gvfs_handles):
            if handle[0:6] == 'gphoto':
                iphone_handle = handle
                count += 1

        if count:
            dir_type = "gphoto"
        else:
            timeout = 20
            print("Standard DCIM location not found. Attempting fallback "
                                            "method (%d seconds)." % timeout)
            # Try fallback method of mounting device
            # Find device S/N
            SN_return = subprocess.run(["dmesg | grep SerialNumber:"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            # Parse grep output. S/N is 24 digits
            iphone_SN = str(SN_return.stdout).split("SerialNumber: ")[1][:24]

            ### mount device by using its S/N
            pid = os.fork()
            # https://stackoverflow.com/questions/3032805/starting-a-separate-process
            if pid: # parent process
                for i in trange(timeout):
                    time.sleep(1)
                pass
            else: # child process
                try:
                    subprocess.run(["nemo", "afc://%s" % iphone_SN],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
                   # Will throw error but often still mounts.
                except subprocess.TimeoutExpired:
                    print("Timeout expired")
                    quit()
                except:
                    print("Child process encountered unexpected error before timeout.")
                    quit()
                finally:
                    quit()

            for i, handle in enumerate(gvfs_handles):
                # Target dir has S/N digits as last characters in name
                if handle[-len(iphone_SN):] == iphone_SN:
                    iphone_handle = handle
                    count += 1
            if count:
                dir_type = "fallback (S/N-based)"
                while True:
                    fallback_ans = input("Use fallback DCIM (includes deleted "
                                    "images) [Y] or retry DCIM search [N].\n> ")
                    if fallback_ans in ["Y", "y"]:
                        try:
                            subprocess.run(["xdg-open", "%s" % iphone_handle],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except OSError:
                            print("Fallback DCIM not reachable. Retrying search.")
                            print("\n")
                            self.find_root()
                            return
                        break
                    elif fallback_ans in ["N", "n"]:
                        print("\n")
                        self.find_root()
                        return

        if count == 1 and os.listdir(IPHONE_DCIM_PREFIX + iphone_handle):
            # Found exactly one "gphoto" folder
            self.DCIM_path = IPHONE_DCIM_PREFIX + iphone_handle + "/DCIM/"
            self.APPLE_folders = os.listdir(self.DCIM_path)
            if not self.APPLE_folders:
                # Empty DCIM folder indicates temporary issue like locked device.
                os_error_response = input("\nCan't access device pictures.\n"
                "Plugging device in again and unlocking will likely fix issue."
                "\nPlug back in then press Enter to continue, or press 'q' "
                                                                "to quit.\n> ")
                if os_error_response.lower() == 'q':
                    raise iPhoneIOError("Cannot access files on source device. "
                    "Plug device in again and unlock to fix. Then run program "
                                                                    "again.")
                else:
                    # Retry everything.
                    # Need to re-find gvfs root ("gphoto" handle likely changed)
                    print("\n")
                    self.find_root()
                    return
            else:
                print("Successfully accessed %s DCIM mount point." % dir_type)
            self.APPLE_folders.sort()

        elif count == 1:
            # iPhone handle exists, but DCIM folder not present.
            # Unlocking doesn't always solve it.
            input("Error: Found %s mount point, but DCIM folder not "
                                    "present.\nUnlock device (or reconnect) and "
                                        "press Enter to try again." % dir_type)
            print("\n")
            self.find_root()
            return
        elif count > 1:
            raise iPhoneLocError("Error: Multiple '%s' handles in %s"
                                               % (dir_type, IPHONE_DCIM_PREFIX))
            # Have not seen this happen. In fact, with two iOS devices plugged
            # in, only the first one shows up as a gvfs directory.
        else:
            input("Error: Can't find iOS device in %s\nPress Enter to try "
                                                "again." % IPHONE_DCIM_PREFIX)
            print("\n")
            self.find_root()
            return

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
                                     % (APPLE_folder_name, self.get_root()))

    def APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by APPLE_folder_path() method
        APPLE_contents = os.listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    # def update_root_path(self):
    #     self.find_root()
    #     return self.get_root()

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
        if not os.path.exists(self.RO_root_path):
            raise RawOffloadError("Raw_Offload dir not found at %s! "
                        "Pics not offloaded. Terminating" % self.RO_root_path)

        self.generate_offload_list()
        # Remove extraneous things from raw-offload root, like files or empty folders.
        self.remove_bad_dir_items()

        # create latest offload object (self.LatestOffload)
        self.find_latest_offload()

        # Find all folders that contain the newest APPLE folder (the "overlap" folder)
        # and create RawOffload objects for them. Put into a list.
        self.find_overlap_offloads()

    def get_BU_root(self):
        return self.bu_root_path

    def get_RO_root(self):
        return self.RO_root_path

    def generate_offload_list(self):
        # Create list that contains all raw-offload folder names.
        RO_root_contents = os.listdir(self.RO_root_path)
        RO_root_contents.sort()
        self.offload_list = RO_root_contents

    def get_offload_list(self):
        # List of names
        return self.offload_list.copy()

    def get_last_offload_name(self):
        # returns name only
        return self.get_offload_list()[-1]

    def find_latest_offload(self):
        self.LatestOffload = RawOffload(self.get_last_offload_name(), self)

    def get_latest_offload_obj(self):
        # Returns RawOffload object
        return self.LatestOffload

    def get_overlap_offload_list(self):
        return self.overlap_offload_list.copy()

    def newest_APPLE_folder(self):
        # needs object
        return self.get_latest_offload_obj().list_APPLE_folders()[-1]

    def remove_bad_dir_items(self):
        if os.path.isfile(self.get_RO_root() + self.get_last_offload_name()):
            input("File found where only offload folders should be in RO root.\n"
            "Press Enter to try again.\n> ")
            # try again
            self.remove_bad_dir_items()
        elif not os.listdir(self.get_RO_root() + self.get_last_offload_name()):
            delete_empty_ro = input("Folder %s in raw_offload directory is empty, "
            "probably from previous aborted offload.\n"
            "Press 'd' to delete folder and retry operation.\n"
            "Or press 'q' to quit.\n> " % self.get_last_offload_name())

            if delete_empty_ro == 'd':
                # Delete that folder name from list attribute
                os.rmdir(self.get_RO_root() + self.get_last_offload_name())

                # re-generate offload list after deleting an element
                self.generate_offload_list()
                # Start over to check for any other invalid items
                self.remove_bad_dir_items()
            elif delete_empty_ro == 'q':
                raise RawOffloadError("Remove empty folder from raw-offload directory.")
            else:
                # Repeat prompt if input not recognized
                self.remove_bad_dir_items()
        else:
            pass

    def find_overlap_offloads(self):
        """Create a RawOffload instance representing most recent offload."""

        # Find every offload that shares the overlap folder (latest APPLE).
        self.overlap_offload_list = [self.get_latest_offload_obj()]
        overlap_folder = self.get_latest_offload_obj().newest_APPLE_folder()

        # Check all other offload folders for the overlap folder
        for offload in self.offload_list[:-1]:
            if overlap_folder in os.listdir(self.get_RO_root() + offload):
                # Make RawOffload object for each offload containing overlap
                # folder, and add them to the list.
                PrevOL = RawOffload(offload, self)
                self.overlap_offload_list += [PrevOL]
        self.overlap_offload_list.sort()

    def create_new_offload(self):
        # Pass in current timestamp as the new offload's name
        new_timestamp = time.strftime(DATETIME_FORMAT)
        NewOffload = NewRawOffload(new_timestamp, self)
        self.merge_todays_offloads()
        return NewOffload

    def merge_todays_offloads(self):
        today = time.strftime("%Y-%m-%d")
        todays_offloads = []

        # Have to refresh offload list. Doesn't yet contain new offload folder
        self.generate_offload_list()

        for offload_folder_name in self.get_offload_list():
            if today in offload_folder_name:
                todays_offloads.append(offload_folder_name)
        todays_offloads.sort()

        if len(todays_offloads) > 1:
            print("Multiple Raw_Offload folders with today's date:")
            for folder in todays_offloads:
                print("\t%s" % folder)

            while True:
                merge_response = input("Merge folders? (Y/N)\n> ")
                if merge_response.lower() == 'y':
                    self.raw_offload_merge(todays_offloads)
                    break
                elif merge_response.lower() == 'n':
                    break
                else:
                    continue

    def raw_offload_merge(self, list_of_offload_names):
        # Merges folders together into latest one
        list_of_offload_names.sort()
        newest_folder = list_of_offload_names[-1]
        old_folders = list_of_offload_names[:-1]

        DestFolder = RawOffload(newest_folder, self)

        for folder_i in old_folders:
            SrcFolder = RawOffload(folder_i, self)

            for APPLE_folder in SrcFolder.list_APPLE_folders():
                # If the folder doesn't exist in the destination folder yet, create it.
                if not APPLE_folder in DestFolder.list_APPLE_folders():
                    os.mkdir(DestFolder.get_full_path() + APPLE_folder)

                for image in SrcFolder.APPLE_contents(APPLE_folder):
                    shutil.move(SrcFolder.APPLE_folder_path(APPLE_folder) + image,
                            DestFolder.APPLE_folder_path(APPLE_folder))
                # Delete each APPLE directory after copying everything out of it
                os.rmdir(SrcFolder.APPLE_folder_path(APPLE_folder))
            # Delete each RO directory after copying everything out of it
            os.rmdir(SrcFolder.get_full_path())

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
            self.offload_dir_name = offload_name

    def get_parent(self):
        return self.Parent

    def get_full_path(self):
        return self.full_path

    def list_APPLE_folders(self):
        # Sorted; not full paths
        APPLE_folders = os.listdir(self.get_full_path())
        APPLE_folders.sort()
        return APPLE_folders

    def newest_APPLE_folder(self):
        if os.path.isfile(self.list_APPLE_folders()[-1]):
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
        APPLE_contents = os.listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def get_dir_name(self):
        return self.offload_dir_name

    def get_timestamp_struct(self):
        return time.strptime(self.offload_dir_name, DATETIME_FORMAT)

    def __str__(self):
        return self.full_path

    def __repr__(self):
        return "RawOffload object with path:\n\t" + self.full_path

    def __lt__(self, other):
        return self.offload_dir_name < other.offload_dir_name


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
        self.offload_dir_name = offload_name
        self.full_path = (self.Parent.get_RO_root() + self.offload_dir_name + '/')
        if os.path.exists(self.full_path):
            # Make sure folder w/ this name (current date/time stamp) doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                  "directory already exists. No changes made."
                                                    % self.full_path)
        else:
            os.mkdir(self.full_path)

    def run_overlap_offload(self):
        # Find the last (newest) APPLE dir in the most recent offload.
        self.overlap_folder = self.Parent.newest_APPLE_folder()
        print("Overlap folder: %s" % self.overlap_folder)

        # See if the newest APPLE folder in the offload dir is found on the phone
        # as well. Example when it won't be: new phone.
        # Also will not be found if device got locked or something and program can't see photos.
        while True:
            try:
                src_APPLE_path = self.src_iPhone_dir.APPLE_folder_path(self.overlap_folder)
                break
            except DirectoryNameError:
                no_ovp_response = input("\nWARNING: No folder found on source "
                "device corresponding to overlap offload folder %s.\n"
                "Check source device for folder %s.\n"
                "Press Enter to retry.\n"
                "Or press 'c' to continue, skipping overlap offload.\n"
                "Or press 'q' to quit.\n> "
                         % (self.overlap_folder, self.overlap_folder))

                if no_ovp_response.lower() == 'c':
                    self.overlap_folder = None
                    return
                elif no_ovp_response.lower() == 'q':
                    raise DirectoryNameError("Tried to access %s on source device "
                    "for overlap offload, but it could not be found."
                     % self.overlap_folder)
                else:
                    # Go back to top of while loop and retry
                    continue

        # Runs only if there is a match found between overlap folder in offload
        # directory and the source device.
        src_APPLE_pics = self.src_iPhone_dir.APPLE_contents(self.overlap_folder)
        src_APPLE_pics.sort()

        # Create a destination folder in the new Raw Offload directory with the same APPLE name.
        self.new_overlap_path = self.full_path + self.overlap_folder + '/'
        os.mkdir(self.new_overlap_path)

        # Iterate through each folder that contains the overlap folder.
        # store the img names in a set for fast membership testing (order not important).
        prev_APPLE_pics = set()
        for PrevOffload in self.Parent.get_overlap_offload_list():

            for pic in PrevOffload.APPLE_contents(self.overlap_folder):
                prev_APPLE_pics.add(pic)

        # Run througha all photos, only copying ones which are new (not contained
        # in overlap folders):
        print("Overlap-transfer progress:")
        # tqdm provides the terminal status bar
        for img_name in tqdm(src_APPLE_pics):

            if img_name not in prev_APPLE_pics:
                src_img_path = src_APPLE_path + img_name

                # iOS has bug that can terminate PC connection.
                # Requires iOS restart to fix.
                while True:
                    try:
                        shutil.copy2(src_img_path, self.new_overlap_path)
                        break
                    except OSError:
                        os_error_response = input("\nEncountered device I/O error during overlap "
                        "offload. iPhone/iPad may need to be restarted to fix.\n"
                        "Press Enter to attempt to continue offload.\n"
                        "Or press 'q' to quit.\n> ")
                        if os_error_response.lower() == 'q':
                            raise iPhoneIOError("Cannot access files on source device. "
                            "for overlap offload. Restart device to fix then run program again.")
                        else:
                            # tell iPhoneDCIM object to re-find its gvfs root
                            # ("gphoto" handle likely changed)
                            self.src_iPhone_dir.find_root()
                            # update local variable that has gvfs root path embedded
                            src_APPLE_path = self.src_iPhone_dir.APPLE_folder_path(self.overlap_folder)
                            # retry
                            continue
            else:
                # If a picture of the same name is found in an overlap folder,
                # ignore new one. Leave old one in place.
                pass

        # If the target overlap APPLE folder ends up being empty, delete it.
        # This would happen in the rare case of the previous offload happening
        # just before the next photo saved starts a new APPLE photo on the device.
        if not self.APPLE_contents(self.overlap_folder):
            os.rmdir(self.new_overlap_path)
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
                os.mkdir(new_dst_APPLE_path)

                # Loop through source APPLE folder and copy to new dst folder.
                imgs = os.listdir(self.src_iPhone_dir.APPLE_folder_path(folder))
                imgs.sort() # Need to sort so if a pic offload fails, you can determine which
                for img in tqdm(imgs):
                    while True:
                        try:
                            shutil.copy2(self.src_iPhone_dir.APPLE_folder_path(folder) + img,
                                    new_dst_APPLE_path)
                            break
                        except OSError:
                            os_error_response = input("\nEncountered device I/O error during new "
                            "offload. iPhone/iPad may need to be restarted to fix.\n"
                            "Press Enter to attempt to continue offload.\n"
                            "Or press 'q' to quit.\n> ")
                            if os_error_response.lower() == 'q':
                                raise iPhoneIOError("Cannot access files on source device. "
                                "for overlap offload. Restart device to fix then run program again.")
                            else:
                                # tell iPhoneDCIM object to re-find its gvfs root
                                # ("gphoto" handle likely changed)
                                self.src_iPhone_dir.find_root()
                                # try again
                                continue

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
