import PIL.Image
# https://stackoverflow.com/questions/11911480/python-pil-has-no-attribute-image
from PIL.ExifTags import TAGS
import os
import time
import exiftool

from pic_categorize_tool import copy_to_target, display_photo


# class ImgTypeError(Exception):
#     pass

class DirectoryNameError(Exception):
    pass

DATETIME_FORMAT = "%Y-%m-%dT%H%M%S"  # Global format
DATE_FORMAT = "%Y-%m-%d"  # Global format


def list_all_img_dates(path, skip_unknown=True, rename_with_datestamp=False):
    """Function that takes either a directory or single image path and prints
    all available timestamps for each JPG, HEIC, GIF, PNG, AAE, or MOV file for
    comparison.
    Optional argument allows the creation timestamp to be prepended to image(s)
    as they are processed.
    datestamp_all() function below now preferred."""

    if not os.path.exists(path):
        print("Not a valid path.")
        return None
    elif os.path.isdir(path):
        if path[-1] != '/':
            path += '/'
        image_list = os.listdir(path)
        image_list.sort()
    else:
        # If path is only a single image instead of a directory, separate out
        # the image name from the path to conform to path + img convention in
        # rest of code. Create a length-one list with that image name to
        # loop through.
        single_image = os.path.basename(path)
        # single-img path has no trailing slash
        path = os.path.dirname(path) + "/"
        image_list = [single_image]

    for img in image_list:
        img_ext = os.path.splitext(img)[-1].upper()
        file_mod_time = time.strftime(DATETIME_FORMAT,
                                time.localtime(os.path.getmtime(path + img)))

        if img_ext in [".JPG", ".JPEG"]:
            img_obj = PIL.Image.open(path + img)

            encoded_exif = img_obj._getexif()
            pil_metadata = {}
            if encoded_exif:
                for tag, value in encoded_exif.items():
                     decoded_key = PIL.ExifTags.TAGS.get(tag, tag)
                     if "DateTime" in str(decoded_key):
                         pil_metadata[decoded_key] = value
            else:
                pil_metadata = dict()

            with exiftool.ExifTool() as et:
                exiftool_metadata = et.get_metadata(path + img)

            # "*" indicates metadata most likely to be actual creation time.
            print((img + ":\n"
                    "        file_mod_time:\t\t%s\n"
                    "        PIL-getexif DateTimeOriginal:\t%s\n"
                    "        PIL-getexif DateTimeDigitized:\t%s\n"
                    "        PIL-getexif DateTime:\t%s\n"
                    "        Exiftool EXIF:ModifyDate:\t%s\n"
                    "        Exiftool EXIF:DateTimeOriginal*:\t%s\n"
                    "        Exiftool EXIF:CreateDate:\t%s\n"
                    "        Exiftool Composite:SubSecCreateDate:\t%s\n"
                    "        Exiftool Composite:SubSecDateTimeOriginal:\t%s\n"
                    % (file_mod_time, pil_metadata.get('DateTimeOriginal'),
                      pil_metadata.get('DateTimeDigitized'),
                      pil_metadata.get('DateTime'),
                      exiftool_metadata.get('EXIF:ModifyDate'),
                      exiftool_metadata.get('EXIF:DateTimeOriginal'),
                      exiftool_metadata.get('EXIF:CreateDate'),
                      exiftool_metadata.get('Composite:SubSecCreateDate'),
                      exiftool_metadata.get('Composite:SubSecDateTimeOriginal')
                      )).expandtabs(28))

        elif img_ext == ".HEIC":
            with exiftool.ExifTool() as et:
                exiftool_metadata = et.get_metadata(path + img)

            # "*" indicates metadata most likely to be actual creation time.
            print((img + ":\n"
                    "        file_mod_time:\t\t%s\n"
                    "        Exiftool EXIF:ModifyDate:\t%s\n"
                    "        Exiftool EXIF:DateTimeOriginal*:\t%s\n"
                    "        Exiftool EXIF:CreateDate:\t%s\n"
                    "        Exiftool Composite:SubSecCreateDate:\t%s\n"
                    "        Exiftool Composite:SubSecDateTimeOriginal:\t%s\n"
                    % (file_mod_time,
                      exiftool_metadata.get('EXIF:ModifyDate'),
                      exiftool_metadata.get('EXIF:DateTimeOriginal'),
                      exiftool_metadata.get('EXIF:CreateDate'),
                      exiftool_metadata.get('Composite:SubSecCreateDate'),
                      exiftool_metadata.get('Composite:SubSecDateTimeOriginal')
                      )).expandtabs(28))

        elif img_ext in [".GIF", ".WEBP"]:
            with exiftool.ExifTool() as et:
                metadata = et.get_metadata(path + img)
                fmod_date = metadata.get("File:FileModifyDate")

            # "*" indicates metadata most likely to be actual creation time.
            print((img + ":\n"
                        "        file_mod_time:\t\t%s\n"
                        "        EXIFtool File:FileModifyDate*:\t%s\n"
                        % (file_mod_time, fmod_date)).expandtabs(28))

        elif img_ext == ".MOV":
            with exiftool.ExifTool() as et:
                metadata = et.get_metadata(path + img)
                qt_create_date = metadata.get("QuickTime:CreateDate")
                qt_mod_date = metadata.get("QuickTime:ModifyDate")
                qt_trk_create_date = metadata.get("QuickTime:TrackCreateDate")
                qt_trk_mod_date = metadata.get("QuickTime:TrackModifyDate")
                qt_med_create_date = metadata.get("QuickTime:MediaCreateDate")
                qt_med_mod_date = metadata.get("QuickTime:MediaModifyDate")
                qt_creation_date = metadata.get("QuickTime:CreationDate")

            # "*" indicates metadata most likely to be actual creation time.
            print((img + ":\n"
                        "        file_mod_time:\t\t%s\n"
                        "        EXIFtool QuickTime:CreateDate:\t%s\n"
                        "        EXIFtool QuickTime:ModifyDate:\t%s\n"
                        "        EXIFtool QuickTime:TrackCreateDate:\t%s\n"
                        "        EXIFtool QuickTime:TrackModifyDate:\t%s\n"
                        "        EXIFtool QuickTime:MediaCreateDate:\t%s\n"
                        "        EXIFtool QuickTime:MediaModifyDate:\t%s\n"
                        "        EXIFtool QuickTime:CreationDate*:\t%s\n"
                        % (file_mod_time,
                        qt_create_date, qt_mod_date,
                        qt_trk_create_date, qt_trk_mod_date,
                        qt_med_create_date, qt_med_mod_date,
                        qt_creation_date)).expandtabs(28))

        elif img_ext == ".MP4":
            with exiftool.ExifTool() as et:
                metadata = et.get_metadata(path + img)
                qt_create_date = metadata.get("QuickTime:CreateDate")
                qt_mod_date = metadata.get("QuickTime:ModifyDate")
                qt_trk_create_date = metadata.get("QuickTime:TrackCreateDate")
                qt_trk_mod_date = metadata.get("QuickTime:TrackModifyDate")
                qt_med_create_date = metadata.get("QuickTime:MediaCreateDate")
                qt_med_mod_date = metadata.get("QuickTime:MediaModifyDate")

            # "*" indicates metadata most likely to be actual creation time.
            print((img + ":\n"
                        "        file_mod_time:\t\t%s\n"
                        "        EXIFtool QuickTime:CreateDate*:\t%s\n"
                        "        EXIFtool QuickTime:ModifyDate:\t%s\n"
                        "        EXIFtool QuickTime:TrackCreateDate:\t%s\n"
                        "        EXIFtool QuickTime:TrackModifyDate:\t%s\n"
                        "        EXIFtool QuickTime:MediaCreateDate:\t%s\n"
                        "        EXIFtool QuickTime:MediaModifyDate:\t%s\n"
                        "\tDates 4 hrs ahead because no time zone adjustment.\n"
                        % (file_mod_time,
                        qt_create_date, qt_mod_date,
                        qt_trk_create_date, qt_trk_mod_date,
                        qt_med_create_date, qt_med_mod_date)).expandtabs(28))

        elif img_ext == ".PNG":
            img_obj = PIL.Image.open(path + img)

            pil_metadata = img_obj.info.get('XML:com.adobe.xmp')
            if pil_metadata and "<photoshop:DateCreated>" in pil_metadata:
                pil_date_created = pil_metadata.split(
                                    "<photoshop:DateCreated>")[1].split(
                                    "</photoshop:DateCreated>")[0]
            else:
                pil_date_created = None

            with exiftool.ExifTool() as et:
                metadata = et.get_metadata(path + img)
                xmp_date_created = metadata.get("XMP:DateCreated")

            # "*" indicates metadata most likely to be actual creation time.
            print((img + ":\n"
                        "        file_mod_time:\t\t%s\n"
                        "        PIL-info date_created:\t%s\n"
                        "        EXIFtool XMP:DateCreated*:\t%s\n"
                        % (file_mod_time, pil_date_created,
                                            xmp_date_created)).expandtabs(28))

        elif img_ext == ".AAE":
            img_obj = open(path + img, 'r')

            for line in img_obj:
                if '<date>' in line:
                    adjustmentTimestamp = line.split("<date>")[1].split(
                                                                "Z</date>")[0]
                else:
                    adjustmentTimestamp = None

            with exiftool.ExifTool() as et:
                metadata = et.get_metadata(path + img)
                adj_time = metadata.get("PLIST:AdjustmentTimestamp")

            # "*" indicates metadata most likely to be actual creation time.
            print((img + "\n"
                        "        file_mod_time:\t\t%s\n"
                        "        AAEparse adjustmentTimestamp:\t%s\n"
                        "        EXIFtool PLIST:AdjustmentTimestamp*:\t%s\n"
                        % (file_mod_time, adjustmentTimestamp,
                                                    adj_time)).expandtabs(28))
        elif skip_unknown:
            print("%s\n"
            "        Cannot get EXIF data for this file type. Skipping\n" % img)
            return # Don't try to rename with datestamp.

        else:
            print((img + "\n"
                        "        file_mod_time:\t\t%s\n"
                        % file_mod_time).expandtabs(28))

        # Add datestamp to image name if desired.
        if rename_with_datestamp:
            # This requires redundant use of exiftool, but not a big deal
            # if runtime isn't bad.
            add_datestamp(path + img)


def datestamp_all(dir_path, longstamp=False):
    """Function to prepend datestamp to all images in a directory without
    terminal output. Use add_datestamp() function below for each file processed.
    Second parameter determines if date only or both date/time will be added."""

    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        print("Not a valid directory path.")
        return None

    if dir_path[-1] != '/':
        dir_path += '/'

    image_list = os.listdir(dir_path)
    image_list.sort()

    for img in image_list:
        add_datestamp(dir_path + img, longstamp)


def add_datestamp(img_path, long_stamp=False):
    """Retrieve and prepend creation timestamp to image filename.
    Uses get_img_date() function below to retrieve date/time from EXIF data.
    Second parameter determines if date only or both date/time will be added."""
    # test rename operation to see if mtime changes
    # need a variable name that stores images best guess-time. look at
    # get_img_date end code.

    if not os.path.exists(img_path):
        raise DirectoryNameError("Invalid path passed to add_datestamp() "
                                                                    "function.")

    # Separate out image name from directory path
    img_name = os.path.basename(img_path)  # no trailing slash present
    dir_path = os.path.dirname(img_path) + "/"

    # See if file already datestamped (regardless of correctness)
    if len(img_name) >= 10:
        try:
            time.strptime(img_name[:10], DATE_FORMAT)
            if long_stamp:
                pass
            else:
                return
        except ValueError:
            pass

    datestamp_obj = get_img_date(img_path)

    if datestamp_obj:
        datestamp_short = time.strftime(DATE_FORMAT, datestamp_obj)
        datestamp_long = time.strftime(DATETIME_FORMAT, datestamp_obj)
    else:
        # if get_img_date returned None (because file wasn't a recognized img
        # format), don't proceed further.
        return

    if long_stamp:
        datestamp = datestamp_long
    else:
        datestamp = datestamp_short

    if datestamp in img_name:
        # Don't prepend redundant datestamp.
        print("%s already has correct datestamp." % img_name)
    elif not long_stamp and datestamp_long in img_name:
        # rename longer-stamped names when short stamp desired.
        img_shortened = img_name.replace(datestamp_long, datestamp_short)
        safe_rename(img_path, img_shortened)
    elif long_stamp and datestamp_short in img_name:
        # rename shorter-stamped names when long stamp desired.
        # note that datestamp_short appears in imgs w/ datestamp_long.
        img_lengthened = img_name.replace(datestamp_short, datestamp_long)
        safe_rename(img_path, img_lengthened)
    elif img_name[:4] != 'IMG_':
        # Detect presence of non-standard naming (could be pre-existing
        # alternate datestamp)
        rename_choice = input("%s has non-standard naming. "
                "Add %s datestamp anyway? [y/n]\n> " % (img_name, datestamp))
        if rename_choice and rename_choice.lower() == 'y':
            safe_rename(img_path, datestamp + '_' + img_name)
        else:
            print("Skipped %s\n" % img_name)
    else:
        safe_rename(img_path, datestamp + '_' + img_name)


def safe_rename(img_path, new_img_name):
    """Ensures that rename action does not overwrite existing img in
    target dir."""

    if not os.path.exists(img_path):
        raise DirectoryNameError("Invalid path passed to safe_rename() "
                                                                    "function.")

    target_dir = os.path.dirname(img_path)
    target_dir_imgs = os.listdir(target_dir)

    new_img_name_noext = os.path.splitext(new_img_name)[0]
    img_ext = os.path.splitext(new_img_name)[-1]

    if new_img_name in target_dir_imgs:
        n = 1
        # need to split off extension before appending increment
        new_img_name_noext = new_img_name_noext + "_%d" % n

        while new_img_name_noext + img_ext in target_dir_imgs:
            n += 1
            new_img_name_noext = new_img_name_noext[:-1] + "%d" % n
            # This will not increment correctly after more than nine iterations,
            # but that would require nine instances of the same img name taken
            # on the same date, which is very unlikely.

        new_img_name = new_img_name_noext + img_ext

    os.rename(img_path, target_dir + "/" + new_img_name)


def get_img_date_plus(img_path, skip_unknown=True):
    """Function that returns best available timestamp for any single JPG, HEIC,
    GIF, PNG, AAE, MP4, or MOV file located at img_path.
    Returns a tuple with a struct_time object and boolean indicating if the time
    was manually specified or automatically found."""
    # modify to look for each metadata type and fall back on mtime if needed.

    if not os.path.exists(img_path):
        raise DirectoryNameError("Invalid path passed to get_img_date() "
                                                                "function.")

    img_name = os.path.basename(img_path)  # no trailing slash in path
    img_ext = os.path.splitext(img_name)[-1].upper()

    if os.path.isdir(img_path):
        print("%s is a directory. Skipping"
                                    % img_name)
        return None

    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(img_path)

        # Different files have different names for the creation date in the
        # metadata.
        if img_ext in [".JPG", ".JPEG", ".HEIC"]:
            create_time = metadata.get("EXIF:DateTimeOriginal")
            # ex. 2019:08:26 09:11:21
            format = "%Y:%m:%d %H:%M:%S"
        elif img_ext == ".PNG":
            create_time = metadata.get("XMP:DateCreated")
            # ex. 2019:08:26 03:51:19
            format = "%Y:%m:%d %H:%M:%S"
        elif img_ext in [".GIF", ".WEBP"]:
            # create_time = metadata.get("File:FileModifyDate")
            # # ex. 2019:10:05 10:13:04-04:00
            # # non-standard format - adjust manually before passing to strftime
            # if create_time:
            #     create_time = create_time[0:22] + create_time[23:]
            #     # Now formatted this way: 2019:08:26 19:22:27-0400
            #     format = "%Y:%m:%d %H:%M:%S%z"

            # only file mod time available.
            create_time = None
        elif img_ext == ".MOV":
            create_time = metadata.get("QuickTime:CreationDate")
            # ex. 2019:08:26 19:22:27-04:00
            # non-standard format - adjust manually before passing to strftime
            if create_time:
                create_time = create_time[0:22] + create_time[23:]
                # Now formatted this way: 2019:08:26 19:22:27-0400
                format = "%Y:%m:%d %H:%M:%S%z"
        elif img_ext == ".MP4":
            create_time = metadata.get("QuickTime:CreateDate")
            # ex. 2019:08:26 03:51:19
            format = "%Y:%m:%d %H:%M:%S"

            if create_time == "0000:00:00 00:00:00":
                # Fall back on fs mod time (below).
                create_time = None
            elif create_time:
                # MP4 metadata isn't in correct time zone.
                create_time = tz_adjust(create_time, format, 4)
                if not create_time:
                    print("Changing time stamp would require date change: %s"
                                                                % img_name)
        elif img_ext == ".AAE":
            create_time = metadata.get("PLIST:AdjustmentTimestamp")
            # ex. 2019:07:05 12:46:46Z
            format = "%Y:%m:%d %H:%M:%SZ"
        else:
            print("%s - Cannot get EXIF data for this file type." % img_name)
            if skip_unknown:
                print("Skipping.")
                return None
            else:
                create_time = None

        if create_time:
            create_time_obj = time.strptime(create_time, format)
            return (create_time_obj, False)
        else:
            # Fall back on fs mod time if more precise metadata unavailable.
            print("\nNo valid EXIF timestamp found. Enter new timestamp or "
                                                "fall back on fs mod time.")
            man_date_output = spec_manual_date(img_path)
            # will be a time_struct object if a date entered.
            if isinstance(man_date_output, time.struct_time):
                # If user entered a date:
                return (man_date_output, True)
            elif man_date_output=="s":
                # Skip
                return (None, False)
            else:
                # Go ahead w/ fs mod time if user accepts fallback.
                return (time.localtime(os.path.getmtime(img_path)), True)


def get_img_date(img_path, skip_unknown=True):
    """Wrapper function for get_img_date_plus() that returns only
    the struct_time object."""

    return_vals = get_img_date_plus(img_path, skip_unknown)
    # function might return None instead of a tuple, so have to check.
    if return_vals:
        return return_vals[0]


def spec_manual_date(img_path):
    """Prompts user to enter a timestamp for displayed pic. Returns a
    struct_time object or "s" to skip this file or None if user accepts
    (caller-defined) fallback option."""

    list_all_img_dates(img_path, skip_unknown=False)
    display_photo(img_path)
    man_date_response = input("Manually specify datestamp in YYYY-MM-DD format, "
                                        "enter nothing to accept fallback, "
                            "or enter 's' to skip organizing this file.\n> ")
    if man_date_response in ["s", "S"]:
        return "s"
    elif man_date_response:
        try:
            man_img_time_struct = time.strptime(man_date_response, DATE_FORMAT)
            return man_img_time_struct
        except ValueError:
            print("Invalid reponse. Confirm proper date format.\n")
            return spec_manual_date(img_path)
    else:
        # If nothing valid specified, indicate to caller fxn to use fallback
        return None


def tz_adjust(time_str, format, shift):
    """Function to adjust timezone of a datestamp."""
    time_obj = time.strptime(time_str, format)

    ts_list = list(time_obj)
    if ts_list[3] <= shift:
        # Function doesn't handle date adjustments resulting from hr change.
        return None
    else:
        ts_list[3] -= shift         # EST. DST not accounted for.
        time_obj_adjusted = time.struct_time(tuple(ts_list))
        time_str_adjusted = time.strftime(format, time_obj_adjusted)
        return time_str_adjusted


def get_comment(img_path, print_type=False):
    if not os.path.isfile(img_path):
        print("Not a valid image path.")
        return None

    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(img_path)
        exif_img_desc = metadata.get("EXIF:ImageDescription")
        caption_abst = metadata.get("IPTC:Caption-Abstract")
        qt_comment = metadata.get("QuickTime:Comment")
        basic_comment = metadata.get("File:Comment")
        # File:Comment is tag used by ''$ exiftool -Comment=...'

        # Count non-empty comment/caption values
        if sum(x is not None for x in
                  [exif_img_desc, caption_abst, qt_comment, basic_comment]) > 1:
            input("Found caption in multiple EXIF tags for %s. Unhandled case."
                                                % os.path.basename(img_path))
        elif exif_img_desc:
            if print_type:
                print("%s: %s" % ("EXIF:ImageDescription", exif_img_desc))
            return exif_img_desc
        elif caption_abst:
            if print_type:
                print("%s: %s" % ("IPTC:Caption-Abstract", caption_abst))
            return caption_abst
        elif qt_comment:
            if print_type:
                print("%s: %s" % ("QuickTime:Comment", qt_comment))
            return qt_comment
        elif basic_comment:
            if print_type:
                print("%s: %s" % ("File:Comment", basic_comment))
            return basic_comment
        else:
            return None


def meta_dump(img_path):
    """Display all available exiftool data (for any file w/ EXIF data)."""

    if not os.path.exists(img_path):
        print("Not a valid path.")
        return None
    elif os.path.isdir(img_path):
        print("%s is a directory. Need path to image."
                                                % os.path.basename(img_path))
        return None

    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(img_path)
        for key in metadata:
             print(str(key) + ": " + str(metadata[key]))


# References:
# https://www.blog.pythonlibrary.org/2010/03/28/getting-photo-metadata-exif-using-python/
# https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image#4765242
# https://gist.github.com/erans/983821#comment-377080
# https://stackoverflow.com/questions/48631908/python-extract-metadata-from-png#51249611
# https://www.vice.com/en_us/article/aekn58/hack-this-extra-image-metadata-using-python

# https://stackoverflow.com/questions/21355316/getting-metadata-for-mov-video#21395803
# https://github.com/smarnach/pyexiftool
# https://smarnach.github.io/pyexiftool/
# https://sno.phy.queensu.ca/~phil/exiftool/
