import logging

from babelfish import Language
from guessit import guessit
import requests
import zipfile
import io
import os
from collections import namedtuple

from . import Provider
from .. import __short_version__
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_ending, guess_matches
from ..video import Episode, Movie

_SERVER_API_URL = "http://api.screwzira.com/"
_CLIENT_API_VERSION = "1.0"

SCREWZIRA_OPERATION_FIND_FILM = "FindFilm"
SCREWZIRA_OPERATION_FIND_SERIES = "FindSeries"
SCREWZIRA_OPERATION_DOWNLOAD = "Download"

SCREWZIRA_SEARCH_TYPE_FILM_NAME = "FilmName"
SCREWZIRA_SEARCH_TYPE_SUBTITILE = "Subtitle"
SCREWZIRA_SEARCH_TYPE_IMDB_ID = "ImdbID"

logger = logging.getLogger(__name__)


ScrewZiraSubtitleResult = namedtuple("ScrewZiraSubtitleResult", ["name", "id"])


class ScrewZiraResponseError(ProviderError):
    pass


def _validate_operation_name(operation):

    if operation not in [SCREWZIRA_OPERATION_FIND_FILM,
                         SCREWZIRA_OPERATION_FIND_SERIES,
                         SCREWZIRA_OPERATION_DOWNLOAD]:
        raise ValueError("Unsupported operation: {0}".format(operation))


def _validate_search_type(search_type):

    if search_type not in [SCREWZIRA_SEARCH_TYPE_FILM_NAME,
                           SCREWZIRA_SEARCH_TYPE_SUBTITILE,
                           SCREWZIRA_SEARCH_TYPE_IMDB_ID]:
        raise ValueError("Unsupported search type: {0}".format(search_type))


def _extract_content_disposition_file_name(content_disposition):

    return content_disposition.repleace("attachment; filename=", "")


def _get_screwzira_json_response(response):

    json_response = response.json()
    if not json_response['IsSuccess']:
        raise ScrewZiraResponseError(json_response['ErrorMessage'])

    return json_response['Results']


def _parse_subtitle_result(results):

    return [ScrewZiraSubtitleResult(r['SubtitleName'], r['Identifier']) for r in results]


class ScrewZiraSession(object):

    def __init__(self, user_agent):

        self._session = requests.Session()
        self._session.headers['User-Agent'] = user_agent

    def close(self):

        self._session.close()
        self._session = None

    def _ensure_valid_state(self):

        if self._session is None:
            raise RuntimeError(
                "Can't perform a request after close was called")

    def _request(self, operation, **kwargs):

        self._ensure_valid_state()
        _validate_operation_name(operation)

        request_obj = {"Version": _CLIENT_API_VERSION}
        request_obj.extend(**kwargs)

        response = session.post("{0}{1}".format(
            _SERVER_API_URL, operation), json=request_obj)
        response.raise_for_status()

        return response

    def _find_film(self, search_type, search_phrase, year=None):

        self._ensure_valid_state()
        _validate_search_type(search_type)

        args = dict(SearchType=search_type, SearchPhrase=search_phrase)
        if year is not None:
            args['Year'] = year

        response = self._request(SCREWZIRA_OPERATION_FIND_FILM, **args)

        return _parse_subtitle_result(_get_screwzira_json_response(response))

    def _find_series(self, search_type, search_phrase, season, episode, year=None):

        self._ensure_valid_state()
        _validate_search_type(search_type)
        args = dict(SearchType=search_type, SearchPhrase=search_phrase,
                    Season=season, Episode=episode)
        if year is not None:
            args['Year'] = year

        response = self._request(SCREWZIRA_OPERATION_FIND_SERIES, **args)

        return _parse_subtitle_result(_get_screwzira_json_response(response))

    def find_movie_by_name(self, name, year=None):

        return self._find_film(SCREWZIRA_SEARCH_TYPE_FILM_NAME, name, year)

    def find_movie_by_file_name(self, file_name, year=None):

        return self._find_film(SCREWZIRA_SEARCH_TYPE_SUBTITILE, file_name, year)

    def find_movie_by_imdb_id(self, imdb_id, year=None):

        return self._find_film(SCREWZIRA_SEARCH_TYPE_IMDB_ID, imdb_id, year)

    def find_series_by_name(self, series_name, season, episode, year=None):

        return self._find_series(SCREWZIRA_SEARCH_TYPE_FILM_NAME, series_name, season, episode, year)

    def find_series_by_file_name(self, file_name, season, episode, year=None):

        return self._find_series(SCREWZIRA_SEARCH_TYPE_SUBTITILE, file_name, season, episode, year)

    def find_series_by_imdb_id(self, imdb_id, season, episode, year=None):

        return self._find_series(SCREWZIRA_SEARCH_TYPE_IMDB_ID, imdb_id, season, episode, year)

    def download(self, subtitle_id):

        response = self._request(
            SCREWZIRA_OPERATION_DOWNLOAD, SubtitleID=subtitle_id)

        if response.header['Content-Length'] == 0:
            raise ScrewZiraResponseError(_extract_content_disposition_file_name(
                response.headeres['Content-Disposition']))

        return io.BytesIO(response.content)


class ScrewZiraSubtitle(Subtitle):

    provide_name = "screwzira"

    def __init__(self, subtitle_name, subtitle_id, imdb_id=None, video_name=None):

        self._id = subtitle_id
        self._subtitle_name = subtitle_name
        self._imdb_id = imdb_id
        self._video_name = video_name

    @property
    def id(self):
        return self._id

    def get_matches(self, video):

        matches = set()

        if isinstance(video, Episode):
            matches |= guess_matches(video, guessit(
                self._name, {'type': 'episode'}))
        elif isinstance(video, Movie):
            matches |= guess_matches(video, guessit(
                self._name, {'type': 'movie'}))
        else:
            logger.warning("Got video of unexpected type")

        # if video.imdb_id and self._imdb_id == video.imdb_id:
        #     matches.add("imdb_id")

        return matches


def _convert_screwzira_session_subtitle_result(subtitles, imdb_id=None, video_name=None):

    return [ScrewZiraSubtitle(s.name, s.id, imdb_id, video_name) for s in subtitles]


class ScrewZiraProvider(Provider):

    languages = {Language(l) for l in ['heb']}

    def __init__(self):

        self._session = None

     def initialize(self):

        self._session = ScrewZiraSession('Subliminal/{}'.format(__short_version__))

    def terminate(self):

        self._session.close()

    def _query_movies_by_imdb_id(self, imdb_id, year=None):
        pass

    def _query_movies_by_name(self, movie_name, year=None):
        pass

    def _query_movies_by_file_name(self, file_name, year=None):
        pass

    def _query_series_by_imdb_id(self, imdb_id, season, episode, year=None):
        pass

    def _query_series_by_name(self, series_name, season, episode, year=None):
        pass

    def _query_series_by_file_name(self, file_name, season, episode, year=None):
        pass

    def list_subtitles(self, video, languages):

        if isinstance(video, Episode):
            pass
        elif isinstance(video, Movie):
            pass
        else:
            pass

    def download_subtitle(self, subtitle):

        raise NotImplementedError()
