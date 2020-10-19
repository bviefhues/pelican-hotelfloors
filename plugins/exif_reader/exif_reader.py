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
        author = Author(exif_tags.get('Artist', 'Unknown'), self.settings)
        date_string = exif_tags.get('DateTimeOriginal', '')
        if len(date_string):
            date = datetime.datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")
        else:
            date = datetime.datetime.now()
        slug = URLWrapper(expand_umlauts_ascii(title), self.settings).slug
        description = exif_tags.get('UserComment', '')
        summary = description[:140]
        tags = list()

        metadata = {
                # Pelican reserved keys
                'title': expand_umlauts_html(title), 
                'date': date, 
                'tags': tags,
                # 'category': None,
                'slug': slug,
                'author': author,
                'summary': expand_umlauts_html(summary),
                # Plugin custom keys
                'description': expand_umlauts_html(description),
                'image_url': '',
                'thumb_url': '',
                'exif': exif_tags,
        }
        
        def file_newer(filename, other_filename):
            return os.path.getmtime(filename) > os.path.getmtime(other_filename)

        # generate thumbnail
        filename, ext = os.path.splitext(source_path)
        thumb_save_as = filename + '.thumb'
        if os.path.isfile(thumb_save_as) and file_newer(thumb_save_as, source_path):
            logger.debug(f'Skipping thumb generation for {source_path}')
        else:
            logger.debug(f'Generating thumb for {source_path}')
            img.thumbnail(ExifReader.thumb_size)
            img.save(thumb_save_as, 'JPEG') # .thumb extension to mark as generated

        return description, metadata


def exif_static_content(generator):
    for article in generator.context['articles']:
        if 'exif' not in article.metadata:
            continue

        logger.info(f'Registering static content for Relative Source Path: {article.relative_source_path}')
        
        source_name, ext = os.path.splitext(article.relative_source_path)
        
        if ext.lower() == '.jpg':
            ext = '.jpeg'
        if ext.lower() == '.jpeg' and ext != '.jpeg':
            ext = '.jpeg'
        
        if article.url.endswith('.html'):
            image_url = article.url[:-5] + ext
            image_save_as = article.save_as[:-5] + ext
            thumb_url = article.url[:-5] + '.thumb' + ext
            thumb_save_as = article.save_as[:-5] + '.thumb' + ext
        else:
            image_url = article.url + image_ext 
            image_save_as = article.save_as + image_ext
            thumb_url = article.url + '.thumb' + image_ext 
            thumb_save_as = article.save_as + '.thumb' + image_ext
        logger.info(f'Image URL: {image_url}, Thumb URL: {thumb_url}')

        image_metadata = dict(article.metadata)
        image_metadata['url'] = image_url
        image_metadata['save_as'] = image_save_as
        image = Static('', metadata=image_metadata, source_path=article.relative_source_path, context=generator.context)
        generator.context['staticfiles'].append(image) 
        article.metadata['image_url'] = image_url
        setattr(article, 'image_url', image_url)

        thumb_metadata = dict(article.metadata)
        thumb_metadata['url'] = thumb_url
        thumb_metadata['save_as'] = thumb_save_as
        thumb = Static('', metadata=thumb_metadata, source_path=source_name+'.thumb', context=generator.context)
        generator.context['staticfiles'].append(thumb) 
        article.metadata['thumb_url'] = thumb_url
        setattr(article, 'thumb_url', thumb_url)


def add_reader(readers):
    readers.reader_classes['exif_reader'] = ExifReader

def get_generator(pelican_object):
    return ExifGenerator

def register():
    signals.readers_init.connect(add_reader)
    #signals.get_generators.connect(get_generator)
    #signals.article_generator_finalized.connect(exif_static_content)
    signals.static_generator_finalized.connect(exif_static_content)
