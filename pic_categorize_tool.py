import os
import shutil
import time
from tqdm import tqdm
import subprocess
import hashlib

from idevice_media_offload.dir_names import CAT_DIRS


class MediaCatPathError(Exception):
    pass


# Phase 3: Display pics one by one and prompt for where to copy each.
# Have an option to ignore photo (not categorize and copy anywhere).
# Check for name collisions in target directory.
# Allow manual path entry


class Categorizer(object):
    def __init__(self, buffer_root):
        self.buffer_root = buffer_root
        self.manual_dir_list = []

        # Display cat buffer
        display_dir(self.buffer_root)

    def add_manual_dir(self, dir_path):
        # If it's already been added, don't add duplicate.
        if dir_path not in self.manual_dir_list:
            self.manual_dir_list.append(dir_path)
            self.manual_dir_list.sort()

    def find_stored_dir(self, keyword, silent=False):
        """Retrieve directory path from preloaded list or from previously-used
        manual paths entered in this session."""
        # First see if keyword is itself a path to prevent finding a "match"
        # in the form of a longer path containing this path as a substring.
        if os.path.isdir(keyword):
            return None

        # Then look for keyword match in preloaded list.
        if CAT_DIRS.get(keyword):
            return CAT_DIRS[keyword]

        # Then see if keyword is a substring of a previously-entered manual dir.
        # Keyword referencing manually-entered path must be at least three
        # characters long
        if len(keyword) < 3:
            if not silent:
                print("Input keyword for referencing stored dirs must be >3 "
                                                                "characters\n")
            return None

        dirs_found = []
        for dir_path in self.manual_dir_list:
            if keyword.lower() == dir_path.lower():
                # If an already-stored path is entered again, don't print.
                return keyword
            if keyword.lower() in dir_path.lower():
                dirs_found.append(dir_path)

        if len(dirs_found) == 1:
            if not silent: # Suppress duplicate output when called twice.
                print("Interpreted '%s' as %s." % (keyword, dirs_found[0]))
            return dirs_found[0]
        elif len(dirs_found) > 1:
            # If more than one path found found with keyword (ambiguous),
            # inform user and don't return a path.
            print("Multiple matches in stored directories. Be more specific.")
            return None
        elif len(dirs_found) == 0:
            # If 0 paths found with keyword, don't return a path.
            if not silent:
                print("No matches found in stored directories.")
            return None

    def run_auto_cat(self):
        """Function to automatically categorize st media that user puts in
        st_buffer.
        Later may have other auto categorizing groups, but for now just st."""

        # Initialize st buffer directory to automatically categorize from.
        # Program will automatically categorize by date and move to st root.
        st_buffer_path = os.path.join(self.buffer_root, "st_buffer/")
        if not os.path.exists(st_buffer_path):
            os.mkdir(st_buffer_path)

        # Display cat buffer in new window.
        display_dir(st_buffer_path)

        # Prompt to move stuff in bulk before looping through img display.
        input("\nDo any mass copies from categorization buffer now (e.g. "
                "into st_buffer) before proceeding."
                "\nPress Enter when ready to continue Cat program.")

        st_buffer_imgs = os.listdir(st_buffer_path)
        if st_buffer_imgs:
            st_buffer_imgs.sort()

            # Loop through st_buffer categorize.
            print("\nCategorizing st_buffer media now. Progress:")
            for img in tqdm(st_buffer_imgs):
                img_path = os.path.join(st_buffer_path, img)
                if not os.path.isfile(img_path):
                    # Ignore. Shouldn't happen, but handling just in case.
                    continue

                target_dir = self.get_target_dir(img_path, "st")
                if target_dir:
                    copy_to_target(img_path, target_dir, move_op=True)
                else:
                    # If user chooses to discard img, None is returned by
                    # get_target_dir. Delete image from buffer.
                    os.remove(img_path)

            print("Successfully categorized media from st_buffer.")
        else:
            print("Nothing in st_buffer.")


    def photo_transfer(self, start_point=""):
        """Master function to display images in buffer and prompt user
        where each should be copied. Execute copy. Start_point can be specified
        (as img name) to skip processing earlier imgs."""

        # local buffer to be categorized manually
        CAT_DIRS['u'] = os.path.join(self.buffer_root, "manual_" +
                                                time.strftime('%Y-%m-%d') + '/')

        print("\nCategorizing images from buffer:\n\t%s\n" % self.buffer_root)
        # Print dict of directory mappings
        print("Target directories available (standard):")
        for key, cat_path in CAT_DIRS.items():
            print(("\t%s:\t%s" % (key, cat_path)).expandtabs(2))

        print("\nTarget directories available (manual):")
        for dir in self.manual_dir_list:
            print(("\t\t\t%s" % dir).expandtabs(2))

        print("\n(Append '&' to first choice if multiple destinations needed)\n"
                "(Append '+' followed by a two-digit number to use same dest "
                        "folder for subsequent [number] of pics)")

        # Initialize manual-sort directory
        if not os.path.exists(CAT_DIRS['u']):
            os.mkdir(CAT_DIRS['u'])

        buffered_imgs = os.listdir(self.buffer_root)
        buffered_imgs.sort()
        if start_point:
            # If a start point is specified, truncate earlier images.
            start_index = buffered_imgs.index(start_point)
            buffered_imgs = buffered_imgs[start_index:]

        for img in buffered_imgs:
            img_path = os.path.join(self.buffer_root, img)

            if os.path.isdir(img_path):
                # Ignore any manual sort folder left over from previous offload.
                continue
            elif not os.path.exists(img_path):
                # Handle case where user manually deletes img in buffer outside
                # of program.
                print("%s skipped - not found in Cat buffer." % img)
                continue

            if os.path.splitext(img)[-1].upper() == ".HEIC":
                # Can't display these, but they should have already been
                # converted during org step.
                # Look for JPG version.
                jpg_path = os.path.splitext(img_path)[0] + ".jpg"
                if os.path.exists(jpg_path):
                    dup_heif_path = img_path
                    img_path = jpg_path
                    # Will sub in jpg file to use for determining where to
                    # transfer. Then apply the transfer to both.

                    mod_heif_path = dup_heif_path.replace("IMG_", "IMG_E")
                    if not os.path.exists(mod_heif_path) or mod_heif_path==dup_heif_path:
                        # IMG_ --> IMG_E sub may do nothing w/ nonstandard
                        # naming (e.g. YYYY-MM-DD_VNUF5899.HEIC)
                        mod_heif_path = None
                else:
                    dup_heif_path = None
                    print("Cannot find associated JPG for %s. Storing in "
                                                 "manual-sort buffer '%s'"
                                       % (img, os.path.basename(CAT_DIRS['u'])))
                    # Automatically move to manual-sort dir. May change this
                    # to fall through to prompt (w/o img display) and allow user
                    # to decide.
                    copy_to_target(img_path, CAT_DIRS['u'])
                    continue
            else:
                dup_heif_path = None

            # Show image and prompt for location.
            try:
                target_dir = self.get_target_dir(img_path)
            except MediaCatPathError:
                # Runs if file renamed by user during get_target_dir() prompt loop.
                print("Restarting. Name of target img may have changed.\n")
                self.photo_transfer()
                return

            # Have to implement (sometimes redundant) check on directory
            # existence because stored directories might have gone stale (e.g.
            # name changed).

            if target_dir == None:
                # If user chooses to discard img, None is returned by
                # get_target_dir. Delete image from buffer.
                os.remove(img_path)
                if dup_heif_path:
                    os.remove(dup_heif_path)
                    if mod_heif_path:
                        os.remove(mod_heif_path)
                continue

            elif target_dir[0] == '*' and os.path.isdir(target_dir[1:]):
                # If get_target_dir detected the trailing special character '&',
                # then after copying image into one place, the user should be
                # prompted again w/ same photo to put somewhere else.
                copy_to_target(img_path, target_dir[1:])
                if dup_heif_path:
                    copy_to_target(dup_heif_path, target_dir[1:])
                    if mod_heif_path:
                        copy_to_target(mod_heif_path, target_dir[1:])
                self.photo_transfer(start_point=img)
                return

            elif target_dir[0] == '!' and os.path.isdir(target_dir[3:]):
                copy_to_target(img_path, target_dir[3:], move_op=True)
                if dup_heif_path:
                    copy_to_target(dup_heif_path, target_dir[3:], move_op=True)
                    if mod_heif_path:
                        copy_to_target(mod_heif_path, target_dir[3:], move_op=True)

                # If get_target_dir detected the trailing special character '+' and
                # a two-digit number, copy multiple successive images to same place.
                additional_copies = int(target_dir[1:3])
                re_buffered_imgs = os.listdir(self.buffer_root)
                re_buffered_imgs.sort()
                for extra_img in re_buffered_imgs[:additional_copies]:
                    extra_img_path = os.path.join(self.buffer_root, extra_img)
                    copy_to_target(extra_img_path, target_dir[3:], move_op=True)

                self.photo_transfer()
                return

            elif os.path.isdir(target_dir):
                # Execute the move from buffer to appropriate dir.
                copy_to_target(img_path, target_dir, move_op=True)
                if dup_heif_path:
                    copy_to_target(dup_heif_path, target_dir, move_op=True)
                    if mod_heif_path:
                        copy_to_target(mod_heif_path, target_dir, move_op=True)

            else:
                # Path returned by get_target_dir isn't a valid directory.
                print("Invalid path specified. Path of stored dir may have "
                                                                "changed.\n")
                self.photo_transfer()
                return


        while os.listdir(CAT_DIRS['u']):
            sort_folder_response = input("\nToday's manual-sort folder "
                "populated.\nCheck folder(s) for any uncategorized pictures "
                    "and categorize them manually.\nPress Enter to continue "
                                                        "or 'q' to quit.\n> ")
            if sort_folder_response.lower() == 'q':
                return
            else:
                continue
        # Once manual sort folder is empty, remove it as long as it's empty.
        if os.path.exists(CAT_DIRS['u']) and not os.listdir(CAT_DIRS['u']):
            os.rmdir(CAT_DIRS['u'])
        # Also remove any other manual sort folders from other days if they're empty.
        for other_folder in os.listdir(self.buffer_root):
            if "manual_" in other_folder:
                other_folder_path = os.path.join(self.buffer_root, other_folder)
                while os.listdir(other_folder_path):
                    other_folder_response = input("\nAt least one manual-sort "
                        "folder in the buffer is populated.\nCategorize content "
                        "then press Enter to continue or 'q' to quit.\n> ")
                    if other_folder_response.lower() == 'q':
                        return
                    else:
                        continue
                if not os.listdir(other_folder_path):
                    os.rmdir(other_folder_path)


    def get_target_dir(self, img_path, target_input=""):
        """Function to find and return the directory an image should be copied
        into based on translated user input
        Returns target path."""
        image_name = os.path.basename(img_path)

        # Display pic or video and prompt for dest.
        # Continue prompting until valid string input received.
        while True:
            if not os.path.exists(img_path):
                # If item renamed after first prompt, this block runs.
                # Issue will be handled automatically in caller method above.
                raise MediaCatPathError()
            if not target_input:
                # Runs first time and if user enters nothing at prompt
                display_photo(img_path)
                target_input = input("\nEnter target location for %s (or 'n' "
                                            "for no transfer)\n> " % image_name)
                continue
            elif target_input == 'n':
                return None
            elif target_input == 'st':
                # 'st' type images require target folder creation in most cases.
                return self.get_st_target_dir(img_path)
            elif ( (target_input[-1] == '&')
                   and (self.find_stored_dir(target_input[:-1], silent=True)
                        or os.path.isdir(target_input[:-1])) ):
                # If the '&' special character invoked, it means the image needs
                # to be copied into multiple places, and the program should
                # prompt again.
                # pre-pend '*' to returned path to indicate special case to
                # caller.
                return '*' + self.get_target_dir(img_path, target_input[:-1])
            elif ( len(target_input) >= 3
                   and target_input[-3] == '+'
                   and (self.find_stored_dir(target_input[:-3], silent=True)
                        or os.path.isdir(target_input[:-3])) ):
                # If the '+' special character invoked, it means subsequent
                # image(s) need to be copied into same dest.
                # pre-pend '!' to returned path to indicate special case to
                # caller.
                return '!' + target_input[-2:] + self.get_target_dir(img_path,
                                                            target_input[:-3])
            elif self.find_stored_dir(target_input, silent=True):
                return self.find_stored_dir(target_input)
                # no guarantee stored dirs still valid, so have to be checked
                # by caller.
            elif os.path.isdir(target_input):
                # Allow manual entry of target path.
                # Store manually-entered paths each session for quick lookup.
                self.add_manual_dir(target_input)
                return target_input
            else:
                print("Invalid input. Try again.")
                target_input = "" # reset
                continue


    def get_st_target_dir(self, img_path):
        """Function to find correct directory (or make new) within dated
        heirarchy based on image mod date. Return resulting path."""

        img_name = os.path.basename(img_path)
        img_date = img_name.split('_')[0]

        st_root = CAT_DIRS['st']
        st_img_path = os.path.join(st_root, img_date)

        if not img_date in os.listdir(st_root):
            os.mkdir(st_img_path)

        return st_img_path


def copy_to_target(img_path, target_dir, new_name=None, move_op=False):
    """Function to copy img to target directory with collision detection.
    If 'move_op' param specified, delete img from current dir."""

    img = os.path.basename(img_path)

    if not new_name:
        new_name = img

    # Need to assume trailing slash in target_dir later.
    if target_dir[-1] != "/":
        target_dir += "/"

    # Prompt user for decision if collision detected.
    target_dir_imgs = os.listdir(target_dir)
    if new_name in target_dir_imgs:

        if same_hash(img_path, os.path.join(target_dir, new_name)):
            # First check if they are the same file. If so, don't replace.
            print("%s/%s with same file hash exists already. "
                                "Dest file not overwritten.\n"
                            % (os.path.basename(target_dir[:-1]), new_name))
            time.sleep(1) # Pause for one second so user sees above message.
            if move_op:
                os.remove(img_path)
            else:
                return

        else:
            # Otherwise, need user input to decide what to do about collision.
            action = None
            while action != "s" and action != "o" and action != "k":
                action = input("Collision detected: %s in dir:\n\t%s\n"
                    "\tSkip, overwrite, or keep both? [S/O/K]\n\t> "
                                                % (new_name, target_dir))
                if action.lower() == "s":
                    return
                elif action.lower() == "o":
                    # Overwrite file in destination folder w/ same name.
                    os.remove(os.path.join(target_dir, new_name))
                    shutil.move(img_path, target_dir)
                    return
                elif action.lower() == "k":
                    # Repeatedly check for existence of duplicates until a free
                    # name appears. Assume there will never be more than 9.
                    # Prefer shorter file name to spare leading zeros.
                    img_noext = os.path.splitext(new_name)[0]
                    img_ext = os.path.splitext(new_name)[-1]

                    n = 1
                    img_noext = img_noext + "_%d" % n

                    while img_noext + img_ext in target_dir_imgs:
                        n += 1
                        if n > 9:
                            raise Exception("Image incrementer exceeded 9.\n"
                                        "Check dest folder %s" % target_dir)
                        img_noext = img_noext[:-1] + "%d" % n
                    if move_op:
                        shutil.move(img_path,
                                os.path.join(target_dir, img_noext + img_ext))
                    else:
                        shutil.copy2(img_path,
                                os.path.join(target_dir, img_noext + img_ext))

    elif move_op:
        shutil.move(img_path, os.path.join(target_dir, new_name))
    else:
        shutil.copy2(img_path, os.path.join(target_dir, new_name))


def same_hash(img1_path, img2_path):
    with open(img1_path, 'rb') as file_obj:
        img1_hash = hashlib.sha1(file_obj.read())
        # print(img1_hash.hexdigest())

    with open(img2_path, 'rb') as file_obj:
        img2_hash = hashlib.sha1(file_obj.read())
        # print(img2_hash.hexdigest())

    if img1_hash.hexdigest() == img2_hash.hexdigest():
        return True
    else:
        return False


def os_open(input_path):
    """Passes input to xdg-open. Can pass in file paths or URLs.
    """
    if not "http" in input_path and not os.path.exists(input_path):
        raise Exception("Invalid path passed to os_open: %s" % input_path)

    CompProc = subprocess.run(['xdg-open', input_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    # Check for success. Some img formats like HEIC can't be displayed.
    if CompProc.returncode != 0:
        print("Unable to display %s" % os.path.basename(input_path))


def display_dir(dir_path):
    os_open(dir_path)


def display_photo(img_path):
    os_open(img_path)



# TEST


# reference
# Display image:
# subprocess.Popen('xdg-open', filename in quotes])

#Copy file or directory w/ contents:
# shutil.copy2([src file], [dest dir])
# shutil.copytree([src], [dest]])
