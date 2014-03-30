""":mod:`geofront.backends.github` --- GitHub organization and key store
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import collections
import contextlib
import io
import json
import logging
import urllib.request

from werkzeug.http import parse_options_header
from werkzeug.urls import url_encode, url_decode_stream
from werkzeug.wrappers import Request

from ..identity import Identity
from ..team import AuthenticationError, Team
from ..util import typed


__all__ = {'GitHubOrganization', 'request'}


def request(access_token, url: str, method: str='GET'):
    """Make a request to GitHub API, and then return the parsed JSON result.

    :param access_token: api access token string,
                         or :class:`~geofront.identity.Identity` instance
    :type access_token: :class:`str`, :class:`~geofront.identity.Identity`
    :param url: the api url to request
    :type url: :class:`str`
    :param method: an optional http method.  ``'GET'`` by default
    :type method: :class:`str`

    """
    if isinstance(access_token, Identity):
        access_token = access_token.access_token
    req = urllib.request.Request(
        url,
        headers={
            'Authorization': 'token ' + access_token,
            'Accept': 'application/json'
        },
        method=method
    )
    with contextlib.closing(urllib.request.urlopen(req)) as response:
        content_type = response.headers['Content-Type']
        mimetype, options = parse_options_header(content_type)
        assert mimetype == 'application/json', \
            'Content-Type of {} is not application/json but {}'.format(
                url,
                content_type
            )
        charset = options.get('charset')
        io_wrapper = io.TextIOWrapper(response, encoding=charset)
        logger = logging.getLogger(__name__ + '.request')
        if logger.isEnabledFor(logging.DEBUG):
            read = io_wrapper.read()
            logger.debug(
                'HTTP/%d.%d %d %s\n%s\n\n%s',
                response.version // 10,
                response.version % 10,
                response.status,
                response.reason,
                '\n'.join('{}: {}'.format(k, v)
                          for k, v in response.headers.items()),
                read
            )
            return json.loads(read)
        else:
            return json.load(io_wrapper)


class GitHubOrganization(Team):
    """Authenticate team membership through GitHub, and authorize to
    access GitHub key store.

    """

    AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'
    USER_URL = 'https://api.github.com/user'
    ORGS_LIST_URL = 'https://api.github.com/user/orgs'

    @typed
    def __init__(self, client_id: str, client_secret: str, org_login: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.org_login = org_login

    @typed
    def request_authentication(self, auth_nonce: str, redirect_url: str) -> str:
        query = url_encode({
            'client_id': self.client_id,
            'redirect_uri': redirect_url,
            'scope': 'read:org,admin:public_key',
            'state': auth_nonce
        })
        authorize_url = '{}?{}'.format(self.AUTHORIZE_URL, query)
        return authorize_url

    @typed
    def authenticate(self,
                     auth_nonce: str,
                     requested_redirect_url: str,
                     wsgi_environ: dict) -> Identity:
        req = Request(wsgi_environ, populate_request=False, shallow=True)
        try:
            code = req.args['code']
            if req.args['state'] != auth_nonce:
                raise AuthenticationError()
        except KeyError:
            raise AuthenticationError()
        data = url_encode({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': requested_redirect_url
        }).encode()
        response = urllib.request.urlopen(self.ACCESS_TOKEN_URL, data)
        content_type = response.headers['Content-Type']
        mimetype, options = parse_options_header(content_type)
        if mimetype == 'application/x-www-form-urlencoded':
            token_data = url_decode_stream(response)
        elif mimetype == 'application/json':
            charset = options.get('charset')
            token_data = json.load(io.TextIOWrapper(response, encoding=charset))
        else:
            response.close()
            raise AuthenticationError(
                '{} sent unsupported content type: {}'.format(
                    self.ACCESS_TOKEN_URL,
                    content_type
                )
            )
        response.close()
        user_data = request(token_data['access_token'], self.USER_URL)
        identity = Identity(
            type(self),
            user_data['login'],
            token_data['access_token']
        )
        if self.authorize(identity):
            return identity
        raise AuthenticationError(
            '@{} user is not a member of @{} organization'.format(
                user_data['login'],
                self.org_login
            )
        )

    def authorize(self, identity: Identity) -> bool:
        if not issubclass(identity.team_type, type(self)):
            return False
        try:
            response = request(identity, self.ORGS_LIST_URL)
        except IOError:
            return False
        if isinstance(response, collections.Mapping) and 'error' in response:
            return False
        return any(o['login'] == self.org_login for o in response)