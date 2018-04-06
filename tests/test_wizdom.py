import pytest
import os
from vcr import VCR
from babelfish import Language

from subliminal.providers.wizdom import WizdomProvider, WizdomSubtitle

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host',
                    'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'wizdom'))


def test_get_matches_no_match(episodes):

    subtitle = WizdomSubtitle("tt0944947", dict(versioname="Game.of.Thrones.S07E07.720p.WEB.H264-STRiFE",
                                                id="190027", score=3))
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitle_episode(episodes):

    languages = {Language('heb')}
    expected_subtitles = {"166995", "4232", "3748", "40068",
                          "39541", "4231", "46192", "71362",
                          "40067", "61901"}

    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(episodes['got_s03e10'], languages)

    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):

    languages = {Language('heb')}
    expected_subtitles = {"77724", "24384", "24382", "24368",
                          "24355", "24386", "24372", "24396",
                          "24394", "24404", "24351", "24378",
                          "185106", "24402", "24366", "24400",
                          "24405", "95805", "62797", "134088",
                          "155340", "62796", "24359", "24398",
                          "66283", "24370", "114837", "75722",
                          "90978", "24380", "24390", "24363",
                          "24374", "134091", "24361", "24408",
                          "64634", "134085", "24388", "24357",
                          "24392", "24353", "24376", "24410"}

    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(movies['man_of_steel'], languages)

    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):

    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(
            movies['man_of_steel'], {Language('heb')})
        provider.download_subtitle(subtitles[0])

    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True