import date_compare
import os
import subprocess
import glob

# Call bash convert script
def convert_all_webp(dir_name, delete_webp=False):
    file_list = os.listdir(dir_name)
    for file in file_list:
        og_path = os.path.join(dir_name, file)
        if os.path.splitext(file)[1].lower() == ".webp":
            # Check for existing converted file
            file_no_ext = os.path.splitext(file)[0]
            wildcard_filename = file_no_ext + "." + "*"

            # Check if two files w/ same name already exist in the directory.
            matches = glob.glob(os.path.join(dir_name, wildcard_filename))
            if len(matches) > 1:
                print("Skipping: %s (File with same name and different "
                                                "extension exists here)" % file)
            else:
                print("Converting: %s" % file)
                subprocess.run(["./convert_webp", og_path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                # find matches again now that there are two
                matches = glob.glob(os.path.join(dir_name, wildcard_filename))
                # Find non-webp one by deducting sets
                # https://stackoverflow.com/a/21502564
                converted_filepath = ( set(matches) - set([og_path]) ).pop()

                webp_size = humanbytes(os.path.getsize(og_path))
                new_size = humanbytes(os.path.getsize(converted_filepath))
                print("\t%s  ->  %s" % (webp_size, new_size))

            if delete_webp:
                os.remove(os.path.join(dir_name, file))


# humanbytes() copied from here:
# https://stackoverflow.com/a/21502564
def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)

# tests = [1, 1024, 500000, 1048576, 50000000, 1073741824, 5000000000, 1099511627776, 5000000000000]
#
# for t in tests: print '{0} == {1}'.format(t,humanbytes(t))
