import pytest
import os
from vcr import VCR
from babelfish import Language

from subliminal.providers.screwzira import ScrewZiraProvider, ScrewZiraSubtitle

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host',
                    'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'screwzira'))

@pytest.mark.integration
# @vcr.use_cassette
def test_list_subtitle_episode(episodes):
    pass

# 
# @pytest.mark.integration
# @vcr.use_cassette
# def test_list_subtitle_movie(movies):
#     pass
# 
# @pytest.mark.integration
# @vcr.use_cassette
# def test_download_subtitle(movies):
#     pass