# https://docs.python.org/3/library/time.html
import os
import shutil
import time
from tqdm import tqdm, trange
import subprocess

from idevice_media_offload.dir_names import IDEVICE_MOUNT_POINT
from idevice_media_offload.pic_categorize_tool import os_open

class iDeviceLocError(Exception):
    pass

class iDeviceIOError(Exception):
    pass

class DirectoryNameError(Exception):
    pass

class RawOffloadError(Exception):
    pass


DATETIME_FORMAT = "%Y-%m-%dT%H%M%S"  # Global format


# Phase 1: Copy any new pics from device to raw_offload folder.
# Find device in GVFS dir.
# Create new RawOffload folder.
# Copy in all images added since last raw offload (based on inclusion in
# previous offload, not date).

class iDeviceDCIM(object):
    """Represents DCIM folder structure at iDevice's gvfs mount point"""
    def __init__(self):
        self.find_root()

    def find_root(self):
        # Look at all gvfs handles to find one having name starting w/ "gphoto".
        # There should only be one.
        # If none found, an alternate method of mounting will be attempted.
        gvfs_handles = os.listdir(IDEVICE_MOUNT_POINT)
        count = 0
        for i, handle in enumerate(gvfs_handles):
            if handle[0:6] == 'gphoto':
                iDevice_handle = handle
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
            iDevice_SN = str(SN_return.stdout).split("SerialNumber: ")[1][:24]

            ### mount device by using its S/N
            pid = os.fork()
            # https://stackoverflow.com/questions/3032805/starting-a-separate-process
            if pid: # parent process
                for i in trange(timeout):
                    time.sleep(1)
                pass
            else: # child process
                try:
                    subprocess.run(["nemo", "afc://%s" % iDevice_SN],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                                timeout=timeout)
                   # Will throw error but often still mounts.
                except subprocess.TimeoutExpired:
                    print("Timeout expired")
                    quit()
                except:
                    print("Child process encountered unexpected error before "
                                                                    "timeout.")
                    quit()
                finally:
                    quit()

            for i, handle in enumerate(gvfs_handles):
                # Target dir has S/N digits as last characters in name
                if handle[-len(iDevice_SN):] == iDevice_SN:
                    iDevice_handle = handle
                    count += 1
            if count:
                dir_type = "fallback (S/N-based)"
                while True:
                    fallback_ans = input("Use fallback DCIM (includes deleted "
                                    "images) [Y] or retry DCIM search [N].\n> ")
                    if fallback_ans in ["Y", "y"]:
                        try:
                            subprocess.run(["xdg-open", "%s" % iDevice_handle],
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

        if count == 1 and os.listdir(os.path.join(IDEVICE_MOUNT_POINT, iDevice_handle)):
            # Found exactly one "gphoto" folder
            iDevice_root_path = os.path.join(IDEVICE_MOUNT_POINT, iDevice_handle)
            self.DCIM_path = os.path.join(iDevice_root_path, "DCIM/")
            self.APPLE_folders = os.listdir(self.DCIM_path)
            if not self.APPLE_folders:
                # Empty DCIM folder indicates temporary issue like locked device.
                os_error_response = input("\nCan't access iDevice pictures.\n"
                "Plugging device in again and unlocking will likely fix issue."
                "\nPlug back in then press Enter to continue, or press 'q' "
                                                                "to quit.\n> ")
                if os_error_response.lower() == 'q':
                    raise iDeviceIOError("Cannot access files on iDevice. "
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
            # iDevice handle exists, but DCIM folder not present.
            # Unlocking doesn't always solve it.
            input("Error: Found %s mount point, but DCIM folder not present.\n"
                                      "Unlock iDevice (or reconnect) and press "
                                              "Enter to try again." % dir_type)
            print("\n")
            self.find_root()
            return
        elif count > 1:
            raise iDeviceLocError("Error: Multiple '%s' handles in %s"
                                              % (dir_type, IDEVICE_MOUNT_POINT))
            # Have not seen this happen. In fact, with two iDevices plugged
            # in, only the first one shows up as a gvfs directory.
        else:
            input("Error: Can't find iDevice in %s\nPress Enter to try "
                                                 "again." % IDEVICE_MOUNT_POINT)
            print("\n")
            self.find_root()
            return

    def get_root(self):
        return self.DCIM_path

    def list_APPLE_folders(self):
        return self.APPLE_folders

    def APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.APPLE_folders:
            return os.path.join(self.get_root(), APPLE_folder_name + '/')
        else:
            raise DirectoryNameError("Tried to access iDevice DCIM folder %s, "
                                     "but it does not exist in\n%s\n"
                                     % (APPLE_folder_name, self.get_root()))

    def APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by APPLE_folder_path() method
        APPLE_contents = os.listdir(self.APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def __str__(self):
        return self.get_root()

    def __repr__(self):
        return ("iDevice DCIM directory object with path:\n\t%s" % self.get_root())


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
        self.RO_root_path = os.path.join(self.bu_root_path, "Raw_Offload/")

        # Double-check Raw_Offload folder is there.
        if not os.path.exists(self.RO_root_path):
            raise RawOffloadError("Raw_Offload dir not found at %s! "
                        "Pics not offloaded. Terminating" % self.RO_root_path)

        self.generate_offload_list()

        # Test if raw-offload dir is populated or if its a newly-created structure.
        if self.offload_list:
            # create latest offload object (self.LatestOffload)
            self.find_latest_offload()

            # Find all folders that contain the newest APPLE folder (the "overlap"
            # folder)and create RawOffload objects for them. Put into a list.
            self.find_overlap_offloads() # FAILS

        else:
            # If this device has never been offloaded before
            pass

    def get_BU_root(self):
        return self.bu_root_path

    def get_RO_root(self):
        return self.RO_root_path

    def generate_offload_list(self):
        # Create list that contains all raw-offload folder names.
        RO_root_contents = os.listdir(self.RO_root_path)
        RO_root_contents.sort()
        self.offload_list = RO_root_contents
        self.remove_bad_dir_items()

    def get_offload_list(self):
        # List of names
        return self.offload_list.copy()

    def get_last_offload_name(self):
        # returns name only
        if self.offload_list:
            return self.get_offload_list()[-1]
        else:
            return None

    def find_latest_offload(self):
        if self.offload_list:
            self.LatestOffload = RawOffload(self.get_last_offload_name(), self)
            return self.LatestOffload
        else:
            return None

    def get_latest_offload_obj(self):
        # Returns RawOffload object
        if self.offload_list:
            return self.LatestOffload
        else:
            return None

    def get_overlap_offload_list(self):
        if self.offload_list:
            return self.overlap_offload_list.copy()
        else:
            return None

    def get_newest_APPLE_folder(self):
        # needs object
        if self.get_latest_offload_obj():
            return self.get_latest_offload_obj().get_newest_APPLE_folder()
        else:
            return None

    def remove_bad_dir_items(self):
        last_offload_path = os.path.join(self.get_RO_root(), self.get_last_offload_name())
        if not self.offload_list:
            # If the Raw_Offload folder is empty, no action needed.
            return
        elif os.path.isfile(last_offload_path):
            input("File found where only offload folders should be in RO root.\n"
            "Manually remove and press Enter to try again.\n> ")
            os_open(self.get_RO_root())
            # Regenerate list and repeat this function call
            self.generate_offload_list()
        elif not os.listdir(last_offload_path):
            delete_empty_ro = input("Folder %s in raw_offload directory is "
                            "empty, probably from previous aborted offload.\n"
                            "Press 'd' to delete folder and retry operation.\n"
                    "Or press 'q' to quit.\n> " % self.get_last_offload_name())

            if delete_empty_ro == 'd':
                os.rmdir(last_offload_path)
            elif delete_empty_ro == 'q':
                raise RawOffloadError("Remove empty folder from raw-offload "
                                                                  "directory.")

            # Regenerate list and repeat this function call
            self.generate_offload_list()

    def find_overlap_offloads(self):
        """Create a RawOffload instance representing most recent offload."""

        # Find every offload that shares the overlap folder (latest APPLE).
        self.overlap_offload_list = [self.get_latest_offload_obj()]
        overlap_folder = self.get_latest_offload_obj().get_newest_APPLE_folder()

        # Check all other offload folders for the overlap folder
        for offload in self.offload_list[:-1]:
            offload_path = os.path.join(self.get_RO_root(), offload)
            if overlap_folder in os.listdir(offload_path):
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
                # If the dir doesn't exist in the destination dir yet, create it.
                if not APPLE_folder in DestFolder.list_APPLE_folders():
                    dest_APPLE_path = os.path.join(DestFolder.get_full_path(),
                                                                   APPLE_folder)
                    os.mkdir(dest_APPLE_path)

                for image in SrcFolder.APPLE_contents(APPLE_folder):
                    src_img_path = os.path.join(
                               SrcFolder.APPLE_folder_path(APPLE_folder), image)
                    shutil.move(src_img_path,
                                    DestFolder.APPLE_folder_path(APPLE_folder))
                # Delete each APPLE directory after copying everything out of it
                os.rmdir(SrcFolder.APPLE_folder_path(APPLE_folder))
            # Delete each RO directory after copying everything out of it
            os.rmdir(SrcFolder.get_full_path())

    def __str__(self):
        return self.get_RO_root()

    def __repr__(self):
        return "RawOffloadGroup object with path:\n\t%s" % self.get_RO_root()


class RawOffload(object):
    """Represents a datestamped folder under the Raw_Offload root containing
    APPLE folders."""
    def __init__(self, offload_name, Parent):
        self.Parent = Parent
        self.full_path = os.path.join(self.Parent.get_RO_root(),
                                                            offload_name + '/')

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

    def get_newest_APPLE_folder(self):
        if not self.list_APPLE_folders():
            return None
        elif os.path.isfile(self.list_APPLE_folders()[-1]):
            raise DirectoryNameError("File found where only APPLE folders "
                        "should be in %s. Cannot determine newest APPLE folder."
                                                            % self.full_path)
        else:
            return self.list_APPLE_folders()[-1]

    def APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.list_APPLE_folders():
            return os.path.join(self.full_path, APPLE_folder_name + '/')
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
        return "RawOffload object with path:\n\t%s" % self.full_path

    def __lt__(self, other):
        return self.offload_dir_name < other.offload_dir_name


class NewRawOffload(RawOffload):
    """Represents new RawOffload instance (timestamped folder).
    Includes functionality to perform the offload from an iDeviceDCIM obj."""

    def __init__(self, offload_name, Parent):
        self.Parent = Parent
        self.src_iDevice_dir = iDeviceDCIM()

        self.create_target_folder(offload_name)
        self.run_overlap_offload()
        self.run_new_offload()

    def create_target_folder(self, offload_name):
        # Create new directory w/ today's date/time stamp in Raw_Offload.
        self.offload_dir_name = offload_name
        self.full_path = os.path.join(self.Parent.get_RO_root(),
                                                    self.offload_dir_name + '/')
        if os.path.exists(self.full_path):
            # Make sure folder w/ this name (current date/time stamp) doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                  "directory already exists. No changes made."
                                                    % self.full_path)
        else:
            os.mkdir(self.full_path)

    def run_overlap_offload(self):
        # Find the last (newest) APPLE dir in the most recent offload.
        self.overlap_folder = self.Parent.get_newest_APPLE_folder()
        if not self.overlap_folder:
            print("No overlap folder present. Proceeding to new offload.")
            return
        else:
            print("Overlap folder: %s" % self.overlap_folder)


        # See if the newest APPLE folder in the offload dir is found on the phone
        # as well. Example when it won't be: new phone.
        # Also will not be found if device got locked or something and program can't see photos.
        while True:
            try:
                src_APPLE_path = self.src_iDevice_dir.APPLE_folder_path(self.overlap_folder)
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
                    raise DirectoryNameError("Tried to access %s on source "
                    "device for overlap offload, but it could not be found."
                     % self.overlap_folder)
                else:
                    # Go back to top of while loop and retry
                    continue

        # Runs only if there is a match found between overlap folder in offload
        # directory and the source device.
        src_APPLE_pics = self.src_iDevice_dir.APPLE_contents(self.overlap_folder)
        src_APPLE_pics.sort()

        # Create a destination folder in the new Raw Offload directory with the same APPLE name.
        self.new_overlap_path = os.path.join(self.full_path,
                                                     self.overlap_folder + '/')
        os.mkdir(self.new_overlap_path)

        # Iterate through each folder that contains the overlap folder.
        # store the img names in a set for fast membership testing (order not important).
        prev_APPLE_pics = set()
        for PrevOffload in self.Parent.get_overlap_offload_list():

            for pic in PrevOffload.APPLE_contents(self.overlap_folder):
                prev_APPLE_pics.add(pic)

        # Run througha all photos, only copying ones which are new (not contained
        # in overlap folders):
        APPLE_pics_to_copy = []
        for img_name in src_APPLE_pics:
            if img_name not in prev_APPLE_pics:
                APPLE_pics_to_copy.append(img_name)
                # If a picture of the same name is found in an overlap folder,
                # ignore new one. Leave old one in place.
        APPLE_pics_to_copy.sort()

        print("Overlap-transfer progress:")
        # tqdm provides the terminal status bar
        for img_name in tqdm(APPLE_pics_to_copy):
            src_img_path = os.path.join(src_APPLE_path, img_name)

            # iOS has bug that can terminate PC connection.
            # Requires iDevice restart to fix.
            while True:
                try:
                    shutil.copy2(src_img_path, self.new_overlap_path)
                    break
                except OSError:
                    os_error_response = input("\nEncountered device I/O error "
                                "during overlap offload. Device may need to be "
                                "restarted to fix.\n"
                                "Press Enter to attempt to continue offload.\n"
                                "Or press 'q' to quit.\n> ")
                    if os_error_response.lower() == 'q':
                        raise iDeviceIOError("Cannot access files on source "
                                "device for overlap offload. Restart device to "
                                "fix then run program again.")
                    else:
                        # tell iDeviceDCIM object to re-find its gvfs root
                        # ("gphoto" handle likely changed)
                        self.src_iDevice_dir.find_root()
                        # update local variable that has gvfs root path embedded
                        src_APPLE_path = self.src_iDevice_dir.APPLE_folder_path(self.overlap_folder)
                        # retry
                        continue

        # If the target overlap APPLE folder ends up being empty, delete it.
        # This would happen in the rare case of the previous offload happening
        # just before the next photo saved starts a new APPLE photo on the device.
        if not self.APPLE_contents(self.overlap_folder):
            os.rmdir(self.new_overlap_path)
            print("No new pictures contained in %s (overlap folder) since "
                                    "last offload." % self.overlap_folder)


    def run_new_offload(self):
        # Look for new APPLE folders to offload.
        src_APPLE_list = self.src_iDevice_dir.list_APPLE_folders()

        # If the device contains any APPLE folders numbered higher than the
        # overlap case, copy them in full.
        new_APPLE_folder = False
        for folder in src_APPLE_list:
            # If there is no overlap folder, like in the case of a brand new device,
            # folder-name comparison (second half of if stmt) not used. self.overlap_folder
            # is set to None (by run_overlap_offload() method) in that case.
            if not self.overlap_folder or folder > self.overlap_folder:
                print("New APPLE folder %s found on iDevice - copying." % folder)
                # Create the new destination folder
                new_dst_APPLE_path = os.path.join(self.full_path, folder + '/')
                os.mkdir(new_dst_APPLE_path)

                # Loop through source APPLE folder and copy to new dst folder.
                imgs = os.listdir(self.src_iDevice_dir.APPLE_folder_path(folder))
                imgs.sort() # Need to sort so if a pic offload fails, you can determine which
                for img in tqdm(imgs):
                    img_full_path = os.path.join(
                            self.src_iDevice_dir.APPLE_folder_path(folder), img)
                    while True:
                        try:
                            shutil.copy2(img_full_path, new_dst_APPLE_path)
                            break
                        except OSError:
                            os_error_response = input("\nEncountered device I/O "
                            "error during new offload. iDevice may need to "
                                "be restarted to fix.\nPress Enter to attempt \n"
                                "to continue offload. Or press 'q' to quit.\n> ")
                            if os_error_response.lower() == 'q':
                                raise iDeviceIOError("Cannot access files on "
                                        "source device. for overlap offload. "
                                "Restart device to fix then run program again.")
                            else:
                                # tell iDeviceDCIM object to re-find its gvfs root
                                # ("gphoto" handle likely changed)
                                self.src_iDevice_dir.find_root()
                                # try again
                                continue

                new_APPLE_folder = True # Set if any new folder found in loop

        if not new_APPLE_folder:
            print("No new APPLE folders found on iDevice.")

    def __repr__(self):
        return "NewRawOffload object with path:\n\t%s" % self.full_path


# TEST
# rog = RawOffloadGroup()
# nro = rog.create_new_offload()


# iDevice DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.
