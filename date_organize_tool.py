import os
import time
from tqdm import tqdm

from mediadapt import format_convert

from idevice_media_offload import date_compare
from idevice_media_offload.pic_categorize_tool import copy_to_target
from idevice_media_offload.pic_offload_tool import RawOffloadGroup



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
        self.date_root_path = os.path.join(self.bu_root_path, "Organized/")
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
        elif self.get_yr_list():
            latest_yr_name = self.get_yr_list()[-1]
            return [str(self.yr_objs.get(latest_yr_name))]
        else:
            return []

    def make_year(self, year):
        # check that year doesn't already exist in list
        if year in self.get_yr_objs():
            raise OrganizeFolderError("Tried to make year object for %s, "
                                "but already exists in Organized directory."
                                    % (self.year_name))
        else:
            # put into object dictionary
            self.yr_objs[year] = YearDir(year, self)

    def search_img(self, target_img_num, remove=False, debug=False):
        """Searches entire org dir tree for a specific image number, returning
        the path of the last one encountered or None if none encountered.
        Will delete last one encountered if remove set to True.
        target_img_num is a string.
        """
        img_path_found = None # fallback if no img found

        for year, yr_obj in self.get_yr_objs().items():
            if debug: print("Searching year %s" % year)
            for month, mo_obj in yr_obj.get_mo_objs().items():
                if debug: print("\tSearching month %s" % month)
                for img_name in mo_obj.get_img_list():
                    # If number that follows the "IMG_" or "IMG_E" matches,
                    # store then return this datestamp.
                    # Extension not included in string match.
                    if os.path.splitext(img_name)[0][-4:] == target_img_num:
                        img_path_found = os.path.join(mo_obj.get_mo_path(),
                                                                    img_name)
                        if debug: print("\t\t*Found %s in %s/%s" % (img_name, year, month))
        # For-loop may encounter multiple matching images. At end of iteration,
        # last-encountered one (matching chronologically most recent) will be
        # stored in img_path_found.

        if img_path_found and remove:
            if debug: print("\nRemoving %s" % img_path_found)
            os.remove(img_path_found)

        return img_path_found # will default to None if none found


    def insert_img(self, img_orig_path, man_img_date=False):
        # Allow a manually-specified img_time to be passed and substituted.
        if man_img_date:
            img_time = man_img_date
            bypass_age_warn = True
            img_path = img_orig_path
        elif os.path.splitext(img_orig_path)[-1].upper() == ".AAE":
            # Don't copy AAE files into date-organized folders or cat buffer.
            # They will still exist in raw, but it doesn't add any value to copy
            # them elsewhere. They can also have dates that don't match the
            # corresponding img/vid, causing confusion.
            return

        elif os.path.splitext(img_orig_path)[-1].upper() == ".WEBP":
            # Don't think iOS will ever save WEBP w/ IMG_E prefix. Editing
            # WEBP yields IMG_Exxxx.JPG file.

            # Convert to JPG or GIF before moving on. Returns None if unsuccessful.
            converted_img_path = format_convert.convert_webp(img_orig_path)
            if converted_img_path:
                img_path = converted_img_path
            else:
                # If conversion failed, continue with WEBP file as-is.
                img_path = img_orig_path

            # Use WEBP file's mod time since that is the only relevant metadata
            # available. JPG version's mod time will be wrong since it was
            # just created.
            img_time = time.localtime(os.path.getmtime(img_orig_path))
            bypass_age_warn = False
            print("Using file mod time %s for %s."
                    % (time.strftime(date_compare.DATE_FORMAT, img_time),
                       os.path.basename(img_orig_path)))
        elif os.path.basename(img_orig_path)[:5] == "IMG_E":
            # Don't need to search or prompt for date if original pic is in
            # org group. Get its datestamp.
            img_num = os.path.splitext(os.path.basename(img_orig_path))[0][-4:]
            img_path_found = self.search_img(img_num)
            # search_img() ends up being called twice, but it runs fast.
            # Runs a second time in YearDir when original gets removed.
            # Needs to be run first here in case edited photo doesn't have
            # good EXIF datestamp. That way program only prompts once (og pic).
            img_path = img_orig_path
            if img_path_found:
                img_name = os.path.basename(img_path_found)
                img_time = time.strptime(img_name.split("_")[0], "%Y-%m-%d")
                bypass_age_warn = False
            else:
                # If image can't be found in org structure for whatever reason,
                # treat it like any other image.
                (img_time, bypass_age_warn) = date_compare.get_img_date_plus(
                                                   img_path, skip_unknown=False)
                man_img_date = bypass_age_warn
        else:
            img_path = img_orig_path
            (img_time, bypass_age_warn) = date_compare.get_img_date_plus(
                                                   img_path, skip_unknown=False)
            man_img_date = bypass_age_warn

        if not img_time:
            # If user said to skip file when asked to spec time.
            return

        yr_str = str(img_time.tm_year)
        # Have to zero-pad single-digit months pulled from struct_time
        mo_str = str(img_time.tm_mon).zfill(2)

        if not self.get_yr_list():
            # Used for empty Organized directory.
            self.make_year(yr_str)
            NewYr = self.yr_objs[yr_str]
            NewYr.insert_img(img_path, img_time, bypass_age_warn)
        elif yr_str in self.get_latest_yrs():
            # Proceed as normal for this year and last
            self.yr_objs[yr_str].insert_img(img_path, img_time, bypass_age_warn)
        elif yr_str > self.get_latest_yrs()[-1]:
            # If the image is from a later year than the existing folders,
            # make new year object.
            self.make_year(yr_str)
            NewYr = self.yr_objs[yr_str]
            NewYr.insert_img(img_path, img_time, bypass_age_warn)
        elif man_img_date:
            # A new manually-specified date might not be present in yr_objs dir.
            if yr_str not in self.get_yr_list():
                self.make_year(yr_str)
            self.yr_objs[yr_str].insert_img(img_path, img_time, bypass_age_warn)
        else:
            print("Attempted to pull image into %s-%s dir, "
                                "but a more recent year dir exists, so "
                                "timestamp may be wrong.\nFallback bypasses "
                                "warning and copies into older dir anyway."
                                                        % (yr_str, mo_str))

            man_date_output = date_compare.spec_manual_date(img_path)
            # will be a time_struct object if a date entered.
            if isinstance(man_date_output, time.struct_time):
                # If user entered a date:
                self.insert_img(img_path, man_date_output)
                # bypass_age_warn will be set True within function.
            elif man_date_output=="s":
                # Skip
                return
            elif yr_str in self.get_yr_list():
                # If user chose fallback but still in valid years, continue
                # with operation anyway
                self.yr_objs[yr_str].insert_img(img_path, img_time,
                                                        bypass_age_warn=True)
            else:
                # year directory doesn't exist yet, so have make it.
                self.make_year(yr_str)
                self.yr_objs[yr_str].insert_img(img_path, img_time,
                                                        bypass_age_warn=True)

    def run_org(self):
        ROG = RawOffloadGroup(self.bu_root_path)
        LastRawOffload = ROG.get_latest_offload_obj()
        src_APPLE_folders = LastRawOffload.list_APPLE_folders()

        for n, APPLE_dir in enumerate(src_APPLE_folders):
            print("Organizing from raw offload folder %s/%s (%s of %s)" %
                            (LastRawOffload.get_dir_name(), APPLE_dir, str(n+1),
                                                        len(src_APPLE_folders)))

            for img in tqdm(LastRawOffload.get_APPLE_contents(APPLE_dir)):
                full_img_path = os.path.join(
                                  LastRawOffload.get_APPLE_folder_path(APPLE_dir), img)
                self.insert_img(full_img_path)

        print("\nCategorization buffer populated.")

    def __repr__(self):
        return "OrganizedGroup object with path:\n\t%s" % self.get_root_path()


class YearDir(object):
    def __init__(self, year_name, OrgGroup):
        """Represents directory w/ year label that exists inside date-organized
        directory structure. Contains MoDir objects."""
        self.year_name = year_name
        self.year_path = os.path.join(OrgGroup.get_root_path(),
                                                        self.year_name + '/')
        self.OrgGroup = OrgGroup

        if not self.year_name in self.OrgGroup.get_yr_list():
            os.mkdir(self.year_path)
        # Initialize object dictionary.
        self.mo_objs = {}
        # Instantiate object for each month in directory, populating dict.
        mo_list = self.get_mo_list()
        for mo in mo_list:
            self.make_yrmonth(mo)

        # Create set to hold month directories (names) to copy to without
        # prompt. This is sometimes necessary when image naming puts new photo
        # at beginning of queue and causes older photos to run "older month"
        # prompt repeatedly.
        self.no_prompt_months = set()
        # Run get_latest_mo in case it hasn't been run yet so latest_mo obj
        # is created. Add to no_prompt_months set.
        self.og_latest_mo = self.get_latest_mo()
        if self.og_latest_mo:
            self.no_prompt_months.add(self.og_latest_mo.get_yrmon_name())

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
        # check that month doesn't already exist in list
        if yrmonth in self.mo_objs:
            raise OrganizeFolderError("Tried to make month object for %s, "
                                        "but already exists in YearDir."
                                        % (yrmonth))
        else:
            self.mo_objs[yrmonth] = MoDir(yrmonth, self)

    def insert_img(self, img_orig_path, img_time, bypass_age_warn=False):
        if os.path.basename(img_orig_path)[:5] == "IMG_E":
            # Look for any original/edited pairs in all org dirs.
            # "IMG_E" files appear later in sorted order than originals, so
            # the originals are transferred first.
            # Can't assume datestamp is the same. Could have edited later.
            # Extension not included in string match.
            # Edited WEBP files yield separate IMG_Exxxx.JPG.
            img_num = os.path.splitext(os.path.basename(img_orig_path))[0][-4:]
            # If image found, retrieve its name and delete it (remains in
            # raw_offload folder).
            img_ext = os.path.splitext(img_orig_path)[-1]
            if img_ext.upper() == ".HEIC":
                # Keeping IMG_Exxxx.HEIC originals since heif-convert fails
                # to convert IMG_E version for some reason.
                remove_og_img = False
            else:
                remove_og_img = True

            img_path_found = self.OrgGroup.search_img(img_num, remove=remove_og_img)
            # Remove option in search_img() removes from Org dir only.
            # Below conditional handles occurrence in CAT buffer.
            if img_path_found:
                img_name = os.path.basename(img_path_found)
                # Replace "IMG_E" img_time with original's datestamp.
                # This applies to IMG_Exxx.HEIC files too, though their EXIF
                # data seems to reflect correct original capture time.
                if remove_og_img:
                    # Keeping IMG_Exxxx.HEIC originals since heif-convert fails
                    # to convert IMG_E version for some reason.
                    print("Keeping edited file %s and removing original "
                          "%s.\n" % (os.path.basename(img_orig_path), img_name))

                    # Remove from cat buffer (already removed from date-org dir).
                    img_buffer_path = os.path.join(
                                 self.OrgGroup.get_buffer_root_path(), img_name)
                    if os.path.exists(img_buffer_path):
                        # Might not exist if the newly-edited pic had its
                        # original offloaded and categorized previously.
                        os.remove(img_buffer_path)

            # Continue to next conditional. Edited ("IMG_E") file is xfered.
            # If original version of IMG_E not found, treated as standard img.

        yr_str = str(img_time.tm_year)
        # Have to zero-pad single-digit months pulled from struct_time
        mon_str = str(img_time.tm_mon).zfill(2)
        yrmon = "%s-%s" % (yr_str, mon_str)

        if yrmon in self.no_prompt_months:
            # Pass image path to correct month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        elif (not self.og_latest_mo) or (yrmon > str(self.og_latest_mo)):
            # If there are no months in year directory initially, or if the
            # image is from a later month than the existing folders, make new
            # month object.
            self.make_yrmonth(yrmon)
            self.no_prompt_months.add(yrmon)
            # Pass image path to new month object for insertion.
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        elif bypass_age_warn:
            # This is the same as a condition above, but the intervening elif
            # should instead run if it evaluates true. A new manually-specified
            # date might not be present in mo_objs.
            if yrmon not in self.mo_objs.keys():
                # year-month directory doesn't exist yet, so have make it.
                self.make_yrmonth(yrmon)
            self.mo_objs[yrmon].insert_img(img_orig_path, img_time)
        else:
            # If the image is from an earlier month not in no_prompt_months set:
            print("Attempted to pull image into %s dir, but a more recent "
              "month dir exists, so timestamp may be wrong.\nFallback bypasses "
                            "warning and copies into older dir anyway." % yrmon)

            man_date_output = date_compare.spec_manual_date(img_orig_path)
            # will be a time_struct object if a date entered.
            if isinstance(man_date_output, time.struct_time):
                # If user entered a date:
                self.insert_img(img_orig_path, man_date_output,
                                                        bypass_age_warn=True)
            elif man_date_output=="s":
                # Skip
                return
            else: # continue with operation anyway
                if yrmon not in self.mo_objs.keys():
                    # year-month directory doesn't exist yet, so have make it.
                    self.make_yrmonth(yrmon)
                self.mo_objs[yrmon].insert_img(img_orig_path, img_time)

                ignore = input("Ignore future warnings for this month? "
                                                                    "[Y/N]\n> ")
                if ignore and ignore.lower() == "y":
                    self.no_prompt_months.add(yrmon)

    def __str__(self):
        return self.year_name

    def __repr__(self):
        return "YearDir object with path:\n\t%s" % self.get_yr_path()


class MoDir(object):
    """Represents directory w/ month label that exists inside a YrDir object
    within the date-organized directory structure. Contains images."""
    def __init__(self, yrmonth_name, YrDir):
        self.dir_name = yrmonth_name
        self.yrmonth_path = os.path.join(YrDir.get_yr_path(),
                                                            self.dir_name + '/')
        self.YrDir = YrDir

        if not self.dir_name in YrDir.get_mo_list():
            os.mkdir(self.yrmonth_path)

    def get_mo_path(self):
        return self.yrmonth_path

    def get_img_list(self):
        self.img_list = os.listdir(self.yrmonth_path)
        self.img_list.sort()
        return self.img_list

    def insert_img(self, img_orig_path, img_time, move_file=False,
                                                          comment_prompt=True):
        """Prepends timestamp and optionally appends caption (if present in
        metadata)."""

        datestamp_prefix = time.strftime("%Y-%m-%d", img_time) + "_"
        # Reserve 2 extra characters to account for potential collision-resolving
        # underscore + digit applied in copy_to_target()
        captioned_name = date_compare.append_img_comment(img_orig_path,
                                            extra_chars=len(datestamp_prefix)+2,
                                            comment_prompt=comment_prompt,
                                            rename_in_place=False)

        stamped_name = datestamp_prefix + captioned_name
        # Copy into the dated directory
        copy_to_target(img_orig_path, self.yrmonth_path, new_name=stamped_name)

        # Also copy the img into the cat buffer for next step in prog.
        # If file is a converted version of a WEBP file, move instead of copy
        # Converted version of HEIC (JPG) also gets moved (recursive call below).
        img_ext = os.path.splitext(img_orig_path)[-1]
        webp_version = os.path.splitext(img_orig_path)[0] + ".WEBP"
        if (img_ext.upper() != ".WEBP") and os.path.exists(webp_version):
            move_file = True

        # Copy or move to cat buffer
        copy_to_target(img_orig_path, self.YrDir.OrgGroup.get_buffer_root_path(),
                                       new_name=stamped_name, move_op=move_file)

        # For an HEIF file, convert then copy/move converted version to both destinations.
        if img_ext.upper() == ".HEIC":
            converted_img_path = format_convert.convert_heif(img_orig_path)
            if converted_img_path:
                # Recursive call will transfer jpg to both destinations.
                self.insert_img(converted_img_path, img_time, move_file=True,
                                                          comment_prompt=False)
            else:
                # Conversion failed (have seen it happen on IMG_Exxx.HEIC files)
                # No converted file to transfer. Original HEIF will still be transferred.
                pass

    def get_yrmon_name(self):
        return self.dir_name

    def __str__(self):
        return self.dir_name

    def __repr__(self):
        return "MoDir object with path:\n\t%s" % self.get_mo_path()


# TEST
# ORG = OrganizedGroup(DEFAULT_BU_ROOT)
# ORG.run_org()
