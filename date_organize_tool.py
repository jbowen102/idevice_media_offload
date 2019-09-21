from os.path import exists as path_exists
from os import listdir, mkdir, rmdir
from shutil import copy2 as sh_copy2
from shutil import copytree as sh_copytree
from tqdm import tqdm

from pic_offload_tool import iPhoneDCIM, RawOffloadGroup, RawOffload, NewRawOffload

from date_compare import get_img_date

class OrganizeFolderError(Exception):
    pass

# Phase 2: Organize files by date into dated directory.
# Create new folder if none exists

# prompt user to enter which photo is the break point between multiple months.
# make initial guess, open that photo, allow user to browse through photos and
# enter which one ends up being right based on manual check of iPhone metadata.
# always check for existing file before copying into date folders to avoid overwriting.


# DEFAULT_BU_ROOT = '/media/veracrypt4/Storage_Root/Tech/Back-up_Data/iPhone_Pictures/'
# IPHONE_DCIM_PREFIX = '/run/user/1000/gvfs/'

# Test directories (reference only):
DEFAULT_BU_ROOT = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/full_BU_root_dir/'
IPHONE_DCIM_PREFIX = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/full_gvfs_dir/'


# Should each year and month have their own object? And only instantiate the
# most recent ones? That will be an extra safeguard against copying into the
# wrong (older) directory.

class OrganizedGroup(object):

    def __init__(self, bu_root_path):
        self.bu_root_path = bu_root_path
        self.date_root_path = self.bu_root_path + "Organized/"
        # Double-check Organized folder is there.
        if not path_exists(self.date_root_path):
            raise OrganizeFolderError("Organized dir not found at %s! "
                        "Pics not organized. Terminating" % self.date_root_path)
        self.yr_objs = {}
        self.make_year(self.get_yr_list()[-1])

    def get_root_path(self):
        return self.date_root_path

    def get_yr_list(self):
        year_list = listdir(self.date_root_path)
        year_list.sort()
        return year_list

    def get_yr_objs(self):
        return self.yr_objs

    def get_latest_yr(self):
        latest_yr_name = self.get_yr_list()[-1]
        return self.yr_objs.get(latest_yr_name)

    def make_year(self, year):
        # chck that year doesn't already exist in list
        if year in self.get_yr_objs():
            raise OrganizeFolderError("Tried to make year object for %s, "
                                "but already exists in Organized directory."
                                    % (self.year_name))
        else:
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
            self.make_year(yr_str, self)
            NewYr = self.yr_objs[yr_str]
            NewYr.insert_img(img_orig_path, img_time)
        else:
            raise OrganizeFolderError("Attempt to pull image into folder %s, "
                                    "but that is older than one month, so "
                                    "timestamp is likely wrong." % yr_str)

    def __repr__(self):
        return "OrganizedGroup object with path:\n\t" + self.date_root_path


class YearDir(object):
    def __init__(self, year_name, OrgGroup):
        self.year_name = year_name
        self.year_path = OrgGroup.get_root_path() + self.year_name + '/'

        if not self.year_name in OrgGroup.get_yr_list():
            mkdir(self.year_path)
        # Instantiate latest mo and put in dict of months
        self.mo_objs = {}
        self.make_yrmonth(self.get_mo_list()[-1])

    def get_yr_path(self):
        return self.year_path

    def get_mo_list(self):
        mo_list = listdir(self.year_path)
        mo_list.sort()
        return mo_list

    def get_mo_objs(self):
        return self.mo_objs

    def get_latest_mo(self):
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
            self.mo_objs[yrmon].insert_img(img_orig_path)
        elif (not self.get_latest_mo()) or (yrmon > str(self.get_latest_mo())):
            # If there are no months in year directory, or if the image is from
            # a later month than the existing folders, make new month object.
            self.make_yrmonth(yrmon)
            # Pass image path to new month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path)
        else:
            # If the image is from an earlier month, then something's wrong.
            raise OrganizeFolderError("Attempt to pull image into folder %s, "
                        "but that folder is older than one month." % (yrmon))

    def __str__(self):
        return self.year_name

    def __repr__(self):
        return "YearDir object with path:\n\t" + self.date_root_path


class MoDir(object):
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

    def insert_img(self, img_orig_path):
        # make sure image not already here
        img_name = img_orig_path.split('/')[-1]
        if img_name in self.get_img_list():
            raise OrganizeFolderError("Attempt to pull image into folder %s, "
                                "but an image of that name already exists here."
                                                    % self.dir_name)
        else:
            sh_copy2(img_orig_path, self.yrmonth_path)

    def __str__(self):
        return self.dir_name

    def __repr__(self):
        return "MoDir object with path:\n\t" + self.yrmonth_path


class PicOrganize(object):
    def __init__(self, ROG):
        self.ROG = ROG
        self.OrgGroup = OrganizedGroup(ROG.get_BU_root())
        self.run_org()

    def run_org(self):
        LastRawOffload = self.ROG.get_last_offload()
        src_APPLE_folders = LastRawOffload.list_APPLE_folders()

        for n, folder in enumerate(src_APPLE_folders):
            print("Organizing %s -> %s (%s of %s)" %
            (LastRawOffload.get_offload_dir(), folder,
                                str(n+1), len(src_APPLE_folders)))

            for img in tqdm(LastRawOffload.APPLE_contents(folder)):
                full_img_path = LastRawOffload.APPLE_folder_path(folder) + img
                self.OrgGroup.insert_img(full_img_path)

# TEST
ROG = RawOffloadGroup()
PicOrganize(ROG)


# reference
# img_mod_time = strftime('%Y-%m-%d T %H:%M:%S', localtime(getmtime(src_img_path)))

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
