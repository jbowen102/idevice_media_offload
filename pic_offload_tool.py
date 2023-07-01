import os
import shutil
import time
from tqdm import tqdm, trange
import subprocess

from idevice_media_offload.dir_names import IDEVICE_MOUNT_POINT, NAS_TRANSFER
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
            else:
                self.find_root()
                return

        try:
            iDevice_contents = os.listdir(os.path.join(IDEVICE_MOUNT_POINT, iDevice_handle))
        except OSError:
            # OSError when trying to access device dir resolved by hitting Eject
            # in Nemo sidebar and re-selecting (mounting) device there.
            os_open("/")
            input("\nCan't access iDevice contents. Eject and re-mount in file manager.\n")
            self.find_root()
            return

        if count == 1 and iDevice_contents:
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
                print("\nSuccessfully accessed %s DCIM mount point." % dir_type)
            self.APPLE_folders.sort()

        elif count == 1:
            # iDevice handle exists, but DCIM folder not present.
            # Unlocking doesn't always solve it.
            input("Error: Found %s mount point, but DCIM folder not present.\n"
                    "Re-mount iDevice and press Enter to try again." % dir_type)
            print("\n")
            self.find_root()
            return
        elif count > 1:
            raise iDeviceLocError("Error: Multiple '%s' handles in %s"
                                              % (dir_type, IDEVICE_MOUNT_POINT))
            # Have not seen this happen. In fact, with two iDevices plugged
            # in, only the first one shows up as a gvfs directory.
        else:
            input("Error: Can't find iDevice in %s\nUnlock device then press "
                                    "Enter to try again." % IDEVICE_MOUNT_POINT)
            print("\n")
            self.find_root()
            return

    def get_root(self):
        return self.DCIM_path

    def list_APPLE_folders(self):
        return self.APPLE_folders

    def get_APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.APPLE_folders:
            return os.path.join(self.get_root(), APPLE_folder_name + '/')
        else:
            raise DirectoryNameError("Tried to access iDevice DCIM folder %s, "
                                     "but it does not exist in\n%s\n"
                                     % (APPLE_folder_name, self.get_root()))

    def get_APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by get_APPLE_folder_path() method
        APPLE_contents = os.listdir(self.get_APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def reconnect(self):
        """Re-establish connection after an OSError. iOS has bug that can
        terminate PC connection. Requires iDevice restart to fix.
        """
        os_error_response = input("\nEncountered device I/O error during "
                            "offload. Device may need to be restarted to fix.\n"
                            "Press Enter to attempt to continue offload.\n"
                            "Or press 'q' to quit.\n> ")
        if os_error_response.lower() == 'q':
            return False
        else:
            # Re-find gvfs root ("gphoto" handle likely changed)
            self.find_root()
            return True

    def __str__(self):
        return self.get_root()

    def __repr__(self):
        return ("iDevice DCIM directory object with path:\n\t%s" % self.get_root())


##########################################

# Program creates new folder with today’s date in raw offload directory.
# Copies all photos that did not exist last time device was offloaded.

class RawOffloadGroup(object):
    """Represents Raw_Offload root struct.
    """
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

        self.generate_offload_set()

    def get_BU_root(self):
        return self.bu_root_path

    def get_RO_root(self):
        return self.RO_root_path

    def generate_offload_set(self):
        # Create list that contains all items in raw-offload root.
        RO_root_contents = os.listdir(self.RO_root_path)

        self.offload_dir_items = RO_root_contents.copy()
        for item in RO_root_contents:
            if len(item) == 4:
                # Treat as year. Include items from inside the year
                year_contents = os.listdir(os.path.join(self.RO_root_path, item))
                # Check for duplicates
                assert set(self.offload_dir_items).isdisjoint(set(year_contents)), \
                                    "Found more than one RO folder %s" % item
                # Prepend year directory's name to each so they have valid paths.
                self.offload_dir_items += [os.path.join(item, file)
                                                      for file in year_contents]
                # Exclude year
                self.offload_dir_items.remove(item)

        self.offload_dir_items.sort()
        self.offload_obj_set = set()
        self.filter_offload_set()

    def get_offload_obj_set(self):
        # List of names
        return sorted(self.offload_obj_set.copy())

    def get_latest_offload_obj(self):
        # Returns RawOffload object
        if self.offload_obj_set:
            return self.get_offload_obj_set().pop()
            # No element deleted since get_offload_obj_set() returns a copy
        else:
            return None

    def filter_offload_set(self):
        # Populates offload object set
        # If offload_dir_items is empty list, calling this method should do nothing.
        for offload_item in self.offload_dir_items:
            # offload_item may include year-folder + / at beginning
            item_path = os.path.join(self.get_RO_root(), offload_item)

            if os.path.isfile(item_path):
                pass # exclude
            elif "ignore" in offload_item.lower():
                pass # exclude
            else:
                # Validate proper folder name convention
                try:
                    OffloadObj = RawOffload(offload_item, self)
                    OffloadObj.get_timestamp_struct()
                except DirectoryNameError:
                    pass # exclude
                else:
                    if not os.listdir(item_path):
                        delete_empty_ro = input("Folder %s in raw_offload "
                                    "directory is empty, possibly from previous "
                                    "aborted offload.\nPress 'd' to delete "
                                    "folder and continue or any other key to "
                                    "skip.\n> " % offload_item)
                        if delete_empty_ro.lower() == 'd':
                            os.rmdir(item_path)
                        # Need to ignore it either way.
                        pass # exclude
                    else:
                        self.offload_obj_set.add(OffloadObj)

    def create_new_offload(self):
        NewOffload = NewRawOffload(self)
        self.merge_todays_offloads()
        return NewOffload

    def merge_todays_offloads(self):
        today = time.strftime("%Y-%m-%d")
        todays_offloads = []

        # Have to refresh offload list. Doesn't yet contain new offload folder
        self.generate_offload_set()

        for offload_obj in self.get_offload_obj_set():
            if today in offload_obj.get_dir_date_str():
                todays_offloads.append(offload_obj)
        todays_offloads.sort()

        if len(todays_offloads) > 1:
            print("Multiple Raw_Offload folders with today's date:")
            for offload in todays_offloads:
                print("\t%s" % offload.get_dir_name())

            while True:
                merge_response = input("Merge folders? (Y/N)\n> ")
                if merge_response.lower() == 'y':
                    self.raw_offload_merge(todays_offloads)
                    break
                elif merge_response.lower() == 'n':
                    break
                else:
                    continue

    def raw_offload_merge(self, offload_objects):
        # Merges folders together into latest one
        offload_objects.sort()
        DestFolder = offload_objects[-1]
        old_offloads = offload_objects[:-1]

        for SrcFolder in old_offloads:
            for APPLE_folder in SrcFolder.list_APPLE_folders():
                # If the dir doesn't exist in the destination dir yet, create it.
                if not APPLE_folder in DestFolder.list_APPLE_folders():
                    dest_APPLE_path = os.path.join(DestFolder.get_full_path(),
                                                                   APPLE_folder)
                    os.mkdir(dest_APPLE_path)

                for image in SrcFolder.get_APPLE_contents(APPLE_folder):
                    src_img_path = os.path.join(
                           SrcFolder.get_APPLE_folder_path(APPLE_folder), image)
                    shutil.move(src_img_path,
                                    DestFolder.get_APPLE_folder_path(APPLE_folder))
                # Delete each APPLE directory after copying everything out of it
                os.rmdir(SrcFolder.get_APPLE_folder_path(APPLE_folder))
            # Delete each RO directory after copying everything out of it
            os.rmdir(SrcFolder.get_full_path())

    def __str__(self):
        return self.get_RO_root()

    def __repr__(self):
        return "RawOffloadGroup object with path:\n\t%s" % self.get_RO_root()


class RawOffload(object):
    """Represents a datestamped folder under the Raw_Offload root containing
    APPLE folders."""
    def __init__(self, offload_name, Group):
        self.ParentGroup = Group
        self.full_path = os.path.join(self.ParentGroup.get_RO_root(),
                                                            offload_name + '/')
        # May have year directory and slash preceding datestamp, so strip that off.
        self.offload_dir_name = os.path.basename(offload_name)
        # Validate proper folder name convention
        try:
            self.get_timestamp_struct()
        except ValueError:
            raise DirectoryNameError("Raw_Offload directory name '%s' not in "
                                            "expected format." % offload_name)

    def get_parent(self):
        return self.ParentGroup

    def get_full_path(self):
        # Includes year directory it may be inside.
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

    def get_APPLE_folder_path(self, APPLE_folder_name):
        if APPLE_folder_name in self.list_APPLE_folders():
            return os.path.join(self.full_path, APPLE_folder_name + '/')
        else:
            raise DirectoryNameError("Tried to access %s, but it does not exist"
                    " in %s." % (APPLE_folder_name, self.list_APPLE_folders()))

    def create_APPLE_folder(self, APPLE_folder_name):
        os.mkdir(os.path.join(self.full_path, APPLE_folder_name))

    def get_APPLE_contents(self, APPLE_folder_name):
        # Exception handling done by get_APPLE_folder_path() method
        APPLE_contents = os.listdir(self.get_APPLE_folder_path(APPLE_folder_name))
        APPLE_contents.sort()
        return APPLE_contents

    def get_dir_name(self):
        # May have suffix after datestamp
        # Does not include year directory - just basename
        return self.offload_dir_name

    def get_dir_date_str(self):
        return self.offload_dir_name[:len(DATETIME_FORMAT)+2]
        # If dir name is shorter than DATETIME_FORMAT, this will just return dir name;
        # no exception thrown
        # Need extra 2 chars since format string has "%Y" in place of 4-digit yr.

    def get_timestamp_struct(self):
        return time.strptime(self.get_dir_date_str(), DATETIME_FORMAT)
        # This will fail w/ ValueError if strptime fails because of bad format
        # or dir name too short.

    def __str__(self):
        return self.full_path

    def __repr__(self):
        return "RawOffload object with path:\n\t%s" % self.full_path

    def __lt__(self, other):
        return self.get_dir_date_str() < other.get_dir_date_str()


class NewRawOffload(RawOffload):
    """Represents new RawOffload instance (timestamped folder).
    Includes functionality to perform the offload from an iDeviceDCIM obj."""

    def __init__(self, Group):
        self.ParentGroup = Group
        self.offload_dir_name = time.strftime(DATETIME_FORMAT)
        self.full_path = os.path.join(self.ParentGroup.get_RO_root(),
                                                    self.offload_dir_name + '/')

        self.src_iDevice_DCIM = iDeviceDCIM()
        self.MTree = MirrorTree(self.ParentGroup, self.src_iDevice_DCIM)

        self.create_target_folder()
        self.run_offload()

        os_open(self.full_path)
        os_open(NAS_TRANSFER)
        input("\nManually transfer any images with captions into latest "
            "Raw_Offload directory (using NAS transfer)\n\tsince captions "
            "aren't included in EXIF data when offloaded over USB.\n"
            "Press Enter when finished.")

    def create_target_folder(self):
        # Create new directory w/ today's date/time stamp in Raw_Offload.

        if os.path.exists(self.full_path):
            # Make sure folder w/ this name (current date/time stamp) doesn't already exist.
            raise RawOffloadError("Tried to create directory at\n%s\nbut that "
                                  "directory already exists. No changes made."
                                                    % self.full_path)
        else:
            os.mkdir(self.full_path)

    def run_offload(self):
        APPLE_folders = self.src_iDevice_DCIM.list_APPLE_folders()
        # Make set of items for each dir in iDevice DCIM.
        # Compare to set of items in corresponding mirror_tree YYYYMM dir.
        for APPLE_folder in tqdm(APPLE_folders, position=0, desc=" DCIM folders"):
            src_APPLE_path = self.src_iDevice_DCIM.get_APPLE_folder_path(
                                                                APPLE_folder)
            dir_month = APPLE_folder[:6] # ignore chars after YYYYMM
            offload_mon_path = os.path.join(self.full_path, dir_month) + "/"


            imgs = set(self.src_iDevice_DCIM.get_APPLE_contents(APPLE_folder))
            if not os.path.exists(self.MTree.get_mon_path(dir_month)):
                transfer_type = "New"
                # No comparison needed. Copy all imgs from device for this month.
                # Create a destination folder in the new Raw Offload directory
                # with the same APPLE name.
                self.MTree.create_month(dir_month)
                new_imgs = imgs.copy()
            else:
                transfer_type = "Overlap"
                mirror_imgs = set(self.MTree.get_month_contents(dir_month))
                new_imgs = imgs - mirror_imgs

            if new_imgs:
                if not os.path.exists(offload_mon_path):
                    # May already exist since multiple YYYYMMxx folders often
                    # exist on iDevice
                    self.create_APPLE_folder(dir_month)

                print("%s folder: %s" % (transfer_type, APPLE_folder))
                print("%s-transfer progress:" % transfer_type)
            else:
                continue # To prevent loop below from printing empty tqdm bar
            for img_name in tqdm(sorted(new_imgs), position=1, desc=" Images",
                                                   leave=False, colour="green"):
                src_img_path = os.path.join(src_APPLE_path, img_name)
                while True:
                    try:
                        shutil.copy2(src_img_path, offload_mon_path)
                    except OSError:
                        # iOS has bug that can terminate PC connection.
                        # Requires iDevice restart to fix.
                        reconn_success = self.src_iDevice_DCIM.reconnect()
                        if not reconn_success:
                            return
                        # Update local variable that has gvfs root path embedded
                        src_APPLE_path = self.src_iDevice_DCIM.get_APPLE_folder_path(
                                                                   APPLE_folder)
                        continue # retry
                    else:
                        # Runs only if copy operation successful
                        # Create empty file w/ same name in mirror tree
                        self.MTree.create_mirror_file(dir_month, img_name)
                        break

    def __repr__(self):
        return "NewRawOffload object with path:\n\t%s" % self.full_path


class MirrorTree(object):
    """Represents a persistent "mirror" directory tree to document the iDevice's
    contents at the previous offload for future comparison.
    """

    def __init__(self, Group, iDevice_DCIM):
        self.ParentGroup = Group
        self.iDevice_DCIM = iDevice_DCIM
        self.full_path = os.path.join(self.ParentGroup.get_BU_root(), "DCIM_mirror_tree")

        self.log_dir_path = os.path.join(self.ParentGroup.get_BU_root(), "mtree_logs")
        if not os.path.exists(self.log_dir_path):
            os.mkdir(self.log_dir_path)

        # Look for presence of mirror tree (not yet created for first offload
        # w/ new DCIM structure)
        if not os.path.exists(self.get_path()):
            self.build_tree()

        # Save current state for debugging
        self.log_tree()

    def get_path(self):
        return self.full_path

    def get_mon_path(self, YYYYMM):
        # No validation that dir exists
        return os.path.join(self.full_path, YYYYMM)

    def log_tree(self):
        now = time.strftime(DATETIME_FORMAT)
        log_path = os.path.join(self.log_dir_path, "%s_mtree" % now)
        with open(log_path, "w") as mlog:
            subprocess.run(["tree", "%s" % self.full_path],
                                        stdout=mlog, stderr=subprocess.DEVNULL)

    def build_tree(self):
        """Used when iDevice gets offloaded for first time since DCIM structure
        changed (iOS 15.2 ~2021-12).
        """
        os.mkdir(self.full_path)

        # Convert last offload date string to iDevice YYYYMM format.
        LastOffload = self.ParentGroup.get_latest_offload_obj()
        last_offload_mon = time.strftime("%Y%m", time.strptime(
                               LastOffload.get_dir_date_str(), DATETIME_FORMAT))
        # # Truncate list to only look at most recent
        # APPLE_folders = [x for x in APPLE_folders if x[:6] >= last_offload_mon]
        # prev_mon = datetime.strftime(datetime.strptime(last_offload_mon, "%Y%m").date()
        #                                   - relativedelta(months=1), "%Y%m")
        # https://stackoverflow.com/questions/13031559/how-to-change-a-struct-time-object#13031653
        # https://www.programcreek.com/python/example/124421/dateutil.relativedelta

        # If no offload has been done since DCIM change, offload will only look
        # backward one month.
        # Build whole tree before most recent offload month
        APPLE_folders = self.iDevice_DCIM.list_APPLE_folders()
        old_APPLE_folders = [x for x in APPLE_folders if x[:6] < last_offload_mon]
        for APPLE_folder in old_APPLE_folders:
            dir_month = APPLE_folder[:6] # ignore chars after YYYYMM
            if not self.month_exists(dir_month):
                # Might exist already because some months have multiple YYYYMM folders.
                self.create_month(dir_month)
            for img in self.iDevice_DCIM.get_APPLE_contents(APPLE_folder):
                # Pre-structure change months sometimes have dups
                self.create_mirror_file(dir_month, img, allow_dup=True)
        # Create mirror of last offload (not from iDevice) in mirror tree
        self.create_month(last_offload_mon)
        for img in LastOffload.get_APPLE_contents(last_offload_mon):
            # Pre-structure change months sometimes have dups
            self.create_mirror_file(last_offload_mon, img, allow_dup=True)

    def get_month_contents(self, YYYYMM):
        return os.listdir(self.get_mon_path(YYYYMM))

    def month_exists(self, YYYYMM):
        return os.path.exists(self.get_mon_path(YYYYMM))

    def create_month(self, YYYYMM):
        if not self.month_exists(YYYYMM):
            os.mkdir(self.get_mon_path(YYYYMM))

    def create_mirror_file(self, YYYYMM, filename, allow_dup=False):
        file_path = os.path.join(self.get_mon_path(YYYYMM), filename)

        if os.path.exists(file_path) and not allow_dup:
            raise RawOffloadError("Tried creating mirror file %s, but it "
                                    "already exists in %s" % (filename, YYYYMM))
        elif os.path.exists(file_path):
            return
        else:
            fd = open(file_path, "x")
            fd.close()


# iDevice DCIM dir location: /run/user/1000/gvfs/*/DCIM/
# path changes depending on which USB port phone is plugged into.
