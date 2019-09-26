from os import listdir, mkdir, rmdir
from os.path import exists as path_exists
from shutil import copy2 as sh_copy2
from shutil import copytree as sh_copytree
from time import strftime
from tqdm import tqdm

from pic_offload_tool import RawOffloadGroup
from date_compare import get_img_date, list_all_img_dates
from dir_names import DEFAULT_BU_ROOT, BUFFER_ROOT


class OrganizeFolderError(Exception):
    pass


# Phase 2: Organize files by date into dated directory structure.
# Creates new dated folders where needed.
# Prepends timestamps to img names.

# Instantiate an OrganizedGroup instance with bu_root_path then call its run_org() method.

class OrganizedGroup(object):
    """Represents date-organized directory structure. Contains YrDir objects
    which in turn contain MoDir objects."""
    def __init__(self, bu_root_path):
        self.bu_root_path = bu_root_path
        self.date_root_path = self.bu_root_path + "Organized/"
        # Double-check Organized folder is there.
        if not path_exists(self.date_root_path):
            raise OrganizeFolderError("Organized dir not found at %s! "
                        "Pics not organized. Terminating" % self.date_root_path)
        # Initialize object dictionary. Instantiate most recent year object.
        self.yr_objs = {}
        self.make_year(self.get_yr_list()[-1])

    def get_root_path(self):
        return self.date_root_path

    def get_yr_list(self):
        # Refresh date_root_path every time in case dir changes.
        year_list = listdir(self.date_root_path)
        year_list.sort()
        return year_list

    def get_yr_objs(self):
        return self.yr_objs

    def get_latest_yr(self):
        latest_yr_name = self.get_yr_list()[-1]
        return self.yr_objs.get(latest_yr_name)

    def make_year(self, year):
        # check that year doesn't already exist in list
        if year in self.get_yr_objs():
            raise OrganizeFolderError("Tried to make year object for %s, "
                                "but already exists in Organized directory."
                                    % (self.year_name))
        else:
            # put into object dictionary
            self.yr_objs[year] = YearDir(year, self)

    def insert_img(self, img_orig_path):
        img_time = get_img_date(img_orig_path)
        # Have to zero-pad single-digit months pulled from struct_time
        yr_str = str(img_time.tm_year)
        if yr_str in self.yr_objs:
            self.yr_objs[yr_str].insert_img(img_orig_path, img_time)
        elif yr_str > str(self.get_latest_yr()):
            # If the image is from a later year than the existing folders,
            # make new year object.
            self.make_year(yr_str)
            NewYr = self.yr_objs[yr_str]
            NewYr.insert_img(img_orig_path, img_time)
        else:
            raise OrganizeFolderError("Attempt to pull image %s into folder %s, "
                                    "but that is older than one month, so "
                                    "timestamp is likely wrong." %
                                    (img_orig_path.split('/')[-1], yr_str))

    def run_org(self):
        ROG = RawOffloadGroup()

        if listdir(BUFFER_ROOT):
            # If there are still images from last time in the buffer, stop.
            raise OrganizeFolderError("Categorizing Buffer is non-empty.")

        LastRawOffload = ROG.get_last_offload()
        src_APPLE_folders = LastRawOffload.list_APPLE_folders()

        for n, folder in enumerate(src_APPLE_folders):
            print("Organizing from raw offload folder %s/%s (%s of %s)" %
            (LastRawOffload.get_offload_dir(), folder,
                                str(n+1), len(src_APPLE_folders)))

            for img in tqdm(LastRawOffload.APPLE_contents(folder)):
                full_img_path = LastRawOffload.APPLE_folder_path(folder) + img
                self.insert_img(full_img_path)

    def __repr__(self):
        return "OrganizedGroup object with path:\n\t" + self.date_root_path


class YearDir(object):
    def __init__(self, year_name, OrgGroup):
        """Represents directory w/ year label that exists inside date-organized
        directory structure. Contains MoDir objects."""
        self.year_name = year_name
        self.year_path = OrgGroup.get_root_path() + self.year_name + '/'

        if not self.year_name in OrgGroup.get_yr_list():
            mkdir(self.year_path)
        # Instantiate latest mo and put in dict of months
        self.mo_objs = {}
        # Run get_latest_mo in case it hasn't been run yet so latest_mo obj
        # is created. Discard output.
        self.get_latest_mo()

    def get_yr_path(self):
        return self.year_path

    def get_mo_list(self):
        mo_list = listdir(self.year_path)
        mo_list.sort()
        return mo_list

    def get_mo_objs(self):
        return self.mo_objs

    def get_latest_mo(self):
        if not self.get_mo_list():
            # If there are no months yet, return None.
            return None
        elif not self.mo_objs:
            # If there are months in the list but not in the dict, make latest
            # month now and return it.
            latest_mo_name = self.get_mo_list()[-1]
            self.make_yrmonth(latest_mo_name)
            return self.mo_objs.get(latest_mo_name)
        else:
            # If there are months in the directory, and the object dictionary
            # is non-empty, then the latest month should be in there.
            latest_mo_name = self.get_mo_list()[-1]
            return self.mo_objs.get(latest_mo_name)

    def make_yrmonth(self, yrmonth):
        # chck that month doesn't already exist in list
        if yrmonth in self.get_mo_objs():
            raise OrganizeFolderError("Tried to make month object for %s, "
                                        "but already exists in YearDir."
                                        % (yrmonth))
        else:
            self.mo_objs[yrmonth] = MoDir(yrmonth, self)

    def insert_img(self, img_orig_path, img_time):
        yr_str = str(img_time.tm_year)
        # Have to zero-pad single-digit months pulled from struct_time
        mon_str = str(img_time.tm_mon).zfill(2)
        yrmon = "%s-%s" % (yr_str, mon_str)

        if yrmon in self.get_mo_objs():
            # Pass image path to correct month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        elif (not self.get_latest_mo()) or (yrmon > str(self.get_latest_mo())):
            # If there are no months in year directory, or if the image is from
            # a later month than the existing folders, make new month object.
            self.make_yrmonth(yrmon)
            # Pass image path to new month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        else:
            # If the image is from an earlier month, then something's wrong.
            print("Attempt to pull image %s into folder %s, "
                        "but that folder is older than one month."
                        % (img_orig_path.split('/')[-1], yrmon))
            list_all_img_dates(img_orig_path)

    def __str__(self):
        return self.year_name

    def __repr__(self):
        return "YearDir object with path:\n\t" + self.date_root_path


class MoDir(object):
    """Represents directory w/ month label that exists inside a YrDir object
    within the date-organized directory structure. Contains images."""
    def __init__(self, yrmonth_name, YrDir):
        self.dir_name = yrmonth_name
        self.yrmonth_path = YrDir.get_yr_path() + self.dir_name + '/'

        if not self.dir_name in YrDir.get_mo_list():
            mkdir(self.yrmonth_path)

    def get_mo_path(self):
        return self.yrmonth_path

    def get_img_list(self):
        self.img_list = listdir(self.yrmonth_path)
        return self.img_list

    def insert_img(self, img_orig_path, img_time):
        # make sure image not already here
        img_name = img_orig_path.split('/')[-1]
        if img_name in self.get_img_list():
            print("Attempt to pull image %s into folder %s, "
                                "but an image of that name already exists here."
                                                    % (img_name, self.dir_name))
        else:
            stamped_name = strftime('%Y-%m-%d', img_time) + '_' + img_name
            img_new_path = self.yrmonth_path + stamped_name
            # Copy into the dated directory and also into the buffer for
            # later categorization.
            sh_copy2(img_orig_path, img_new_path)
            sh_copy2(img_orig_path, BUFFER_ROOT + stamped_name)

    def __str__(self):
        return self.dir_name

    def __repr__(self):
        return "MoDir object with path:\n\t" + self.yrmonth_path


# TEST
# ORG = OrganizedGroup(DEFAULT_BU_ROOT)
# ORG.run_org()
