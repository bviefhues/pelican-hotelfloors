"""
This is a Pelican plugin for reading (JPEG) images as articles. Features:
    - Process *.jpeg and *.jpg files in the content directory tree
    - Extract EXIF information and map to Pelican metadata
    - Replace simple LaTeX style German umlauts encoding (e.g. "u -> ue) with HTML and ASCII representation
      (Since EXIF allows ASCII only)
    - Generate a thumbnail image
    - Inject the image and its thumbnail into Pelican's static file processing, including
      copying to output

Currently supported mapping:

EXIF               Pelican Metadata
----------------------------------------
ImageDescription   title, slug
Artist             author
DateTimeOriginal   date
UserComment        summary, description

TODO
- Support tags
- Support categories
- Smarter summary formatting (cut on word boundaries, ellipsis)
- Config option to specify content sub-tree
- Config option to write thumbs to a cache directory, instead of next to input file
- Config option for thumb size
"""
import logging
import os
import datetime
import sys
import pathlib
import pprint

from PIL import Image
from PIL.ExifTags import TAGS

from pelican import signals
from pelican.readers import BaseReader
from pelican.generators import Generator
from pelican.urlwrappers import URLWrapper, Category, Author, Tag
from pelican.contents import Static

logger = logging.getLogger('ExifReader')
logger.setLevel(logging.DEBUG)

class ExifReader(BaseReader):
    file_extensions = ('jpeg', 'jpg')
    thumb_size = 300, 300*4/3 # iphone aspect ratio

    def __init__(self, settings):
        super(ExifReader, self).__init__(settings)

    def read(self, source_path):
        logger.info('Processing ' + repr(source_path))

        img = Image.open(source_path)

        def expand_umlauts_html(s):
            s = s.replace('"u','&uuml;')
            s = s.replace('"a','&auml;')
            s = s.replace('"o','&ouml;')
            s = s.replace('"U','&Uuml;')
            s = s.replace('"A','&Auml;')
            s = s.replace('"O','&Ouml;')
            s = s.replace('"s','&szlig;')
            return s

        def expand_umlauts_ascii(s):
            s = s.replace('"u','ue')
            s = s.replace('"a','ae')
            s = s.replace('"o','oe')
            s = s.replace('"U','Ue')
            s = s.replace('"A','Ae')
            s = s.replace('"O','Oe')
            s = s.replace('"s','ss')
            return s

        # get EXIF tags
        exif_raw = img._getexif()
        exif_tags = {TAGS.get(tag): value for tag, value in exif_raw.items()}
        title = exif_tags.get('ImageDescription', os.path.basename(source_path))
        try:
            title = title.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
        author = Author(exif_tags.get('Artist', 'Unknown'), self.settings)
        date_string = exif_tags.get('DateTimeOriginal', '')
        if len(date_string):
            date = datetime.datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")
        else:
            date = datetime.datetime.fromtimestamp(os.path.getmtime(source_path)) # if no EXIF date use the file date
        slug = URLWrapper(expand_umlauts_ascii(title), self.settings).slug
        description = exif_tags.get('UserComment', '')
        try:
            description = description.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
        summary = description[:140]
        tags = list()
        title_split = title.split(", ")
        if len(title_split) == 3:
            # assumption: <hoten name>, <city>, <country>
            category = title_split[1]
        else:
            category = "Unknown"
            raise Exception("Unknown for " + title)

        metadata = {
                # Pelican reserved keys
                'title': expand_umlauts_html(title), 
                'date': date, 
                'tags': tags,
                'category': expand_umlauts_html(category),
                'slug': slug,
                'author': author,
                'summary': expand_umlauts_html(summary),
                # Plugin custom keys
                'description': expand_umlauts_html(description),
                'image_url': '',
                'thumb_url': '',
                'exif': exif_tags,
        }
        
        # pprint.pprint(metadata)

        def file_newer(filename, other_filename):
            return os.path.getmtime(filename) > os.path.getmtime(other_filename)

        # generate thumbnail, skip if already there
        filename, ext = os.path.splitext(source_path)
        thumb_save_as = filename + '.thumb'
        if os.path.isfile(thumb_save_as) and file_newer(thumb_save_as, source_path):
            logger.debug(f'Skipping thumb generation for {source_path}')
        else:
            logger.debug(f'Generating thumb for {source_path}')
            img.thumbnail(ExifReader.thumb_size)
            img.save(thumb_save_as, 'JPEG') # .thumb extension to mark as generated
    
        #parsed = {}
        #for key, value in metadata.items():
        #    parsed[key] = self.process_metadata(key, value)
        metadata["category"] = self.process_metadata("category", metadata["category"])

        return description, metadata


def exif_static_content(generator):
    """
    Inject static files into Pelican's static file processing
    Must be connected through signals.static_generator_finalized.connect() to get data at the right time
    into Pelican's processing
    """
    for article in generator.context['articles']:
        if 'exif' not in article.metadata:
            continue #  this article was not processed by ExifReader

        logger.info(f'Registering static content for Relative Source Path: {article.relative_source_path}')
        
        source_name, ext = os.path.splitext(article.relative_source_path)
        
        if ext.lower() == '.jpg' or ext.lower() == '.jpeg':
            ext = '.jpeg' # normalize all JPEG images to same extension
        
        # Hack to generate image and thumb URL and save_as from article
        # Pelican generates a HTML article and adds a .html extension
        # We strip the extension and add our own, to output image and thumb
        # next to the HTML file
        if article.url.endswith('.html'):
            image_url = article.url[:-5] + ext
            image_save_as = article.save_as[:-5] + ext
            thumb_url = article.url[:-5] + '.thumb' + ext
            thumb_save_as = article.save_as[:-5] + '.thumb' + ext
        else:
            logger.warn(f'Do not know how to process article URL {article.url}, skipping')
            continue
        logger.info(f'Image URL: {image_url}, Thumb URL: {thumb_url}')

        # Append image to Pelican static files context
        image_metadata = dict(article.metadata)
        image_metadata['url'] = image_url
        image_metadata['save_as'] = image_save_as
        image = Static('', metadata=image_metadata, source_path=article.relative_source_path, context=generator.context)
        generator.context['staticfiles'].append(image) 
        # add URL to article metadata, so we can access it later in the jinja template
        article.metadata['image_url'] = image_url
        setattr(article, 'image_url', image_url)

        # Append thumb to Pelican static files context
        thumb_metadata = dict(article.metadata)
        thumb_metadata['url'] = thumb_url
        thumb_metadata['save_as'] = thumb_save_as
        thumb = Static('', metadata=thumb_metadata, source_path=source_name+'.thumb', context=generator.context)
        generator.context['staticfiles'].append(thumb) 
        # add URL to article metadata, so we can access it later in the jinja template
        article.metadata['thumb_url'] = thumb_url
        setattr(article, 'thumb_url', thumb_url)


def add_reader(readers):
    readers.reader_classes['exif_reader'] = ExifReader

def register():
    signals.readers_init.connect(add_reader)
    signals.static_generator_finalized.connect(exif_static_content)
