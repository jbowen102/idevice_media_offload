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

class OrganizedGroup(object):

    def __init__(self, ROG):
        self.bu_root_path = ROG.get_BU_root()
        self.date_root_path = self.bu_root_path + "Organized/"
        # Double-check Organized folder is there.
        if not path_exists(self.date_root_path):
            raise OrganizeFolderError("Organized dir not found at %s! "
                        "Pics not organized. Terminating" % self.date_root_path)

    def get_root_path(self):
        return self.date_root_path

    def get_latest_yr(self):
        yr_list = self.get_yr_list()
        LastYr = YearDir(yr_list[-1], self)

    # Instantiate latest year and provide access
    def get_yr_list(self):
        year_list = listdir(self.date_root_path)
        year_list.sort()
        return year_list

    def create_yr(self, year):
        if year in self.get_yr_list():


    def __repr__(self):
        return "OrganizedGroup object with path:\n\t" + self.date_root_path

class YearDir(object):
    def __init__(self, year_name, OrgGroup):
        if not year_name in OrgGroup.get_yr_list():
            raise OrganizeFolderError("Year '%s' not found in dir:\n\t%s"
                                % (year_name, OrgGroup.get_root_path()))
        else:
            self.year_name = year_name
            self.year_path = OrgGroup.get_root_path() + year_name + '/'
            # Instantiate latest mo and put in dict of months
            self.mo_objs = {self.get_latest_mo(): make_month(self.get_latest_mo())}

    def get_yr_path(self):
        return self.year_path

    def get_mo_list(self, year):
        mo_list = listdir(self.year_path)
        mo_list.sort()
        return mo_list

    def get_mo_objs(self):
        return self.mo_objs

    def get_latest_mo(self):
        latest_mo_name = self.get_mo_list()[-1]
        return self.mo_ojbs.get(latest_mo_name)

    def make_month(self, month):
        # chck that month doesn't already exist in list
        if month in self.get_mo_objs():
            raise OrganizeFolderError("Tried to make month object for %s-%s, "
                                "but already exists in not found in dir:\n\t%s"
                                    % (self.year_name, month, self.year_path))
        else:
            # does this need to be stored somehow in the YearDir object?
            # put in dict?
            return MoDir()

    def __repr__(self):
        return "YearDir object with path:\n\t" + self.date_root_path


class MoDir(object):
    def __init__(self, YrDir):
        pass

    def get_mo_path(self, year, month):
        if (year + '-' + month) in self.get_mo_list(year):
            mo_path = self.get_yr_path(year) + year + '-' + month
            return mo_path
        else:
            raise OrganizeFolderError("Month '%s' does not exist in %s"
                            % (month, self.get_yr_path(year)))


# TEST
rog = RawOffloadGroup()
por = OrganizedGroup(rog)


# reference
# img_mod_time = strftime('%Y-%m-%d T %H:%M:%S', localtime(getmtime(src_img_path)))

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
