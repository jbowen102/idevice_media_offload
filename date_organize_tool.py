import os
import time
from tqdm import tqdm

import date_compare
import pic_categorize_tool as cat_tool
from pic_offload_tool import RawOffloadGroup



class OrganizeFolderError(Exception):
    pass


# Phase 2: Organize files by date into dated directory structure.
# Creates new dated folders where needed.
# Prepends timestamps to img names.

# Instantiate an OrganizedGroup instance with bu_root_path then call its
# run_org() method.

class OrganizedGroup(object):
    """Represents date-organized directory structure. Contains YrDir objects
    which in turn contain MoDir objects."""
    def __init__(self, bu_root_path, buffer_root):
        self.bu_root_path = bu_root_path
        self.date_root_path = self.bu_root_path + "Organized/"
        self.buffer_root_path = buffer_root
        # Double-check Organized folder is there.
        if not os.path.exists(self.date_root_path):
            raise OrganizeFolderError("Organized dir not found at %s! "
                        "Pics not organized. Terminating" % self.date_root_path)
        # Initialize object dictionary.
        self.yr_objs = {}

        # Instantiate year objects.
        yr_list = self.get_yr_list()
        for yr in yr_list:
            self.make_year(yr)

    def get_root_path(self):
        return self.date_root_path

    def get_buffer_root_path(self):
        return self.buffer_root_path

    def get_yr_list(self):
        # Refresh date_root_path every time in case dir changes.
        year_list = os.listdir(self.get_root_path())
        year_list.sort()
        return year_list

    def get_yr_objs(self):
        return self.yr_objs

    def get_latest_yrs(self):
        """Returns most recent year or two years if more than one present."""
        if len(self.get_yr_list()) > 1:
            latest_yr_names = self.get_yr_list()[-2:]
            return [str(self.yr_objs.get(latest_yr_names[0])),
                    str(self.yr_objs.get(latest_yr_names[1]))]
        else:
            latest_yr_name = self.get_yr_list()[-1]
            return [str(self.yr_objs.get(latest_yr_name))]

    def make_year(self, year):
        # check that year doesn't already exist in list
        if year in self.get_yr_objs():
            raise OrganizeFolderError("Tried to make year object for %s, "
                                "but already exists in Organized directory."
                                    % (self.year_name))
        else:
            # put into object dictionary
            self.yr_objs[year] = YearDir(year, self)

    def insert_img(self, img_orig_path, man_img_time=False):
        # Allow a manually-specified img_time to be passed and substituted.
        if man_img_time:
            img_time = man_img_time
        else:
            img_time = date_compare.get_img_date(img_orig_path,
                                                            skip_unknown=False)

        yr_str = str(img_time.tm_year)
        mo_str = str(img_time.tm_mon)
        # print(self.yr_objs)
        # print(str(self.get_latest_yr()))

        if yr_str in self.get_latest_yrs():
            # Proceed as normal for this year and last
            self.yr_objs[yr_str].insert_img(img_orig_path, img_time)
        elif yr_str > self.get_latest_yrs()[-1]:
            # If the image is from a later year than the existing folders,
            # make new year object.
            self.make_year(yr_str)
            NewYr = self.yr_objs[yr_str]
            NewYr.insert_img(img_orig_path, img_time, bypass_age_warn)
        elif man_img_time:
            # If a manual time asserted by user, ignore age-related warnings.
            self.yr_objs[yr_str].insert_img(img_orig_path, img_time,
                                                        bypass_age_warn=True)
        else:
            print("Attempted to pull image into %s-%s dir, "
                                "but a more recent year dir exists, so "
                                "timestamp may be wrong.\nFallback bypasses "
                                "warning and copies into older dir anyway."
                                                        % (yr_str, mo_str))

            man_img_time_struct = date_compare.spec_manual_time(img_orig_path)
            if man_img_time_struct:
                self.insert_img(img_orig_path, man_img_time_struct)
            elif yr_str in self.get_yr_list():
                # continue with operation anyway
                self.yr_objs[yr_str].insert_img(img_orig_path, img_time,
                                                        bypass_age_warn=True)
            else:
                # year directory doesn't exist yet, so have make it.
                self.make_year(yr_str)
                self.yr_objs[yr_str].insert_img(img_orig_path, img_time,
                                                        bypass_age_warn=True)

    def run_org(self):
        ROG = RawOffloadGroup(self.bu_root_path)

        LastRawOffload = ROG.get_latest_offload_obj()
        src_APPLE_folders = LastRawOffload.list_APPLE_folders()

        for n, folder in enumerate(src_APPLE_folders):
            print("Organizing from raw offload folder %s/%s (%s of %s)" %
            (LastRawOffload.get_dir_name(), folder,
                                str(n+1), len(src_APPLE_folders)))

            for img in tqdm(LastRawOffload.APPLE_contents(folder)):
                full_img_path = LastRawOffload.APPLE_folder_path(folder) + img
                self.insert_img(full_img_path)

        print("\nCategorization buffer populated.")

    def __repr__(self):
        return "OrganizedGroup object with path:\n\t" + self.get_root_path()


class YearDir(object):
    def __init__(self, year_name, OrgGroup):
        """Represents directory w/ year label that exists inside date-organized
        directory structure. Contains MoDir objects."""
        self.year_name = year_name
        self.year_path = OrgGroup.get_root_path() + self.year_name + '/'
        self.OrgGroup = OrgGroup

        if not self.year_name in OrgGroup.get_yr_list():
            os.mkdir(self.year_path)
        # Instantiate latest mo and put in dict of months
        self.mo_objs = {}
        # Run get_latest_mo in case it hasn't been run yet so latest_mo obj
        # is created. Discard output.
        self.get_latest_mo()

        # Create list to hold additional month directories to copy to without
        # prompt. This is sometimes necessary when image naming puts new photo
        # at beginning of queue and causes older photos to run "older month"
        # prompt repeatedly.
        self.recent_months = []

    def get_yr_path(self):
        return self.year_path

    def get_mo_list(self):
        mo_list = os.listdir(self.year_path)
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

    def insert_img(self, img_orig_path, img_time, bypass_age_warn=False):
        yr_str = str(img_time.tm_year)
        # Have to zero-pad single-digit months pulled from struct_time
        mon_str = str(img_time.tm_mon).zfill(2)
        yrmon = "%s-%s" % (yr_str, mon_str)

        if yrmon == str(self.get_latest_mo()):
            # Pass image path to correct month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        elif (not self.get_latest_mo()) or (yrmon > str(self.get_latest_mo())):
            # If there are no months in year directory, or if the image is from
            # a later month than the existing folders, make new month object.
            self.make_yrmonth(yrmon)
            # Pass image path to new month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        elif bypass_age_warn or yrmon in self.recent_months:
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        else:
            # If the image is from an earlier month:
            print("Attempted to pull image into %s dir, but a more recent "
            "month dir exists, so timestamp may be wrong.\nFallback bypasses "
                            "warning and copies into older dir anyway." % yrmon)

            man_img_time_struct = date_compare.spec_manual_time(img_orig_path)
            if man_img_time_struct:
                self.insert_img(img_orig_path, man_img_time_struct,
                                                        bypass_age_warn=True)
            else: # continue with operation anyway
                if yrmon not in self.get_mo_objs().keys():
                    # year-month directory doesn't exist yet, so have make it.
                    self.make_yrmonth(yrmon)
                self.mo_objs[yrmon].insert_img(img_orig_path, img_time)

                ignore = input("Ignore future warnings for this month? "
                                                                    "[Y/N]\n>")
                if ignore and ignore.lower() == "y":
                    self.recent_months.append(yrmon)

    def __str__(self):
        return self.year_name

    def __repr__(self):
        return "YearDir object with path:\n\t" + self.get_yr_path()


class MoDir(object):
    """Represents directory w/ month label that exists inside a YrDir object
    within the date-organized directory structure. Contains images."""
    def __init__(self, yrmonth_name, YrDir):
        self.dir_name = yrmonth_name
        self.yrmonth_path = YrDir.get_yr_path() + self.dir_name + '/'
        self.YrDir = YrDir

        if not self.dir_name in YrDir.get_mo_list():
            os.mkdir(self.yrmonth_path)

    def get_mo_path(self):
        return self.yrmonth_path

    def get_img_list(self):
        self.img_list = os.listdir(self.yrmonth_path)
        return self.img_list

    def insert_img(self, img_orig_path, img_time):
        # make sure image not already here
        img_name = os.path.basename(img_orig_path)   # no trailing slash
        stamped_name = time.strftime('%Y-%m-%d', img_time) + '_' + img_name

        # Copy into the dated directory
        cat_tool.copy_to_target(img_orig_path, self.yrmonth_path,
                                                        new_name=stamped_name)

        # Also copy the img into the cat buffer for next step in prog.
        if ".AAE" not in os.path.basename(img_orig_path):
            # Don't copy AAE files into cat buffer.
            # They will still exist in raw and organized folders, but it
            # doesn't serve any value to copy them elsewhere.
            # They can also have dates that don't match the corresponding
            # img/vid, causing confusion.
            cat_tool.copy_to_target(img_orig_path,
                                self.YrDir.OrgGroup.get_buffer_root_path(),
                                new_name=stamped_name)

    def __str__(self):
        return self.dir_name

    def __repr__(self):
        return "MoDir object with path:\n\t" + self.get_mo_path()


# TEST
# ORG = OrganizedGroup(DEFAULT_BU_ROOT)
# ORG.run_org()
