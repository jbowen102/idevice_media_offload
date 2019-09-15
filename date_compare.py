import PIL.Image
from PIL.ExifTags import TAGS
from os import listdir
from os.path import getmtime
from time import localtime, strftime, strptime
import exiftool

# https://www.blog.pythonlibrary.org/2010/03/28/getting-photo-metadata-exif-using-python/
# https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image#4765242
# https://gist.github.com/erans/983821#comment-377080
# https://stackoverflow.com/questions/48631908/python-extract-metadata-from-png#51249611
# https://www.vice.com/en_us/article/aekn58/hack-this-extra-image-metadata-using-python

def comparef(dir):
    if dir[-1] != '/':
        dir += '/'

    image_list = listdir(dir)
    image_list.sort()
    for img in image_list:
        # print(img)
        img_ext = img.upper()[-4:]
        img_mod_time = strftime('%Y-%m-%dT%H%M%S', localtime(getmtime(dir + img)))

        if img_ext == ".JPG" or img_ext == "JPEG":
            img_obj = PIL.Image.open(dir + img)

            encoded_exif = img_obj._getexif()
            metadata = {}
            for tag, value in encoded_exif.items():
                 decoded_key = TAGS.get(tag, tag)
                 if "DateTime" in decoded_key:
                     metadata[decoded_key] = value

            if ('DateTimeOriginal' in metadata and
                'DateTimeDigitized' in metadata and
                'DateTime' in metadata):
                print(img + ":\n"
                            "\timg_mod_time:\t\t %s\n"
                            "\tEXIF DateTimeOriginal: %s\n"
                            "\tEXIF DateTimeDigitized: %s\n"
                            "\tEXIF DateTime:\t\t %s\n"
                            % (img_mod_time, metadata['DateTimeOriginal'],
                                             metadata['DateTimeDigitized'],
                                             metadata['DateTime']))
            else:
                print(img + ":\n"
                            "\timg_mod_time: %s\n" % img_mod_time)

        elif img_ext == ".MOV":
            with exiftool.Exiftool() as et:
                img_obj = PIL.Image.open(dir + img)
                et.get_metadata(img_obj)
                et.get_tag(img_obj)

                # start()
                # terminate()
                # https://stackoverflow.com/questions/21355316/getting-metadata-for-mov-video#21395803
                # https://github.com/smarnach/pyexiftool
                # https://smarnach.github.io/pyexiftool/
                # https://sno.phy.queensu.ca/~phil/exiftool/

        elif img_ext == ".PNG":
            img_obj = PIL.Image.open(dir + img)

            # encoded_exif = getattr(img_obj, '_getexif', lambda: None)()
            date_created = img_obj.info['XML:com.adobe.xmp'].split("<photoshop:DateCreated>")[1].split("</photoshop:DateCreated>")[0]

            print(img + ":\n"
                        "\timg_mod_time:\t %s\n"
                        "\tPNG date_created: %s\n"
                        % (img_mod_time, date_created))

            # Example output of print(img_obj.info):
            # {'srgb': 0, 'XML:com.adobe.xmp': '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">\n
            # <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n
            # <rdf:Description rdf:about=""\n
            # xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"\n
            # xmlns:exif="http://ns.adobe.com/exif/1.0/">\n
            # <photoshop:DateCreated>2019-08-26T03:51:19</photoshop:DateCreated>\n
            # <exif:UserComment>Screenshot</exif:UserComment>\n
            # </rdf:Description>\n
            # </rdf:RDF>\n</x:xmpmeta>\n'}

        elif img_ext == ".AAE":
            img_obj = open(img, 'r')

            # encoded_exif = getattr(img_obj, '_getexif', lambda: None)()
            for line in img_obj:
                if '<date>' in line:
                    adjustmentTimestamp = line.split("<date>")[1].split("Z</date>")[0]

            print(img + ":\n"
                        "\timg_mod_time: %s"
                        "\tAAE adjustmentTimestamp: %s"
                        % (img_mod_time, adjustmentTimestamp))



#
# from PIL import Image
# from PIL.ExifTags import TAGS
# ret = {}
# i = Image.open('IMG_8559.JPG')
# info = i._getexif()
#
# for tag, value in info.items():
#      decoded = TAGS.get(tag, tag)
#      ret[decoded] = value
#      print(decoded)
#      print(value)
