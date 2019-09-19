from os.path import exists as path_exists
from os import listdir, mkdir, rmdir

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

# Test directories:
DEFAULT_BU_ROOT = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/full_BU_root_dir/'
IPHONE_DCIM_PREFIX = '/media/veracrypt11/BU_Data/iPhone_Pictures/TEST/full_gvfs_dir/'


# Should each year and month have their own object? And only instantiate the
# most recent ones? That will be an extra safeguard against copying into the
# wrong (older) directory.

class PicOrganize(object):

    def __init__(self, ROG):
        self.bu_root_path = ROG.get_BU_root()
        self.date_root_path = self.bu_root_path + "Organized/"
        # Double-check Organized folder is there.
        if not path_exists(self.date_root_path):
            raise OrganizeFolderError("Organized dir not found at %s! "
                        "Pics not organized. Terminating" % self.date_root_path)

    def get_yr_list(self):
        year_list = listdir(self.date_root_path)
        year_list.sort()
        return year_list

    def get_yr_path(self, year):
        if year in self.get_yr_list():
            yr_path = self.date_root_path + year + '/'
            return yr_path
        else:
            raise OrganizeFolderError("Year '%s' does not exist in %s"
                            % (year, self.date_root_path))

    def get_mo_list(self, year):
        yr_path = self.get_yr_path(year)
        mo_list = listdir(yr_path)
        mo_list.sort()
        return mo_list

    # change this to accept yr-date format and parse yr from mo?
    def get_mo_path(self, year, month):
        if (year + '-' + month) in self.get_mo_list(year):
            mo_path = self.get_yr_path(year) + year + '-' + month
            return mo_path
        else:
            raise OrganizeFolderError("Month '%s' does not exist in %s"
                            % (month, self.get_yr_path(year)))

    def __repr__(self):
        return "RawOffload object with path:\n\t" + self.date_root_path



# TEST
rog = RawOffloadGroup()
por = PicOrganize(rog)


# reference
# img_mod_time = strftime('%Y-%m-%d T %H:%M:%S', localtime(getmtime(src_img_path)))

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
