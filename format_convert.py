import date_compare
import os
import subprocess
import glob

# Call bash convert script
def convert_all_webp(dir_name, delete_webp=False):
    file_list = os.listdir(dir_name)
    for file in file_list:
        if os.path.splitext(file)[1].lower() == ".webp":
            # Check for existing converted file
            file_no_ext = os.path.splitext(file)[0]
            wildcard_filename = file_no_ext + "." + "*"
            # Check if two files w/ same name already exist in the directory.
            if len(glob.glob(os.path.join(dir_name, wildcard_filename))) > 1:
                print("Skipping: %s (File with same name and different "
                                                "extension exists here)" % file)
            else:
                print("Converting: %s" % file)
                subprocess.run(["./convert_webp", os.path.join(dir_name, file)],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            if delete_webp:
                os.remove(os.path.join(dir_name, file))
